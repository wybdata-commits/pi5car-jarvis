import rclpy
from rclpy.node import Node
from std_msgs.msg import String
from geometry_msgs.msg import Twist
import json


class PersonFollowNode(Node):
    def __init__(self):
        super().__init__('person_follow_node')

        # 图像宽高（camera_node 发布 480×640）
        self.img_w = 640
        self.img_h = 480

        # 跟随参数
        self.target_area = 80000    # 目标 bbox 面积（像素²），小于此值则前进
        self.stop_area = 150000      # 面积超过此值则后退（太近了）
        self.center_deadzone = 80   # 水平偏移死区（像素），在此范围内不转向
        self.linear_speed = 0.3     # 前进速度
        self.angular_speed = 0.4    # 转向速度
        self.conf_threshold = 0.3   # 最低置信度

        self.enabled = False        # 默认关闭，等待指令激活

        # 订阅检测结果
        self.sub = self.create_subscription(
            String, '/vision/detections', self.detection_callback, 10)

        # 订阅激活指令（brain_node 发 "start"/"stop"）
        self.sub_cmd = self.create_subscription(
            String, '/person_follow/cmd', self.cmd_callback, 10)

        # 发布运动指令
        self.pub_vel = self.create_publisher(Twist, '/cmd_vel', 10)

        self.get_logger().info('person_follow_node started (default: disabled)')

    def cmd_callback(self, msg):
        if msg.data == 'start':
            self.enabled = True
            self.get_logger().info('Person following ENABLED')
        elif msg.data == 'stop':
            self.enabled = False
            self.stop_robot()
            self.get_logger().info('Person following DISABLED')

    def detection_callback(self, msg):
        if not self.enabled:
            return

        try:
            detections = json.loads(msg.data)
        except Exception:
            return

        # 找置信度最高的 person
        persons = [d for d in detections
                   if d['class'] == 'person' and d['confidence'] >= self.conf_threshold]

        if not persons:
            self.stop_robot()
            return

        target = max(persons, key=lambda d: d['confidence'])
        cx = target['center'][0]
        area = target['area']

        twist = Twist()
        img_center_x = self.img_w // 2
        offset_x = cx - img_center_x

        # 左右转向
        if offset_x > self.center_deadzone:
            twist.angular.z = -self.angular_speed   # 右转
        elif offset_x < -self.center_deadzone:
            twist.angular.z = self.angular_speed    # 左转

        # 前进/后退
        if area < self.target_area:
            twist.linear.x = self.linear_speed      # 前进
        elif area > self.stop_area:  # too close, just stop
            twist.linear.x = 0.0                    # 太近，停住不后退
        # else: 停在原地，只转向

        self.pub_vel.publish(twist)
        self.get_logger().info(
            f'Follow: area={area}, offset={offset_x}, '
            f'linear={twist.linear.x:.1f}, angular={twist.angular.z:.1f}'
        )

    def stop_robot(self):
        twist = Twist()
        self.pub_vel.publish(twist)


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
