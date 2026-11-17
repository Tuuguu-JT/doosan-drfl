ROBOT_IP = "192.168.137.100"
ROBOT_PORT = 20002
CONNECT_TIMEOUT = 5
REPLY_TIMEOUT = 60   # longer than your slowest motion

import socket


def main() -> None:
    if not ROBOT_IP.strip():
        print("Failed: set ROBOT_IP.")
        return

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.settimeout(CONNECT_TIMEOUT)
        sock.connect((ROBOT_IP, ROBOT_PORT))
        sock.settimeout(REPLY_TIMEOUT)
        print("Connected.")
        while True:
            cmd = input("Enter a command: ").strip()
            if cmd == "exit":
                break
            if not cmd:
                continue
            sock.sendall(cmd.encode())
            reply = sock.recv(1024)
            if not reply:
                print("Robot closed the connection.")
                break
            print("Robot:", reply.decode())
    except socket.timeout:
        print("Failed: no reply from robot (timeout).")
    except OSError as exc:
        print(f"Failed: {exc}")
    finally:
        sock.close()


if __name__ == "__main__":
    main()