# Jetson Hobby Lab

Personal Jetson Orin Nano / Yahboom robotics repository.

## Goals

- Docker-based ROS 2 Humble development
- PyTorch, OpenCV and camera experiments
- Yahboom robot testing
- ROS 2 packages and launch files
- Setup notes and troubleshooting

## Hardware

- NVIDIA Jetson Orin Nano
- Yahboom robot platform

## Workflow

Development is done inside Docker.

The ROS 2 workspace is mounted from the host:

```text
Host:      ~/jetson-hobby-lab/ros2_ws
Container: /workspaces/ros2_ws
