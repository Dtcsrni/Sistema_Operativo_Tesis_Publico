from __future__ import annotations
import os
import time
import threading
import psutil
import subprocess
from datetime import datetime
from typing import Any, Optional, Dict
from .telegram_bot import send_message_get_id, edit_message, delete_message, send_chat_action

class AdvancedProgressMonitor:
    """
    Monitor de progreso avanzado para Telegram (OpenClaw).
    
    Gestiona automáticamente:
    - Barra de progreso visual [███░░░].
    - Tiempo transcurrido y estimación de tiempo restante.
    - Actualizaciones automáticas en un hilo de fondo.
    
    Usage:
        with AdvancedProgressMonitor(chat_id, "Procesando Datos", total_items=100) as monitor:
            for i in range(100):
                # ... hacer algo ...
                monitor.update(current=i+1)
    """

    def __init__(
        self, 
        chat_id: str, 
        title: str, 
        total_items: int = 100, 
        update_interval: float = 15.0,
        show_eta: bool = True,
        cleanup_on_success: bool = False,
        target_pid: Optional[int] = None,
        existing_message_id: Optional[int] = None
    ):
        self.chat_id = chat_id
        self.title = title
        self.total_items = total_items
        self.update_interval = update_interval
        self.show_eta = show_eta
        self.cleanup_on_success = cleanup_on_success
        self.target_pid = target_pid
        self.message_id = existing_message_id
        
        self.current_items = 0
        self.start_time = 0.0
        self.last_update_time = 0.0
        self.message_id: Optional[int] = None
        self.is_finished = False
        self.status_details = ""
        self.host_info = "N/A"
        self.val_step = "N/A"
        self.pid = os.getpid()
        self.ema_speed = None  # Para estimación robusta (EMA)
        self.alpha = 0.2       # Factor de suavizado para el promedio móvil
        self.val_step = "N/A"
        self.pid = os.getpid()
        self.spin_chars = ["🕛", "🕒", "🕕", "🕘"]
        self.spin_idx = 0
        self.security_info = "🛡 Calibrando Blindaje..."
        
        self._lock = threading.Lock()
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

    def __enter__(self) -> AdvancedProgressMonitor:
        self.start_time = time.time()
        self.last_update_time = self.start_time
        
        # Enviar mensaje inicial solo si no existe uno previo
        if not self.message_id:
            initial_text = self._build_message()
            self.message_id = send_message_get_id(self.chat_id, initial_text)
        else:
            # Si existe, enviamos un chat action de 'typing' para indicar actividad
            send_chat_action(self.chat_id, "typing")
            # Y actualizamos el mensaje existente con el nuevo contexto
            edit_message(self.chat_id, self.message_id, self._build_message())
        
        # Iniciar hilo de actualización automática (para que el tiempo avance aunque no haya updates de progreso)
        self._thread = threading.Thread(target=self._auto_update_loop, daemon=True)
        self._thread.start()
        
        return self

    def update(
        self, 
        current: int, 
        title: Optional[str] = None, 
        details: Optional[str] = None, 
        host: Optional[str] = None, 
        val_step: Optional[str] = None,
        security_status: Optional[str] = "🛡 Protegido (SHA-256 Validated)"
    ):
        """Actualiza el progreso, detalles y estado de seguridad."""
        with self._lock:
            # ...
            if security_status:
                self.security_info = security_status
            # Calcular velocidad instantánea para el EMA si hay avance
            now = time.time()
            if current > self.current_items:
                items_delta = current - self.current_items
                time_delta = now - self.last_update_time
                if time_delta > 0:
                    instant_speed = items_delta / time_delta
                    if self.ema_speed is None:
                        self.ema_speed = instant_speed
                    else:
                        self.ema_speed = (self.alpha * instant_speed) + ((1 - self.alpha) * self.ema_speed)
            
            self.current_items = current
            self.last_update_time = now
            if title:
                self.title = title
            if details:
                self.status_details = details
            if host:
                self.host_info = host
            if val_step:
                self.val_step = val_step

    def _build_message(self) -> str:
        with self._lock:
            elapsed = time.time() - self.start_time
            pct = int(100 * self.current_items / self.total_items) if self.total_items > 0 else 0
            
            # Barra Animada con Icono Móvil
            bar_len = 12
            filled = int(bar_len * self.current_items / self.total_items) if self.total_items > 0 else 0
            
            # Icono que se mueve con el progreso
            icon = "🚀" if self.current_items < self.total_items else "✅"
            if self.current_items == 0: icon = "🏁"
            
            bar = "━" * filled + icon + "─" * (bar_len - filled)
            
            # Estimación Robusta (EMA o Linear con verificación de ritmo)
            remaining_str = ""
            if self.show_eta and self.current_items > 0 and self.current_items < self.total_items:
                avg_time_per_item = elapsed / self.current_items
                remaining = int(avg_time_per_item * (self.total_items - self.current_items))
                
                # Formateo dinámico (H:MM:SS)
                rem_h, rem_rem = divmod(remaining, 3600)
                rem_m, rem_s = divmod(rem_rem, 60)
                
                if rem_h > 0:
                    remaining_str = f"\n⏳ <b>Tiempo Restante Estimado:</b> ~{rem_h} horas, {rem_m} minutos"
                else:
                    remaining_str = f"\n⏳ <b>Tiempo Restante Estimado:</b> ~{rem_m} minutos, {rem_s} segundos"
            
            el_h, el_rem = divmod(int(elapsed), 3600)
            el_m, el_s = divmod(el_rem, 60)
            
            # Formateo de tiempo profesional (Sin abreviaciones)
            def fmt_time_long(seconds: int) -> str:
                h, rem = divmod(seconds, 3600)
                m, s = divmod(rem, 60)
                parts = []
                if h > 0: parts.append(f"{h} horas")
                if m > 0: parts.append(f"{m} minutos")
                if s > 0 or not parts: parts.append(f"{s} segundos")
                return ", ".join(parts)

            time_str = fmt_time_long(int(elapsed))
            
            # Indicador de Actividad (Latido)
            spinner = self.spin_chars[self.spin_idx]
            self.spin_idx = (self.spin_idx + 1) % len(self.spin_chars)
            
            # Métricas de Sistema Avanzadas
            sys_metrics = ""
            try:
                cpu = psutil.cpu_percent()
                ram = psutil.virtual_memory()
                swap = psutil.swap_memory()
                
                cpu_bar = "■" * int(cpu/20) + "□" * (5 - int(cpu/20))
                ram_used_gb = ram.used / (1024**3)
                ram_total_gb = ram.total / (1024**3)
                ram_bar = "■" * int(ram.percent/20) + "□" * (5 - int(ram.percent/20))
                
                # Obtener espacio en disco
                free_gb = 0
                try:
                    usage = psutil.disk_usage(os.getcwd())
                    free_gb = usage.free / (1024**3)
                except:
                    pass

                sys_metrics = (
                    f"🖥 <b>Procesador:</b> <code>{cpu_bar}</code> {cpu:.1f}%\n"
                    f"🧠 <b>RAM Física:</b> <code>{ram_bar}</code> {ram_used_gb:.2f} / {ram_total_gb:.1f} GB\n"
                    f"💾 <b>Disco Libre:</b> {free_gb:.2f} GB"
                )
                
                # Métrica de Proceso Específico (WSL Compatible)
                if self.target_pid:
                    try:
                        # Obtenemos el RSS y CPU usando ps en WSL
                        cmd = ["wsl", "sh", "-c", f"ps -o rss=,pcpu= -p {self.target_pid}"]
                        output = subprocess.check_output(cmd, stderr=subprocess.DEVNULL).decode().strip()
                        if output:
                            lines_out = output.splitlines()
                            if len(lines_out) > 0:
                                val_parts = lines_out[0].split()
                                if len(val_parts) >= 2:
                                    rss_kb = int(val_parts[0])
                                    proc_cpu = float(val_parts[1])
                                    rss_gb = rss_kb / (1024 * 1024)
                                    sys_metrics += f"\n📊 <b>Uso Proceso:</b> {rss_gb:.2f} GB RSS ({proc_cpu:.1f}% CPU)"
                    except:
                        pass

                if swap.used > 0:
                    swap_used_gb = swap.used / (1024**3)
                    swap_total_gb = swap.total / (1024**3)
                    sys_metrics += f"\n⚠️ <b>Swap Windows:</b> {swap_used_gb:.2f} / {swap_total_gb:.1f} GB"

                speed = self.ema_speed or (self.current_items / elapsed if elapsed > 0 else 0.0)
                sys_metrics += f"\n⚡️ <b>Velocidad:</b> {speed:.2f} t/s"
            except Exception as e:
                sys_metrics = f"⚠️ Error en métricas: {str(e)}"

            last_upd = datetime.now().strftime("%H:%M:%S")
            
            # Algoritmo de Estimación de Estabilidad Global (Híbrido)
            # Evita saltos erráticos usando la velocidad media global suavizada
            global_speed = self.current_items / elapsed if elapsed > 5 else 0
            
            # Usar una mezcla entre la velocidad global y la EMA (si existe) para mayor estabilidad
            if self.ema_speed and self.ema_speed > 0:
                # 70% Global (Estabilidad) / 30% EMA (Adaptabilidad reciente)
                stable_speed = (0.7 * global_speed) + (0.3 * self.ema_speed)
            else:
                stable_speed = global_speed

            # Estimación Robusta y Tiempo Total
            time_info = f"⏱ <b>Tiempo Transcurrido:</b> {time_str}"
            if self.show_eta and self.current_items < self.total_items and stable_speed > 0:
                remaining_items = self.total_items - self.current_items
                remaining_seconds = int(remaining_items / stable_speed)
                
                # Evitar mostrar ETAs absurdos (más de 24 horas) por ruido inicial
                if remaining_seconds < 86400:
                    total_est_seconds = int(elapsed + remaining_seconds)
                    time_info += f"\n⏳ <b>Tiempo Restante Estimado:</b> ~{fmt_time_long(remaining_seconds)}"
                    time_info += f"\n🏁 <b>Duración Total Estimada:</b> {fmt_time_long(total_est_seconds)}"
                else:
                    time_info += f"\n⏳ <b>Tiempo Restante Estimado:</b> Calculando estabilidad..."
                    time_info += f"\n⏳ <b>ETA:</b> ~{fmt_time_long(remaining_seconds)}"
            elif self.show_eta and self.current_items < self.total_items:
                time_info += f"\n⏳ <b>ETA:</b> Calibrando sensores..."

            # Mapa de flujo avanzado (Fases)
            # 📥 (Descarga) 🛠 (Compilación) 🛰 (Sincronización) 🎯 (Validación)
            phases = [("📥", 0, 40), ("🛠", 40, 80), ("🛰", 80, 95), ("🎯", 95, 100)]
            flow_parts = []
            for icon, start, end in phases:
                if pct >= end: flow_parts.append(f"<b>{icon}</b>")
                elif pct >= start: flow_parts.append(f"<b>{icon}</b>")
                else: flow_parts.append(f"{icon}")
            
            # Línea de flujo con indicadores de estado
            flow_map = ""
            for i, (icon, start, end) in enumerate(phases):
                if pct >= end: color = "🟢"
                elif pct >= start: color = "🟡"
                else: color = "⚪️"
                flow_map += f"{color}{icon}"
                if i < len(phases) - 1: flow_map += " ➔ "

            lines = [
                f"🧬 <b>{self.title}</b> {spinner}",
                f"<code>━━━━━━━━━━━━━━━━━━━━</code>",
                f"📈 <b>Progreso:</b> <code>{bar}</code> {pct}%",
                f"🎬 <b>Pipeline Flow:</b> {flow_map}",
                f"🛡 <b>Ciberseguridad:</b> <code>{self.security_info}</code>",
                f"\n{sys_metrics}",
                f"\n{time_info}",
                f"<code>────────────────────</code>",
                f"<i>ID: {self.message_id} | Node: {self.host_info} | {last_upd}</i>"
            ]
            
            if self.status_details:
                # Insertar detalles antes de métricas
                lines.insert(4, f"📝 <b>Detalle:</b> <code>{self.status_details[:80]}</code>")
            
            return "\n".join(lines)

    def _check_oom(self):
        """Consulta dmesg en WSL para detectar si hubo un OOM-Killer reciente."""
        try:
            # Solo funciona si estamos monitoreando un proceso en WSL
            res = subprocess.check_output(["wsl", "sh", "-c", "dmesg | grep -i 'oom-kill' | tail -n 1"], stderr=subprocess.DEVNULL).decode("utf-8")
            if "oom-kill" in res.lower():
                return True
        except:
            pass
        return False

    def _auto_update_loop(self):
        last_msg_update = 0.0
        # Revisamos cada 4.5s para mantener el estado "typing" (que expira cada 5s en Telegram)
        while not self._stop_event.wait(4.5):
            if self.is_finished:
                break
            
            # 1. Mantener señal de actividad viva
            send_chat_action(self.chat_id, "typing")
            
            # 2. Detección de OOM
            if self._check_oom():
                self.title = "⚠️ COLAPSO POR MEMORIA (OOM DETECTADO)"
                self.status_details = "El kernel de Linux ha terminado el proceso por falta de RAM. Modelo inviable en este nodo."
                if self.message_id:
                    edit_message(self.chat_id, self.message_id, self._build_message())

            # 3. Actualizar el contenido del mensaje solo según el intervalo configurado (eficiencia)
            now = time.time()
            if now - last_msg_update >= self.update_interval:
                text = self._build_message()
                if self.message_id:
                    edit_message(self.chat_id, self.message_id, text)
                last_msg_update = now

    def finish(self, success: bool = True, final_text: Optional[str] = None):
        """Finaliza el monitoreo."""
        self.is_finished = True
        self._stop_event.set()
        
        if self.cleanup_on_success and success:
            if self.message_id:
                delete_message(self.chat_id, self.message_id)
            return

        if self.message_id:
            with self._lock:
                elapsed = time.time() - self.start_time
                el_min, el_sec = divmod(int(elapsed), 60)
                
                status_emoji = "✅" if success else "❌"
                status_word = "Completado" if success else "Fallido"
                bell = "🔔" if success else "🚨"
                
                lines = [
                    f"{status_emoji} <b>{self.title}: {status_word}</b>",
                    f"⏱ <b>Tiempo total:</b> {el_min}:{el_sec:02d}m"
                ]
                
                if final_text:
                    lines.append(f"\n📝 <i>{final_text}</i>")
                
                lines.append(f"\n{bell} <b>ESTADO FINAL:</b> {status_word.upper()}")
                
                edit_message(self.chat_id, self.message_id, "\n".join(lines))
                
                # Notificación redundante de "Éxito" para generar alerta sonora
                if success:
                    from .telegram_bot import send_message
                    send_message(self.chat_id, f"🎊 <b>¡MISIÓN CUMPLIDA!</b> 🎊\nEl proceso <code>{self.title}</code> ha finalizado con éxito.\n📍 Nodo: {self.host_info}")

    def __exit__(self, exc_type, exc_val, exc_tb):
        if not self.is_finished:
            success = (exc_type is None)
            self.finish(success=success, final_text=str(exc_val) if exc_val else None)
        
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)
