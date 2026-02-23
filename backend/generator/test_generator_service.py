import os
import re
import json
import asyncio
from concurrent.futures import ThreadPoolExecutor
from backend.llm.llm_service import llm_service
from backend.agent.harvester_agent import harvester_agent
from backend.utils.file_util import save_to_file, get_file_structure
from backend.utils.logger import log_to_ui

class TestGeneratorService:
    def _extract_scenarios(self, bdd_content):
        """Extract all scenario names from Gherkin feature content"""
        scenarios = re.findall(r"Scenario:\s*(.*)", bdd_content)
        return [s.strip() for s in scenarios] or ["Unknown Scenario"]

    def _extract_feature_name(self, bdd_content):
        """Extract feature name from Gherkin feature content"""
        match = re.search(r"Feature:\s*(.*)", bdd_content)
        if match:
            # Clean name: remove everything except alphanumeric and spaces/underscores
            name = re.sub(r'[^a-zA-Z0-9\s_]', '', match.group(1).strip())
            # Replace spaces with underscores and collapse multiple underscores
            name = re.sub(r'[\s_]+', '_', name)
            return name.strip('_')
        return None

    def _detect_data_file(self, story_text, bdd_content=None):
        """Detect data files mentioned in the story text or BDD content"""
        # Look for "file.csv" patterns
        matches = re.findall(r'["\']([^"\']+\.(?:csv|json|xlsx|xls))["\']', story_text)
        
        # Also look for <file.column_row> patterns
        placeholder_matches = re.findall(r'<([^.]+)\.[^>]+>', story_text)
        if bdd_content:
            placeholder_matches += re.findall(r'<([^.]+)\.[^>]+>', bdd_content)
        
        found_files = matches + placeholder_matches
        
        for filename in found_files:
            # Try with and without extension
            for ext in ["", ".csv", ".xlsx", ".xls", ".json"]:
                full_name = filename + ext if ext else filename
                file_path = os.path.join("backend/data", full_name)
                if os.path.exists(file_path) and os.path.isfile(file_path):
                    structure = get_file_structure(file_path)
                    return {"filename": full_name, "structure": structure}
        return None

    def _run_async_harvest(self, story_id, nav_steps, recorded_trace=None, suite="Default"):
        """Run async harvest from sync context"""
        print(f"🔍 Starting async harvest for {story_id} (Suite: {suite})...")
        try:
            try:
                loop = asyncio.get_running_loop()
                future = asyncio.run_coroutine_threadsafe(
                    harvester_agent.harvest(story_id, nav_steps, recorded_trace=recorded_trace, suite=suite),
                    loop
                )
                return future.result(timeout=180)
            except RuntimeError:
                return asyncio.run(harvester_agent.harvest(story_id, nav_steps, recorded_trace=recorded_trace, suite=suite))
        except Exception as e:
            print(f"   ❌ Harvest failed: {str(e)}")
            # Return a failure trace instead of an empty list
            return json.dumps([{
                "status": "FAILED", 
                "error": f"Harvester process crashed: {str(e)}",
                "step_index": 0
            }])

    def generate_bdd_only(self, story_id, story_text, suite="Default"):
        """Phase 1 only: Generate BDD from story"""
        print(f"📝 Phase 1: Generating BDD for {story_id} (Suite: {suite})...")
        llm_service.reset_token_count()
        bdd_content = llm_service.generate_bdd_from_story(story_id, story_text)
        
        feature_name = self._extract_feature_name(bdd_content) or story_id
        # Sync: save same BDD content to both .feature and .txt
        save_to_file(bdd_content, f"backend/storage/suites/{suite}/bdd/{feature_name}.feature")
        save_to_file(bdd_content, f"backend/storage/suites/{suite}/stories/{feature_name}.txt")
        
        return bdd_content

    def generate_full_test(self, story_id, story_text, on_phase_change=None, bdd_content=None, suite="Default"):
        """Main method to generate test"""
        log_to_ui(f"🚀 Initializing generation for {story_id}...")
        print(f"🚀 Generating full test for: {story_id} (Suite: {suite})")
        old_story_id = story_id
        if not bdd_content:
            llm_service.reset_token_count()
        
        def update_phase(phase):
            if on_phase_change: on_phase_change(phase)

        data_context = self._detect_data_file(story_text, bdd_content=bdd_content)
        
        if not bdd_content:
            update_phase("Generating BDD started")
            bdd_content = llm_service.generate_bdd_from_story(story_id, story_text)
            update_phase("Generating BDD completed")
        
        # Determine feature name and save files before starting harvester
        feature_name = self._extract_feature_name(bdd_content) or story_id
        # Sync: save same BDD content to both .feature and .txt
        save_to_file(bdd_content, f"backend/storage/suites/{suite}/bdd/{feature_name}.feature")
        save_to_file(bdd_content, f"backend/storage/suites/{suite}/stories/{feature_name}.txt")
        
        # Rename trace log if it exists under the old story_id
        trace_dir = f"backend/storage/suites/{suite}/trace_logs"
        os.makedirs(trace_dir, exist_ok=True)
        old_trace_path = os.path.join(trace_dir, f"{old_story_id}_trace.json")
        new_trace_path = os.path.join(trace_dir, f"{feature_name}_trace.json")
        
        if old_story_id != feature_name and os.path.exists(old_trace_path) and not os.path.exists(new_trace_path):
            os.rename(old_trace_path, new_trace_path)
            print(f"🔄 Renamed trace log from {old_story_id} to {feature_name}")

        # Update story_id to feature_name for consistent file naming hereafter
        story_id = feature_name

        # Load recorded trace if available (e.g. from a Scan session)
        recorded_trace = None
        if os.path.exists(new_trace_path):
            try:
                with open(new_trace_path, "r", encoding="utf-8") as f:
                    recorded_trace = json.load(f)
                print(f"📖 Loaded recorded trace for {story_id}")
            except Exception as e:
                print(f"⚠️ Failed to load recorded trace: {e}")
        
        nav_steps = llm_service.generate_nav_steps_from_bdd(bdd_content)
        if not nav_steps:
            raise Exception("AI failed to generate navigation steps from the BDD. Please check your BDD format or Story content.")
        
        print(f"✅ Generated {len(nav_steps)} navigation steps.")

        update_phase("Launching the harvester agent")
        log_to_ui("🕵️ Step 2: Hitting Harvester agent - Analyzing UI elements...")
        log_to_ui("🔍 Step 3: Collecting XPath of scenario & scenario name...")
        trace_log = self._run_async_harvest(story_id, nav_steps, recorded_trace=recorded_trace, suite=suite)
        trace_data = json.loads(trace_log) if trace_log else []
        
        # Check for failure in trace. We don't raise exception anymore, just log to UI and continue if possible.
        # However, we still want to inform the user.
        failures = [t for t in trace_data if t.get("status") == "FAILED"]
        if failures:
            log_to_ui(f"Harvester completed with {len(failures)} failed steps. Check messages for details.", type="error")
            for failure in failures:
                error_msg = failure.get("error") or ""
                element_name = failure.get("element_query") or "Unknown Element"
                log_to_ui(f"Failed to harvest element '{element_name}': {error_msg}", type="error")

        healed_steps = [t for t in trace_data if t.get("status") == "HEALED"]
        
        update_phase("Script generation started")
        generated_code = llm_service.generate_code_from_bdd_and_map(
            story_id, bdd_content, trace_log, data_context=data_context, suite=suite
        )
        
        total_tokens = llm_service.get_total_tokens()
        log_to_ui(f"✅ LLM Completed - Total Tokens Used: {total_tokens}")
        
        script_path = f"backend/storage/suites/{suite}/scripts/test_{story_id}.py"
        save_to_file(generated_code, script_path)
        
        return {
            "story_id": story_id,
            "bdd": bdd_content[:500] + "..." if len(bdd_content) > 500 else bdd_content,
            "script_path": script_path,
            "data_context": data_context,
            "healing_report": {
                "total_steps": len(trace_data),
                "healed_steps": len(healed_steps),
                "details": healed_steps
            }
        }

    def self_heal(self, story_id, suite="Default"):
        """Self-heal existing test"""
        print(f"🔧 Self-healing test: {story_id} (Suite: {suite})")
        llm_service.reset_token_count()
        
        from backend.utils.file_util import read_file
        bdd_content = read_file(f"backend/storage/suites/{suite}/bdd/{story_id}.feature")
        if not bdd_content:
            raise Exception(f"BDD content not found: backend/storage/suites/{suite}/bdd/{story_id}.feature")
        
        nav_steps = llm_service.generate_nav_steps_from_bdd(bdd_content)
        if not nav_steps:
            raise Exception("AI failed to generate navigation steps from the BDD.")

        trace_log = self._run_async_harvest(story_id, nav_steps, suite=suite)
        trace_data = json.loads(trace_log)
        
        failure = next((t for t in trace_data if t.get("status") == "FAILED"), None)
        if failure:
            from backend.utils.pdf_util import generate_pdf_report
            screenshot = failure.get("screenshot")
            error_msg = failure.get("error") or ""
            step_idx = failure.get("step_index", 0)
            
            # Identify Scenario Name and Number
            scenario_name = "Unknown Scenario"
            scenario_count = 0
            for t in trace_data:
                if t.get("action") == "SCENARIO_MARKER":
                    scenario_count += 1
                    if trace_data.index(t) < trace_data.index(failure):
                        scenario_name = t.get("scenario_name", "Unknown Scenario")
            
            if scenario_count == 0:
                scenario_count = 1
                all_scenarios = self._extract_scenarios(bdd_content)
                scenario_name = all_scenarios[0] if all_scenarios else "Unknown Scenario"

            human_error = f"Issue occurred in Scenario {scenario_count}: {scenario_name}\n\nIssue details:\n\n"
            
            if "DATA_MISSING" in error_msg:
                data_placeholder = error_msg.split(": ")[1] if ": " in error_msg else "specified data"
                human_error += f"The provided data path for {data_placeholder} is available. Kindly check the data file."
            else:
                element_name = failure.get("element_query") or "Unknown Element"
                human_error += f"The element provided in Scenario {scenario_count} ('{element_name}') could not be found in the application. Kindly check the BDD steps and start the agent again. Please find the attached screenshot for reference."
            
            pdf_path = generate_pdf_report(story_id, human_error, screenshot, suite=suite)
            
            raise Exception(json.dumps({
                "type": "HARVEST_FAILURE",
                "message": human_error,
                "screenshot": screenshot,
                "pdf_url": f"/api/download-error-report/{story_id}?suite={suite}"
            }))

        healed_steps = [t for t in trace_data if t.get("status") == "HEALED"]
        
        data_context = self._detect_data_file("", bdd_content=bdd_content)
        generated_code = llm_service.generate_code_from_bdd_and_map(
            story_id, bdd_content, trace_log, data_context=data_context, suite=suite
        )
        
        script_path = f"backend/storage/suites/{suite}/scripts/test_{story_id}.py"
        save_to_file(generated_code, script_path)
        
        return {
            "story_id": story_id,
            "script_path": script_path,
            "message": "Self-healing completed successfully",
            "healing_report": {
                "total_steps": len(trace_data) if 'trace_data' in locals() else 0,
                "healed_steps": len(healed_steps) if 'healed_steps' in locals() else 0
            }
        }

test_generator_service = TestGeneratorService()
