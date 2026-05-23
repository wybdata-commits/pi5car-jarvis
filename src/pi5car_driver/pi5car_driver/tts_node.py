import rclpy
from rclpy.node import Node
from std_msgs.msg import String
import dashscope
from dashscope.audio.tts_v2 import SpeechSynthesizer
import os
import tempfile
import subprocess

class TtsNode(Node):
    def __init__(self):
        super().__init__('tts_node')
        dashscope.api_key = os.environ.get('DASHSCOPE_API_KEY')
        self.create_subscription(String, '/tts/say', self.say_cb, 10)
        self.get_logger().info('TTS node started (CosyVoice) — listening on /tts/say')

    def say_cb(self, msg):
        text = msg.data
        self.get_logger().info(f'Speaking: {text}')
        try:
            synthesizer = SpeechSynthesizer(
                model='cosyvoice-v1',
                voice='longxiaochun',
            )
            audio = synthesizer.call(text)
            with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as f:
                f.write(audio)
                tmp_path = f.name
            subprocess.run(['aplay', '-D', 'plughw:2,0', tmp_path])
            os.unlink(tmp_path)
        except Exception as e:
            self.get_logger().error(f'TTS error: {e}')
            subprocess.run(f'espeak -v zh "{text}" --stdout | aplay -D plughw:2,0', shell=True)

def main():
    rclpy.init()
    node = TtsNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
