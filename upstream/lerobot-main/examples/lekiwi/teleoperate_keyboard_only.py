#!/usr/bin/env python

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

# 纯键盘遥操作（无 leader 遥控臂版本）
#
# 适用场景：leader 臂还没到货/未组装时，先用键盘控制 LeKiwi 底盘移动。
# 机械臂部分不控制：把观测到的舵机位置原样回写为目标，让机械臂保持在原地不动。
#
# 用法：
#   1) 先在犀牛派上启动 host：
#      cd ~/lerobot && source .venv/bin/activate
#      python -m lerobot.robots.lekiwi.lekiwi_host --robot.id=my_kiwi --host.connection_time_s=3600
#   2) 在 Windows 笔记本上（本仓库根目录）：
#      uv run python examples/lekiwi/teleoperate_keyboard_only.py
#
# 按键（建议焦点保持在终端窗口）：
#   w / s       前进 / 后退
#   a / d       左移 / 右移
#   z / x       左转 / 右转
#   r / f       加速 / 减速（三档：0.1 / 0.2 / 0.3 m/s，30 / 60 / 90 °/s）
#   Ctrl+C      退出（ESC 也可）

import time

from lerobot.robots.lekiwi import LeKiwiClient, LeKiwiClientConfig
from lerobot.teleoperators.keyboard.teleop_keyboard import KeyboardTeleop, KeyboardTeleopConfig
from lerobot.utils.errors import DeviceNotConnectedError
from lerobot.utils.robot_utils import precise_sleep

FPS = 30

REMOTE_IP = "192.168.112.249"  # 犀牛派 IP
ROBOT_ID = "my_lekiwi"


def main():
    robot_config = LeKiwiClientConfig(remote_ip=REMOTE_IP, id=ROBOT_ID)
    keyboard_config = KeyboardTeleopConfig(id="my_laptop_keyboard")

    robot = LeKiwiClient(robot_config)
    keyboard = KeyboardTeleop(keyboard_config)

    robot.connect()
    keyboard.connect()

    if not robot.is_connected or not keyboard.is_connected:
        raise ValueError("Robot or keyboard is not connected!")

    print("已连接到机器人。w/s 前后，a/d 左右，z/x 旋转，r/f 调速，Ctrl+C 退出。")
    print(f"当前速度档位：{robot.speed_levels[robot.speed_index]}")

    last_speed_index = robot.speed_index
    try:
        while True:
            t0 = time.perf_counter()

            # 读取机器人状态（机械臂位置 + 底盘速度 + 相机帧）
            observation = robot.get_observation()

            # 没有 leader 臂：把机械臂当前位姿原样发回去，让它保持在原地
            arm_hold = {k: v for k, v in observation.items() if k.endswith(".pos")}
            if len(arm_hold) == 0:
                # 还没收到完整状态，暂不下发指令
                precise_sleep(0.1)
                continue

            # 键盘 → 底盘速度指令
            keyboard_keys = keyboard.get_action()
            base_action = robot._from_keyboard_to_base_action(keyboard_keys)

            action = {**arm_hold, **base_action}
            robot.send_action(action)

            # 速度档位变化时提示
            if robot.speed_index != last_speed_index:
                last_speed_index = robot.speed_index
                print(f"速度档位：{robot.speed_levels[robot.speed_index]}")

            precise_sleep(max(1.0 / FPS - (time.perf_counter() - t0), 0.0))
    except (KeyboardInterrupt, DeviceNotConnectedError):
        print("\n退出中…")
    finally:
        # 先判断连接状态再断开，避免 ESC 退出时二次 disconnect 抛异常
        if robot.is_connected:
            robot.disconnect()
        if keyboard.is_connected:
            keyboard.disconnect()
        print("已断开。")


if __name__ == "__main__":
    main()
