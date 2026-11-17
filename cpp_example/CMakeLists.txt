cmake_minimum_required(VERSION 3.16)
project(doosan_cpp_example LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Controller generation: 2 for DRCF v2.x (e.g. GF02120500), 3 for v3.x.
set(DRCF_VERSION 2 CACHE STRING "DRCF controller major version (2 or 3)")

set(DRFL_DIR "${CMAKE_CURRENT_LIST_DIR}/../drfl")

add_executable(motion_demo main.cpp)
target_include_directories(motion_demo PRIVATE "${DRFL_DIR}/include")
target_compile_definitions(motion_demo PRIVATE DRCF_VERSION=${DRCF_VERSION})

if(WIN32)
    set(DRFL_LIB_DIR "${DRFL_DIR}/lib/win64")
    # MSVC links the .lib import library; MinGW links the .dll.a.
    if(MSVC)
        target_link_libraries(motion_demo PRIVATE "${DRFL_LIB_DIR}/DRFLWin64.lib")
    else()
        target_link_libraries(motion_demo PRIVATE "${DRFL_LIB_DIR}/DRFLWin64.dll.a")
    endif()
    # Copy the runtime DLLs next to the .exe.
    add_custom_command(TARGET motion_demo POST_BUILD
        COMMAND ${CMAKE_COMMAND} -E copy_if_different
            "${DRFL_LIB_DIR}/DRFLWin64.dll"
            "${DRFL_LIB_DIR}/PocoFoundation64.dll"
            "${DRFL_LIB_DIR}/PocoNet64.dll"
            $<TARGET_FILE_DIR:motion_demo>)
else()
    # Linux: pick drfl/lib/linux/<arch>/<ubuntu version>.
    if(CMAKE_SYSTEM_PROCESSOR MATCHES "aarch64|arm64")
        set(DRFL_ARCH arm64)
    else()
        set(DRFL_ARCH amd64)
    endif()
    if(NOT UBUNTU_VERSION)
        file(STRINGS /etc/os-release _ver REGEX "^VERSION_ID=")
        string(REGEX REPLACE "^VERSION_ID=\"?([^\"]*)\"?$" "\\1" UBUNTU_VERSION "${_ver}")
    endif()
    set(DRFL_LIB_DIR "${DRFL_DIR}/lib/linux/${DRFL_ARCH}/${UBUNTU_VERSION}")
    if(NOT EXISTS "${DRFL_LIB_DIR}/libDRFL.a")
        message(FATAL_ERROR "No DRFL library for ${DRFL_ARCH} Ubuntu ${UBUNTU_VERSION}. "
                            "Pass -DUBUNTU_VERSION=22.04 (or 18.04/20.04/24.04).")
    endif()
    find_package(Threads REQUIRED)
    target_link_libraries(motion_demo PRIVATE
        "${DRFL_LIB_DIR}/libDRFL.a"
        "${DRFL_LIB_DIR}/libPocoFoundation.so"
        "${DRFL_LIB_DIR}/libPocoNet.so"
        Threads::Threads)
    set_target_properties(motion_demo PROPERTIES BUILD_RPATH "${DRFL_LIB_DIR}")
endif()
