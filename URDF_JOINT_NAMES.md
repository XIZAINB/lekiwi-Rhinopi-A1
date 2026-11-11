# URDF joint names

The nine actuated joints use the same names as the LeKiwi motors in
[LeRobot](https://github.com/huggingface/lerobot/blob/main/src/lerobot/robots/lekiwi/lekiwi.py).
This makes joint-state and command dictionaries directly comparable between the
robot driver and the URDF.

| LeRobot/URDF name | Previous generated URDF name |
| --- | --- |
| `base_left_wheel` | `ST3215_Servo_Motor-v1_Revolute-64` |
| `base_back_wheel` | `ST3215_Servo_Motor-v1-2_Revolute-60` |
| `base_right_wheel` | `ST3215_Servo_Motor-v1-1_Revolute-62` |
| `arm_shoulder_pan` | `STS3215_03a-v1_Revolute-45` |
| `arm_shoulder_lift` | `STS3215_03a-v1-1_Revolute-49` |
| `arm_elbow_flex` | `STS3215_03a-v1-2_Revolute-51` |
| `arm_wrist_flex` | `STS3215_03a-v1-3_Revolute-53` |
| `arm_wrist_roll` | `STS3215_03a_Wrist_Roll-v1_Revolute-55` |
| `arm_gripper` | `STS3215_03a-v1-4_Revolute-57` |

Consumers that refer to joints by name must update from the generated names in
the right column to the stable names in the left column.

