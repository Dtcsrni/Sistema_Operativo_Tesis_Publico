# ==============================================================================
# socket_utils.py - Utilerías de Red Resiliente para el SIOT
# ==============================================================================
# Proporciona funciones robustas para comprobar puertos y enlazar sockets,
# evitando el fallo clásico de 'Address already in use' durante reinicios rápidos.
# ==============================================================================

import socket
import time
import logging

LOGGER = logging.getLogger("siot.socket_utils")

def is_port_in_use(host: str, port: int, timeout: float = 1.0) -> bool:
    """
    Comprueba de forma pasiva si un puerto TCP está ocupado en el host especificado.
    """
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(timeout)
            s.connect((host, port))
            return True
    except (socket.timeout, ConnectionRefusedError):
        return False
    except Exception as e:
        LOGGER.debug(f"Error al verificar puerto {host}:{port}: {e}")
        return False

def create_resilient_server_socket(host: str, port: int, retries: int = 5, backoff_sec: float = 1.5) -> socket.socket:
    """
    Crea y enlaza (bind) un socket TCP servidor de forma resiliente.
    Configura SO_REUSEADDR para permitir la reutilización inmediata del puerto
    e implementa reintentos en caso de que esté ocupado temporalmente.
    """
    for attempt in range(1, retries + 1):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            # Habilitar reutilización del socket a nivel del SO
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            
            LOGGER.info(f"Intentando enlazar socket en {host}:{port} (Intento {attempt}/{retries})...")
            s.bind((host, port))
            return s
        except OSError as e:
            s.close()
            if attempt == retries:
                LOGGER.error(f"Fallo crítico al enlazar socket tras {retries} intentos: {e}")
                raise e
            LOGGER.warning(f"Puerto {port} ocupado. Reintentando en {backoff_sec} segundos...")
            time.sleep(backoff_sec)
            backoff_sec *= 1.5 # Backoff exponencial

    raise OSError(f"No se pudo enlazar el socket en {host}:{port}")
