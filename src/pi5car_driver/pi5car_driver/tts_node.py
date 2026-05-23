import rclpy
from rclpy.node import Node
from std_msgs.msg import String
import subprocess

class TtsNode(Node):
    def __init__(self):
        super().__init__('tts_node')
        self.create_subscription(String, '/tts/say', self.say_cb, 10)
        self.get_logger().info('TTS node started — listening on /tts/say')

    def say_cb(self, msg):
        text = msg.data
        self.get_logger().info(f'Speaking: {text}')
        subprocess.run(
            f'espeak -v zh "{text}" --stdout | aplay -D plughw:2,0',
            shell=True
        )

def main():
    rclpy.init()
    node = TtsNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()
