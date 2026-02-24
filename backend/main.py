# uvicorn backend.main:app --reload

import os
import sys
import subprocess
import asyncio
import uuid
import threading
import shutil
import re
import zipfile
import io
import json
import tempfile
from allure_combine import combine_allure
from concurrent.futures import ThreadPoolExecutor
from fastapi import FastAPI, UploadFile, File, BackgroundTasks, HTTPException, WebSocket, WebSocketDisconnect, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import StreamingResponse, FileResponse
from pydantic import BaseModel
from typing import List, Optional
from backend.config.config_manager import config_manager
from backend.utils.file_util import read_file, get_file_structure
from backend.utils.logger import set_broadcast_func, log_to_ui
from backend.agent.recorder_agent import recorder_agent

# Use ThreadPoolExecutor for sync operations
executor = ThreadPoolExecutor(max_workers=4)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Storage for simple in-memory state of jobs (ideally use a DB)
jobs = {}

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                pass

manager = ConnectionManager()
set_broadcast_func(manager.broadcast)

def is_story_match(sid, dname):
    """Fuzzy match story_id to a directory name"""
    s1 = sid.lower().replace("_", "").replace(" ", "")
    s2 = dname.lower().replace("_", "").replace(" ", "")
    if s1 == s2: return True
    if s1 in s2 or s2 in s1: return True
    # Check if words match
    parts1 = set(sid.lower().split("_"))
    parts2 = set(dname.lower().split("_"))
    if parts1.intersection(parts2):
            # If at least 2 words match or one long word matches
            common = parts1.intersection(parts2)
            if len(common) >= 2: return True
            if len(common) == 1 and list(common)[0] not in ["login", "test", "script", "viking"]: # avoid too broad matches
                return True
    return False

def find_report_dir(suites_dir, suite, story_id):
    """Fuzzy match story_id to a report directory"""

    # 1. Try exact match in specified suite
    report_dir = os.path.join(suites_dir, suite, "reports", story_id)
    if os.path.exists(report_dir) and os.path.isdir(report_dir):
        return report_dir, suite

    # 2. Try fuzzy match in specified suite
    suite_reports_dir = os.path.join(suites_dir, suite, "reports")
    if os.path.exists(suite_reports_dir):
        for d in os.listdir(suite_reports_dir):
            if is_story_match(story_id, d):
                return os.path.join(suite_reports_dir, d), suite

    # 3. Search across all suites
    for s in os.listdir(suites_dir):
        if not os.path.isdir(os.path.join(suites_dir, s)): continue

        # Fuzzy match in this suite
        suite_reports_dir = os.path.join(suites_dir, s, "reports")
        if os.path.exists(suite_reports_dir):
            for d in os.listdir(suite_reports_dir):
                if is_story_match(story_id, d):
                    return os.path.join(suite_reports_dir, d), s

    return None, None

def run_generation_task_sync(job_id, story_id, story_text, bdd_content=None, suite="Default"):
    """Sync version that handles async internally"""
    try:
        jobs[job_id]["status"] = "processing"
        
        # Import here to avoid circular imports
        from backend.generator.test_generator_service import test_generator_service
        
        def on_phase_change(phase):
            jobs[job_id]["phase"] = phase

        result = test_generator_service.generate_full_test(
            story_id, story_text, on_phase_change=on_phase_change, bdd_content=bdd_content, suite=suite
        )
        jobs[job_id]["status"] = "completed"
        jobs[job_id]["result"] = result
        jobs[job_id]["story_id"] = story_id
    except Exception as e:
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["error"] = str(e)

class StoryUpload(BaseModel):
    story_text: str
    story_id: Optional[str] = None
    is_update: Optional[bool] = False
    generate_only_bdd: Optional[bool] = False
    suite: Optional[str] = "Default"

class BDDApproval(BaseModel):
    story_id: str
    story_text: str
    bdd_content: str
    suite: Optional[str] = "Default"

class RunTestRequest(BaseModel):
    story_id: str
    suite: Optional[str] = "Default"

class ScriptUpdate(BaseModel):
    code: str
    suite: str

class SuiteCreate(BaseModel):
    name: str

class StoryRename(BaseModel):
    old_id: str
    new_id: str
    suite: str

class Settings(BaseModel):
    GEMINI_API_KEY: Optional[str] = None
    GPT_API_KEY: Optional[str] = None
    DEEPSEEK_API_KEY: Optional[str] = None
    OLLAMA_BASE_URL: Optional[str] = None
    MODEL_NAME: str
    LLM_PROVIDER: str
    IS_PAID_LLM: bool
    HEADLESS_AGENT: Optional[bool] = True
    HEADLESS_SCRIPT: Optional[bool] = True
    SHOW_CODE_ICON: Optional[bool] = True
    CUSTOM_MODELS: List[str] = []

@app.get("/api/suites")
def get_suites():
    suites_dir = os.path.join(BASE_DIR, "storage", "suites")
    if not os.path.exists(suites_dir):
        os.makedirs(suites_dir, exist_ok=True)
    return [d for d in os.listdir(suites_dir) if os.path.isdir(os.path.join(suites_dir, d))]

@app.post("/api/suites")
def create_suite(suite: SuiteCreate):
    suite_name = suite.name.strip()
    if not suite_name:
        raise HTTPException(status_code=400, detail="Suite name cannot be empty")
    
    suite_dir = os.path.join("backend/storage/suites", suite_name)
    if os.path.exists(suite_dir):
        raise HTTPException(status_code=409, detail="Suite already exists")
    
    for sub in ["stories", "bdd", "scripts", "reports", "trace_logs"]:
        os.makedirs(os.path.join(suite_dir, sub), exist_ok=True)
    
    return {"status": "success", "suite": suite_name}

@app.get("/api/stories")
def get_stories(suite: str = "Default"):
    stories_dir = f"backend/storage/suites/{suite}/stories"
    bdd_dir = f"backend/storage/suites/{suite}/bdd"
    if not os.path.exists(stories_dir):
        return []
    files = [f for f in os.listdir(stories_dir) if f.endswith(".txt")]
    
    stories = []
    for f in files:
        story_id = f.replace(".txt", "")
        bdd_path = os.path.join(bdd_dir, f"{story_id}.feature")
        stories.append({
            "story_id": story_id,
            "has_bdd": os.path.exists(bdd_path)
        })
    return stories

@app.get("/api/story/{story_id}")
def get_story(story_id: str, suite: str = "Default"):
    story_path = f"backend/storage/suites/{suite}/stories/{story_id}.txt"
    content = read_file(story_path)
    if content is None:
        raise HTTPException(status_code=404, detail="Story not found")
    return {"story_id": story_id, "story_text": content}

@app.get("/api/bdd/{story_id}")
def get_bdd(story_id: str, suite: str = "Default"):
    bdd_path = f"backend/storage/suites/{suite}/bdd/{story_id}.feature"
    content = read_file(bdd_path)
    if content is None:
        raise HTTPException(status_code=404, detail="BDD not found")
    return {"story_id": story_id, "bdd_content": content}

@app.get("/api/scripts")
def get_scripts():
    suites_dir = os.path.join(BASE_DIR, "storage", "suites")
    if not os.path.exists(suites_dir):
        return []
    
    all_scripts = []
    for suite in os.listdir(suites_dir):
        suite_path = os.path.join(suites_dir, suite)
        if not os.path.isdir(suite_path):
            continue
            
        scripts_dir = os.path.join(suite_path, "scripts")
        if not os.path.exists(scripts_dir):
            continue
            
        files = [f for f in os.listdir(scripts_dir) if f.endswith(".py")]
        
        scripts = []
        for f in files:
            story_id = f.replace("test_", "").replace(".py", "")
            # Allure generates index.html
            report_path = os.path.join(suite_path, "reports", story_id, "index.html")
            scripts.append({
                "story_id": story_id,
                "filename": f,
                "has_report": os.path.exists(report_path),
                "suite": suite
            })
        all_scripts.append({"suite": suite, "scripts": scripts})
    return all_scripts

@app.delete("/api/script/{story_id}")
def delete_script(story_id: str, scope: str = "full", suite: str = "Default"):
    suite_dir = os.path.join(BASE_DIR, "storage", "suites", suite)
    script_path = os.path.join(suite_dir, "scripts", f"test_{story_id}.py")
    bdd_path = os.path.join(suite_dir, "bdd", f"{story_id}.feature")
    report_dir = os.path.join(suite_dir, "reports", story_id)
    story_path = os.path.join(suite_dir, "stories", f"{story_id}.txt")
    trace_log_path = os.path.join(suite_dir, "trace_logs", f"{story_id}_trace.json")

    deleted_any = False
    
    files_to_delete = []
    if scope == "script_only":
        # Delete script, trace log, AND report directory (keep story and BDD)
        files_to_delete = [script_path, trace_log_path]
    else:
        # Full delete
        files_to_delete = [script_path, bdd_path, story_path, trace_log_path]

    for path in files_to_delete:
        if os.path.exists(path):
            os.remove(path)
            deleted_any = True
            
    # Always delete report directory if it exists, regardless of scope
    if os.path.exists(report_dir):
        shutil.rmtree(report_dir)
        deleted_any = True
        
    if not deleted_any:
        raise HTTPException(status_code=404, detail="Files not found")
        
    return {"status": "success", "message": f"Deleted {scope} for {story_id}"}

@app.delete("/api/suite/{suite_name}")
def delete_suite(suite_name: str):
    suite_dir = os.path.join(BASE_DIR, "storage", "suites", suite_name)
    if not os.path.exists(suite_dir):
        raise HTTPException(status_code=404, detail="Suite not found")
    
    if suite_name == "Default":
        # Don't delete Default directory, just its contents if needed, 
        # but usually we want to keep Default. 
        # Let's allow deleting it if the user really wants, or just empty it.
        # User said "delete the all the associated data which is stored under the suite".
        pass

    try:
        shutil.rmtree(suite_dir)
        return {"status": "success", "message": f"Suite {suite_name} and all associated data deleted"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/story/rename")
def rename_story(payload: StoryRename):
    suite_dir = os.path.join(BASE_DIR, "storage", "suites", payload.suite)
    old_id = payload.old_id
    new_id = payload.new_id
    
    if old_id == new_id:
        return {"status": "success"}

    # Paths to rename
    paths = {
        os.path.join(suite_dir, "stories", f"{old_id}.txt"): os.path.join(suite_dir, "stories", f"{new_id}.txt"),
        os.path.join(suite_dir, "bdd", f"{old_id}.feature"): os.path.join(suite_dir, "bdd", f"{new_id}.feature"),
        os.path.join(suite_dir, "scripts", f"test_{old_id}.py"): os.path.join(suite_dir, "scripts", f"test_{new_id}.py"),
        os.path.join(suite_dir, "reports", old_id): os.path.join(suite_dir, "reports", new_id),
        os.path.join(suite_dir, "trace_logs", f"{old_id}_trace.json"): os.path.join(suite_dir, "trace_logs", f"{new_id}_trace.json"),
        os.path.join(suite_dir, "error_reports", f"{old_id}_error_report.pdf"): os.path.join(suite_dir, "error_reports", f"{new_id}_error_report.pdf"),
        os.path.join(suite_dir, "screenshots", old_id): os.path.join(suite_dir, "screenshots", new_id)
    }

    renamed_something = False
    for old_path, new_path in paths.items():
        if os.path.exists(old_path):
            os.makedirs(os.path.dirname(new_path), exist_ok=True)
            os.rename(old_path, new_path)
            renamed_something = True
            
    if not renamed_something:
        raise HTTPException(status_code=404, detail="Original files not found")
        
    return {"status": "success", "new_id": new_id}

@app.delete("/api/data-file/{filename}")
def delete_data_file(filename: str):
    data_dir = "backend/data"
    file_path = os.path.join(data_dir, filename)

    if os.path.exists(file_path):
        os.remove(file_path)
        return {"status": "success", "message": f"Deleted {filename}"}

    raise HTTPException(status_code=404, detail="File not found")

@app.post("/api/upload-story")
async def upload_story(payload: StoryUpload, background_tasks: BackgroundTasks):
    suite = payload.suite or "Default"
    if not payload.story_id:
        raise HTTPException(status_code=400, detail="Story Name is required")
    
    # Clean story_id: remove .txt, lower case, replace spaces
    story_id = payload.story_id.replace(".txt", "").strip().lower().replace(" ", "_")
    story_id = re.sub(r'[^a-z0-9_]', '', story_id)
    
    if not story_id:
        raise HTTPException(status_code=400, detail="Invalid Story Name")

    stories_dir = f"backend/storage/suites/{suite}/stories"
    os.makedirs(stories_dir, exist_ok=True)
    story_path = os.path.join(stories_dir, f"{story_id}.txt")
    
    if not payload.is_update and os.path.exists(story_path):
        raise HTTPException(status_code=409, detail="Duplicate entries found. Please rename the file.")
    
    # Save original story text
    with open(story_path, "w", encoding="utf-8") as f:
        f.write(payload.story_text)

    if payload.generate_only_bdd:
        from backend.generator.test_generator_service import test_generator_service
        bdd_content = test_generator_service.generate_bdd_only(story_id, payload.story_text)
        # Extract feature name to return it to the frontend
        feature_name = test_generator_service._extract_feature_name(bdd_content) or story_id
        
        # Save BDD and Story to the specific suite if generating only BDD
        # This is for the "Save & Preview" flow
        bdd_dir = f"backend/storage/suites/{suite}/bdd"
        os.makedirs(bdd_dir, exist_ok=True)
        with open(os.path.join(bdd_dir, f"{feature_name}.feature"), "w", encoding="utf-8") as f:
            f.write(bdd_content)
            
        return {"story_id": feature_name, "bdd_content": bdd_content}
    
    job_id = str(uuid.uuid4())
    jobs[job_id] = {"status": "pending", "story_id": story_id}
    
    # Run in thread to avoid async issues
    background_tasks.add_task(
        lambda: run_generation_task_sync(job_id, story_id, payload.story_text, suite=suite)
    )
    return {"job_id": job_id, "story_id": story_id}

@app.post("/api/start-scan")
async def start_scan():
    try:
        log_to_ui("Scan started. Browser launching...")
        # Start in a separate task or just await if we want it to block until closed?
        # User said "Once the user clicks Scan: It navigates to a Chrome browser."
        # This should probably be handled by a background task that keeps the browser open
        # But we need to return something to the UI.
        await recorder_agent.start_session()
        return {"status": "success", "message": "Scan started"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/scan-status")
async def get_scan_status():
    status = recorder_agent.status
    if status == "completed":
        actions = recorder_agent.actions
        if not actions:
            recorder_agent.status = "idle"
            return {"status": "empty", "bdd_content": ""}
        
        try:
            from backend.llm.llm_service import llm_service
            bdd_content = llm_service.generate_bdd_from_trace(actions)
            recorder_agent.status = "idle"
            return {"status": "completed", "bdd_content": bdd_content}
        except Exception as e:
            recorder_agent.status = "idle"
            raise HTTPException(status_code=500, detail=f"BDD generation failed: {str(e)}")
    
    return {"status": status}

@app.post("/api/stop-scan")
async def stop_scan(suite: str = "Default"):
    try:
        log_to_ui("Stopping scan and collecting recorded actions...")
        print("🛑 Stopping scan...")
        actions = await recorder_agent.stop_session()
        if not actions:
            log_to_ui("No actions were recorded during the session.", type="error")
            print("⚠️ No actions recorded")
            recorder_agent.status = "idle"
            return {"status": "empty", "bdd_content": ""}
        
        log_to_ui(f"Collected {len(actions)} actions. Generating BDD story...")
        print(f"📄 Generating BDD from {len(actions)} actions...")
        from backend.llm.llm_service import llm_service
        from backend.generator.test_generator_service import test_generator_service
        bdd_content = llm_service.generate_bdd_from_trace(actions)
        
        feature_name = test_generator_service._extract_feature_name(bdd_content) or "RecordedSession"
        
        # Save BDD and Story files so they appear in the UI immediately
        stories_dir = f"backend/storage/suites/{suite}/stories"
        bdd_dir = f"backend/storage/suites/{suite}/bdd"
        os.makedirs(stories_dir, exist_ok=True)
        os.makedirs(bdd_dir, exist_ok=True)
        
        with open(os.path.join(stories_dir, f"{feature_name}.txt"), "w", encoding="utf-8") as f:
            f.write(bdd_content) # For recorded sessions, story text is the same as BDD initially
        with open(os.path.join(bdd_dir, f"{feature_name}.feature"), "w", encoding="utf-8") as f:
            f.write(bdd_content)

        # Save trace logs from scan
        trace_logs_dir = os.path.join(BASE_DIR, "storage", "suites", suite, "trace_logs")
        os.makedirs(trace_logs_dir, exist_ok=True)
        trace_path = os.path.join(trace_logs_dir, f"{feature_name}_trace.json")
        with open(trace_path, "w", encoding="utf-8") as f:
            json.dump(actions, f, indent=4)
            
        print(f"✅ BDD generated and trace saved to {trace_path}")
        recorder_agent.status = "idle"
        return {"status": "success", "bdd_content": bdd_content, "story_id": feature_name}
    except Exception as e:
        import traceback
        print(f"❌ Stop Scan Error: {str(e)}")
        traceback.print_exc()
        recorder_agent.status = "idle"
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/approve-bdd")
async def approve_bdd(payload: BDDApproval, background_tasks: BackgroundTasks):
    job_id = str(uuid.uuid4())
    suite = payload.suite or "Default"
    jobs[job_id] = {"status": "pending", "story_id": payload.story_id}
    
    # Run in thread to avoid async issues
    background_tasks.add_task(
        lambda: run_generation_task_sync(job_id, payload.story_id, payload.story_text, bdd_content=payload.bdd_content, suite=suite)
    )
    return {"job_id": job_id, "story_id": payload.story_id}

@app.get("/api/job-status/{job_id}")
async def get_job_status(job_id: str):
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job

# @app.post("/api/run-test/{story_id}")
def record_execution_result(suite, story_id, success, duration, passed_count, failed_count):
    history_file = os.path.join(BASE_DIR, "storage", "execution_history.json")
    os.makedirs(os.path.dirname(history_file), exist_ok=True)

    from datetime import datetime

    history = []
    if os.path.exists(history_file):
        try:
            with open(history_file, "r", encoding="utf-8") as f:
                history = json.load(f)
        except:
            history = []

    history.append({
        "timestamp": datetime.now().isoformat(),
        "suite": suite,
        "story_id": story_id,
        "success": success,
        "duration": duration,
        "passed": passed_count,
        "failed": failed_count
    })

    # Keep last 1000 executions
    if len(history) > 1000:
        history = history[-1000:]

    with open(history_file, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=4)

@app.post("/api/run-test")
def run_test(req: RunTestRequest):
    story_id = req.story_id
    suite = req.suite or "Default"
    """Synchronous test execution to avoid async issues"""
    suite_dir = os.path.abspath(os.path.join(BASE_DIR, "storage", "suites", suite))
    script_path = os.path.join(
        suite_dir,
        "scripts",
        f"test_{story_id}.py"
    )

    if not os.path.exists(script_path):
        raise HTTPException(status_code=404, detail="Script not found")

    # ✅ DEFINE report_dir
    report_dir = os.path.abspath(os.path.join(
        suite_dir,
        "reports",
        story_id
    ))
    os.makedirs(report_dir, exist_ok=True)
    
    # We'll use Allure results and json-report for dashboard
    allure_results_dir = os.path.join(suite_dir, "allure-results", story_id)
    os.makedirs(allure_results_dir, exist_ok=True)
    
    # Save JSON report in a separate directory to avoid it being deleted by Allure's --clean
    json_reports_dir = os.path.abspath(os.path.join(suite_dir, "json-reports"))
    os.makedirs(json_reports_dir, exist_ok=True)
    json_report_path = os.path.join(json_reports_dir, f"{story_id}.json")

    abs_script_path = os.path.abspath(script_path)
    
    config = config_manager.get_config()
    headless = config.get("HEADLESS_SCRIPT", True)
    
    try:
        # Check for required pytest plugins
        import importlib.metadata
        plugins = {
            "pytest-json-report": "--json-report",
            "allure-pytest": "--alluredir"
        }
        missing_plugins = []
        installed_packages = {pkg.metadata['Name'].lower(): pkg.version for pkg in importlib.metadata.distributions()}

        for pkg_name in plugins:
            if pkg_name not in installed_packages:
                missing_plugins.append(pkg_name)

        if missing_plugins:
            msg = f"❌ Missing required pytest plugins: {', '.join(missing_plugins)}. Please run: pip install {' '.join(missing_plugins)}"
            print(msg)
            log_to_ui(msg, type="error")
            # We continue but some features might fail

        # Run pytest using sys.executable to ensure the same environment
        pytest_command = [
            sys.executable, "-m", "pytest",
            abs_script_path,
            "--verbose"
        ]
        
        if "allure-pytest" in installed_packages:
            pytest_command.extend([
                f"--alluredir={allure_results_dir}",
                "--clean-alluredir"
            ])

        if "pytest-json-report" in installed_packages:
            pytest_command.extend([
                f"--json-report",
                f"--json-report-file={json_report_path}"
            ])

        if not headless:
            pytest_command.append("--headed")
        
        print(f"🏃 Running test: {' '.join(pytest_command)}")
        env = os.environ.copy()
        env["CURRENT_SUITE"] = suite
        
        log_to_ui(f"🏃 Starting test execution for {story_id}...")

        # We use subprocess.Popen to stream logs to the UI
        process = subprocess.Popen(
            pytest_command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            env=env,
            bufsize=1,
            universal_newlines=True
        )

        full_stdout = []
        for line in iter(process.stdout.readline, ""):
            line_str = line.strip()
            if line_str:
                print(f"pytest: {line_str}")
                log_to_ui(line_str)
                full_stdout.append(line_str)

        process.stdout.close()
        return_code = process.wait(timeout=300)
        stdout_text = "\n".join(full_stdout)

        # Generate static Allure report
        try:
            # Use npx allure-commandline to avoid hardcoded paths
            # Use forward slashes for paths to avoid syntax errors on Windows
            results_dir_alt = allure_results_dir.replace("\\", "/")
            report_dir_alt = report_dir.replace("\\", "/")

            # --yes is used to skip the installation prompt if allure-commandline is not yet installed
            # We use "allure" command as provided by allure-commandline package
            gen_command = [
                "npx", "--yes", "allure-commandline", "generate",
                f'"{results_dir_alt}"',
                "-o", f'"{report_dir_alt}"',
                "--clean"
            ]

            full_cmd = " ".join(gen_command)
            print(f"📊 Generating Allure report: {full_cmd}")
            log_to_ui("📊 Generating Allure report...")

            # Use shell=True to ensure npx is found in the environment
            subprocess.run(full_cmd, check=True, shell=True, timeout=90)

            log_to_ui("✅ Allure report generated successfully.")

        except Exception as e:
            error_msg = f"Failed to generate Allure report: {e}"
            print(error_msg)
            log_to_ui(error_msg, type="error")
        
        # Parse report for history recording
        story_passed = 0
        story_failed = 0
        duration = 0
        if os.path.exists(json_report_path):
            with open(json_report_path, "r", encoding="utf-8") as rf:
                try:
                    data = json.load(rf)
                    summary = data.get("summary", {})
                    story_passed = summary.get("passed", 0)
                    story_failed = summary.get("failed", 0) + summary.get("error", 0)
                    duration = summary.get("duration", 0)
                except: pass

        record_execution_result(suite, story_id, return_code == 0, duration, story_passed, story_failed)

        return {
            "success": return_code == 0,
            "exit_code": return_code,
            "stdout": stdout_text,
            "stderr": "",
            "report_url": f"/suites/{suite}/reports/{story_id}/index.html"
        }
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=500, detail="Test timeout")
    except FileNotFoundError as e:
        raise HTTPException(status_code=500, detail=f"Command not found: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/self-heal/{story_id}")
def self_heal(story_id: str, suite: str = "Default"):
    """Synchronous self-healing"""
    try:
        from backend.generator.test_generator_service import test_generator_service
        result = test_generator_service.self_heal(story_id, suite=suite)
        return {"status": "success", "message": "Self-healing completed", "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/data-files")
def get_data_files():
    data_dir = "backend/data"
    if not os.path.exists(data_dir):
        return []
    files = [f for f in os.listdir(data_dir) if os.path.isfile(os.path.join(data_dir, f))]
    return files

@app.post("/api/upload-data")
async def upload_data(file: UploadFile = File(...)):
    data_dir = "backend/data"
    os.makedirs(data_dir, exist_ok=True)
    file_path = os.path.join(data_dir, file.filename)
    
    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large")
    
    with open(file_path, "wb") as f:
        f.write(content)
    return {"status": "success", "filename": file.filename}

@app.get("/api/data-file/{filename}/structure")
def get_data_structure(filename: str):
    file_path = os.path.join("backend/data", filename)
    structure = get_file_structure(file_path)
    if structure is None:
        raise HTTPException(status_code=404, detail="File not found")
    return {"filename": filename, "structure": structure}

@app.get("/api/script-content/{story_id}")
def get_script_content(story_id: str, suite: str = "Default"):
    script_path = os.path.join(BASE_DIR, "storage", "suites", suite, "scripts", f"test_{story_id}.py")
    if not os.path.exists(script_path):
        raise HTTPException(status_code=404, detail="Script not found")
    with open(script_path, "r", encoding="utf-8") as f:
        return {"code": f.read()}

@app.post("/api/script-content/{story_id}")
def update_script_content(story_id: str, payload: ScriptUpdate):
    script_path = os.path.join(BASE_DIR, "storage", "suites", payload.suite, "scripts", f"test_{story_id}.py")
    with open(script_path, "w", encoding="utf-8") as f:
        f.write(payload.code)
    return {"status": "success"}

@app.get("/api/dashboard/stats")
def get_dashboard_stats(suite: str = "All", story_id: str = "All"):
    suites_dir = os.path.join(BASE_DIR, "storage", "suites")
    if not os.path.exists(suites_dir):
        return {"total_stories": 0, "passed": 0, "failed": 0, "suites": []}
    
    target_suites = [suite] if suite != "All" else [d for d in os.listdir(suites_dir) if os.path.isdir(os.path.join(suites_dir, d))]
    
    total_stories = 0
    total_passed = 0
    total_failed = 0
    total_scenarios = 0
    total_steps = 0
    total_accuracy = 0
    accuracy_count = 0

    manual_stories = 0
    automated_stories = 0

    suite_stats = []
    all_story_details = []

    for s in target_suites:
        s_path = os.path.join(suites_dir, s)
        reports_dir = os.path.join(s_path, "reports")
        stories_dir = os.path.join(s_path, "stories")
        metadata_dir = os.path.join(s_path, "metadata")
        scripts_dir = os.path.join(s_path, "scripts")
        
        if not os.path.exists(stories_dir):
            continue
            
        s_story_files = [f for f in os.listdir(stories_dir) if f.endswith(".txt")]
        
        s_passed = 0
        s_failed = 0
        s_story_details = []

        for f in s_story_files:
            sid = f.replace(".txt", "")
            if story_id != "All" and sid != story_id:
                continue
            
            total_stories += 1
            
            # Check automation status
            script_exists = os.path.exists(os.path.join(scripts_dir, f"test_{sid}.py"))
            if script_exists:
                automated_stories += 1
            else:
                manual_stories += 1

            # Load metadata for accuracy and steps
            meta_path = os.path.join(metadata_dir, f"{sid}.json")
            # Fuzzy match metadata if exact match fails
            if not os.path.exists(meta_path) and os.path.exists(metadata_dir):
                for mfile in os.listdir(metadata_dir):
                    if is_story_match(sid, mfile.replace(".json", "")):
                        meta_path = os.path.join(metadata_dir, mfile)
                        break

            story_accuracy = 0
            if os.path.exists(meta_path):
                try:
                    with open(meta_path, "r", encoding="utf-8") as mf:
                        mdata = json.load(mf)
                        t_steps = mdata.get("total_steps", 0)
                        total_steps += t_steps
                        story_accuracy = mdata.get("accuracy", 0)
                        total_accuracy += story_accuracy
                        accuracy_count += 1
                except: pass

            # Look for report.json (case-insensitive directory search)
            # Look for report.json in the new safe location first
            json_report_path = os.path.join(s_path, "json-reports", f"{sid}.json")
            matched_report_dir = sid

            # Fallback to legacy location or fuzzy match if not found
            if not os.path.exists(json_report_path):
                # Try finding it in reports dir (legacy)
                legacy_path = os.path.join(reports_dir, sid, "report.json")
                if os.path.exists(legacy_path):
                    json_report_path = legacy_path
                else:
                    # Fuzzy match the directory in reports/
                    if os.path.exists(reports_dir):
                        for d in os.listdir(reports_dir):
                            if is_story_match(sid, d):
                                candidate = os.path.join(reports_dir, d, "report.json")
                                if os.path.exists(candidate):
                                    json_report_path = candidate
                                    matched_report_dir = d
                                    break

            story_passed = 0
            story_failed = 0
            duration = 0
            scenarios = []
            failure_reasons = []

            if os.path.exists(json_report_path):
                with open(json_report_path, "r", encoding="utf-8") as rf:
                    try:
                        data = json.load(rf)
                        summary = data.get("summary", {})
                        story_passed = summary.get("passed", 0)
                        story_failed = summary.get("failed", 0) + summary.get("error", 0)
                        duration = summary.get("duration", 0)
                        
                        s_passed += story_passed
                        s_failed += story_failed
                        total_passed += story_passed
                        total_failed += story_failed
                        total_scenarios += (story_passed + story_failed)

                        for test in data.get("tests", []):
                            name = test.get("nodeid", "").split("::")[-1]
                            status = test.get("outcome", "passed")

                            call = test.get("call", {})
                            excinfo = call.get("excinfo", {})
                            msg = excinfo.get("message", "")

                            reason = "Unknown"
                            category = "Real Bug"
                            if status != "passed":
                                if "Timeout" in msg or "timed out" in msg.lower():
                                    reason = "Element Timeout"
                                    category = "Environment Issue"
                                elif "no such element" in msg.lower() or "Selector" in msg:
                                    reason = "Brittle XPath"
                                    category = "Script Issue"
                                elif "assertion" in msg.lower():
                                    reason = "Assertion Failure"
                                    category = "Real Bug"

                                failure_reasons.append({"reason": reason, "category": category, "message": msg[:200]})

                            scenarios.append({
                                "name": name.replace("test_", "").replace("_", " "),
                                "status": "passed" if status == "passed" else "failed",
                                "duration": round(call.get("duration", 0), 2),
                                "error": msg,
                                "report_url": f"/suites/{s}/reports/{matched_report_dir}/index.html"
                            })
                    except Exception as e:
                        print(f"Error parsing report for {sid}: {e}")
            
            story_info = {
                "story_id": sid,
                "suite": s,
                "passed": story_passed,
                "failed": story_failed,
                "duration": round(duration, 2),
                "accuracy": story_accuracy,
                "is_automated": script_exists,
                "scenarios": scenarios,
                "failures": failure_reasons
            }
            s_story_details.append(story_info)
            all_story_details.append(story_info)
        
        suite_stats.append({
            "suite": s,
            "total_stories": len(s_story_details),
            "passed": s_passed,
            "failed": s_failed,
            "stories": s_story_details
        })

    # Load history for trends
    history_file = os.path.join(BASE_DIR, "storage", "execution_history.json")
    history_data = []
    if os.path.exists(history_file):
        try:
            with open(history_file, "r", encoding="utf-8") as f:
                history_data = json.load(f)
        except: pass

    # AI Insights
    failure_categories = {}
    for story in all_story_details:
        for fail in story.get("failures", []):
            cat = fail["category"]
            failure_categories[cat] = failure_categories.get(cat, 0) + 1

    recommendations = []
    if failure_categories.get("Script Issue", 0) > 2:
        recommendations.append("High number of script issues detected. Consider re-harvesting XPaths for brittle elements.")
    if failure_categories.get("Environment Issue", 0) > 2:
        recommendations.append("Frequent timeouts observed. Check application latency or increase wait times.")

    return {
        "total_stories": total_stories,
        "manual_stories": manual_stories,
        "automated_stories": automated_stories,
        "total_scenarios": total_scenarios,
        "total_steps": total_steps,
        "passed": total_passed,
        "failed": total_failed,
        "avg_accuracy": round(total_accuracy / accuracy_count, 2) if accuracy_count > 0 else 0,
        "suites": suite_stats,
        "history": history_data,
        "ai_insights": {
            "failure_summary": failure_categories,
            "recommendations": recommendations
        }
    }

@app.get("/api/settings")
def get_settings():
    return config_manager.get_config()

@app.post("/api/settings")
def update_settings(settings: Settings):
    config_manager.save_config(settings.dict())
    return {"status": "success"}

@app.get("/api/health")
def health_check():
    return {"status": "healthy"}

@app.websocket("/ws/logs")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive
            await websocket.receive_text()
            # await asyncio.sleep(30)
    except WebSocketDisconnect:
        manager.disconnect(websocket)

@app.get("/api/download-error-report/{story_id}")
def download_error_report(story_id: str, suite: str = "Default"):
    report_path = os.path.join(BASE_DIR, "storage", "suites", suite, "error_reports", f"{story_id}_error_report.pdf")
    if not os.path.exists(report_path):
        raise HTTPException(status_code=404, detail="Error report not found")
    return FileResponse(report_path, filename=f"{story_id}_failure.pdf", media_type="application/pdf")

@app.get("/api/download-report/{story_id}")
def download_report(story_id: str, background_tasks: BackgroundTasks, suite: str = "Default"):
    # Allure generates a directory of files. To provide a single HTML file,
    # we use allure-combine to merge all assets into one.
    suites_dir = os.path.join(BASE_DIR, "storage", "suites")
    
    report_dir, found_suite = find_report_dir(suites_dir, suite, story_id)

    if not report_dir:
        raise HTTPException(status_code=404, detail="Report not found")

    # Generate combined HTML report
    try:
        # Create a permanent-ish temp file that we'll delete after serving
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".html")
        temp_file_path = temp_file.name
        temp_file.close()

        # allure-combine creates 'complete.html' inside the dest_folder
        # We need to pass a directory as dest_folder
        temp_dir = tempfile.mkdtemp()
        combine_allure(report_dir, dest_folder=temp_dir)
        combined_html_path = os.path.join(temp_dir, "complete.html")

        if os.path.exists(combined_html_path):
            shutil.move(combined_html_path, temp_file_path)
            shutil.rmtree(temp_dir)

            background_tasks.add_task(os.remove, temp_file_path)

            return FileResponse(
                temp_file_path,
                media_type="text/html",
                filename=f"{story_id}_report.html"
            )
        else:
            shutil.rmtree(temp_dir)
    except Exception as e:
        print(f"Failed to combine Allure report: {e}")
    
    # Fallback to ZIP if combine fails or other issues occur
    memory_file = io.BytesIO()
    with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(report_dir):
            for file in files:
                abs_path = os.path.join(root, file)
                rel_path = os.path.relpath(abs_path, report_dir)
                zf.write(abs_path, rel_path)
    
    memory_file.seek(0)
    return StreamingResponse(
        memory_file,
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename={story_id}_report.zip"}
    )

# Serve static files
SUITES_DIR = os.path.join(BASE_DIR, "storage", "suites")
os.makedirs(SUITES_DIR, exist_ok=True)
app.mount("/suites", StaticFiles(directory=SUITES_DIR), name="suites")

# Screenshots might still be global or suite-specific.
# Let's keep a global one for now or move to suite if needed.
# For Allure Report, they should probably be suite-specific.

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
