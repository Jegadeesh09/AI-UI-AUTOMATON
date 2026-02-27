# Work Manual: Guide for Frontend and Backend

## For Backend Developers

### Project Structure

- `backend/main.py`: Main entry point and API definitions.
- `backend/agent/`: Contains the Harvester Agent logic.
- `backend/generator/`: Service that coordinates script generation.
- `backend/llm/`: LLM integration layer.
- `backend/storage/`: Persistent storage for BDD files, scripts, trace logs, and reports.

### Adding a New LLM Provider

1. Update `Settings` model in `main.py`.
2. Update `config_manager.py` to handle the new API key.
3. Update `llm_service.py`'s `_get_client` and `_call_llm` methods.
4. Update `SettingsModal.jsx` in the frontend to include the new provider.

### Manual Test Execution

You can run generated tests manually from the terminal:

```bash
pytest backend/storage/suites/Default/scripts/test_<story_id>.py --html=backend/storage/suites/Default/reports/<story_id>/extent-report.html --self-contained-html
```

## For Frontend Developers

### Key Components

- `UploadTab.jsx`: Main workspace for script generation.
- `ExecutionTab.jsx`: Dashboard for running tests and viewing results.
- `SettingsModal.jsx`: Configuration of global app state.

### Adding New UI Settings

1. Add the state variable in `SettingsModal.jsx`.
2. Update the `handleSave` function to send the new setting to the backend.
3. Ensure the backend `Settings` Pydantic model is updated to accept the new field.

## User Guide

### Generating a Script

1. Enter a **Story Name** (e.g., `LoginTest`).
2. Paste your user story or upload a `.txt` file.
3. Click **Generate Automation Script**.
4. Alternatively, use the **Scan** button to record a session manually. The AI will convert the recording into a BDD story.
5. Wait for the process to complete. You can see the progress in the button text.

### Handling Sensitive Data

The application automatically masks sensitive fields (passwords, secrets) as `<Sensitive Data>`. You should replace these placeholders in the generated BDD or use the **Data Documents** sidebar to upload a file and reference it like `<FileName.ColumnName_RowNumber>`.

### Running a Test

1. Go to the **Execution** tab.
2. Find your story in the list.
3. Click **Run Agent**.
4. Once finished, click **Allure Report** to see screenshots and step-by-step execution for each scenario.

### Settings

- Click the **Gear Icon** to configure your LLM provider and API keys.
- Toggle **Headless Mode** to show or hide the browser during the Harvesting phase.
- Note: Chrome paths are managed via environment variables or the backend configuration for security.

### Running a Local LLM (Ollama)

To use a local LLM instead of a paid API:

1. **Install Ollama**: Download and install from [ollama.com](https://ollama.com/).
2. **Pull a Model**: Open your terminal and run:
   ```bash
   ollama run llama3
   ```
3. **Configure Settings**:
   - In the application, open **Settings**.
   - Toggle to **Local LLM (Ollama)**.
   - Set **Ollama Base URL** to `http://localhost:11434`.
   - Select your model (e.g., `llama3`) in the **Model Name** dropdown.
   - Save changes.
