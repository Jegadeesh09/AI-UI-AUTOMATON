import google.generativeai as genai
from google.api_core import exceptions as google_exceptions
import json
import re
import os
from openai import OpenAI, RateLimitError
from backend.config.config_manager import config_manager
from backend.utils.logger import log_to_ui

class LLMService:
    def __init__(self):
        self.total_tokens_in_session = 0

    def reset_token_count(self):
        self.total_tokens_in_session = 0

    def get_total_tokens(self):
        return self.total_tokens_in_session

    def _get_client(self):
        config = config_manager.get_config()
        is_paid = config.get("IS_PAID_LLM", True)
        provider = config.get("LLM_PROVIDER", "Gemini")
        model_name = config.get("MODEL_NAME", "gemini-1.5-pro")

        if not is_paid:
            base_url = config.get("OLLAMA_BASE_URL", "http://localhost:11434/v1")
            if not base_url.endswith("/v1"):
                base_url = base_url.rstrip("/") + "/v1"
            return "openai", OpenAI(base_url=base_url, api_key="ollama"), model_name

        if provider == "Gemini":
            api_key = config.get("GEMINI_API_KEY", "")
            genai.configure(api_key=api_key)
            return "gemini", genai.GenerativeModel(model_name), model_name
        
        elif provider == "OpenAI":
            api_key = config.get("GPT_API_KEY", "")
            return "openai", OpenAI(api_key=api_key), model_name
        
        elif provider == "DeepSeek":
            api_key = config.get("DEEPSEEK_API_KEY", "")
            return "openai", OpenAI(api_key=api_key, base_url="https://api.deepseek.com"), model_name

        api_key = config.get("GEMINI_API_KEY", "")
        genai.configure(api_key=api_key)
        return "gemini", genai.GenerativeModel("gemini-1.5-pro"), "gemini-1.5-pro"

    def _call_llm(self, system_prompt, user_prompt):
        ptype, client, model = self._get_client()
        log_to_ui("Step 1: LLM called")
        
        try:
            if ptype == "gemini":
                full_prompt = f"{system_prompt}\n\n{user_prompt}"
                print(f"🤖 LLM Call [Gemini]: {model}")
                response = client.generate_content(full_prompt)
                try:
                    tokens = response.usage_metadata.total_token_count
                    self.total_tokens_in_session += tokens
                    log_to_ui(f"Tokens used in this call: {tokens}", type="token", metadata={"total_tokens": self.total_tokens_in_session})
                except:
                    pass
                return response.text.strip()
            else:
                print(f"🤖 LLM Call [OpenAI/Ollama]: {model}")
                
                # Optimization for Ollama speed
                extra_params = {}
                if "ollama" in str(client.base_url).lower():
                    extra_params = {
                        "extra_body": {
                            "options": {
                                "temperature": 0.1,
                                "top_p": 0.9,
                                "num_ctx": 8192,
                                "num_predict": 2048,
                                "num_thread": 12,
                                "repeat_penalty": 1.0,
                                "mirostat": 0,
                                "num_gpu": 1,
                                "tfs_z": 1.0,
                                "typical_p": 1.0,
                                "low_vram": False,
                                "vocab_only": False,
                                "use_mmap": True,
                                "use_mlock": False
                            }
                        }
                    }

                response = client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    **extra_params
                )
                try:
                    tokens = response.usage.total_tokens
                    self.total_tokens_in_session += tokens
                    log_to_ui(f"Tokens used in this call: {tokens}", type="token", metadata={"total_tokens": self.total_tokens_in_session})
                except:
                    pass
                return response.choices[0].message.content.strip()
        except (google_exceptions.ResourceExhausted, RateLimitError) as e:
            print(f"❌ API Limit Exceeded: {str(e)}")
            raise Exception("API limit quota is exceeded") from e
        except Exception as e:
            print(f"❌ LLM Call Failed: {str(e)}")
            import traceback
            traceback.print_exc()
            raise e

    def generate_bdd_from_story(self, story_id, story_text):
        system_prompt = f"""
        You are a Senior QA Engineer. Convert the user story into a BDD Gherkin feature.
        Rules: Output ONLY Gherkin syntax. Feature name MUST be Story ID. No explanations.
        Story ID: {story_id}
        """
        return self._call_llm(system_prompt, f"Story:\n{story_text}")

    def generate_bdd_from_trace(self, trace_actions):
        system_prompt = """
        You are a Senior QA Engineer. Convert the following sequence of recorded browser actions into a BDD Gherkin feature.
        RULES:
        1. Output ONLY Gherkin syntax.
        2. Feature name should be 'RecordedSession'.
        3. Identify high-level steps (Given/When/Then).
        4. Represent assertions as 'Then' steps.
        5. Sensitive data is marked as <Sensitive Data>. Keep it exactly as <Sensitive Data> so the user can replace it later with a data reference.
        6. Consolidate multiple clicks/types into logical business steps if possible.
        7. For dropdowns (SELECT actions), use steps like 'Select "Text" from "Dropdown Label"'.
        8. For drag and drop (DRAG_AND_DROP actions), use steps like 'Drag "Source Element" and drop onto "Target Element"'.
        9. For navigation (NAVIGATE actions), use steps like 'Navigate to "URL"'.
        """
        user_prompt = f"Recorded Actions:\n{json.dumps(trace_actions, indent=2)}"
        return self._call_llm(system_prompt, user_prompt)

    def _extract_json(self, text):
        """Extract JSON from LLM response more robustly"""
        # Remove markdown code blocks
        text = re.sub(r'```json\s*', '', text)
        text = re.sub(r'```', '', text)
        text = text.strip()
        
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # Try to find array or object in the text
            match = re.search(r'(\[.*\]|\{.*\})', text, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(0))
                except json.JSONDecodeError:
                    # One more attempt: handle common LLM mistakes like single quotes
                    cleaned = match.group(0).replace("'", '"')
                    try:
                        return json.loads(cleaned)
                    except:
                        pass
        return None

    def generate_nav_steps_from_bdd(self, bdd_content):
        system_prompt = """
        Act as a Test Automation Architect.
        Convert the Gherkin Feature into a simplified JSON List of robot navigation instructions.
        RULES:
        1. Return ONLY a JSON Array of Strings.
        2. Commands: 'GOTO: <url>', 'CLICK: <text>', 'TYPE: <label>=<value>', 'SELECT: <label>=<text>', 'VALIDATE: <text>', 'DRAG_AND_DROP: <source> to <target>'.
        3. No 'Given/When/Then'.
        4. Be descriptive. For 'CLICK: Submit', ensure 'Submit' is the actual text or role of the element.
        5. If the BDD mentions a specific URL, use it in 'GOTO'.
        6. For each Scenario, start with a step 'SCENARIO: <Scenario Name>'.
        7. Use 'SELECT' for dropdowns/select elements.
        8. GHERKIN TABLES: If a step includes a table (e.g. Then I should see: | Param | Value |), convert each row of the table into an individual 'VALIDATE: <Param>=<Value>' step.
        """
        text = self._call_llm(system_prompt, f"BDD Content:\n{bdd_content}")
        result = self._extract_json(text)
        if result is not None and isinstance(result, list):
            return result
        raise Exception("Failed to parse navigation steps from LLM response")

    def heal_step(self, step_goal, current_url, page_context, previous_steps_summary, error_msg=""):
        system_prompt_template = """
        You are an AI Self-Healing Agent for UI Automation.
        A step in the automation flow has failed. Your goal is to find the best next action to achieve the intended goal on the current page.

        INTENT:
        The user wanted to perform: [[STEP_GOAL]]

        CONTEXT:
        - Current URL: [[CURRENT_URL]]
        - Page Elements (Simplified): [[PAGE_CONTEXT]]
        - History: [[HISTORY]]
        - Last Error: [[ERROR_MSG]]

        RULES:
        1. Analyze the page elements to find the correct target for the goal.
        2. If the last error indicates the wrong element type (e.g., trying to fill a link), look for a proper <input> or <textarea> instead.
        3. Semantic matching is key: If 'Login' is missing but 'Sign In' exists, use 'Sign In'.
        4. If an unexpected page/modal appeared (e.g. OTP, cookie consent), handle it as a step towards the goal.
        5. For SELECT actions, look for <select> elements or custom dropdowns (buttons that open menus).
        6. Return ONLY a JSON object:
           {
             "action": "CLICK" | "TYPE" | "SELECT" | "NAVIGATE" | "WAIT" | "FAIL",
             "selector": "css or xpath selector",
             "stable_selector": "Suggest a stable selector if possible (e.g. [data-testid='...'] or #id)",
             "value": "the value to type (if action is TYPE)",
             "reason": "Explain your reasoning (e.g., 'Previous element was a link, found the actual password input field instead')",
             "confidence": 0.0 to 1.0
           }
        6. Prioritize stable selectors: data-testid > id > aria-label > role > text.
        7. CSS selectors are preferred. Use absolute XPaths ONLY as a last resort.
        """
        
        system_prompt = system_prompt_template.replace("[[STEP_GOAL]]", str(step_goal)) \
                                             .replace("[[CURRENT_URL]]", str(current_url)) \
                                             .replace("[[PAGE_CONTEXT]]", str(page_context)) \
                                             .replace("[[HISTORY]]", str(previous_steps_summary)) \
                                             .replace("[[ERROR_MSG]]", str(error_msg))

        prompt = f"Goal: {step_goal}\nError: {error_msg}\nURL: {current_url}\nElements: {page_context}\nHistory: {previous_steps_summary}"
        text = self._call_llm(system_prompt, prompt)
        result = self._extract_json(text)
        if result is not None and isinstance(result, dict):
            return result
        return {"action": "FAIL", "reason": "Failed to parse AI response", "confidence": 0}

    def generate_code_from_bdd_and_map(self, story_id, bdd, trace_log_json, data_context=None, suite="Default"):
        data_instruction = ""
        if data_context:
            filename = data_context.get("filename")
            structure = data_context.get("structure")
            data_instruction = f"""
        DATA DRIVEN TESTING:
        - The test must use data from 'backend/data/{filename}'.
        - The file has the following columns/keys: {structure}.
        - You MUST generate code that reads this file (CSV, JSON, or Excel) and iterates through the data if applicable, or uses it for validation.
        - Use pandas to read the file.
        - If the file is missing, the test should fail with a clear message that will be captured in the report.
        """

        system_prompt = f"""
        You are an expert Senior Test Automation Architect.
        Your task is to generate a Playwright Python automation test using pytest (Sync API)
        from a BDD story, execution TRACE LOG, and selector data.

        MANDATORY GENERATION CONTRACT:
        1. Use Python 3.x, pytest, playwright-python (Sync API).
        2. Use POM (Page Object Model). Define a Page Class and the test functions in the same file.
        3. DO NOT manually launch playwright or browser. Use the `page` fixture provided by pytest.
        4. SCENARIO ISOLATION: Generate a SEPARATE test function for EVERY scenario in the BDD. This ensures that if one scenario fails, others still run.
        3. DEDUPLICATE SELECTORS: Store all selectors (XPaths/CSS) as class variables or constants at the top of the Page Class. If multiple steps use the same element (even if the action is different, like CLICK then TYPE), they MUST use the same variable.
        4. No duplicate XPath/CSS strings in the code. Every unique selector MUST be defined exactly once as a class attribute.
        5. Return ONLY valid Python source code. NO markdown.
        6. DATA INHERITANCE & SENSITIVE DATA:
           - If a value is in the format <FileName.ColumnName_RowNumber>, generate code to read this specific cell from 'backend/data/FileName.csv' (or .xlsx, .xls, .json).
           - Row 2 in the file is the first data row (pd.iloc[0]).
           - Use pandas (`pd`) to read the data file.
           - SENSITIVE DATA: If a value is <Sensitive Data>, it MUST be fetched from a data document using the existing flow. Avoid hardcoding credentials.

        STORY ↔ SCRIPT CONSISTENCY:
        - URLs, actions, and assertions MUST match the story.
        - Use `page.select_option(selector, label=...)` for SELECT actions.
        - For Drag and Drop: use `page.drag_and_drop(source_selector, target_selector)`.

        SELECTOR & LOCATOR RULES:
        1. Use selector values (XPath or CSS) from the TRACE LOG for every step.
        2. SYNCHRONIZATION & WAITS:
           - CRITICAL: Test scripts MUST have robust wait/sleep handling.
           - ALWAYS include `page.wait_for_selector(selector, state="visible", timeout=30000)` before any interaction (CLICK, TYPE, SELECT).
           - For navigation (GOTO) or after a click that causes a page load, ALWAYS use `page.wait_for_load_state("networkidle")`.
           - If an element is expected to disappear, use `page.wait_for_selector(selector, state="hidden")`.
           - Use `page.wait_for_timeout(2000)` if a brief pause is needed for animations or state changes that aren't easily detectable.
           - Ensure the test doesn't fail due to flaky loading; be generous with timeouts but favor intelligent waits over hard sleeps.
        3. ABSOLUTELY FORBIDDEN: NEVER use absolute XPaths like /html/body/div...
        4. Selector Fix Priority: data-testid, id, unique stable attributes, text-based XPath normalize-space().
        5. DO NOT generate random selectors.

        ALLURE REPORTING:
        - The test will be run with `allure-pytest`.
        - Use `allure.step("Step description")` for EVERY step.
        - For EVERY step, take a screenshot and attach it to Allure.
        - CRITICAL: Ensure the screenshot filename does not contain special characters like ':', '/', '?', or '*'.
        - Use this EXACT pattern for screenshots:
          ```python
          import re
          # inside the test step
          safe_name = re.sub(r'[^a-zA-Z0-9_]', '_', step_description)[:50]
          screenshot_path = f"backend/storage/suites/{suite}/screenshots/{story_id}/step_{{i}}_{{safe_name}}.png"
          os.makedirs(os.path.dirname(screenshot_path), exist_ok=True)
          page.screenshot(path=screenshot_path)
          allure.attach.file(screenshot_path, name=f"Step {{i}}", attachment_type=allure.attachment_type.PNG)
          ```
        - Import `allure` at the top.
        - The test function should be `def test_{story_id}(page):`.
        
        STORY ID: {story_id}
        SUITE: {suite}
        """
        
        content = f"--- BDD ---\n{bdd}\n\n--- TRACE LOG ---\n{trace_log_json}"
        raw_code = self._call_llm(system_prompt, f"Content:\n{content}")
        raw_code = re.sub(r'```python\s*', '', raw_code)
        raw_code = re.sub(r'```', '', raw_code)
        return raw_code

llm_service = LLMService()
