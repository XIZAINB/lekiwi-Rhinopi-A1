# !/usr/bin/env python

# Copyright 2025 The HuggingFace Inc. team. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import time

from lerobot.robots.lekiwi import LeKiwiClient, LeKiwiClientConfig
from lerobot.teleoperators.keyboard.teleop_keyboard import KeyboardTeleop, KeyboardTeleopConfig
from lerobot.teleoperators.so_leader import SO100Leader, SO100LeaderConfig
from lerobot.utils.robot_utils import precise_sleep
from lerobot.utils.visualization_utils import init_rerun, log_rerun_data

FPS = 30
# rerun 可视化降频：每帧推送 480x640 图像约 27MB/s，30fps 会在 ~40s 内吃满
# rerun gRPC 缓存的 1 GiB 上限（日志会报 "Exceeded gRPC proxy server memory limit"）。
# 控制回路仍跑 30fps，只是图像记录降到 5fps。
LOG_FPS = 5
LOG_EVERY = max(1, FPS // LOG_FPS)


def main():
    # Create the robot and teleoperator configurations
    # 本机实况：犀牛派 IP 192.168.112.249；leader 臂 CH343 串口 COM11
    robot_config = LeKiwiClientConfig(remote_ip="192.168.112.249", id="my_lekiwi")
    teleop_arm_config = SO100LeaderConfig(port="COM11", id="my_awesome_leader_arm")
    keyboard_config = KeyboardTeleopConfig(id="my_laptop_keyboard")

    # Initialize the robot and teleoperator
    robot = LeKiwiClient(robot_config)
    leader_arm = SO100Leader(teleop_arm_config)
    keyboard = KeyboardTeleop(keyboard_config)

    # Connect to the robot and teleoperator
    # To connect you already should have this script running on LeKiwi: `python -m lerobot.robots.lekiwi.lekiwi_host --robot.id=my_awesome_kiwi`
    robot.connect()
    leader_arm.connect()
    keyboard.connect()

    # Init rerun viewer
    init_rerun(session_name="lekiwi_teleop")

    if not robot.is_connected or not leader_arm.is_connected or not keyboard.is_connected:
        raise ValueError("Robot or teleop is not connected!")

    print("Starting teleop loop...")
    frame_idx = 0
    while True:
        t0 = time.perf_counter()

        # Get robot observation
        observation = robot.get_observation()

        # Get teleop action
        # Arm
        arm_action = leader_arm.get_action()
        arm_action = {f"arm_{k}": v for k, v in arm_action.items()}
        # Keyboard
        keyboard_keys = keyboard.get_action()
        base_action = robot._from_keyboard_to_base_action(keyboard_keys)

        action = {**arm_action, **base_action} if len(base_action) > 0 else arm_action

        # Send action to robot
        _ = robot.send_action(action)

        # Visualize
        if frame_idx % LOG_EVERY == 0:
            log_rerun_data(observation=observation, action=action)
        frame_idx += 1

        precise_sleep(max(1.0 / FPS - (time.perf_counter() - t0), 0.0))


if __name__ == "__main__":
    main()
