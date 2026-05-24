import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
import cv2
from cv_bridge import CvBridge

class CameraNode(Node):
    def __init__(self):
        super().__init__('camera_node')
        self.pub = self.create_publisher(Image, '/camera/image_raw', 10)
        self.bridge = CvBridge()
        self.cap = cv2.VideoCapture(0)
        if not self.cap.isOpened():
            self.get_logger().error('Cannot open camera /dev/video0')
            return
        self.create_timer(0.1, self.timer_cb)
        self.get_logger().info('Camera node started (/dev/video0)')

    def timer_cb(self):
        ret, frame = self.cap.read()
        if not ret:
            self.get_logger().warn('Failed to read frame')
            return
        frame = cv2.rotate(frame, cv2.ROTATE_90_COUNTERCLOCKWISE)
        msg = self.bridge.cv2_to_imgmsg(frame, encoding='bgr8')
        self.pub.publish(msg)
        self.get_logger().info(f'Frame published: {frame.shape}')

    def destroy_node(self):
        self.cap.release()
        super().destroy_node()

def main():
    rclpy.init()
    node = CameraNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()
