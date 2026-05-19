from setuptools import setup

package_name = 'pi5car_driver'

setup(
    name=package_name,
    version='0.0.1',
    packages=[package_name],
    install_requires=['setuptools'],
    zip_safe=True,
    entry_points={
        'console_scripts': [
            'motor_node = pi5car_driver.motor_node:main',
        ],
    },
)
