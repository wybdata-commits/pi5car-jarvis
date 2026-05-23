import rclpy
from rclpy.node import Node
from std_msgs.msg import String
from geometry_msgs.msg import Twist
import anthropic
import os

class BrainNode(Node):
    def __init__(self):
        super().__init__('brain_node')
        self.client = anthropic.Anthropic(api_key=os.environ.get('ANTHROPIC_API_KEY'))
        self.conversation_history = []

        # 订阅 STT 输出
        self.create_subscription(String, '/stt/text', self.on_speech, 10)
        # 订阅视觉描述（可选，有视觉上下文时使用）
        self.create_subscription(String, '/vision/description', self.on_vision, 10)
        # 订阅 TTS 播完信号 → 触发下一轮录音
        self.create_subscription(String, '/tts/done', self.on_tts_done, 10)

        # 发布 TTS 和运动指令
        self.tts_pub  = self.create_publisher(String, '/tts/say', 10)
        self.cmd_pub  = self.create_publisher(Twist, '/cmd_vel', 10)
        self.stt_pub  = self.create_publisher(String, '/stt/listen', 10)

        self.latest_vision = ''

        self.get_logger().info('Brain node started — ARIA is ready')
        self.say('你好，我是ARIA，有什么可以帮你的吗？')

    def on_vision(self, msg):
        self.latest_vision = msg.data

    def on_tts_done(self, msg):
        self.trigger_stt()

    def on_speech(self, msg):
        text = msg.data.strip()
        if not text:
            return
        self.get_logger().info(f'User said: {text}')
        self.think_and_respond(text)

    def think_and_respond(self, user_text):
        system_prompt = (
            '你是 ARIA，一个有温度、有性格的家庭机器人助手。'
            '回答简短口语化，不超过两句话。'
            '如果用户让你移动，回复"好的"并在回复末尾加上动作标记：'
            '[前进] [后退] [左转] [右转] [停止]'
        )
        if self.latest_vision:
            user_text = f'（当前视野：{self.latest_vision}）\n用户说：{user_text}'

        self.conversation_history.append({'role': 'user', 'content': user_text})

        try:
            response = self.client.messages.create(
                model='claude-haiku-4-5',
                max_tokens=150,
                system=system_prompt,
                messages=self.conversation_history
            )
            answer = response.content[0].text
            self.conversation_history.append({'role': 'assistant', 'content': answer})
            self.get_logger().info(f'ARIA: {answer}')
            self.execute_action(answer)
            self.say(answer)
        except Exception as e:
            self.get_logger().error(f'Brain error: {e}')

    def execute_action(self, text):
        twist = Twist()
        if '[前进]' in text:
            twist.linear.x = 0.5
        elif '[后退]' in text:
            twist.linear.x = -0.5
        elif '[左转]' in text:
            twist.angular.z = 1.0
        elif '[右转]' in text:
            twist.angular.z = -1.0
        elif '[停止]' in text:
            pass  # 全零即停止
        else:
            return  # 无动作指令，不发布
        self.cmd_pub.publish(twist)
        # 0.5秒后停止
        self.create_timer(0.5, self.stop_once)

    def stop_once(self):
        self.cmd_pub.publish(Twist())

    def say(self, text):
        # 去掉动作标记再播报
        for tag in ['[前进]', '[后退]', '[左转]', '[右转]', '[停止]']:
            text = text.replace(tag, '')
        msg = String()
        msg.data = text.strip()
        self.tts_pub.publish(msg)
        # 不再用 Timer 估算延迟，改为等 /tts/done 信号触发录音

    def trigger_stt(self):
        msg = String()
        msg.data = 'start'
        self.stt_pub.publish(msg)
        self.get_logger().info('Listening...')

def main():
    rclpy.init()
    node = BrainNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
