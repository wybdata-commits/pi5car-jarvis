import rclpy
from rclpy.node import Node
from std_msgs.msg import Float32
from geometry_msgs.msg import Twist

SAFE_DISTANCE_CM = 30.0

class ObstacleAvoidanceNode(Node):
    def __init__(self):
        super().__init__('obstacle_avoidance_node')
        self.cmd_pub = self.create_publisher(Twist, '/cmd_vel', 10)
        self.create_subscription(Float32, '/ultrasonic/distance', self.distance_cb, 10)
        self.blocked = False
        self.get_logger().info('Obstacle avoidance node started — safe distance: 30cm')

    def distance_cb(self, msg):
        dist = msg.data
        if dist < SAFE_DISTANCE_CM and not self.blocked:
            self.blocked = True
            self.stop()
            self.get_logger().warn(f'Obstacle at {dist:.1f}cm — STOP')
        elif dist >= SAFE_DISTANCE_CM and self.blocked:
            self.blocked = False
            self.get_logger().info(f'Path clear ({dist:.1f}cm) — ready')

    def stop(self):
        msg = Twist()
        self.cmd_pub.publish(msg)

def main():
    rclpy.init()
    node = ObstacleAvoidanceNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
