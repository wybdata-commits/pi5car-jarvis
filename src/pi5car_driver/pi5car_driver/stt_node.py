import rclpy
from rclpy.node import Node
from std_msgs.msg import String
import dashscope
from dashscope.audio.asr import Recognition
import sounddevice as sd
import numpy as np
import os
import wave
import tempfile

SAMPLE_RATE = 48000
RECORD_SECONDS = 5

class SttNode(Node):
    def __init__(self):
        super().__init__('stt_node')
        dashscope.api_key = os.environ.get('DASHSCOPE_API_KEY')
        self.text_pub = self.create_publisher(String, '/stt/text', 10)
        self.create_subscription(String, '/stt/listen', self.listen_cb, 10)
        self.get_logger().info('STT node started — send "start" to /stt/listen to record')

    def listen_cb(self, msg):
        if msg.data.strip() != 'start':
            return
        self.get_logger().info(f'Recording {RECORD_SECONDS}s...')
        audio = sd.rec(int(RECORD_SECONDS * SAMPLE_RATE),
                       samplerate=SAMPLE_RATE, channels=1, dtype='int16')
        sd.wait()
        self.get_logger().info('Recording done, recognizing...')

        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
            tmp_path = f.name
            with wave.open(tmp_path, 'w') as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(SAMPLE_RATE)
                wf.writeframes(audio.tobytes())

        recognition = Recognition(
            model='paraformer-realtime-v2',
            format='wav',
            sample_rate=SAMPLE_RATE,
            language_hints=['zh', 'en'],
            callback=None
        )
        result = recognition.call(tmp_path)

        if result and result.output and result.output.get('sentence'):
            text = ''.join([s['text'] for s in result.output['sentence']])
            self.get_logger().info(f'Recognized: {text}')
            msg_out = String()
            msg_out.data = text
            self.text_pub.publish(msg_out)
        else:
            self.get_logger().warn('No speech recognized')

def main():
    rclpy.init()
    node = SttNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
