from __future__ import annotations

import json
import os
from typing import Dict

CONFIG_PATH = "app_config.json"

DEFAULT_CONFIG: Dict = {
    "service_account_json": "service_account.json",
    "targets": {
        "high_side": {
            "spreadsheet_id": "",
            "worksheet_name": "HS ENTRY",
        },
        "low_side": {
            "spreadsheet_id": "",
            "worksheet_name": "LS ENTRY",
        },
    },
}


def _merge_defaults(config: Dict) -> Dict:
    merged = json.loads(json.dumps(DEFAULT_CONFIG))
    merged.update(config or {})
    merged.setdefault("targets", {})
    for key, default_target in DEFAULT_CONFIG["targets"].items():
        merged["targets"].setdefault(key, {})
        for field, value in default_target.items():
            merged["targets"][key].setdefault(field, value)
    return merged


def load_config(path: str = CONFIG_PATH) -> Dict:
    if not os.path.exists(path):
        return json.loads(json.dumps(DEFAULT_CONFIG))
    with open(path, "r", encoding="utf-8") as fh:
        return _merge_defaults(json.load(fh))


def save_config(config: Dict, path: str = CONFIG_PATH) -> None:
    config = _merge_defaults(config)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(config, fh, indent=2)
