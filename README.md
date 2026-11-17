# Doosan Robot Control (DRFL) — Python & C++

Examples for controlling a Doosan robot (tested with the H2017 on the DART-Studio
virtual controller) through Doosan's DRFL API, on Windows and Linux.

```
.
├── drfl/                  Doosan DRFL API GL013305 (v1.33.5), headers + prebuilt libraries
│   ├── include/           DRFLEx.h, DRFL.h, DRFC.h, DRFS.h
│   ├── lib/win64/         DRFLWin64.dll (+ .lib / .dll.a import libs), Poco DLLs
│   ├── lib/linux/         <amd64|arm64>/<18.04|20.04|22.04|24.04>/libDRFL.a + Poco .so
│   └── LICENSE            Doosan Robotics BSD-3-Clause
├── cpp_example/           C++ example using the CDRFLEx class from DRFLEx.h
│   ├── main.cpp
│   └── CMakeLists.txt
└── python/                Python ctypes wrapper around the DRFL library
    ├── doosan_config.py       settings (host, speeds, joint) + DRFL constants
    ├── doosan_robot.py        Robot class: connect, take_control, servo_on, move, I/O
    ├── simulator_motion_demo.py   blocking move J1 +30° and back
    ├── async_motion_demo.py       non-blocking move while blinking a digital output
    ├── socket_test.py             raw TCP command test (robot-side socket server)
    ├── build_linux_lib.sh         Linux: builds libDRFL.so for Python
    └── run_simulator_demo.bat     Windows launcher
```

## Before running (simulator)

1. Start DART-Studio and its virtual controller (listens on `127.0.0.1:12345`).
2. **Disconnect DART-Studio from the controller** (leave the controller running).
   DART-Studio holds control authority and denies every request while connected.
3. Run an example below. With `--watch` the Python demo pauses after taking
   control so you can reconnect DART-Studio and watch the motion.

The examples refuse to run unless the controller reports `ROBOT_SYSTEM_VIRTUAL`.

## Python (64-bit Python 3.8+, no pip packages)

**Windows**
```bat
cd python
python simulator_motion_demo.py --watch
python async_motion_demo.py
```

**Linux** (Ubuntu 18.04–24.04, amd64 or arm64). Doosan ships only a static
`libDRFL.a` for Linux, so build a shared library for ctypes once:
```bash
bash python/build_linux_lib.sh          # -> drfl/lib/linux/<arch>/<ver>/libDRFL.so
cd python && python3 simulator_motion_demo.py
```

Edit `python/doosan_config.py` to change the joint, distance, speed or host.

## C++ (CMake 3.16+, C++17)

```bash
cmake -S cpp_example -B build            # Windows MinGW: add -G "MinGW Makefiles"
cmake --build build
./build/motion_demo                      # Windows: build\motion_demo.exe
```

Options: `-DDRCF_VERSION=3` for a v3 controller (default 2),
`-DUBUNTU_VERSION=22.04` to override the detected Ubuntu version on Linux.

## How it fits together

```
python/doosan_robot.py ──ctypes──┐
                                 ├──> DRFL library (DRFLWin64.dll / libDRFL) ──TCP──> controller
cpp_example/main.cpp ──CDRFLEx───┘
```

The DRFL library is closed source; `drfl/include/*.h` declares its exported
C functions (`_movej`, `_open_connection`, ...). C++ includes the headers and uses
the `CDRFLEx` wrapper class; Python declares the same functions by hand with ctypes.

## Status

- Windows: C++ example builds with MinGW; Python wrapper loads the DLL.
- Linux: build files and loader are provided but not yet tested.

## License

`drfl/` is © Doosan Robotics, BSD-3-Clause (see `drfl/LICENSE`), from
[doosan-robotics/API-DRFL](https://github.com/doosan-robotics/API-DRFL).
