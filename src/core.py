from pathlib import Path
from rich import print
from pprint import pprint
import json
from typing import Any

def load_json_data(filepath: str) -> dict:
    if Path(filepath).exists():
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
                # If the JSON file is valid but completely empty ({}),
                # fall back to default configuration
                if data:
                    return data
                return {}
        except json.JSONDecodeError:
            print(f"[bold yellow]Warning: {filepath} is corrupted or invalid. Using default configuration.[/bold yellow]")
            return {}

    # This catches the case where self.config_file.exists() is False
    return {}


def get_kleinanzeigen_results(data: dict) -> list[dict[str, Any]]:
    try:
        results: list[dict[str, Any]] = data["results"]
        return results
    except Exception as ex:
        msg = f"An exception occurred of type {type(ex).__name__}, error message: {str(ex)}"
        pprint(msg)


def enrich_listing_data(data: dict[str, Any]) -> dict[str, Any]:
    """Adds a 'detail_id' key to every listing in the API response."""

    for item in data.get("results", []):
        item["detail_id"] = item["url"].rsplit("/", 1)[-1]

    return data
