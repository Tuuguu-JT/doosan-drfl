"""User settings (top) and DRFL constants (bottom) for the doosan package."""

from pathlib import Path

# --- Connection -------------------------------------------------------------
HOST = "127.0.0.1"          # simulator; a real controller is usually 192.168.137.100
PORT = 12345
ALLOW_REAL_ROBOT = False    # safety: refuse to move unless the controller is virtual
DRFL_DIR = Path(__file__).resolve().parents[2] / "drfl"   # repo/drfl
LINUX_UBUNTU_VERSION = None # None = auto-detect from /etc/os-release, or e.g. "22.04"
# Controller v2.x (DRCF 2) is assumed: functions like _set_digital_output are the
# v2 variants. For a v3 controller use the *_ex variants instead.

# --- Motion -----------------------------------------------------------------
JOINT_INDEX = 0             # 0 = J1 (base rotation, easy to see in the 3D view)
JOINT_DELTA_DEG = 30.0
VEL = 15.0                  # deg/s
ACC = 20.0                  # deg/s^2
TOLERANCE_DEG = 1.5
TIMEOUT_S = 25.0

# --- DRFL constants (from DRFLEx.h / DRFL enums) ------------------------------
NUM_JOINT = 6
MAX_STRING_SIZE = 256

STATE_STANDBY = 1
STATE_SAFE_OFF = 3
STATE_SAFE_STOP = 5
STATE_SAFE_STOP2 = 9
STATE_SAFE_OFF2 = 10

CONTROL_RESET_SAFE_STOP = 2
CONTROL_SERVO_ON = 3
CONTROL_RECOVERY_SAFE_STOP = 4
CONTROL_RECOVERY_SAFE_OFF = 5

ROBOT_SYSTEM_VIRTUAL = 1
ROBOT_MODE_AUTONOMOUS = 1

MANAGE_ACCESS_CONTROL_FORCE_REQUEST = 0
ACCESS_DENY = 1
ACCESS_GRANT = 2

MOVE_MODE_ABSOLUTE = 0
BLENDING_SPEED_TYPE_DUPLICATE = 0

MOTION_IDLE = 0             # _check_motion: 0 idle, 1 planning, 2 moving
STOP_TYPE_SLOW = 2
