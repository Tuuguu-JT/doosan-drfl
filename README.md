# Doosan Robot Control with DRFL (Python & C++)

Control a Doosan collaborative robot from your own Python or C++ program using
Doosan's official **DRFL** API, on **Windows** and **Linux**.

This repo gives you:

- **`drfl/`**: Doosan's DRFL library (headers and prebuilt binaries), ready to use.
- **`python/doosan/`**: a small Python package (`Robot` class) that wraps DRFL. It has no pip dependencies.
- **`python/main.py`** and **`cpp_example/main.cpp`**: minimal programs that move one joint out and back.

Tested with an H2017 on the DART-Studio v2.12 virtual controller. The calls are the
same for other Doosan models (M, H, A and E series), because DRFL talks to the
controller, not to a specific arm.

---

## Contents

1. [Repository layout](#repository-layout)
2. [Requirements](#requirements)
3. [Quick start (simulator)](#quick-start-simulator)
4. [Using the Python package in your own code](#using-the-python-package-in-your-own-code)
5. [Using DRFL from your own C++ project](#using-drfl-from-your-own-c-project)
6. [Running on a real robot](#running-on-a-real-robot)
7. [How it works](#how-it-works)
8. [Troubleshooting](#troubleshooting)
9. [License](#license)

---

## Repository layout

```
.
├── drfl/                          Doosan DRFL API GL013305 (v1.33.5)
│   ├── include/                   DRFLEx.h (API + CDRFLEx class), DRFL.h, DRFC.h (enums), DRFS.h (structs)
│   ├── lib/win64/                 DRFLWin64.dll, DRFLWin64.lib (MSVC), DRFLWin64.dll.a (MinGW), Poco DLLs
│   ├── lib/linux/<arch>/<ver>/    libDRFL.a + Poco .so   (arch: amd64|arm64, ver: 18.04|20.04|22.04|24.04)
│   ├── build_linux_so.sh          Linux only: builds libDRFL.so for Python
│   └── LICENSE                    Doosan Robotics, BSD-3-Clause
├── python/
│   ├── main.py                    example: connect, servo on, move J1 +30° and back
│   └── doosan/                    the reusable package
│       ├── __init__.py            exports Robot, cfg
│       ├── config.py              settings (host, speed, ...) + DRFL constants
│       └── robot.py               Robot class (ctypes wrapper around DRFL)
└── cpp_example/
    ├── main.cpp                   same example in C++ using CDRFLEx
    └── CMakeLists.txt             builds on Windows (MinGW/MSVC) and Linux
```

---

## Requirements

| | Windows | Linux |
|---|---|---|
| OS | Windows 10/11, 64-bit | Ubuntu 18.04 / 20.04 / 22.04 / 24.04, amd64 or arm64 |
| Python | 64-bit Python 3.8+ | Python 3.8+ and `g++` (for the one-time build of `libDRFL.so`) |
| C++ | CMake 3.16+ and MinGW-w64 or Visual Studio 2019+ | CMake 3.16+, `g++` |
| Robot | A Doosan controller **or** the DART-Studio virtual controller | A Doosan controller **or** the Doosan emulator |

No `pip install` is needed. Python uses only the standard library.

---

## Quick start (simulator)

### 1. Clone

```bash
git clone <this-repo-url>
cd <repo-folder>
```

### 2. Start the virtual controller

1. Open **DART-Studio**, create or open a workcell, and connect in **virtual mode**.
   This starts the virtual controller on `127.0.0.1:12345`.
2. **Disconnect DART-Studio from the controller, but leave the virtual controller running.**
   While DART-Studio is connected it holds *control authority* and rejects every
   request from other programs (`MONITORING_ACCESS_CONTROL_DENY`).

### 3a. Run the Python example

```bash
cd python
python main.py              # Linux: python3 main.py
```

On **Linux**, first build the shared library once from the repo root:

```bash
bash drfl/build_linux_so.sh     # creates drfl/lib/linux/<arch>/<ver>/libDRFL.so
```

To **watch the motion** in DART-Studio, run `python main.py --watch`. The script
takes control and then pauses. Reconnect DART-Studio, then press Enter.

Expected output:

```
connected: 127.0.0.1:12345 (virtual)
control: granted
robot: STANDBY, autonomous mode
start: [0.00, 0.00, 90.00, 0.00, 90.00, 0.00]
movej -> [30.00, 0.00, 90.00, 0.00, 90.00, 0.00]
movej -> [0.00, 0.00, 90.00, 0.00, 90.00, 0.00]
motion_result: ok
```

### 3b. Run the C++ example

```bash
cmake -S cpp_example -B build                       # Windows + MinGW: add  -G "MinGW Makefiles"
cmake --build build
./build/motion_demo                                 # Windows: build\motion_demo.exe
```

CMake options:

- `-DDRCF_VERSION=3` if your controller firmware is v3.x. The default is 2, for v2.x.
- `-DUBUNTU_VERSION=22.04` on Linux, to override the detected Ubuntu version.

### Changing the motion

Edit `python/doosan/config.py` (Python) or the constants at the top of
`cpp_example/main.cpp` (C++):

| Setting | Meaning | Default |
|---|---|---|
| `HOST`, `PORT` | Controller address | `127.0.0.1`, `12345` |
| `JOINT_INDEX` | Joint to move (0 = J1 … 5 = J6) | `0` |
| `JOINT_DELTA_DEG` | How far to move | `30.0` |
| `VEL`, `ACC` | Joint speed (deg/s) and acceleration (deg/s²) | `15`, `20` |
| `ALLOW_REAL_ROBOT` | Allow a non-virtual controller (Python) | `False` |

---

## Using the Python package in your own code

Put your script in `python/`, next to `main.py`, so `import doosan` works. To use it
from somewhere else, copy the `python/doosan/` folder **and** keep `drfl/` two levels
above it, or change `DRFL_DIR` in `config.py`.

### Minimal program

```python
from doosan import Robot

robot = Robot()                 # loads the DRFL library for your OS
try:
    robot.connect()             # TCP connect to cfg.HOST:cfg.PORT
    robot.take_control()        # get control authority
    robot.servo_on()            # servo on -> STANDBY, autonomous mode

    home = robot.joints()                       # [j1..j6] in degrees
    robot.move_to([0, 0, 90, 0, 90, 0])         # blocking joint move
    robot.move_to(home)
finally:
    robot.close()
```

### Doing other work while the robot moves (non-blocking)

```python
robot.start_move([45, 0, 90, 0, 90, 0])   # returns immediately
while robot.is_moving():
    robot.set_output(1, True)             # e.g. control-box digital output DO1
    # read sensors, talk to a gripper, grab camera frames, ...
robot.set_output(1, False)
```

### `Robot` API

| Method | DRFL function | Description |
|---|---|---|
| `connect()` | `_open_connection` | Connect and check whether the controller is virtual |
| `take_control()` | `_manage_access_control` | Request control authority (FORCE_REQUEST) |
| `has_control()` | (callback) | `True` while this program holds control |
| `servo_on()` | `_set_robot_control`, `_set_robot_mode` | Servo on until STANDBY, then switch to autonomous mode |
| `joints()` | `_get_current_posj` | Current joint angles in degrees |
| `move_to(j)` | `_movej` | Blocking joint move; raises an error if the target isn't reached |
| `start_move(j)` | `_amovej` | Non-blocking joint move |
| `is_moving()` | `_check_motion` | `True` while a motion is running |
| `wait_motion()` | `_mwait` | Block until the current motion ends |
| `stop()` / `pause()` / `resume()` | `_stop`, `_move_pause`, `_move_resume` | Motion control |
| `set_output(i, on)` / `get_input(i)` | `_set_digital_output`, `_get_digital_input` | Control-box digital I/O, numbered 1–16 |
| `alarm()` | `_get_last_alarm` | Last controller alarm as text |
| `close()` | `_close_connection` | Disconnect |

### Adding more DRFL functions

DRFL has about 375 functions. The wrapper binds only the ones above. To add one,
for example `_movel`:

1. Find its declaration in `drfl/include/DRFLEx.h`:
   ```cpp
   DRFL_API bool _movel(LPROBOTCONTROL pCtrl, float fTargetPos[NUM_TASK], float fTargetVel[2],
                        float fTargetAcc[2], float fTargetTime, MOVE_MODE eMoveMode,
                        MOVE_REFERENCE eMoveReference, float fBlendingRadius,
                        BLENDING_SPEED_TYPE eBlendingType, DR_MV_APP eAppType);
   ```
2. Bind it in `Robot.__init__` (`python/doosan/robot.py`) with matching ctypes types
   (enums are `ctypes.c_int`; Python has no default arguments here, so pass every one):
   ```python
   self._movel = b("_movel", ctypes.c_bool, c_ctrl, ctypes.c_float * 6,
                   ctypes.c_float * 2, ctypes.c_float * 2, ctypes.c_float,
                   ctypes.c_int, ctypes.c_int, ctypes.c_float, ctypes.c_int, ctypes.c_int)
   ```
3. Look up any enum values you need in `drfl/include/DRFC.h`, add them to `config.py`,
   and write a small method that calls the function.

Python cannot read `.h` files, so the types must match the header exactly.
If they don't, the call can crash or return garbage.

---

## Using DRFL from your own C++ project

You need three things: the headers, the library to link against, and the runtime
library files next to your executable.

```cmake
set(DRFL_DIR "path/to/this/repo/drfl")
target_include_directories(my_app PRIVATE "${DRFL_DIR}/include")
target_compile_definitions(my_app PRIVATE DRCF_VERSION=2)        # 3 for v3.x firmware

# Windows (MSVC: DRFLWin64.lib, MinGW: DRFLWin64.dll.a), then copy the 3 DLLs next to the .exe
target_link_libraries(my_app PRIVATE "${DRFL_DIR}/lib/win64/DRFLWin64.lib")

# Linux
set(LIB "${DRFL_DIR}/lib/linux/amd64/22.04")
target_link_libraries(my_app PRIVATE "${LIB}/libDRFL.a" "${LIB}/libPocoFoundation.so" "${LIB}/libPocoNet.so" pthread)
```

`cpp_example/CMakeLists.txt` does all of this automatically for both platforms.
Copy it as a starting point.

```cpp
#include "DRFLEx.h"
using namespace DRAFramework;

CDRFLEx robot;
robot.open_connection("127.0.0.1");
robot.manage_access_control(MANAGE_ACCESS_CONTROL_FORCE_REQUEST);
// ...wait for MONITORING_ACCESS_CONTROL_GRANT via set_on_monitoring_access_control...
robot.set_robot_control(CONTROL_SERVO_ON);
float target[6] = {30, 0, 90, 0, 90, 0};
robot.movej(target, 15, 20);
```

See `cpp_example/main.cpp` for the full sequence: callbacks, waiting, and error checks.
The full API reference is the
[Doosan Robotics API manual](https://doosanrobotics.github.io/doosan-robotics-api-manual/).

---

## Running on a real robot

> ⚠️ A real robot can injure people. Clear the workspace, reduce speeds, keep the
> emergency stop within reach, and test in the simulator first.

1. Connect your PC to the controller network. The default controller IP is
   `192.168.137.100`, so give your PC an address such as `192.168.137.50`.
2. In `python/doosan/config.py`, set `HOST = "192.168.137.100"` and `ALLOW_REAL_ROBOT = True`.
3. The teach pendant must allow external control. If `take_control()` is denied,
   release control on the pendant and try again.

The C++ example always refuses to run on a real controller. Remove the
`ROBOT_SYSTEM_VIRTUAL` check in `main.cpp` once you are sure you want this.

---

## How it works

```
python/main.py ─> doosan.Robot ──ctypes──┐
                                         ├──> DRFL library ──TCP :12345──> robot controller
cpp_example/main.cpp ─> CDRFLEx ─────────┘   (DRFLWin64.dll / libDRFL)
```

- **The DRFL library** is closed source and prebuilt by Doosan. It implements the
  network protocol to the controller.
- **The headers** (`drfl/include`) declare the C functions the library exports
  (`_open_connection`, `_movej`, ...). `DRFLEx.h` also contains `CDRFLEx`, a thin
  C++ class around those functions.
- **C++** includes the headers and links the library.
- **Python** can't use C++ headers, so `doosan/robot.py` declares the same C
  functions with `ctypes` and loads the library at run time.
- **Linux:** Doosan ships only a static `libDRFL.a`. `drfl/build_linux_so.sh` links it
  into a shared `libDRFL.so`, because ctypes can only load shared libraries.
- **Motion runs on the controller.** `move_to()` waits for the move to finish, while
  `start_move()` returns immediately, so your program can do other work.

---

## Troubleshooting

| Symptom | Cause / fix |
|---|---|
| `control denied` / `MONITORING_ACCESS_CONTROL_DENY` | DART-Studio (or the teach pendant) holds control. Disconnect DART-Studio, keep the virtual controller running, and run again. |
| `cannot connect` / `open_connection failed` | The controller isn't running or `HOST` is wrong. Check that something is listening on port 12345. |
| `Needs 64-bit Python` | Install 64-bit Python. The DLL is 64-bit only. |
| `libDRFL.so not found` (Linux) | Run `bash drfl/build_linux_so.sh` from the repo root. |
| `No DRFL library for ... Ubuntu X` | Your Ubuntu version isn't in `drfl/lib/linux`. Set `LINUX_UBUNTU_VERSION` (Python) or `-DUBUNTU_VERSION` (CMake) to the nearest version. |
| `Refusing to run: controller is a REAL robot` | Safety check. See [Running on a real robot](#running-on-a-real-robot). |
| Robot never reaches STANDBY | Clear alarms or a safety stop in DART-Studio or on the pendant. The error message shows the last alarm. |

---

## License

- `drfl/`: © Doosan Robotics Inc., BSD-3-Clause (`drfl/LICENSE`), from
  [doosan-robotics/API-DRFL](https://github.com/doosan-robotics/API-DRFL), release GL013305 (v1.33.5).
- Everything else: example code, free to use and modify.

**Status:** Windows is tested (the C++ example builds with MinGW, and the Python
package loads the DLL). Linux build files are included but not yet tested on hardware.
