import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from gpiozero import Motor

MOTOR_PINS = {
    'fl': (24, 25),  # 左前
    'fr': (27, 26),  # 右前
    'rl': (5,  6),   # 左后
    'rr': (22, 9),   # 右后
}

# 接线反了的电机在这里翻转，True=反转
INVERT = {
    'fl': False,
    'fr': False,
    'rl': True,
    'rr': True
,
}

class MotorNode(Node):
    def __init__(self):
        super().__init__('motor_node')
        self.motors = {
            k: Motor(*v) for k, v in MOTOR_PINS.items()
        }
        self.sub = self.create_subscription(
            Twist, '/cmd_vel', self.cmd_cb, 10)
        self.get_logger().info('Motor node started')

    def _drive(self, name, speed):
        m = self.motors[name]
        if INVERT[name]:
            speed = -speed
        if speed > 0:
            m.forward(min(speed, 1.0))
        elif speed < 0:
            m.backward(min(-speed, 1.0))
        else:
            m.stop()

    def cmd_cb(self, msg):
        vx = msg.linear.x   # 前后
        vy = msg.linear.y   # 左右平移
        wz = msg.angular.z  # 原地旋转

        self._drive('fl',  vx - vy - wz)
        self._drive('fr',  vx + vy + wz)
        self._drive('rl',  vx + vy - wz)
        self._drive('rr',  vx - vy + wz)

def main():
    rclpy.init()
    node = MotorNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()
