"""Minimal ctypes wrapper around the DRFL library (GL013305 extern "C" exports).

Windows: loads drfl/lib/win64/DRFLWin64.dll.
Linux:   loads drfl/lib/linux/<arch>/<ubuntu>/libDRFL.so, built once from Doosan's
         static libDRFL.a by python/build_linux_lib.sh.
"""

import ctypes
import os
import platform
import sys
import time
from pathlib import Path

import doosan_config as cfg

c_ctrl = ctypes.c_void_p
c_float6 = ctypes.c_float * cfg.NUM_JOINT


class LogAlarm(ctypes.Structure):
    _pack_ = 1
    _fields_ = [
        ("level", ctypes.c_ubyte),
        ("group", ctypes.c_ubyte),
        ("index", ctypes.c_uint),
        ("param", (ctypes.c_char * cfg.MAX_STRING_SIZE) * 3),
    ]


def _ubuntu_version() -> str:
    if cfg.LINUX_UBUNTU_VERSION:
        return cfg.LINUX_UBUNTU_VERSION
    for line in Path("/etc/os-release").read_text().splitlines():
        if line.startswith("VERSION_ID="):
            return line.split("=", 1)[1].strip('"')
    raise SystemExit("Cannot detect Ubuntu version; set LINUX_UBUNTU_VERSION in doosan_config.py.")


def load_library() -> ctypes.CDLL:
    """Load the DRFL shared library for this OS / CPU."""
    if ctypes.sizeof(ctypes.c_void_p) != 8:
        raise SystemExit("Needs 64-bit Python.")
    drfl = (Path(__file__).resolve().parent / cfg.DRFL_DIR).resolve()
    if sys.platform == "win32":
        lib_dir = drfl / "lib" / "win64"
        os.add_dll_directory(str(lib_dir))           # so the Poco DLLs are found
        return ctypes.CDLL(str(lib_dir / "DRFLWin64.dll"))
    if sys.platform.startswith("linux"):
        arch = {"x86_64": "amd64", "aarch64": "arm64"}.get(platform.machine(), platform.machine())
        so = drfl / "lib" / "linux" / arch / _ubuntu_version() / "libDRFL.so"
        if not so.exists():
            raise SystemExit(f"{so} not found. Run: bash python/build_linux_lib.sh")
        return ctypes.CDLL(str(so))                  # finds Poco via rpath $ORIGIN
    raise SystemExit(f"Unsupported platform: {sys.platform}")


def _bind(lib, name, restype, *argtypes):
    fn = getattr(lib, name)
    fn.restype = restype
    fn.argtypes = list(argtypes)
    return fn


class Robot:
    def __init__(self) -> None:
        lib = load_library()
        b = lambda name, res, *args: _bind(lib, name, res, *args)  # noqa: E731

        self._create = b("_CreateRobotControl", c_ctrl)
        self._destroy = b("_DestroyRobotControl", None, c_ctrl)
        self._open = b("_open_connection", ctypes.c_bool, c_ctrl, ctypes.c_char_p, ctypes.c_uint)
        self._close = b("_close_connection", ctypes.c_bool, c_ctrl)
        self._monitoring_version = b("_setup_monitoring_version", ctypes.c_bool, c_ctrl, ctypes.c_int)
        self._get_system = b("_get_robot_system", ctypes.c_int, c_ctrl)
        self._get_state = b("_get_robot_state", ctypes.c_int, c_ctrl)
        self._set_control = b("_set_robot_control", ctypes.c_bool, c_ctrl, ctypes.c_int)
        self._set_mode = b("_set_robot_mode", ctypes.c_bool, c_ctrl, ctypes.c_int)
        self._access = b("_manage_access_control", ctypes.c_bool, c_ctrl, ctypes.c_int)
        self._posj = b("_get_current_posj", ctypes.c_void_p, c_ctrl)
        self._last_alarm = b("_get_last_alarm", ctypes.c_void_p, c_ctrl)
        self._movej = b(
            "_movej", ctypes.c_bool, c_ctrl, c_float6,
            ctypes.c_float, ctypes.c_float, ctypes.c_float, ctypes.c_int, ctypes.c_float, ctypes.c_int,
        )
        # Non-blocking motion and I/O
        self._amovej = b(
            "_amovej", ctypes.c_bool, c_ctrl, c_float6,
            ctypes.c_float, ctypes.c_float, ctypes.c_float, ctypes.c_int, ctypes.c_int,
        )
        self._check_motion = b("_check_motion", ctypes.c_int, c_ctrl)
        self._mwait = b("_mwait", ctypes.c_bool, c_ctrl)
        self._stop = b("_stop", ctypes.c_bool, c_ctrl, ctypes.c_int)
        self._pause = b("_move_pause", ctypes.c_bool, c_ctrl)
        self._resume = b("_move_resume", ctypes.c_bool, c_ctrl)
        self._set_do = b("_set_digital_output", ctypes.c_bool, c_ctrl, ctypes.c_int, ctypes.c_bool)
        self._get_di = b("_get_digital_input", ctypes.c_bool, c_ctrl, ctypes.c_int)

        access_cb_t = ctypes.CFUNCTYPE(None, ctypes.c_int)
        disc_cb_t = ctypes.CFUNCTYPE(None)
        set_on_access = b("_set_on_monitoring_access_control", None, c_ctrl, access_cb_t)
        set_on_disc = b("_set_on_disconnected", None, c_ctrl, disc_cb_t)

        self.access = -1
        self.disconnected = False
        self.ctrl = self._create()
        if not self.ctrl:
            raise SystemExit("_CreateRobotControl returned null.")
        # Keep references to the callbacks so they are not garbage-collected.
        self._cbs = [access_cb_t(self._on_access), disc_cb_t(self._on_disconnected)]
        set_on_access(self.ctrl, self._cbs[0])
        set_on_disc(self.ctrl, self._cbs[1])
        self.connected = False

    # --- callbacks ------------------------------------------------------------
    def _on_access(self, access: int) -> None:
        self.access = access

    def _on_disconnected(self) -> None:
        self.disconnected = True

    # --- helpers --------------------------------------------------------------
    def alarm(self) -> str:
        ptr = self._last_alarm(self.ctrl)
        if not ptr:
            return "none"
        a = ctypes.cast(ptr, ctypes.POINTER(LogAlarm)).contents
        params = " ".join(p.value.decode("ascii", "replace") for p in a.param if p.value)
        return f"level={a.level} group={a.group} index={a.index} {params}".rstrip()

    def _require(self, ok: bool, what: str) -> None:
        if not ok:
            raise SystemExit(f"ERROR: {what} failed. last_alarm: {self.alarm()}")

    def _wait(self, done, what: str) -> None:
        deadline = time.time() + cfg.TIMEOUT_S
        while time.time() < deadline:
            if self.disconnected:
                raise SystemExit(f"ERROR: controller disconnected during {what}.")
            if done():
                return
            time.sleep(0.2)
        raise SystemExit(f"ERROR: timed out during {what}. last_alarm: {self.alarm()}")

    # --- public API -----------------------------------------------------------
    def connect(self) -> None:
        self._require(self._open(self.ctrl, cfg.HOST.encode(), cfg.PORT), "open_connection")
        self.connected = True
        self._monitoring_version(self.ctrl, 1)
        if self._get_system(self.ctrl) != cfg.ROBOT_SYSTEM_VIRTUAL:
            raise SystemExit("Refusing to run: controller is not ROBOT_SYSTEM_VIRTUAL.")
        print(f"connected: {cfg.HOST}:{cfg.PORT} (virtual)")

    def take_control(self) -> None:
        self.access = -1
        self._access(self.ctrl, cfg.MANAGE_ACCESS_CONTROL_FORCE_REQUEST)
        self._wait(lambda: self.access in (cfg.ACCESS_GRANT, cfg.ACCESS_DENY), "control request")
        if self.access == cfg.ACCESS_DENY:
            raise SystemExit(
                "ERROR: control denied. Disconnect DART-Studio from the controller "
                "(keep the virtual controller running) and run again."
            )
        print("control: granted")

    def has_control(self) -> bool:
        return self.access == cfg.ACCESS_GRANT and not self.disconnected

    def servo_on(self) -> None:
        commands = {
            cfg.STATE_SAFE_STOP: cfg.CONTROL_RESET_SAFE_STOP,
            cfg.STATE_SAFE_STOP2: cfg.CONTROL_RECOVERY_SAFE_STOP,
            cfg.STATE_SAFE_OFF2: cfg.CONTROL_RECOVERY_SAFE_OFF,
        }

        def ready() -> bool:
            state = self._get_state(self.ctrl)
            if state == cfg.STATE_STANDBY:
                return True
            self._set_control(self.ctrl, commands.get(state, cfg.CONTROL_SERVO_ON))
            time.sleep(0.2)
            return False

        self._wait(ready, "servo on")
        self._require(self._set_mode(self.ctrl, cfg.ROBOT_MODE_AUTONOMOUS), "set_robot_mode(AUTONOMOUS)")
        print("robot: STANDBY, autonomous mode")

    def joints(self) -> list[float]:
        ptr = self._posj(self.ctrl)
        if not ptr:
            raise SystemExit(f"ERROR: could not read joints. last_alarm: {self.alarm()}")
        return list(ctypes.cast(ptr, ctypes.POINTER(c_float6)).contents)

    def move_to(self, target: list[float]) -> None:
        """Blocking absolute joint move; raises if rejected or target not reached."""
        print(f"movej -> {fmt(target)}")
        ok = self._movej(
            self.ctrl, c_float6(*target), cfg.VEL, cfg.ACC, 0.0,
            cfg.MOVE_MODE_ABSOLUTE, 0.0, cfg.BLENDING_SPEED_TYPE_DUPLICATE,
        )
        self._require(ok, "movej")
        now = self.joints()
        if any(abs(a - b) > cfg.TOLERANCE_DEG for a, b in zip(now, target)):
            raise SystemExit(f"ERROR: move ended at {fmt(now)}, expected {fmt(target)}.")

    # --- non-blocking motion -------------------------------------------------
    def start_move(self, target: list[float]) -> None:
        """Start an absolute joint move and return immediately (_amovej)."""
        print(f"amovej -> {fmt(target)}")
        ok = self._amovej(
            self.ctrl, c_float6(*target), cfg.VEL, cfg.ACC, 0.0,
            cfg.MOVE_MODE_ABSOLUTE, cfg.BLENDING_SPEED_TYPE_DUPLICATE,
        )
        self._require(ok, "amovej")

    def is_moving(self) -> bool:
        return self._check_motion(self.ctrl) != cfg.MOTION_IDLE

    def wait_motion(self) -> None:
        """Block until the current motion finishes (_mwait)."""
        self._require(self._mwait(self.ctrl), "mwait")

    def stop(self) -> None:
        self._stop(self.ctrl, cfg.STOP_TYPE_SLOW)

    def pause(self) -> None:
        self._require(self._pause(self.ctrl), "move_pause")

    def resume(self) -> None:
        self._require(self._resume(self.ctrl), "move_resume")

    # --- control-box digital I/O (index 1..16) -------------------------------
    def set_output(self, index: int, on: bool) -> None:
        self._require(self._set_do(self.ctrl, index - 1, on), f"set_digital_output({index})")

    def get_input(self, index: int) -> bool:
        return bool(self._get_di(self.ctrl, index - 1))

    def close(self) -> None:
        if self.connected:
            self._close(self.ctrl)
            self.connected = False
        if self.ctrl:
            self._destroy(self.ctrl)
            self.ctrl = None


def fmt(joints: list[float]) -> str:
    return "[" + ", ".join(f"{v:.2f}" for v in joints) + "]"
