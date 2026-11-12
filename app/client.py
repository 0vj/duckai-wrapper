import asyncio
import json
import logging
import time
import uuid
from typing import AsyncGenerator, Dict, List, Optional
from playwright.async_api import async_playwright, Browser, BrowserContext, Page, Response

from app.config import settings, AVAILABLE_MODELS, resolve_model
from app.models import ChatMessage

logger = logging.getLogger("duckai_client")
logging.basicConfig(level=logging.INFO)

class DuckAISession:
    """Manages an active Duck.ai browser page session with anti-bot handling."""
    
    def __init__(self, page: Page, session_id: str):
        self.page = page
        self.session_id = session_id
        self.lock = asyncio.Lock()
        self.current_model: Optional[str] = None
        self.created_at = time.time()
        self.last_used = time.time()
        self.is_ready = False
        self.has_errors = False

    async def init(self, target_model: str = "gpt-6-luna"):
        """Navigate to Duck.ai and ensure readiness with the target model."""
        target_model = resolve_model(target_model)
        setting_id = AVAILABLE_MODELS.get(target_model, {}).get("setting_id", "291")
        
        # Inject preferred model into localStorage before load
        await self.page.add_init_script(f"""
            try {{
                localStorage.setItem('preferredDuckaiModel', JSON.stringify('{setting_id}'));
            }} catch (e) {{}}
        """)
        
        logger.info(f"[{self.session_id}] Navigating to https://duck.ai for model {target_model}...")
        await self.page.goto("https://duck.ai", wait_until="networkidle", timeout=45000)
        self.current_model = target_model
        self.is_ready = True
        self.last_used = time.time()

    async def switch_model(self, target_model: str):
        """Switch active model inside the page session."""
        target_model = resolve_model(target_model)
        if self.current_model == target_model:
            return

        model_info = AVAILABLE_MODELS.get(target_model)
        if not model_info:
            return

        display_name = model_info["name"]
        logger.info(f"[{self.session_id}] Switching model from {self.current_model} to {target_model} ({display_name})...")

        try:
            # Click model picker dropdown
            picker_btn = await self.page.query_selector('button:has-text("Luna"), button:has-text("mini"), button:has-text("Haiku"), button:has-text("Mistral"), button:has-text("gpt-oss"), button:has-text("Gemma"), button[aria-label="Reasoning mode"] ~ button')
            if picker_btn:
                await picker_btn.click()
                await self.page.wait_for_timeout(400)

                # Select option matching model name or short name
                target_selector = f'button:has-text("{display_name}"), div:has-text("{display_name}")'
                opt = await self.page.query_selector(target_selector)
                if opt:
                    await opt.click()
                    await self.page.wait_for_timeout(400)
                    self.current_model = target_model
                    logger.info(f"[{self.session_id}] Successfully switched model to {target_model}")
                    return

            # Fallback: re-initialize with new model in localStorage
            await self.page.evaluate(f"localStorage.setItem('preferredDuckaiModel', JSON.stringify('{model_info['setting_id']}'));")
            await self.page.reload(wait_until="networkidle")
            self.current_model = target_model
        except Exception as e:
            logger.warning(f"[{self.session_id}] Could not switch model in-place: {e}. Session will reload.")
            self.has_errors = True

    async def reset(self):
        """Reset conversation state for a fresh request."""
        try:
            new_chat_btn = await self.page.query_selector('button:has-text("New Chat")')
            if new_chat_btn:
                await new_chat_btn.click()
                await self.page.wait_for_timeout(500)
            else:
                await self.page.reload(wait_until="networkidle")
        except Exception as e:
            logger.warning(f"[{self.session_id}] Error resetting chat: {e}")
            self.has_errors = True

    async def send_chat(self, prompt: str, target_model: str) -> AsyncGenerator[str, None]:
        """Send chat prompt to Duck.ai and yield streaming tokens."""
        async with self.lock:
            target_model = resolve_model(target_model)
            if self.current_model != target_model:
                await self.switch_model(target_model)

            stream_queue = asyncio.Queue()
            error_holder = []

            async def on_response(response: Response):
                if "/chat" in response.url:
                    if response.status == 200:
                        try:
                            body = await response.text()
                            for line in body.splitlines():
                                line = line.strip()
                                if line.startswith("data: "):
                                    payload_str = line[6:].strip()
                                    if payload_str == "[DONE]":
                                        await stream_queue.put(None)
                                        return
                                    if payload_str.startswith("[CHAT_TITLE:"):
                                        continue
                                    try:
                                        data = json.loads(payload_str)
                                        msg = data.get("message")
                                        if msg:
                                            await stream_queue.put(msg)
                                    except Exception:
                                        pass
                        except Exception as e:
                            logger.error(f"[{self.session_id}] Error parsing chat stream: {e}")
                            await stream_queue.put(None)
                    else:
                        try:
                            err_body = await response.text()
                            error_holder.append(f"HTTP {response.status}: {err_body}")
                        except Exception:
                            error_holder.append(f"HTTP {response.status}")
                        await stream_queue.put(None)

            self.page.on("response", on_response)

            try:
                # Type prompt in textarea
                textarea = await self.page.wait_for_selector('textarea[name="user-prompt"]', timeout=15000)
                await textarea.fill(prompt)
                await self.page.wait_for_timeout(200)

                # Click Ask or Send
                submit_btn = await self.page.query_selector('button[aria-label="Ask"], button[aria-label="Send"]')
                if submit_btn:
                    await submit_btn.click()
                else:
                    await self.page.keyboard.press("Enter")

                self.last_used = time.time()

                # Stream tokens
                token_count = 0
                while True:
                    try:
                        token = await asyncio.wait_for(stream_queue.get(), timeout=45.0)
                    except asyncio.TimeoutError:
                        logger.error(f"[{self.session_id}] Timed out waiting for stream response")
                        self.has_errors = True
                        break

                    if token is None:
                        break

                    token_count += 1
                    yield token

                if error_holder:
                    err_msg = " | ".join(error_holder)
                    logger.error(f"[{self.session_id}] Duck.ai API error: {err_msg}")
                    self.has_errors = True
                    raise RuntimeError(f"Duck.ai upstream error: {err_msg}")

            except Exception as e:
                self.has_errors = True
                raise e
            finally:
                self.page.remove_listener("response", on_response)
                # Cleanup chat for next caller
                await self.reset()

    async def close(self):
        """Close browser page."""
        try:
            await self.page.close()
        except Exception:
            pass


class DuckAIClientPool:
    """Connection pool maintaining warm browser sessions to Duck.ai."""

    def __init__(self):
        self._playwright = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._pool: List[DuckAISession] = []
        self._lock = asyncio.Lock()
        self._semaphore = asyncio.Semaphore(settings.MAX_CONCURRENT_SESSIONS)
        self._is_running = False

    async def start(self):
        """Initialize browser and pre-warm default session."""
        if self._is_running:
            return

        logger.info("Initializing Playwright browser and session pool...")
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(
            headless=settings.BROWSER_HEADLESS,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-infobars",
                "--window-size=1440,900"
            ]
        )

        self._context = await self._browser.new_context(
            user_agent=settings.USER_AGENT,
            viewport={"width": 1440, "height": 900},
            extra_http_headers={
                "sec-ch-ua": settings.SEC_CH_UA,
                "sec-ch-ua-mobile": "?0",
                "sec-ch-ua-platform": '"macOS"'
            }
        )

        # Apply stealth script
        await self._context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => false });
            window.chrome = { runtime: {} };
        """)

        self._is_running = True
        logger.info("Pre-warming initial Duck.ai session...")
        try:
            session = await self._create_session(settings.DEFAULT_MODEL)
            self._pool.append(session)
            logger.info("Initial session ready and pre-warmed.")
        except Exception as e:
            logger.error(f"Failed to pre-warm initial session: {e}")

    async def _create_session(self, target_model: str) -> DuckAISession:
        """Create and initialize a new browser page session."""
        session_id = str(uuid.uuid4())[:8]
        page = await self._context.new_page()
        session = DuckAISession(page, session_id)
        await session.init(target_model)
        return session

    async def acquire_session(self, target_model: str) -> DuckAISession:
        """Acquire a ready session from pool or spawn a new one."""
        await self._semaphore.acquire()
        async with self._lock:
            # Check for an idle matching session
            for session in list(self._pool):
                if not session.lock.locked() and not session.has_errors:
                    # Clean up expired sessions
                    if time.time() - session.created_at > settings.SESSION_TIMEOUT_SECONDS:
                        self._pool.remove(session)
                        asyncio.create_task(session.close())
                        continue

                    # If model matches or can be reused
                    self._pool.remove(session)
                    return session

            # Create fresh session if pool empty
            session = await self._create_session(target_model)
            return session

    async def release_session(self, session: DuckAISession):
        """Release session back into the pool."""
        try:
            if session.has_errors or (time.time() - session.created_at > settings.SESSION_TIMEOUT_SECONDS):
                logger.info(f"[{session.session_id}] Discarding stale or failed session.")
                await session.close()
            else:
                async with self._lock:
                    if len(self._pool) < settings.MAX_CONCURRENT_SESSIONS:
                        self._pool.append(session)
                    else:
                        await session.close()
        finally:
            self._semaphore.release()

    async def shutdown(self):
        """Shutdown all active sessions and the browser."""
        logger.info("Shutting down DuckAIClientPool...")
        self._is_running = False
        async with self._lock:
            for session in self._pool:
                await session.close()
            self._pool.clear()

        if self._context:
            await self._context.close()
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()
        logger.info("DuckAIClientPool stopped.")

def format_openai_messages(messages: List[ChatMessage]) -> str:
    """Format OpenAI conversation messages into a clean prompt string for Duck.ai."""
    if not messages:
        return ""
    if len(messages) == 1:
        content = messages[0].content
        if isinstance(content, list):
            return " ".join(part.get("text", "") for part in content if isinstance(part, dict))
        return str(content)

    formatted_parts = []
    for msg in messages:
        role = msg.role.capitalize()
        content = msg.content
        if isinstance(content, list):
            text_val = " ".join(part.get("text", "") for part in content if isinstance(part, dict))
        else:
            text_val = str(content)
        
        if msg.role == "system":
            formatted_parts.append(f"[System Instruction: {text_val}]")
        else:
            formatted_parts.append(f"{role}: {text_val}")

    return "\n\n".join(formatted_parts)

# Global client pool instance
client_pool = DuckAIClientPool()
