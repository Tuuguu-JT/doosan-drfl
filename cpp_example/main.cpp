// Minimal DRFL C++ example: same steps as python/simulator_motion_demo.py.
// Connect to the DART-Studio virtual controller, take control, servo on,
// move J1 by +30 deg and back.
//
// DART-Studio must be disconnected from the controller first (it refuses to
// hand over control while connected); leave the virtual controller running.

#include "DRFLEx.h"

#include <atomic>
#include <chrono>
#include <cmath>
#include <functional>
#include <iostream>
#include <thread>

using namespace DRAFramework;

// --- Settings ----------------------------------------------------------------
static const char* HOST = "127.0.0.1";
static const unsigned int PORT = 12345;
static const int JOINT_INDEX = 0;       // J1
static const float JOINT_DELTA_DEG = 30.0f;
static const float VEL = 15.0f;         // deg/s
static const float ACC = 20.0f;         // deg/s^2
static const float TOLERANCE_DEG = 1.5f;
static const double TIMEOUT_S = 25.0;

static CDRFLEx robot;
static std::atomic<int> g_access{-1};
static std::atomic<bool> g_disconnected{false};

// Poll `done` every 200 ms until it returns true or the timeout expires.
static bool wait_for(const std::function<bool()>& done) {
    auto deadline = std::chrono::steady_clock::now() + std::chrono::duration<double>(TIMEOUT_S);
    while (std::chrono::steady_clock::now() < deadline) {
        if (g_disconnected) return false;
        if (done()) return true;
        std::this_thread::sleep_for(std::chrono::milliseconds(200));
    }
    return false;
}

static void print_joints(const char* label, const float* j) {
    std::cout << label << " [";
    for (int i = 0; i < NUM_JOINT; ++i) std::cout << j[i] << (i + 1 < NUM_JOINT ? ", " : "]\n");
}

static bool move_to(float target[NUM_JOINT]) {
    print_joints("movej ->", target);
    if (!robot.movej(target, VEL, ACC)) {          // blocks until the move ends
        std::cerr << "ERROR: movej rejected\n";
        return false;
    }
    const float* now = robot.get_current_posj()->_fPosition;
    for (int i = 0; i < NUM_JOINT; ++i) {
        if (std::fabs(now[i] - target[i]) > TOLERANCE_DEG) {
            print_joints("ERROR: move ended at", now);
            return false;
        }
    }
    return true;
}

static int run() {
    if (!robot.open_connection(HOST, PORT)) {
        std::cerr << "ERROR: cannot connect to " << HOST << ":" << PORT << "\n";
        return 1;
    }
    robot.setup_monitoring_version(1);
    if (robot.get_robot_system() != ROBOT_SYSTEM_VIRTUAL) {
        std::cerr << "Refusing to run: controller is not ROBOT_SYSTEM_VIRTUAL\n";
        return 1;
    }
    std::cout << "connected: " << HOST << ":" << PORT << " (virtual)\n";

    // 1. Take control.
    g_access = -1;
    robot.manage_access_control(MANAGE_ACCESS_CONTROL_FORCE_REQUEST);
    if (!wait_for([] { return g_access == MONITORING_ACCESS_CONTROL_GRANT ||
                              g_access == MONITORING_ACCESS_CONTROL_DENY; }) ||
        g_access != MONITORING_ACCESS_CONTROL_GRANT) {
        std::cerr << "ERROR: control not granted. Disconnect DART-Studio and run again.\n";
        return 1;
    }
    std::cout << "control: granted\n";

    // 2. Servo on until STANDBY, then autonomous mode.
    bool ready = wait_for([] {
        ROBOT_STATE s = robot.get_robot_state();
        if (s == STATE_STANDBY) return true;
        if (s == STATE_SAFE_STOP) robot.set_robot_control(CONTROL_RESET_SAFET_STOP);
        else if (s == STATE_SAFE_STOP2) robot.set_robot_control(CONTROL_RECOVERY_SAFE_STOP);
        else if (s == STATE_SAFE_OFF2) robot.set_robot_control(CONTROL_RECOVERY_SAFE_OFF);
        else robot.set_robot_control(CONTROL_SERVO_ON);
        return false;
    });
    if (!ready || !robot.set_robot_mode(ROBOT_MODE_AUTONOMOUS)) {
        std::cerr << "ERROR: robot did not reach STANDBY / autonomous mode\n";
        return 1;
    }
    std::cout << "robot: STANDBY, autonomous mode\n";

    // 3. Move out and back.
    float start[NUM_JOINT], target[NUM_JOINT];
    const float* pos = robot.get_current_posj()->_fPosition;
    for (int i = 0; i < NUM_JOINT; ++i) start[i] = target[i] = pos[i];
    target[JOINT_INDEX] += JOINT_DELTA_DEG;
    print_joints("start:", start);

    bool out_ok = move_to(target);
    bool back_ok = move_to(start);                 // always try to return
    if (!(out_ok && back_ok)) return 1;
    std::cout << "motion_result: ok\n";
    return 0;
}

int main() {
    robot.set_on_monitoring_access_control([](const MONITORING_ACCESS_CONTROL a) { g_access = a; });
    robot.set_on_disconnected([] { g_disconnected = true; });
    int code = run();
    robot.close_connection();
    return code;
}
