from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    return LaunchDescription([
        Node(package='pi5car_driver', executable='motor_node',      name='motor_node'),
        Node(package='pi5car_driver', executable='ultrasonic_node', name='ultrasonic_node'),
        Node(package='pi5car_driver', executable='camera_node',     name='camera_node'),
        Node(package='pi5car_driver', executable='gimbal_node',     name='gimbal_node'),
        Node(package='pi5car_driver', executable='tts_node',        name='tts_node'),
        Node(package='pi5car_driver', executable='stt_node',        name='stt_node'),
        Node(package='pi5car_driver', executable='brain_node',      name='brain_node'),
    ])
