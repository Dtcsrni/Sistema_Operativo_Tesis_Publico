from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Any


CHATGPT_DEFAULT_URL = "https://chatgpt.com/"
WEB_SESSION_PROVIDERS = {"web_session", "chatgpt_web_session", "chatgpt_plus_web_session"}


def _env_flag(name: str, *, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on", "si", "sí"}


def _select_locator(page: Any, selectors: list[str]) -> Any:
    for selector in selectors:
        locator = page.locator(selector)
        try:
            if locator.count() > 0:
                return locator.first
        except Exception:
            continue
    return None


def _extract_response_text(page: Any) -> str:
    selectors = [
        "[data-message-author-role='assistant']",
        "[data-testid='conversation-turn']",
        "article",
        "main",
    ]
    for selector in selectors:
        locator = page.locator(selector)
        try:
            count = locator.count()
        except Exception:
            continue
        if count <= 0:
            continue
        for index in range(count - 1, max(count - 4, -1), -1):
            try:
                text = locator.nth(index).inner_text(timeout=2000).strip()
            except Exception:
                continue
            if text:
                return text
    return ""


def web_session_user_data_dir() -> Path:
    return Path(
        os.getenv(
            "OPENCLAW_WEB_SESSION_USER_DATA_DIR",
            str(Path(os.getenv("OPENCLAW_DATA_DIR", Path.cwd() / "runtime" / "openclaw" / "state")) / "web_session_profile"),
        )
    )


def _browser_executable() -> str:
    browser_path = os.getenv("OPENCLAW_WEB_SESSION_CHROMIUM_PATH", "/usr/bin/chromium").strip()
    if browser_path and Path(browser_path).exists():
        return browser_path
    return shutil.which(browser_path) or ""


def _playwright_import_status() -> tuple[bool, str]:
    try:
        from playwright.sync_api import sync_playwright as _sync_playwright  # noqa: F401
    except ModuleNotFoundError as exc:
        return False, f"playwright_missing:{exc}"
    return True, "ok"


def build_web_session_status() -> dict[str, Any]:
    provider = os.getenv("OPENCLAW_TELEGRAM_CHAT_PROVIDER", "web_session").strip().lower()
    user_data_dir = web_session_user_data_dir()
    playwright_ok, playwright_status = _playwright_import_status()
    browser_executable = _browser_executable()
    gui_available = _gui_session_available()
    return {
        "status": "ok" if playwright_ok else "not_ready",
        "provider": provider,
        "provider_supported": provider in WEB_SESSION_PROVIDERS,
        "playwright": playwright_status,
        "install_command": "python -m pip install -r runtime/openclaw/requirements-web.txt",
        "browser_install_command": "python -m playwright install chromium",
        "browser_executable": browser_executable or "playwright_managed_chromium",
        "target_url": os.getenv("OPENCLAW_WEB_SESSION_URL", CHATGPT_DEFAULT_URL).strip() or CHATGPT_DEFAULT_URL,
        "user_data_dir": str(user_data_dir),
        "profile_exists": user_data_dir.exists(),
        "headless": _env_flag("OPENCLAW_WEB_SESSION_HEADLESS", default=True),
        "gui_session_available": gui_available,
        "login_required": "unknown_until_browser_opens",
        "credential_policy": "manual_login_only_no_tokens_in_repo",
    }


def _launch_persistent_context(playwright: Any, *, user_data_dir: Path, headless: bool) -> tuple[Any | None, str]:
    browser_executable = _browser_executable()
    launch_args = ["--disable-dev-shm-usage", "--no-sandbox"]
    if headless:
        launch_args.append("--headless=new")
    launch_attempts: list[str | None] = []
    if browser_executable:
        launch_attempts.append(browser_executable)
    launch_attempts.append(None)

    last_error: Exception | None = None
    for executable_path in launch_attempts:
        try:
            context = playwright.chromium.launch_persistent_context(
                user_data_dir=str(user_data_dir),
                executable_path=executable_path,
                headless=headless,
                args=launch_args,
            )
            return context, ""
        except Exception as exc:
            last_error = exc
            continue
    return None, str(last_error)


def open_login_session(*, timeout_seconds: int = 900) -> tuple[bool, str, dict[str, Any]]:
    if not _gui_session_available():
        return False, "web_session_requires_gui_or_x11_forwarding", build_web_session_status()

    try:
        from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
        from playwright.sync_api import sync_playwright
    except ModuleNotFoundError as exc:
        return False, f"playwright_missing:{exc}", build_web_session_status()

    target_url = os.getenv("OPENCLAW_WEB_SESSION_URL", CHATGPT_DEFAULT_URL).strip() or CHATGPT_DEFAULT_URL
    user_data_dir = web_session_user_data_dir()
    user_data_dir.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as playwright:
        context, launch_error = _launch_persistent_context(playwright, user_data_dir=user_data_dir, headless=False)
        if context is None:
            return False, f"web_session_launch_failed:{launch_error}", build_web_session_status()
        try:
            page = context.pages[0] if context.pages else context.new_page()
            page.goto(target_url, wait_until="domcontentloaded", timeout=timeout_seconds * 1000)
            page.wait_for_timeout(timeout_seconds * 1000)
            return True, "web_session_login_window_closed_after_timeout", build_web_session_status()
        except PlaywrightTimeoutError as exc:
            return False, f"web_session_timeout:{exc}", build_web_session_status()
        except Exception as exc:
            return False, f"web_session_error:{exc}", build_web_session_status()
        finally:
            context.close()


def generate_web_session_response(prompt: str, *, timeout_seconds: int = 60) -> tuple[bool, str, str]:
    provider = os.getenv("OPENCLAW_TELEGRAM_CHAT_PROVIDER", "web_session").strip().lower()
    if provider not in WEB_SESSION_PROVIDERS:
        return False, f"web_session_provider_not_supported:{provider}", ""

    headless = _env_flag("OPENCLAW_WEB_SESSION_HEADLESS", default=True)
    if not headless and not _gui_session_available():
        return False, "web_session_requires_gui_or_x11_forwarding", ""

    try:
        from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
        from playwright.sync_api import sync_playwright
    except ModuleNotFoundError as exc:
        return False, f"playwright_missing:{exc}", ""

    target_url = os.getenv("OPENCLAW_WEB_SESSION_URL", CHATGPT_DEFAULT_URL).strip() or CHATGPT_DEFAULT_URL
    user_data_dir = Path(
        os.getenv(
            "OPENCLAW_WEB_SESSION_USER_DATA_DIR",
            str(Path(os.getenv("OPENCLAW_DATA_DIR", Path.cwd() / "runtime" / "openclaw" / "state")) / "web_session_profile"),
        )
    )
    user_data_dir.mkdir(parents=True, exist_ok=True)
    prompt_selectors = [
        "textarea",
        "[role='textbox']",
        "[contenteditable='true']",
    ]

    with sync_playwright() as playwright:
        context, launch_error = _launch_persistent_context(playwright, user_data_dir=user_data_dir, headless=headless)
        if context is None:
            return False, f"web_session_launch_failed:{launch_error}", ""
        try:
            page = context.pages[0] if context.pages else context.new_page()
            page.goto(target_url, wait_until="domcontentloaded", timeout=timeout_seconds * 1000)
            page.wait_for_timeout(2000)
            prompt_box = _select_locator(page, prompt_selectors)
            if prompt_box is None:
                # Reintento rápido si el DOM no está listo
                page.wait_for_timeout(3000)
                prompt_box = _select_locator(page, prompt_selectors)
                
            if prompt_box is None:
                return False, "web_session_prompt_box_not_found", ""

            before = 0
            try:
                before = page.locator("[data-message-author-role='assistant']").count()
            except Exception:
                before = 0

            try:
                prompt_box.click(timeout=5000)
            except Exception:
                pass
            try:
                prompt_box.fill(prompt)
            except Exception:
                prompt_box.press_sequentially(prompt, delay=0)
            try:
                prompt_box.press("Enter")
            except Exception:
                page.keyboard.press("Enter")

            deadline_ms = timeout_seconds * 1000
            elapsed_ms = 0
            response_text = ""
            while elapsed_ms < deadline_ms:
                try:
                    after = page.locator("[data-message-author-role='assistant']").count()
                except Exception:
                    after = before
                if after > before:
                    response_text = _extract_response_text(page)
                    if response_text:
                        break
                page.wait_for_timeout(1000)
                elapsed_ms += 1000

            if not response_text:
                response_text = _extract_response_text(page)
            if not response_text:
                return False, "web_session_empty_response", ""

            model = os.getenv("OPENCLAW_TELEGRAM_CHAT_MODEL", "gpt-5.4").strip() or "gpt-5.4"
            return True, response_text, model
        except PlaywrightTimeoutError as exc:
            return False, f"web_session_timeout:{exc}", ""
        except Exception as exc:
            return False, f"web_session_error:{exc}", ""
        finally:
            context.close()


def _gui_session_available() -> bool:
    return bool(os.getenv("DISPLAY", "").strip() or os.getenv("WAYLAND_DISPLAY", "").strip())
