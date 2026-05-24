import rclpy
from rclpy.node import Node
from std_msgs.msg import String, Float32MultiArray
import json


class GimbalTrackNode(Node):
    def __init__(self):
        super().__init__('gimbal_track_node')

        self.img_w = 640
        self.img_h = 480

        self.pan = 0.0
        self.tilt = 10.0    # +30 = 水平，0 = 仰头，更正 = 低头
        self.pan_limit = 60.0
        self.tilt_limit = 25.0
        self.tilt_min = -20.0
        self.deadzone = 60
        self.step = 5.0
        self.conf_threshold = 0.3

        self.sub = self.create_subscription(
            String, '/vision/detections', self.detection_callback, 10)

        self.pub_gimbal = self.create_publisher(
            Float32MultiArray, '/gimbal/cmd', 10)

        # 启动时立即归中到水平位置
        self.create_timer(0.5, self.send_initial_position)
        self._init_sent = False

        self.get_logger().info('gimbal_track_node started, centering to tilt=+30')

    def send_initial_position(self):
        if not self._init_sent:
            cmd = Float32MultiArray()
            cmd.data = [self.pan, self.tilt]
            self.pub_gimbal.publish(cmd)
            self._init_sent = True
            self.get_logger().info(f'Initial position sent: pan={self.pan}, tilt={self.tilt}')

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
        cy = target['center'][1]

        img_cx = self.img_w // 2
        img_cy = self.img_h // 2

        offset_x = cx - img_cx
        offset_y = cy - img_cy

        changed = False

        # 人在右边 → 云台右转（pan 减小）
        if offset_x > self.deadzone:
            self.pan = max(-self.pan_limit, self.pan - self.step)
            changed = True
        elif offset_x < -self.deadzone:
            self.pan = min(self.pan_limit, self.pan + self.step)
            changed = True

        # 人在上方（offset_y < 0）→ 云台仰起（tilt 减小，更负=朝上）
        # 人在下方（offset_y > 0）→ 云台低头（tilt 增大，更正=朝下）
        if offset_y < -self.deadzone:
            self.tilt = max(self.tilt_min, self.tilt - self.step)
            changed = True
        elif offset_y > self.deadzone:
            self.tilt = min(self.tilt_limit, self.tilt + self.step)
            changed = True

        if changed:
            cmd = Float32MultiArray()
            cmd.data = [self.pan, self.tilt]
            self.pub_gimbal.publish(cmd)
            self.get_logger().info(
                f'Gimbal: pan={self.pan:.1f}, tilt={self.tilt:.1f}, '
                f'offset=({offset_x},{offset_y})')


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
