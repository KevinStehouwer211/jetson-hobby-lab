import os
from glob import glob

from setuptools import setup

package_name = 'jetson_gpio_driver'

setup(
    name=package_name,
    version='0.1.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'), glob('launch/*.launch.py')),
        (os.path.join('share', package_name, 'config'), glob('config/*.yaml')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Kevin Stehouwer',
    maintainer_email='stehouwerkevin@gmail.com',
    description='ROS 2 driver exposing NVIDIA Jetson board GPIO over topics.',
    license='MIT',
    entry_points={
        'console_scripts': [
            'gpio_driver = jetson_gpio_driver.gpio_driver_node:main',
        ],
    },
)
