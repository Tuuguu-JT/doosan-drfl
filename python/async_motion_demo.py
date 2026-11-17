"""Non-blocking motion demo: blink a digital output while the robot moves.

Usage: python async_motion_demo.py   (DART-Studio disconnected, as for the main demo)

Pattern:
    robot.start_move(target)    # returns immediately (_amovej)
    while robot.is_moving():    # poll _check_motion
        ...do other work...     # I/O, sensors, grippers, cameras, ...
"""

import time

import doosan_config as cfg
from doosan_robot import Robot, fmt

BLINK_OUTPUT = 1      # control-box digital output DO1
BLINK_PERIOD_S = 0.5


def move_and_blink(robot: Robot, target: list[float]) -> None:
    robot.start_move(target)
    led = False
    while robot.is_moving():
        led = not led
        robot.set_output(BLINK_OUTPUT, led)          # peripheral work during motion
        print(f"  moving... DO{BLINK_OUTPUT}={int(led)} J={fmt(robot.joints())}")
        time.sleep(BLINK_PERIOD_S)
    robot.set_output(BLINK_OUTPUT, False)
    print(f"  arrived: {fmt(robot.joints())}")


def main() -> None:
    robot = Robot()
    try:
        robot.connect()
        robot.take_control()
        robot.servo_on()
        start = robot.joints()
        target = list(start)
        target[cfg.JOINT_INDEX] += cfg.JOINT_DELTA_DEG
        try:
            move_and_blink(robot, target)
        finally:
            move_and_blink(robot, start)
        print("motion_result: ok")
    finally:
        robot.close()


if __name__ == "__main__":
    main()
