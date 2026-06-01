import socket
import threading
import sys
import os

LOG_FILE = os.path.join(os.getcwd(), "07_scripts", "ops", "ollama_bridge.log")

def log(msg):
    print(msg)
    with open(LOG_FILE, "a") as f:
        f.write(f"{msg}\n")

def handle_client(client_socket, target_host, target_port):
    try:
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.connect((target_host, target_port))
        
        def forward(source, destination, name):
            try:
                while True:
                    data = source.recv(8192)
                    if not data:
                        break
                    destination.sendall(data)
            except:
                pass
            finally:
                source.close()
                destination.close()

        threading.Thread(target=forward, args=(client_socket, server_socket, "c2s"), daemon=True).start()
        threading.Thread(target=forward, args=(server_socket, client_socket, "s2c"), daemon=True).start()
    except Exception as e:
        log(f"[Bridge] Error connecting to target: {e}")
        client_socket.close()

def start_bridge(listen_host, listen_port, target_host, target_port):
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        server.bind((listen_host, listen_port))
    except Exception as e:
        log(f"[Bridge] Could not bind to {listen_host}:{listen_port}: {e}")
        sys.exit(1)
        
    server.listen(10)
    log(f"[Bridge] Listening on {listen_host}:{listen_port} -> {target_host}:{target_port}")
    
    try:
        while True:
            client, addr = server.accept()
            log(f"[Bridge] Connection from {addr}")
            threading.Thread(target=handle_client, args=(client, target_host, target_port), daemon=True).start()
    except KeyboardInterrupt:
        log("[Bridge] Stopping...")
    finally:
        server.close()

if __name__ == "__main__":
    if os.path.exists(LOG_FILE):
        os.remove(LOG_FILE)
    start_bridge("0.0.0.0", 11435, "127.0.0.1", 11434)
