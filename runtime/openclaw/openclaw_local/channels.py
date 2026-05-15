from __future__ import annotations
from pathlib import Path
from typing import Any
from . import telegram_bot
# from . import matrix_bot # Evitar circular si matrix_bot importa orchestrator

class TelegramChannel:
    def __init__(self, chat_id: str):
        self.chat_id = chat_id

    def send_message(self, text: str, **kwargs) -> Any:
        return telegram_bot.send_message(self.chat_id, text)

    def send_action(self, action: str) -> None:
        telegram_bot.send_chat_action(self.chat_id, action)

    def update_message(self, message_id: Any, text: str) -> None:
        telegram_bot.edit_message(self.chat_id, message_id, text)

    def send_photo(self, image_path: Path, caption: str = "") -> Any:
        return telegram_bot.send_photo_message(self.chat_id, image_path, caption=caption)

class MatrixChannel:
    def __init__(self, room_id: str):
        self.room_id = room_id

    def send_message(self, text: str, **kwargs) -> Any:
        # Importación tardía para evitar circulares si matrix_bot se refactoriza
        from . import matrix_bot
        return matrix_bot.matrix_send_message(self.room_id, text)

    def send_action(self, action: str) -> None:
        # Matrix no tiene 'typing' tan directo por API simple, pero se puede extender
        pass

    def update_message(self, message_id: Any, text: str) -> None:
        pass

    def send_photo(self, image_path: Path, caption: str = "") -> Any:
        pass

class WebChannel:
    def __init__(self, session_id: str, callback: Any = None):
        self.session_id = session_id
        self.callback = callback
        self.history = []

    def send_message(self, text: str, **kwargs) -> Any:
        self.history.append({"role": "assistant", "content": text})
        if self.callback:
            # Sincronizar con firma (token_count, delta, stream_type)
            self.callback(0, text, "agent")
        return {"status": "queued", "session_id": self.session_id}

    def send_action(self, action: str) -> None:
        if self.callback:
            # Sincronizar con firma (token_count, delta, stream_type)
            self.callback(0, f"ACTION:{action}", "action")

    def update_message(self, message_id: Any, text: str) -> None:
        pass

    def send_photo(self, image_path: Path, caption: str = "") -> Any:
        pass
