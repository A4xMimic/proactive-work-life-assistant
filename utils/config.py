import os
from typing import Dict, Any, List
import json

class Config:
    """Configuration management for the Proactive Work-Life Assistant"""
    
    def __init__(self):
        self.settings = self.load_default_settings()
        
    def load_default_settings(self) -> Dict[str, Any]:
        """Load default configuration settings"""
        return {
            "app": {
                "name": "Proactive Work-Life Assistant",
                "version": "1.0.0",
                "debug": os.getenv("DEBUG", "False").lower() == "true"
            },
            "api": {
                "gemini": {
                    "model_preferences": [
                        "gemini-2.0-flash",      # Latest as of July 2024+
                        "gemini-1.5-flash",      # Fast and reliable
                        "gemini-1.5-pro"        # Most capable
                    ],
                    "deprecated_models": [
                        "gemini-pro",
                        "gemini-pro-vision",
                        "gemini-1.0-pro-vision"
                    ],
                    "temperature": 0.7,
                    "max_tokens": 2048,
                    "safety_settings": [
                        {
                            "category": "HARM_CATEGORY_HARASSMENT",
                            "threshold": "BLOCK_MEDIUM_AND_ABOVE"
                        },
                        {
                            "category": "HARM_CATEGORY_HATE_SPEECH",
                            "threshold": "BLOCK_MEDIUM_AND_ABOVE"
                        }
                    ]
                },
                "gomaps": {
                    "base_url": "https://maps.gomaps.pro/maps/api",
                    "radius_default": 5000,
                    "max_results": 20
                },
                "calendar": {
                    "scopes": [
                        "https://www.googleapis.com/auth/calendar",
                        "https://www.googleapis.com/auth/calendar.events"
                    ],
                    "timezone": "Asia/Kolkata"
                }
            },
            "automation": {
                "selenium": {
                    "implicit_wait": 10,
                    "page_load_timeout": 30,
                    "headless": True
                },
                "retry_attempts": 3,
                "timeout_seconds": 30
            },
            "ui": {
                "theme": "light",
                "sidebar_expanded": True,
                "max_chat_history": 50
            },
            "logging": {
                "level": "INFO",
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                "file": "app.log"
            }
        }
    
    def get_preferred_models(self) -> List[str]:
        """Get list of preferred Gemini models (current)"""
        return self.get("api.gemini.model_preferences", [
            "gemini-2.0-flash",
            "gemini-1.5-flash", 
            "gemini-1.5-pro"
        ])
    
    def get_deprecated_models(self) -> List[str]:
        """Get list of deprecated Gemini models"""
        return self.get("api.gemini.deprecated_models", [
            "gemini-pro",
            "gemini-pro-vision",
            "gemini-1.0-pro-vision"
        ])
    
    def get(self, key_path: str, default=None):
        """Get configuration value using dot notation"""
        keys = key_path.split('.')
        value = self.settings
        
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
                
        return value
    
    def set(self, key_path: str, value: Any):
        """Set configuration value using dot notation"""
        keys = key_path.split('.')
        target = self.settings
        
        for key in keys[:-1]:
            if key not in target:
                target[key] = {}
            target = target[key]
            
        target[keys[-1]] = value
    
    def update_from_session(self, session_state: Dict):
        """Update configuration from Streamlit session state"""
        if "gemini_key" in session_state:
            self.set("api.gemini.api_key", session_state["gemini_key"])
            
        if "gomaps_key" in session_state:
            self.set("api.gomaps.api_key", session_state["gomaps_key"])
            
        if "calendar_creds" in session_state:
            self.set("api.calendar.credentials", session_state["calendar_creds"])
    
    def save_to_file(self, filepath: str):
        """Save configuration to file"""
        try:
            with open(filepath, 'w') as f:
                json.dump(self.settings, f, indent=2)
        except Exception as e:
            print(f"Error saving config: {e}")
    
    def load_from_file(self, filepath: str):
        """Load configuration from file"""
        try:
            if os.path.exists(filepath):
                with open(filepath, 'r') as f:
                    self.settings.update(json.load(f))
        except Exception as e:
            print(f"Error loading config: {e}")