import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
import sys
import tty
import termios
import threading

SPEED = 0.5
TURN  = 1.0

KEY_BINDINGS = {
    'w': ( SPEED,  0.0,   0.0 ),
    's': (-SPEED,  0.0,   0.0 ),
    'a': (  0.0,  SPEED,  0.0 ),
    'd': (  0.0, -SPEED,  0.0 ),
    'q': (  0.0,   0.0,  TURN ),
    'e': (  0.0,   0.0, -TURN ),
    'z': ( SPEED,  SPEED, 0.0 ),
    'c': ( SPEED, -SPEED, 0.0 ),
    'x': (  0.0,   0.0,  0.0 ),
}

def get_key():
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        ch = sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)
    return ch

class TeleopNode(Node):
    def __init__(self):
        super().__init__('teleop_node')
        self.pub = self.create_publisher(Twist, '/cmd_vel', 10)

    def send(self, lx, ly, az):
        msg = Twist()
        msg.linear.x  = lx
        msg.linear.y  = ly
        msg.angular.z = az
        self.pub.publish(msg)

    def stop(self):
        self.send(0.0, 0.0, 0.0)

def main():
    rclpy.init()
    node = TeleopNode()
    print('=== ARIA 键盘遥控 ===')
    print('w/s: 前进/后退   a/d: 左移/右移   q/e: 左转/右转')
    print('z/c: 左前斜/右前斜   x: 停止   Ctrl+C: 退出')
    print('每次按键自动 0.5 秒后停止')
    try:
        while rclpy.ok():
            key = get_key()
            if key == '\x03':
                break
            if key in KEY_BINDINGS:
                lx, ly, az = KEY_BINDINGS[key]
                node.send(lx, ly, az)
                if key != 'x':
                    threading.Timer(0.5, node.stop).start()
    finally:
        node.stop()
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
