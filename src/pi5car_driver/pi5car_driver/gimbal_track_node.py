import rclpy
from rclpy.node import Node
from std_msgs.msg import String, Float32MultiArray, Float32
import json


class GimbalTrackNode(Node):
    def __init__(self):
        super().__init__('gimbal_track_node')

        self.img_w = 640
        self.img_h = 480

        self.pan = 0.0
        self.tilt = 10.0        # 水平基准
        self.pan_limit = 60.0
        self.tilt_limit = 25.0  # 低头极限
        self.tilt_min = -20.0   # 仰头极限
        self.deadzone = 60
        self.step = 5.0
        self.conf_threshold = 0.3

        # 超声波距离（cm），默认远距离
        self.ultrasonic_dist = 300.0

        # 订阅 YOLO 检测结果
        self.sub_yolo = self.create_subscription(
            String, '/vision/detections', self.detection_callback, 10)

        # 订阅超声波距离
        self.sub_ultrasonic = self.create_subscription(
            Float32, '/ultrasonic/distance', self.ultrasonic_callback, 10)

        # 订阅归中指令（person_follow_node 在车身旋转时发出）
        self.sub_recenter = self.create_subscription(
            String, '/follow/gimbal_recenter', self.recenter_callback, 10)

        # 发布云台指令
        self.pub_gimbal = self.create_publisher(
            Float32MultiArray, '/gimbal/cmd', 10)

        # 发布当前 pan 角度（供 person_follow_node 判断是否需要旋转车身）
        self.pub_pan = self.create_publisher(
            Float32, '/follow/pan_angle', 10)

        # 定时根据超声波更新 tilt（每 200ms）
        self.create_timer(0.2, self.update_tilt_timer)

        # 启动时归中
        self.create_timer(0.5, self.send_initial_position)
        self._init_sent = False

        self.get_logger().info('gimbal_track_node started (ultrasonic tilt mode)')

    def send_initial_position(self):
        if not self._init_sent:
            cmd = Float32MultiArray()
            cmd.data = [self.pan, self.tilt]
            self.pub_gimbal.publish(cmd)
            self._init_sent = True
            self.get_logger().info(f'Initial position: pan={self.pan}, tilt={self.tilt}')

    def ultrasonic_callback(self, msg):
        self.ultrasonic_dist = msg.data

    def recenter_callback(self, msg):
        """收到归中指令：重置 pan，云台回到水平"""
        self.pan = 0.0
        self.tilt = 10.0
        cmd = Float32MultiArray()
        cmd.data = [self.pan, self.tilt]
        self.pub_gimbal.publish(cmd)
        self.get_logger().info('Gimbal recentered (pan=0, tilt=10)')

    def tilt_from_distance(self, dist_cm):
        """根据超声波距离计算目标 tilt（线性插值）
        >200cm  → tilt=+10（水平，看全身）
        100-200 → tilt=+5 （微抬）
        60-100  → tilt=0  （抬头，看腰以上）
        <60cm   → tilt=-15（大幅抬头，看脸/胸）
        """
        if dist_cm > 200:
            return 10.0
        elif dist_cm > 100:
            # 200→+10, 100→+5，线性
            return 5.0 + (dist_cm - 100) / 100.0 * 5.0
        elif dist_cm > 60:
            # 100→+5, 60→0，线性
            return 0.0 + (dist_cm - 60) / 40.0 * 5.0
        else:
            return -15.0

    def update_tilt_timer(self):
        """定时根据超声波距离更新 tilt。
        注意：超声波固定在车身，只有 pan 角度较小时方向才对齐。
        """
        # 发布当前 pan 角度（每次都发，保持 person_follow_node 数据新鲜）
        pan_msg = Float32()
        pan_msg.data = self.pan
        self.pub_pan.publish(pan_msg)

        # 超声波有效区间：pan < ±15°
        if abs(self.pan) >= 15.0:
            return

        target_tilt = self.tilt_from_distance(self.ultrasonic_dist)

        # 平滑跟随：每次最多移动一步，避免抖动
        if abs(target_tilt - self.tilt) > 2.0:
            if target_tilt > self.tilt:
                self.tilt = min(self.tilt_limit, self.tilt + self.step)
            else:
                self.tilt = max(self.tilt_min, self.tilt - self.step)

            cmd = Float32MultiArray()
            cmd.data = [self.pan, self.tilt]
            self.pub_gimbal.publish(cmd)
            self.get_logger().info(
                f'Tilt updated: dist={self.ultrasonic_dist:.0f}cm → tilt={self.tilt:.1f}')

    def detection_callback(self, msg):
        try:
            detections = json.loads(msg.data)
        except Exception:
            return

        persons = [d for d in detections
                   if d['class'] == 'person' and d['confidence'] >= self.conf_threshold]

        if not persons:
            return

        target = max(persons, key=lambda d: d['confidence'])
        cx = target['center'][0]

        img_cx = self.img_w // 2
        offset_x = cx - img_cx

        changed = False

        # pan 跟踪：人在右边 → 云台右转（pan 减小）
        if offset_x > self.deadzone:
            self.pan = max(-self.pan_limit, self.pan - self.step)
            changed = True
        elif offset_x < -self.deadzone:
            self.pan = min(self.pan_limit, self.pan + self.step)
            changed = True

        # 注意：tilt 由超声波定时器驱动，不再用 bbox center_y

        if changed:
            cmd = Float32MultiArray()
            cmd.data = [self.pan, self.tilt]
            self.pub_gimbal.publish(cmd)
            self.get_logger().info(
                f'Pan track: pan={self.pan:.1f}, tilt={self.tilt:.1f}, offset_x={offset_x}')


def main(args=None):
    rclpy.init(args=args)
    node = GimbalTrackNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
