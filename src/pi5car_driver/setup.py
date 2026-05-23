import os
from glob import glob
from setuptools import setup

package_name = 'pi5car_driver'

setup(
    name=package_name,
    version='0.0.1',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'), glob('launch/*.launch.py')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    entry_points={
        'console_scripts': [
            'motor_node = pi5car_driver.motor_node:main',
            'ultrasonic_node = pi5car_driver.ultrasonic_node:main',
            'camera_node = pi5car_driver.camera_node:main',
            'gimbal_node = pi5car_driver.gimbal_node:main',
            'tts_node = pi5car_driver.tts_node:main',
            'teleop_node = pi5car_driver.teleop_node:main',
            'obstacle_avoidance_node = pi5car_driver.obstacle_avoidance_node:main',
        ],
    },
)
