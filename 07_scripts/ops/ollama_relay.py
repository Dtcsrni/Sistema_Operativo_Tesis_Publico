import socket
import select
import sys

def relay(p1, p2):
    while True:
        r, w, e = select.select([p1, p2], [], [])
        if p1 in r:
            data = p1.recv(8192)
            if not data: break
            p2.sendall(data)
        if p2 in r:
            data = p2.recv(8192)
            if not data: break
            p1.sendall(data)

def start_relay(lp, th, tp):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(('0.0.0.0', lp))
    s.listen(10)
    print(f"Relay 0.0.0.0:{lp} -> {th}:{tp} started")
    while True:
        c, a = s.accept()
        print(f"Connection from {a}")
        t = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            t.connect((th, tp))
            import threading
            threading.Thread(target=relay, args=(c, t), daemon=True).start()
        except Exception as e:
            print(f"Error connecting to target: {e}")
            c.close()

if __name__ == "__main__":
    # Use port 11435 to avoid conflicts
    start_relay(11435, '127.0.0.1', 11434)
