import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from std_msgs.msg import String
from cv_bridge import CvBridge
import anthropic
import base64
import cv2
import os

class VisionNode(Node):
    def __init__(self):
        super().__init__('vision_node')
        self.bridge = CvBridge()
        self.latest_frame = None
        self.client = anthropic.Anthropic(api_key=os.environ.get('ANTHROPIC_API_KEY'))

        self.create_subscription(Image, '/camera/image_raw', self.image_cb, 10)
        self.create_subscription(String, '/vision/query', self.query_cb, 10)
        self.desc_pub = self.create_publisher(String, '/vision/description', 10)
        self.tts_pub  = self.create_publisher(String, '/tts/say', 10)

        self.get_logger().info('Vision node started — waiting for queries on /vision/query')

    def image_cb(self, msg):
        self.latest_frame = msg

    def query_cb(self, msg):
        if self.latest_frame is None:
            self.get_logger().warn('No camera frame yet')
            return

        query = msg.data
        self.get_logger().info(f'Query received: {query}')

        cv_image = self.bridge.imgmsg_to_cv2(self.latest_frame, 'bgr8')
        _, buffer = cv2.imencode('.jpg', cv_image)
        image_b64 = base64.b64encode(buffer).decode('utf-8')

        try:
            response = self.client.messages.create(
                model='claude-haiku-4-5',
                max_tokens=150,
                system='你是 ARIA，一个有温度的家庭机器人助手。用简短、口语化的中文回答，不超过两句话。',
                messages=[{
                    'role': 'user',
                    'content': [
                        {'type': 'image', 'source': {'type': 'base64', 'media_type': 'image/jpeg', 'data': image_b64}},
                        {'type': 'text', 'text': query}
                    ]
                }]
            )
            answer = response.content[0].text
            self.get_logger().info(f'ARIA: {answer}')

            desc_msg = String(); desc_msg.data = answer
            self.desc_pub.publish(desc_msg)

            tts_msg = String(); tts_msg.data = answer
            self.tts_pub.publish(tts_msg)

        except Exception as e:
            self.get_logger().error(f'Claude API error: {e}')

def main():
    rclpy.init()
    node = VisionNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
