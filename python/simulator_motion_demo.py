"""Move one joint of the DART-Studio virtual H2017 out and back.

Usage (64-bit Python 3.8+):
    python simulator_motion_demo.py           # DART-Studio disconnected
    python simulator_motion_demo.py --watch   # pause so DART-Studio can reconnect and watch

DART-Studio refuses to hand over control while it is connected, so disconnect it
first (leave the virtual controller running). Settings live in doosan_config.py.
"""

import sys

import doosan_config as cfg
from doosan_robot import Robot, fmt


def main() -> None:
    robot = Robot()
    try:
        robot.connect()
        robot.take_control()
        robot.servo_on()

        if "--watch" in sys.argv[1:]:
            input("Reconnect DART-Studio to 127.0.0.1 to watch, then press Enter...")
            if not robot.has_control():
                raise SystemExit("ERROR: DART-Studio took control back on reconnect. Run without --watch.")

        start = robot.joints()
        print(f"start: {fmt(start)}")
        target = list(start)
        target[cfg.JOINT_INDEX] += cfg.JOINT_DELTA_DEG
        try:
            robot.move_to(target)
        finally:
            robot.move_to(start)  # always try to return to the start pose
        print("motion_result: ok")
    finally:
        robot.close()


if __name__ == "__main__":
    main()
