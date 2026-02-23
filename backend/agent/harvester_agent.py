import json
import os
import asyncio
import shutil
import tempfile
from pathlib import Path
from playwright.async_api import async_playwright, Page
from backend.config.config_manager import config_manager
from backend.agent.browser_agent import browser_agent
from backend.utils.logger import log_to_ui

GET_BEST_SELECTOR_JS = r"""
(element) => {
    if (!element) return null;
    
    const getPath = (node) => {
        if (node.id && !node.id.match(/[0-9]{5,}/)) return `//*[@id='${node.id}']`;
        if (node === document.body) return '/html/body';
        let ix = 0;
        let siblings = node.parentNode.childNodes;
        for (let i = 0; i < siblings.length; i++) {
            let sibling = siblings[i];
            if (sibling === node) return getPath(node.parentNode) + '/' + node.tagName.toLowerCase() + '[' + (ix + 1) + ']';
            if (sibling.nodeType === 1 && sibling.tagName === node.tagName) ix++;
        }
        return '';
    };

    // 1. Data Test IDs
    const testIdAttrs = ['data-testid', 'data-test', 'data-qa', 'data-cy'];
    for (const attr of testIdAttrs) {
        if (element.getAttribute(attr)) return `[${attr}='${element.getAttribute(attr)}']`;
    }
    
    // 2. ID
    if (element.id && !element.id.match(/[0-9]{5,}/)) return `#${element.id}`;
    
    // 3. Name or Title
    if (element.getAttribute('name')) return `${element.tagName.toLowerCase()}[name='${element.getAttribute('name')}']`;
    if (element.getAttribute('title')) return `${element.tagName.toLowerCase()}[title='${element.getAttribute('title')}']`;

    // 4. ARIA Label or Placeholder
    const ariaLabel = element.getAttribute('aria-label');
    if (ariaLabel) return `${element.tagName.toLowerCase()}[aria-label='${ariaLabel}']`;
    if (element.getAttribute('placeholder')) return `${element.tagName.toLowerCase()}[placeholder='${element.getAttribute('placeholder')}']`;

    // 5. Role + Text (Semantic)
    const role = element.getAttribute('role');
    const text = element.innerText.trim().replace(/\s+/g, ' ');
    if (role && text && text.length < 50) {
        return `//${element.tagName.toLowerCase()}[@role='${role}' and contains(normalize-space(.), '${text}')]`;
    }
    if (text && text.length > 0 && text.length < 50 && ['BUTTON', 'A', 'SPAN', 'LABEL', 'H1', 'H2', 'H3'].includes(element.tagName)) {
        return `//${element.tagName.toLowerCase()}[contains(normalize-space(.), '${text}')]`;
    }

    // 6. Final fallback: Robust XPath
    return getPath(element);
}
"""

SIMPLIFY_DOM_JS = """
() => {
    const interactiveElements = [];
    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_ELEMENT);
    let node;
    while (node = walker.nextNode()) {
        const style = window.getComputedStyle(node);
        if (style.display === 'none' || style.visibility === 'hidden' || parseFloat(style.opacity) === 0) continue;
        
        const rect = node.getBoundingClientRect();
        if (rect.width === 0 || rect.height === 0) continue;

        const isClickable = ['BUTTON', 'A', 'INPUT', 'SELECT', 'TEXTAREA'].includes(node.tagName) || 
                           node.onclick || node.getAttribute('role') === 'button' ||
                           node.classList.contains('btn') || style.cursor === 'pointer';
        
        if (isClickable || (node.innerText.length < 100 && node.innerText.trim().length > 0)) {
            interactiveElements.push({
                tagName: node.tagName,
                id: node.id,
                text: node.innerText.trim().substring(0, 100),
                type: node.type,
                name: node.getAttribute('name'),
                title: node.getAttribute('title'),
                role: node.getAttribute('role'),
                ariaLabel: node.getAttribute('aria-label'),
                dataTestId: node.getAttribute('data-testid') || node.getAttribute('data-test') || node.getAttribute('data-qa'),
                placeholder: node.getAttribute('placeholder')
            });
        }
    }
    return interactiveElements.slice(0, 100);
}
"""

class HarvesterAgent:
    def _robust_copytree(self, src, dst):
        """Custom recursive copy that ignores locked files and common temp data"""
        if not os.path.exists(dst):
            os.makedirs(dst, exist_ok=True)
        
        ignore_patterns = ["Cache*", "Code Cache", "GPUCache", "Media Cache", "*.lock", "LOCK", "Singleton*", "TransportSecurity"]
        
        try:
            for item in os.listdir(src):
                s = os.path.join(src, item)
                d = os.path.join(dst, item)
                
                # Skip ignored patterns
                if any(Path(item).match(p) for p in ignore_patterns):
                    continue

                try:
                    if os.path.isdir(s):
                        self._robust_copytree(s, d)
                    else:
                        shutil.copy2(s, d)
                except Exception:
                    pass # Ignore locked files or individual errors
        except Exception:
            pass

    async def harvest(self, story_id, navigation_steps, recorded_trace=None, suite="Default"):
        """Async method to perform harvesting with real-time AI healing"""
        log_to_ui("Step: Hitting Harvester agent")
        print(f"⚡ [Harvester] Starting Smart Trace for: {story_id} (Suite: {suite})")
        interaction_log = []
        healed_steps_count = 0
        
        config = config_manager.get_config()
        headless = config.get("HEADLESS_AGENT", True)

        # Get Chrome paths from config
        chrome_exe = config.get("CHROME_EXECUTABLE_PATH", "")
        chrome_user_data = config.get("CHROME_USER_DATA_DIR", "")

        async with async_playwright() as p:
            # Setup User Data Dir and Executable
            user_data_dir = chrome_user_data if chrome_user_data and os.path.exists(chrome_user_data) else os.path.join(os.getcwd(), "backend/storage/user_data")
            os.makedirs(user_data_dir, exist_ok=True)
            executable_path = chrome_exe if chrome_exe and os.path.exists(chrome_exe) else None
            
            print(f"   Using Profile: {user_data_dir}")
            
            launch_args = ["--disable-blink-features=AutomationControlled"]
            temp_dir_obj = None
            
            try:
                print(f"   Attempting to launch Chrome (Channel: chrome, Exe: {executable_path})...")
                context = await p.chromium.launch_persistent_context(
                    user_data_dir,
                    headless=headless,
                    executable_path=executable_path,
                    channel="chrome" if not executable_path else None,
                    args=launch_args
                )
            except Exception as e:
                print(f"   ⚠️ Initial launch failed: {e}")
                if ("lock" in str(e).lower() or "used by another" in str(e).lower()) and os.path.exists(user_data_dir):
                    print(f"   ⚠️ Profile locked, cloning to temporary directory...")
                    temp_dir_obj = tempfile.TemporaryDirectory(prefix="chrome_profile_")
                    actual_user_data_dir = temp_dir_obj.name
                    try:
                        print(f"      Cloning profile... (this may take a few seconds)")
                        self._robust_copytree(user_data_dir, actual_user_data_dir)
                        context = await p.chromium.launch_persistent_context(
                            actual_user_data_dir,
                            headless=headless,
                            executable_path=executable_path,
                            channel="chrome" if not executable_path else None,
                            args=launch_args
                        )
                    except Exception as clone_e:
                        print(f"   ❌ Clone failed: {clone_e}. Falling back to bundled Chromium.")
                        context = await p.chromium.launch_persistent_context("", headless=headless)
                else:
                    print(f"   ❌ Launch failed. Falling back to bundled Chromium.")
                    context = await p.chromium.launch_persistent_context("", headless=headless)

            page = context.pages[0] if context.pages else await context.new_page()
            
            step_index = 0
            while step_index < len(navigation_steps):
                step = navigation_steps[step_index]
                print(f"   ▶ Step {step_index + 1}: {step}")
                log_entry = {"step_original": step}
                
                # Setup directories
                screenshot_dir = Path(f"backend/storage/suites/{suite}/screenshots") / story_id
                screenshot_dir.mkdir(parents=True, exist_ok=True)

                try:
                    # Clean the step query for logging
                    step_query = step.split(":", 1)[1].strip() if ":" in step else step
                    log_entry["element_query"] = step_query

                    if step.startswith("SCENARIO:"):
                        log_to_ui(f"Step: Collecting XPath of scenario & {step_query}")
                        log_entry["status"] = "SUCCESS"
                        log_entry["action"] = "SCENARIO_MARKER"
                        log_entry["scenario_name"] = step_query
                        interaction_log.append(log_entry)
                        step_index += 1
                        continue

                    if step.startswith("GOTO:"):
                        url = step.replace("GOTO:", "").strip()
                        await page.goto(url, wait_until="networkidle", timeout=30000)
                        screenshot_path = screenshot_dir / f"step_{step_index}_goto.png"
                        await page.screenshot(path=screenshot_path)
                        interaction_log.append({**log_entry, "status": "SUCCESS", "action": "GOTO", "screenshot": str(screenshot_path).replace("\\", "/")})
                        step_index += 1
                        continue

                    # EXECUTION LOOP WITH HEALING
                    success = False
                    error_context = ""
                    
                    # 1. Try recorded trace if available
                    target = None
                    if recorded_trace and step_index < len(recorded_trace):
                        rec_step = recorded_trace[step_index]
                        # Verify if types match (optional but safer)
                        rec_action = rec_step.get("action")
                        if (step.startswith("CLICK:") and rec_action == "CLICK") or \
                           (step.startswith("TYPE:") and rec_action == "TYPE") or \
                           (step.startswith("SELECT:") and rec_action == "SELECT"):
                            print(f"      📍 Using recorded selector: {rec_step.get('selector')}")
                            try:
                                target = page.locator(rec_step.get("selector")).first
                                await target.wait_for(state="attached", timeout=2000)
                                if await target.count() == 0:
                                    target = None
                            except:
                                target = None

                    # 2. Try best-effort finding if recorded trace failed or not available
                    if not target:
                        target = await self.find_element_best_effort(page, step)
                    if target and await target.count() > 0:
                        try:
                            if step.startswith("CLICK:"):
                                result = await self.smart_click(target, page)
                                if result["strategyUsed"] != "FAILED_TO_CLICK":
                                    log_entry.update({
                                        "selector": result["selector"],
                                        "action": "CLICK",
                                        "learning_note": result["strategyUsed"],
                                        "status": "SUCCESS"
                                    })
                                    success = True
                                else:
                                    error_context = "Click failed on all strategies"
                            elif step.startswith("TYPE:"):
                                query_part = step.replace("TYPE:", "").strip()
                                label, val = query_part.split("=", 1) if "=" in query_part else (query_part, "")
                                
                                # Resolve data if it's a placeholder
                                resolved_val = str(browser_agent.resolve_data(val))
                                
                                # Check if resolution failed for a data placeholder
                                if val.startswith("<") and val.endswith(">") and val not in ["<Sensitive Data>", "<data>"] and resolved_val == val:
                                    success = False
                                    error_context = f"DATA_MISSING: {val}"
                                    raise Exception(error_context)

                                is_sensitive = val.startswith("<") and val.endswith(">")

                                # Final safety check for resolved_val
                                if resolved_val is None:
                                    resolved_val = ""

                                print(f"      ⌨️ Typing: {resolved_val if not is_sensitive else '********'}")
                                await target.fill(value=resolved_val, timeout=5000)
                                log_entry.update({
                                    "selector": await self.get_xpath(target),
                                    "action": "TYPE",
                                    "value": val if is_sensitive else resolved_val, # Store placeholder if sensitive
                                    "status": "SUCCESS"
                                })
                                success = True
                            elif step.startswith("DRAG_AND_DROP:"):
                                query_part = step.replace("DRAG_AND_DROP:", "").strip()
                                source_q, target_q = query_part.split(" to ", 1) if " to " in query_part else (query_part, "")
                                
                                source_target = await self.find_element_best_effort(page, f"CLICK:{source_q}")
                                dest_target = await self.find_element_best_effort(page, f"CLICK:{target_q}")
                                
                                if source_target and dest_target:
                                    print(f"      Drag from {source_q} to {target_q}")
                                    await source_target.drag_to(dest_target)
                                    log_entry.update({
                                        "selector": await self.get_xpath(source_target),
                                        "target": await self.get_xpath(dest_target),
                                        "action": "DRAG_AND_DROP",
                                        "status": "SUCCESS"
                                    })
                                    success = True
                                else:
                                    error_context = "Source or target element for drag and drop not found"
                            elif step.startswith("SELECT:"):
                                query_part = step.replace("SELECT:", "").strip()
                                label, val = query_part.split("=", 1) if "=" in query_part else (query_part, "")
                                
                                # Resolve data if it's a placeholder
                                resolved_val = str(browser_agent.resolve_data(val))
                                
                                # Final safety check
                                if resolved_val is None:
                                    resolved_val = ""

                                print(f"      🔽 Selecting: {resolved_val}")
                                # Try select_option by label or value
                                try:
                                    await target.select_option(label=resolved_val, timeout=3000)
                                except:
                                    try:
                                        await target.select_option(value=resolved_val, timeout=2000)
                                    except Exception as e:
                                        print(f"      ⚠️ Failed to select option '{resolved_val}': {e}")
                                        raise e

                                log_entry.update({
                                    "selector": await self.get_xpath(target),
                                    "action": "SELECT",
                                    "value": resolved_val,
                                    "status": "SUCCESS"
                                })
                                success = True
                            elif step.startswith("VALIDATE:"):
                                await target.wait_for(state="visible", timeout=5000)
                                log_entry.update({
                                    "selector": await self.get_xpath(target),
                                    "action": "VALIDATE",
                                    "status": "SUCCESS"
                                })
                                success = True
                        except Exception as e:
                            error_context = f"Action failed: {str(e)}"
                    else:
                        error_context = "Target element not found by standard heuristics"

                    if success:
                        screenshot_path = screenshot_dir / f"step_{step_index}_success.png"
                        await page.screenshot(path=screenshot_path)
                        log_entry["screenshot"] = str(screenshot_path).replace("\\", "/")
                        interaction_log.append(log_entry)
                        step_index += 1
                        continue
                    
                    if "DATA_MISSING" in error_context:
                        print(f"      ❌ Data resolution failed: {error_context}. Skipping healing.")
                        raise Exception(error_context)

                    # 2. Trigger AI Healing if standard attempt failed
                    print(f"      ⚠️ {error_context}. Attempting AI healing...")
                    screenshot_path_fail = screenshot_dir / f"step_{step_index}_failed.png"
                    await page.screenshot(path=screenshot_path_fail)
                    
                    healed_action = await self.heal_flow_with_ai(page, step, interaction_log, error_context)
                    
                    if healed_action and healed_action.get("action") != "FAIL":
                        print(f"      ✨ AI Healed: {healed_action['reason']}")
                        healed_steps_count += 1
                        result = await self.execute_healed_action(page, healed_action)
                        
                        if result["status"] == "SUCCESS":
                            screenshot_path_healed = screenshot_dir / f"step_{step_index}_healed.png"
                            await page.screenshot(path=screenshot_path_healed)

                            interaction_log.append({
                                **log_entry,
                                "status": "HEALED",
                                "healed_action": healed_action,
                                "selector": healed_action.get("stable_selector") or result.get("selector"),
                                "action": healed_action["action"],
                                "learning_note": f"AI Healed: {healed_action['reason']}",
                                "screenshot": str(screenshot_path_healed).replace("\\", "/")
                            })
                            step_index += 1
                            continue
                        elif result["status"] == "RETRY":
                            # Don't increment step_index, let it retry the same goal
                            continue
                        else:
                            error_context = f"Healed action failed: {healed_action.get('action')}"
                    
                    # 3. If healing fails or gives up
                    print(f"      ❌ AI Healing failed for step: {step}. Skipping to next scenario...")
                    
                    # Try to get more context for the human-readable error
                    failed_tag = ""
                    try:
                        failed_tag = await target.evaluate("node => node.tagName") if target else ""
                    except: pass

                    interaction_log.append({
                        **log_entry, 
                        "status": "FAILED", 
                        "error": error_context,
                        "failed_tag": failed_tag,
                        "step_index": step_index + 1,
                        "screenshot": str(screenshot_path_fail).replace("\\", "/")
                    })

                    # SKIP TO NEXT SCENARIO
                    # Find next scenario marker
                    next_scenario_idx = -1
                    for i in range(step_index + 1, len(navigation_steps)):
                        if navigation_steps[i].startswith("SCENARIO:"):
                            next_scenario_idx = i
                            break
                    
                    if next_scenario_idx != -1:
                        step_index = next_scenario_idx
                        print(f"      ⏩ Skipped failed scenario. Resuming at Step {step_index + 1}")
                        continue
                    else:
                        # No more scenarios
                        print("      🏁 No more scenarios to execute.")
                        break

                except Exception as e:
                    print(f"      ❌ Unexpected error in loop: {str(e)}")
                    import traceback
                    traceback.print_exc()
                    interaction_log.append({
                        **log_entry,
                        "status": "FAILED",
                        "error": f"Unexpected execution error: {str(e)}",
                        "step_index": step_index + 1
                    })
                    break
            
            if not headless and healed_steps_count > 0:
                 print(f"   ✅ Finished with {healed_steps_count} healed steps. Waiting 5s before closing.")
                 await asyncio.sleep(5)

            await context.close()

        output_dir = Path(f"backend/storage/suites/{suite}/trace_logs")
        output_dir.mkdir(parents=True, exist_ok=True)
        json_path = output_dir / f"{story_id}_trace.json"
        
        with open(json_path, "w") as f:
            json.dump(interaction_log, f, indent=4)
            
        print(f"✅ [Harvester] Trace Log Saved: {json_path}")
        return json.dumps(interaction_log, indent=4)

    async def heal_flow_with_ai(self, page, step_goal, history, error_msg=""):
        """Call AI to heal the flow in real-time"""
        from backend.llm.llm_service import llm_service
        
        url = page.url
        elements = await page.evaluate(SIMPLIFY_DOM_JS)
        history_summary = [f"{h.get('action')}: {h.get('step_original')}" for h in history[-5:]]
        
        loop = asyncio.get_event_loop()
        try:
            return await loop.run_in_executor(
                None, 
                llm_service.heal_step, 
                step_goal, url, json.dumps(elements), ", ".join(history_summary), error_msg
            )
        except Exception as e:
            print(f"      ❌ AI Heal Call Failed: {e}")
            return None

    async def execute_healed_action(self, page: Page, healed_action):
        """Execute the action suggested by AI"""
        action = healed_action.get("action")
        selector = healed_action.get("selector")
        value = healed_action.get("value", "")

        try:
            if action == "CLICK":
                loc = page.locator(selector).first
                await loc.click(timeout=5000)
            elif action == "TYPE":
                loc = page.locator(selector).first
                # Resolve data if it's a placeholder
                resolved_val = str(browser_agent.resolve_data(value))
                if resolved_val is None: resolved_val = ""
                await loc.fill(value=resolved_val, timeout=5000)
            elif action == "SELECT":
                loc = page.locator(selector).first
                resolved_val = str(browser_agent.resolve_data(value))
                if resolved_val is None: resolved_val = ""
                try:
                    await loc.select_option(label=resolved_val, timeout=3000)
                except:
                    await loc.select_option(value=resolved_val, timeout=2000)
            elif action == "NAVIGATE":
                await page.goto(value, wait_until="networkidle")
            elif action == "WAIT":
                await asyncio.sleep(2)
                return {"status": "RETRY", "selector": selector}
            
            return {"status": "SUCCESS", "selector": selector}
        except Exception as e:
            print(f"      ❌ Healed action execution failed: {e}")
            return {"status": "FAILED", "selector": selector}

    async def smart_click(self, locator, page: Page):
        """Async click with multiple strategies"""
        try:
            await locator.click(timeout=3000)
            return {"selector": await self.get_xpath(locator), "strategyUsed": "Direct Click"}
        except: 
            pass

        try:
            await locator.click(force=True, timeout=3000)
            return {"selector": await self.get_xpath(locator), "strategyUsed": "Force Click"}
        except: 
            pass

        try:
            selector = await self.get_xpath(locator)
            if selector and "ERROR" not in selector:
                if selector.startswith("/") or selector.startswith("("):
                    parent = page.locator(f"xpath=({selector})/..")
                else:
                    parent = page.locator(selector).locator("..")
                await parent.click(timeout=3000)
                return {"selector": await self.get_xpath(parent), "strategyUsed": "Clicked Parent Element"}
        except: 
            pass

        try:
            await locator.evaluate("node => node.click()")
            return {"selector": await self.get_xpath(locator), "strategyUsed": "JS Click"}
        except: 
            pass

        return {"selector": await self.get_xpath(locator), "strategyUsed": "FAILED_TO_CLICK"}

    async def find_element_best_effort(self, page: Page, step: str):
        """Async element finding with multiple strategies and semantic prioritization"""
        query = step.split(":", 1)[1].strip()
        if (step.startswith("TYPE:") or step.startswith("SELECT:")) and "=" in query:
            query = query.split("=")[0]
        
        # Resolve query if it's a data placeholder
        query = browser_agent.resolve_data(query)

        # Define strategies
        strategies = []
        
        if step.startswith("TYPE:"):
            strategies.extend([
                lambda q: page.get_by_role("textbox", name=q),
                lambda q: page.get_by_role("search", name=q),
                lambda q: page.get_by_placeholder(q),
                lambda q: page.get_by_label(q)
            ])
        elif step.startswith("CLICK:") or step.startswith("SELECT:"):
            strategies.extend([
                lambda q: page.get_by_role("button", name=q),
                lambda q: page.get_by_role("link", name=q),
                lambda q: page.get_by_role("combobox", name=q),
                lambda q: page.get_by_role("listbox", name=q),
                lambda q: page.get_by_role("menuitem", name=q),
                lambda q: page.get_by_role("tab", name=q),
                lambda q: page.get_by_role("checkbox", name=q),
                lambda q: page.get_by_role("radio", name=q)
            ])
        
        # General text match fallback
        strategies.append(lambda q: page.get_by_text(q))

        for strategy in strategies:
            loc = strategy(query).first
            try:
                # Wait up to 2 seconds for each strategy
                await loc.wait_for(state="attached", timeout=2000)
                if await loc.count() > 0:
                    # Label check
                    tagName = await loc.evaluate("node => node.tagName")
                    if tagName == "LABEL":
                        for_id = await loc.getAttribute("for")
                        if for_id:
                            target = page.locator(f"id={for_id}")
                            if await target.count() > 0: return target
                    return loc
            except:
                continue

        return None

    async def get_xpath(self, locator):
        """Async Selector extraction (preferring stable selectors)"""
        try:
            return await locator.evaluate(GET_BEST_SELECTOR_JS)
        except:
            return "ERROR_SELECTOR"

harvester_agent = HarvesterAgent()
