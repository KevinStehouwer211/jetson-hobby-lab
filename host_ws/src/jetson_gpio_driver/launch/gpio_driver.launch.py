import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    params = os.path.join(
        get_package_share_directory('jetson_gpio_driver'),
        'config', 'gpio_params.yaml')
    return LaunchDescription([
        Node(
            package='jetson_gpio_driver',
            executable='gpio_driver',
            name='gpio_driver',
            output='screen',
            parameters=[params],
        ),
    ])
