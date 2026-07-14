import json
from pathlib import Path
from typing import Any

DEFAULT_CONFIG_DATA = {
    "Default": {
        "searchQuerry": "",
        "searchLocation": "",
        "searchRadius": 5,
        "seachMinPrice": 0,
        "searchMaxPrice": 0,
        "searchPages": 1,
        "searchMaxItems": 0,
        "searchMinDate": "",
        }
    }

class ConfigHandler:
    def __init__(self, config_file : str | Path):
        self.config_file = config_file
        self.data = self.load_preset()  # Load the config file

    def load_preset(self) -> dict[str, dict]:
        if self.config_file.exists():
            try:
                with open(self.config_file, "r") as f:
                    data = json.load(f)
                    # If the JSON file is valid but completely empty ({}),
                    # fall back to default configuration
                    if data:
                        return data
                    return self.get_default_preset()
            except json.JSONDecodeError:
                print(f"Warning: {self.config_file} is corrupted or invalid. Using default configuration.")
                return self.get_default_preset()

        # This catches the case where self.config_file.exists() is False
        return self.get_default_preset()

    def get_default_preset(self) -> dict[str, dict]:
        return DEFAULT_CONFIG_DATA

    def save_config(self) -> None:
        with open(self.config_file, "w") as f:
            json.dump(self.data, f, indent=4)

    # Custom rules
    def add_custom_preset(self, name: str, raw_data: dict[str, Any]) -> None:
        """Adds or updates a rule mapping to your specific JSON format."""
        self.data[name] = raw_data
        self.save_config()

    def get_custom_preset(self, name: str) -> dict:
        """Returns the dictionary containing extensions and folder, or None if not found."""
        return self.data.get(name, {})

    def remove_custom_preset(self, name: str) -> None:
        """Safely removes a rule by its name."""
        if name in self.data:
            del self.data[name]
            self.save_config()
