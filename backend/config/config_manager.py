import json
import os
from pathlib import Path

CONFIG_FILE = Path(__file__).parent.parent / "config" / "settings.json"

class ConfigManager:
    def __init__(self):
        self._ensure_config_exists()

    def _ensure_config_exists(self):
        if not CONFIG_FILE.parent.exists():
            CONFIG_FILE.parent.mkdir(parents=True)
        if not CONFIG_FILE.exists():
            self.save_config({
                "GEMINI_API_KEY": "",
                "GPT_API_KEY": "",
                "DEEPSEEK_API_KEY": "",
                "OLLAMA_BASE_URL": "http://localhost:11434",
                "MODEL_NAME": "gemini-3-pro",
                "LLM_PROVIDER": "Gemini",
                "IS_PAID_LLM": True,
                "CUSTOM_MODELS": [],
                "DEFAULT_URL": "https://www.google.com",
                "HEADLESS_AGENT": True,
                "HEADLESS_SCRIPT": True,
                "INC_MODE": False,
                "CHROME_EXECUTABLE_PATH": None,
                "CHROME_USER_DATA_DIR": None,
                "SHOW_CODE_ICON": True
            })

    def get_config(self):
        try:
            with open(CONFIG_FILE, "r") as f:
                config = json.load(f)
                # Ensure new keys are present even if they weren't in the saved file
                if "INC_MODE" not in config:
                    config["INC_MODE"] = False
                return config
        except Exception:
            return {}

    def save_config(self, config_data):
        with open(CONFIG_FILE, "w") as f:
            json.dump(config_data, f, indent=4)

    def get_api_key(self, provider=None):
        config = self.get_config()
        if provider is None:
            provider = config.get("LLM_PROVIDER", "Gemini")
        
        if provider == "Gemini":
            return config.get("GEMINI_API_KEY", "")
        elif provider == "OpenAI":
            return config.get("GPT_API_KEY", "")
        elif provider == "DeepSeek":
            return config.get("DEEPSEEK_API_KEY", "")
        return ""

config_manager = ConfigManager()
