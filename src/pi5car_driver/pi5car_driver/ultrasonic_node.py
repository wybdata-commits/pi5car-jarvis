import rclpy
from rclpy.node import Node
from std_msgs.msg import Float32
from gpiozero import DistanceSensor
from gpiozero.pins.lgpio import LGPIOFactory
from gpiozero import Device

Device.pin_factory = LGPIOFactory()

class UltrasonicNode(Node):
    def __init__(self):
        super().__init__('ultrasonic_node')
        self.sensor = DistanceSensor(echo=21, trigger=20, max_distance=3)
        self.pub = self.create_publisher(Float32, '/ultrasonic/distance', 10)
        self.create_timer(0.1, self.timer_cb)
        self.get_logger().info('Ultrasonic node started (TRIGGER=GPIO20, ECHO=GPIO21)')

    def timer_cb(self):
        distance_cm = self.sensor.distance * 100
        msg = Float32()
        msg.data = distance_cm
        self.pub.publish(msg)
        self.get_logger().info(f'Distance: {distance_cm:.1f} cm')

def main():
    rclpy.init()
    node = UltrasonicNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()
