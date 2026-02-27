import json
import asyncio
from playwright.async_api import async_playwright
from backend.config.config_manager import config_manager

RECORD_SCRIPT_JS = """
(function() {
    if (window.is_recording_initialized) return;
    window.is_recording_initialized = true;
    console.log('AI Automation Recorder: Initializing...');

    const isSensitive = (el) => {
        if (el.type === 'password') return true;
        const sensitiveKeywords = ['password', 'passwd', 'pwd', 'secret', 'token', 'creditcard', 'cvv'];
        const attrs = ['name', 'id', 'placeholder', 'aria-label'];
        for (const attr of attrs) {
            const val = el.getAttribute(attr)?.toLowerCase() || '';
            if (sensitiveKeywords.some(k => val.includes(k))) return true;
        }
        if (el.id) {
            const label = document.querySelector(`label[for="${el.id}"]`);
            if (label) {
                const labelText = label.innerText.toLowerCase();
                if (sensitiveKeywords.some(k => labelText.includes(k))) return true;
            }
        }
        return false;
    };

    const getSelector = (el) => {
        if (!el || el.tagName === 'HTML') return '';
        if (el.tagName === 'BODY') return 'body';

        // 1. Data Attributes (Strongest)
        const testIdAttrs = ['data-testid', 'data-test', 'data-qa', 'data-cy'];
        for (const attr of testIdAttrs) {
            if (el.getAttribute(attr)) return `[${attr}='${el.getAttribute(attr)}']`;
        }
        
        // 2. ID (if stable)
        if (el.id && !el.id.match(/[0-9]{5,}/) && !el.id.includes('ember') && !el.id.includes('react')) {
            return `#${el.id}`;
        }
        
        // 3. Name or ARIA Label
        if (el.getAttribute('name')) return `${el.tagName.toLowerCase()}[name='${el.getAttribute('name')}']`;
        if (el.getAttribute('aria-label')) return `${el.tagName.toLowerCase()}[aria-label='${el.getAttribute('aria-label')}']`;

        // 4. Unique Role + Text
        const role = el.getAttribute('role');
        const text = el.innerText?.trim();
        if (text && text.length > 0 && text.length < 50) {
             if (['BUTTON', 'A', 'SPAN', 'LABEL'].includes(el.tagName)) {
                 // Try text-based XPath
                 return `//${el.tagName.toLowerCase()}[contains(normalize-space(.), '${text.replace(/'/g, "\\'").substring(0, 30)}')]`;
             }
        }

        // 5. Hierarchy-based fallback
        let path = el.tagName.toLowerCase();
        if (el.parentNode && el.parentNode.tagName !== 'HTML') {
            const siblings = Array.from(el.parentNode.children).filter(s => s.tagName === el.tagName);
            if (siblings.length > 1) {
                const index = siblings.indexOf(el) + 1;
                path += `:nth-of-type(${index})`;
            }
            const parentSelector = getSelector(el.parentNode);
            if (parentSelector) path = parentSelector + ' > ' + path;
        }
        return path;
    };

    let lastAction = null;
    const logAction = async (data) => {
        // Prevent duplicate consecutive actions with same data (ignore timestamp for comparison)
        const currentAction = JSON.stringify({ ...data, url: window.location.href });
        if (lastAction === currentAction) return;
        
        // For TYPE actions, only store the last state for a particular selector to avoid keypress flood
        if (data.action === 'TYPE' && lastAction) {
            const last = JSON.parse(lastAction);
            if (last.action === 'TYPE' && last.selector === data.selector) {
                // Skip if it's the same field, but don't set lastAction yet so we capture the final value on blur/change
                // Actually handleInputChange already handles this by listening to 'change'/'blur'
            }
        }

        lastAction = currentAction;

        if (window.emitRecorderAction) {
            window.emitRecorderAction({
                ...data,
                timestamp: Date.now(),
                url: window.location.href
            });
        }
    };

    document.addEventListener('click', (e) => {
        if (['INPUT', 'SELECT', 'TEXTAREA'].includes(e.target.tagName)) return;
        const selector = getSelector(e.target);
        logAction({ action: 'CLICK', selector, text: e.target.innerText?.trim().substring(0, 50) });
    }, true);

    const handleInputChange = (e) => {
        if (['INPUT', 'SELECT', 'TEXTAREA'].includes(e.target.tagName)) {
            const el = e.target;
            
            // For text inputs, only capture on BLUR to avoid duplicates with 'change'
            // and to avoid capturing every keystroke.
            if (['text', 'password', 'email', 'number', 'tel', 'url', 'search'].includes(el.type) || el.tagName === 'TEXTAREA') {
                if (e.type !== 'blur') return; 
            }
            
            // For checkboxes, radios, and SELECT, capture on CHANGE
            if (['checkbox', 'radio'].includes(el.type) || el.tagName === 'SELECT') {
                if (e.type !== 'change') return;
            }

            const selector = getSelector(el);
            const sensitive = isSensitive(el);
            const value = sensitive ? '<Sensitive Data>' : el.value;
            const action = el.tagName === 'SELECT' ? 'SELECT' : 'TYPE';
            const label = el.placeholder || el.name || el.getAttribute('aria-label') || el.id || '';
            
            let extra = {};
            if (el.tagName === 'SELECT') {
                const selectedOption = el.options[el.selectedIndex];
                extra.text = selectedOption ? selectedOption.text : '';
                // Also capture the value/label for better BDD generation
                logAction({ action: 'SELECT', selector, value: selectedOption.value, label: label, text: selectedOption.text });
                return;
            }

            logAction({ 
                action, 
                selector, 
                value, 
                label,
                ...extra
            });
        }
    };

    document.addEventListener('change', handleInputChange, true);
    document.addEventListener('blur', handleInputChange, true);

    // Drag and Drop support
    let dragSelector = null;
    document.addEventListener('dragstart', (e) => {
        dragSelector = getSelector(e.target);
    }, true);

    document.addEventListener('drop', (e) => {
        const dropSelector = getSelector(e.target);
        logAction({ 
            action: 'DRAG_AND_DROP', 
            selector: dragSelector, 
            target: dropSelector 
        });
        dragSelector = null;
    }, true);

    // Navigation support
    const handleNavigation = () => {
        logAction({ action: 'NAVIGATE', url: window.location.href, title: document.title });
    };
    window.addEventListener('popstate', handleNavigation);
    window.addEventListener('hashchange', handleNavigation);
    
    // Capture initial navigation if not already captured
    if (window.location.href !== 'about:blank') {
        setTimeout(handleNavigation, 500);
    }

    document.addEventListener('keydown', (e) => {
        if (e.code === 'Space') {
            const selection = window.getSelection();
            const selectedText = selection.toString().trim();
            if (selectedText) {
                let element = selection.anchorNode.parentElement;
                const selector = getSelector(element);
                const span = document.createElement('span');
                span.style.backgroundColor = 'rgba(0, 255, 0, 0.4)';
                span.style.border = '2px solid #00ff00';
                span.style.borderRadius = '2px';
                span.style.padding = '1px';
                span.style.zIndex = '9999';
                try {
                    const range = selection.getRangeAt(0);
                    range.surroundContents(span);
                    setTimeout(() => {
                        const parent = span.parentNode;
                        if (parent) {
                            while (span.firstChild) parent.insertBefore(span.firstChild, span);
                            parent.removeChild(span);
                        }
                    }, 1500);
                } catch (err) {}
                logAction({ action: 'ASSERT', text: selectedText, selector });
                e.preventDefault();
            }
        }
    });
    console.log('AI Automation Recorder: Running...');
})();
"""

class RecorderAgent:
    def __init__(self):
        self.context = None
        self.browser = None
        self.actions = []
        self.p = None
        self.status = "idle" # idle, recording, completed
        self.stop_event = asyncio.Event()

    async def _on_action(self, action):
        url = action.get('url', '').lower()
        # Filter out Google, chrome://, and about:blank
        if 'google.com' in url or 'chrome://' in url or 'about:blank' in url:
            return
        print(f"🎥 [Recorder] Captured: {action.get('action')} at {url}")
        self.actions.append(action)

    async def start_session(self):
        config = config_manager.get_config()
        inc_mode = config.get("INC_MODE", False)
        print(f"DEBUG: RecorderAgent.start_session called. INC_MODE in config: {inc_mode}")

        # Cleanup any existing session first
        if self.p or self.browser or self.context:
            print("🔄 RecorderAgent: Cleaning up existing session before starting new one...")
            try:
                if self.context: await self.context.close()
                if self.browser: await self.browser.close()
                if self.p: await self.p.stop()
            except: pass
            
        self.actions = []
        self.status = "recording"
        self.stop_event.clear()
        self.p = await async_playwright().start()

        chrome_exe = config.get("CHROME_EXECUTABLE_PATH", "")
        chrome_user_data = config.get("CHROME_USER_DATA_DIR", "")
        launch_args = ["--disable-blink-features=AutomationControlled"]
        
        print(f"🚀 RecorderAgent: Starting session (Incognito: {inc_mode}, Chrome Path: {chrome_exe or 'System Default'})")

        try:
            if inc_mode:
                # 🛠️ TRULY INCOGNITO: Launch regular browser with --incognito and use a fresh context
                # Force --incognito in launch args
                if "--incognito" not in launch_args:
                    launch_args.append("--incognito")

                launch_args.extend([
                    "--no-first-run",
                    "--no-default-browser-check",
                    "--no-sandbox"
                ])
                print(f"   🚀 Launching with args: {launch_args}")
                self.browser = await self.p.chromium.launch(
                    executable_path=chrome_exe if chrome_exe else None,
                    channel="chrome" if not chrome_exe else None,
                    headless=False,
                    args=launch_args
                )
                self.context = await self.browser.new_context()
                print(f"   ✅ Browser launched in Incognito mode. Context is incognito: {self.context}")
            else:
                # 🛠️ NORMAL MODE: Use persistent context to maintain state/profile
                user_data_dir = chrome_user_data if chrome_user_data and os.path.exists(chrome_user_data) else os.path.join(os.getcwd(), "backend/storage/user_data")
                os.makedirs(user_data_dir, exist_ok=True)

                print(f"   Using Profile: {user_data_dir}")
                self.context = await self.p.chromium.launch_persistent_context(
                    user_data_dir,
                    executable_path=chrome_exe if chrome_exe else None,
                    channel="chrome" if not chrome_exe else None,
                    headless=False,
                    args=launch_args
                )
                self.browser = None # In persistent mode, the context handles the browser lifecycle
                print("   ✅ Browser launched in Normal (Persistent) mode.")

        except Exception as e:
            print(f"⚠️ RecorderAgent: Failed to launch browser with primary strategy ({e}). Falling back to fresh bundled Chromium.")
            # Absolute fallback
            fallback_args = ["--incognito"] if inc_mode else []
            self.browser = await self.p.chromium.launch(headless=False, args=fallback_args)
            self.context = await self.browser.new_context()
        await self.context.expose_function("emitRecorderAction", self._on_action)
        await self.context.add_init_script(RECORD_SCRIPT_JS)
        
        page = await self.context.new_page()
        
        # Listen for browser/page closure
        page.on("close", lambda p: asyncio.create_task(self._handle_auto_stop()))
        self.browser.on("disconnected", lambda b: asyncio.create_task(self._handle_auto_stop()))

        default_url = config.get("DEFAULT_URL", "https://www.google.com")
        await page.goto(default_url)
        return page

    async def _handle_auto_stop(self):
        if self.status == "recording":
            print("🛑 RecorderAgent: Browser/Page closed by user. Stopping session automatically...")
            await self.stop_session()

    async def stop_session(self):
        if self.status == "idle" and not self.context:
            return self.actions

        try:
            self.status = "completed"
            print("💾 RecorderAgent: Closing browser and context...")
            await asyncio.sleep(0.5)
            
            # Close context first
            if self.context:
                try:
                    await self.context.close()
                except:
                    pass

            # Close browser if it's still open
            if self.browser:
                try:
                    await self.browser.close()
                except:
                    pass
            
            if self.p:
                try:
                    await self.p.stop()
                except:
                    pass
            
            self.context = None
            self.browser = None
            self.p = None
            
            print(f"📊 RecorderAgent: Sorting {len(self.actions)} actions...")
            # Ensure every action has a timestamp to avoid sort errors
            for a in self.actions:
                if 'timestamp' not in a:
                    import time
                    a['timestamp'] = int(time.time() * 1000)
            
            self.actions.sort(key=lambda x: x.get('timestamp', 0))
            print("✅ RecorderAgent: Session stopped and actions sorted.")
            return self.actions
        except Exception as e:
            print(f"❌ RecorderAgent Stop Session Error: {e}")
            import traceback
            traceback.print_exc()
            return self.actions # Return what we have anyway

recorder_agent = RecorderAgent()
