import rclpy
from rclpy.node import Node
from std_msgs.msg import Float32MultiArray
from gpiozero import AngularServo
from gpiozero.pins.lgpio import LGPIOFactory
from gpiozero import Device
import time

Device.pin_factory = LGPIOFactory()

class GimbalNode(Node):
    def __init__(self):
        super().__init__('gimbal_node')
        self.pan  = AngularServo(12, min_angle=-90, max_angle=90,
                                 min_pulse_width=0.0005, max_pulse_width=0.0025)
        self.tilt = AngularServo(13, min_angle=-90, max_angle=90,
                                 min_pulse_width=0.0005, max_pulse_width=0.0025)
        # 归中后断开PWM，防止抖动
        self.pan.angle  = 0
        self.tilt.angle = 0
        time.sleep(0.5)
        self.pan.value  = None
        self.tilt.value = None
        self.get_logger().info('Gimbal node started — pan/tilt centered and locked')

        self.create_subscription(
            Float32MultiArray, '/gimbal/cmd', self.cmd_cb, 10)

    def cmd_cb(self, msg):
        if len(msg.data) < 2:
            return
        pan_angle  = max(-90, min(90, msg.data[0]))
        tilt_angle = max(-90, min(90, msg.data[1]))
        self.pan.angle  = pan_angle
        self.tilt.angle = tilt_angle
        time.sleep(0.3)
        self.pan.value  = None
        self.tilt.value = None
        self.get_logger().info(f'Gimbal -> pan={pan_angle}, tilt={tilt_angle} (locked)')

def main():
    rclpy.init()
    node = GimbalNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()
