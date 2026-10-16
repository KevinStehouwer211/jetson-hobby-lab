from launch import LaunchDescription
from launch_ros.actions import Node
import os
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from ament_index_python.packages import get_package_share_directory

def generate_launch_description():
    kin_node = Node(
     package='dofbot_info',
     executable='kinemarics_dofbot',
     name='kinemarics_dofbot',
    )

    cam_node = Node(
     package='usb_cam',
     executable='usb_cam_node_exe',
     name='camera_node',
    )

     
    return LaunchDescription([kin_node,cam_node])

 