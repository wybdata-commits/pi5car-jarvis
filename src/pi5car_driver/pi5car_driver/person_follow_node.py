import rclpy
from rclpy.node import Node
from std_msgs.msg import String, Float32, Float32MultiArray
from geometry_msgs.msg import Twist
import json


# ── 状态定义 ──────────────────────────────────────────
IDLE        = 'IDLE'        # 待机，等待指令
DETECTING   = 'DETECTING'   # 搜索中：超声波有物体，等 YOLO 确认
LOCKED      = 'LOCKED'      # 锁定跟随中
REACQUIRING = 'REACQUIRING' # 短暂丢失，保持惯性
LOST        = 'LOST'        # 彻底丢失，停车重新扫描
# ─────────────────────────────────────────────────────


class PersonFollowNode(Node):
    def __init__(self):
        super().__init__('person_follow_node')

        # 图像参数
        self.img_w = 640
        self.img_h = 480

        # 跟随参数
        self.target_area   = 80000   # 小于此面积 → 前进
        self.stop_area     = 150000  # 大于此面积 → 停（太近）
        self.center_dz     = 80      # 水平死区（px）
        self.linear_speed  = 0.3
        self.angular_speed = 0.4
        self.conf_threshold = 0.3

        # ── 状态机 ──
        self.state = IDLE
        self.last_seen_time  = None   # 最后一次看到人的时刻
        self.grace_period    = 1.0    # REACQUIRING → LOST 等待时间（秒）
        self.last_twist      = Twist() # 惯性用：最后执行的运动指令

        # ── 传感器数据 ──
        self.ultrasonic_dist      = 300.0   # cm
        self.ultrasonic_trigger   = 150.0   # cm，触发 DETECTING
        self.current_pan          = 0.0     # 来自 gimbal_track_node
        self.pan_rotate_threshold = 25.0    # 超过此角度旋转车身

        # ── 订阅 ──
        self.sub_yolo = self.create_subscription(
            String, '/vision/detections', self.detection_callback, 10)
        self.sub_cmd = self.create_subscription(
            String, '/person_follow/cmd', self.cmd_callback, 10)
        self.sub_ult = self.create_subscription(
            Float32, '/ultrasonic/distance', self.ultrasonic_callback, 10)
        self.sub_pan = self.create_subscription(
            Float32, '/follow/pan_angle', self.pan_callback, 10)

        # ── 发布 ──
        self.pub_vel    = self.create_publisher(Twist,  '/cmd_vel', 10)
        self.pub_state  = self.create_publisher(String, '/follow/state', 10)
        self.pub_recenter = self.create_publisher(
            String, '/follow/gimbal_recenter', 10)

        # 状态机定时器（100ms）
        self.create_timer(0.1, self.state_machine_tick)

        self.get_logger().info('person_follow_node started (state machine v2)')

    # ── 回调：外部指令 ─────────────────────────────────
    def cmd_callback(self, msg):
        if msg.data == 'start':
            self._transition(DETECTING)
            self.get_logger().info('CMD start → DETECTING')
        elif msg.data == 'stop':
            self._transition(IDLE)
            self.get_logger().info('CMD stop → IDLE')

    def ultrasonic_callback(self, msg):
        self.ultrasonic_dist = msg.data

    def pan_callback(self, msg):
        self.current_pan = msg.data

    # ── 回调：YOLO 检测结果 ────────────────────────────
    def detection_callback(self, msg):
        if self.state == IDLE:
            return

        try:
            detections = json.loads(msg.data)
        except Exception:
            return

        persons = [d for d in detections
                   if d['class'] == 'person'
                   and d['confidence'] >= self.conf_threshold]

        if persons:
            target = max(persons, key=lambda d: d['confidence'])
            cx   = target['center'][0]
            area = target['area']
            self.last_seen_time = self.get_clock().now()

            # 任何非 LOCKED 状态看到人都升级为 LOCKED
            if self.state in (DETECTING, REACQUIRING):
                self._transition(LOCKED)

            if self.state == LOCKED:
                self._do_follow(cx, area)
        else:
            # 没检测到人
            if self.state == LOCKED:
                self._transition(REACQUIRING)

    # ── 跟随运动逻辑 ───────────────────────────────────
    def _do_follow(self, cx, area):
        twist = Twist()
        offset_x = cx - (self.img_w // 2)

        # pan 超限 → 旋转车身，让摄像头重新正对人
        if abs(self.current_pan) > self.pan_rotate_threshold:
            # pan 为正 → 云台偏左（人在左） → 车身左转
            twist.angular.z = (self.angular_speed
                               if self.current_pan > 0
                               else -self.angular_speed)
            self.pub_vel.publish(twist)
            self.last_twist = twist

            # 通知 gimbal 归中
            self.pub_recenter.publish(String(data='recenter'))
            self.get_logger().info(
                f'[LOCKED] pan={self.current_pan:.1f}° > {self.pan_rotate_threshold}°, '
                f'rotating body + recenter gimbal')
            return

        # 正常跟随
        if offset_x > self.center_dz:
            twist.angular.z = -self.angular_speed   # 右转
        elif offset_x < -self.center_dz:
            twist.angular.z = self.angular_speed    # 左转

        if area < self.target_area:
            twist.linear.x = self.linear_speed      # 前进
        elif area > self.stop_area:
            twist.linear.x = 0.0                    # 太近，停

        self.pub_vel.publish(twist)
        self.last_twist = twist
        self.get_logger().info(
            f'[LOCKED] area={area} offset={offset_x:+d} '
            f'lin={twist.linear.x:.1f} ang={twist.angular.z:.1f}')

    # ── 状态机定时器 ───────────────────────────────────
    def state_machine_tick(self):
        now = self.get_clock().now()

        # 发布当前状态（供调试）
        self.pub_state.publish(String(data=self.state))

        if self.state == IDLE:
            pass  # 等待 start 指令

        elif self.state == DETECTING:
            # 超声波无物体 → 慢速旋转扫描
            if self.ultrasonic_dist > self.ultrasonic_trigger:
                t = Twist()
                t.angular.z = 0.2
                self.pub_vel.publish(t)
            else:
                # 有物体靠近，原地等待 YOLO 确认，停止旋转
                self._stop_robot()

        elif self.state == REACQUIRING:
            if self.last_seen_time is not None:
                elapsed = (now - self.last_seen_time).nanoseconds / 1e9
                if elapsed > self.grace_period:
                    self._transition(LOST)
                else:
                    # 惯性：半速保持最后运动方向
                    t = Twist()
                    t.linear.x  = self.last_twist.linear.x  * 0.5
                    t.angular.z = self.last_twist.angular.z * 0.5
                    self.pub_vel.publish(t)
                    self.get_logger().debug(
                        f'[REACQUIRING] inertia {elapsed:.2f}s/{self.grace_period}s')

        elif self.state == LOST:
            self._stop_robot()
            # 立即重新进入扫描
            self._transition(DETECTING)

    # ── 状态转换 ───────────────────────────────────────
    def _transition(self, new_state):
        if self.state == new_state:
            return
        self.get_logger().info(f'★ State: {self.state} → {new_state}')
        self.state = new_state

        if new_state == IDLE:
            self._stop_robot()
        elif new_state == DETECTING:
            # 云台归中，扩大视野
            self.pub_recenter.publish(String(data='recenter'))
        elif new_state == LOCKED:
            pass
        elif new_state == REACQUIRING:
            pass   # last_seen_time 已在 detection_callback 更新
        elif new_state == LOST:
            self._stop_robot()

    def _stop_robot(self):
        self.pub_vel.publish(Twist())


def main(args=None):
    rclpy.init(args=args)
    node = PersonFollowNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
