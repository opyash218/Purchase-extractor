from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from typing import Dict, List, Sequence

from extractor import HIGH_SIDE_HEADERS, LOW_SIDE_HEADERS

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


@dataclass
class SheetCheckResult:
    name: str
    ok: bool
    message: str
    spreadsheet_title: str = ""
    worksheet_name: str = ""


def extract_spreadsheet_id(value: str) -> str:
    """Accept a raw spreadsheet ID or a full Google Sheets URL."""
    value = (value or "").strip()
    if not value:
        return ""
    match = re.search(r"/spreadsheets/d/([a-zA-Z0-9-_]+)", value)
    if match:
        return match.group(1)
    return value


class GoogleSheetsClient:
    def __init__(self, service_account_json_path: str):
        try:
            import gspread
            from google.oauth2.service_account import Credentials
        except ImportError as exc:
            raise RuntimeError(
                "Missing Google Sheets packages. Run: pip install -r requirements.txt"
            ) from exc

        service_account_json_path = os.path.expanduser(service_account_json_path or "service_account.json")
        if not os.path.exists(service_account_json_path):
            raise FileNotFoundError(
                f"Service account JSON not found: {service_account_json_path}"
            )

        with open(service_account_json_path, "r", encoding="utf-8") as fh:
            info = json.load(fh)
        self.service_account_email = info.get("client_email", "")
        credentials = Credentials.from_service_account_info(info, scopes=SCOPES)
        self.client = gspread.authorize(credentials)

    def _open_worksheet(self, spreadsheet_id: str, worksheet_name: str):
        spreadsheet_id = extract_spreadsheet_id(spreadsheet_id)
        spreadsheet = self.client.open_by_key(spreadsheet_id)
        worksheet = spreadsheet.worksheet(worksheet_name)
        return spreadsheet, worksheet

    def _format_connection_error(self, exc: Exception, worksheet_name: str) -> str:
        error_name = exc.__class__.__name__
        detail = str(exc).strip()
        account = self.service_account_email or "the service account in your JSON file"

        if error_name == "SpreadsheetNotFound":
            return (
                "Google could not open the spreadsheet. Check the spreadsheet ID and "
                f"share it with {account} as Editor."
            )
        if error_name == "WorksheetNotFound":
            return f"Worksheet/tab '{worksheet_name}' was not found in this spreadsheet."
        if detail:
            return detail
        return f"Connection failed. Share the spreadsheet with {account} as Editor, then try again."

    def check_target(
        self,
        name: str,
        spreadsheet_id: str,
        worksheet_name: str,
        expected_headers: Sequence[str],
    ) -> SheetCheckResult:
        spreadsheet_id = extract_spreadsheet_id(spreadsheet_id)
        if not spreadsheet_id:
            return SheetCheckResult(name=name, ok=False, message="Spreadsheet ID is blank.")
        if not worksheet_name:
            return SheetCheckResult(name=name, ok=False, message="Worksheet name is blank.")

        try:
            spreadsheet, worksheet = self._open_worksheet(spreadsheet_id, worksheet_name)
            actual = worksheet.row_values(3)
            actual = [str(x).strip().upper() for x in actual[: len(expected_headers)]]
            expected = [str(x).strip().upper() for x in expected_headers]
            if actual != expected:
                return SheetCheckResult(
                    name=name,
                    ok=False,
                    spreadsheet_title=spreadsheet.title,
                    worksheet_name=worksheet.title,
                    message=(
                        "Connected, but row 3 headers do not match. "
                        "Run the Apps Script setup function for this sheet."
                    ),
                )
            return SheetCheckResult(
                name=name,
                ok=True,
                spreadsheet_title=spreadsheet.title,
                worksheet_name=worksheet.title,
                message="Connected and headers match.",
            )
        except Exception as exc:
            return SheetCheckResult(
                name=name,
                ok=False,
                message=self._format_connection_error(exc, worksheet_name),
            )

    def check_all(self, config: Dict) -> List[SheetCheckResult]:
        high = config.get("targets", {}).get("high_side", {})
        low = config.get("targets", {}).get("low_side", {})
        return [
            self.check_target(
                "High Side / OFN",
                high.get("spreadsheet_id", ""),
                high.get("worksheet_name", "HS ENTRY"),
                HIGH_SIDE_HEADERS,
            ),
            self.check_target(
                "Low Side / PO",
                low.get("spreadsheet_id", ""),
                low.get("worksheet_name", "LS ENTRY"),
                LOW_SIDE_HEADERS,
            ),
        ]

    @staticmethod
    def _next_sr_no(worksheet) -> int:
        values = worksheet.col_values(1)
        max_seen = 0
        for value in values[3:]:  # rows below title/blank/header
            try:
                max_seen = max(max_seen, int(float(str(value).strip())))
            except Exception:
                continue
        return max_seen + 1

    def append_dict_rows(
        self,
        spreadsheet_id: str,
        worksheet_name: str,
        rows: List[Dict[str, object]],
        headers: Sequence[str],
        auto_serial: bool = True,
    ) -> int:
        if not rows:
            return 0
        _, worksheet = self._open_worksheet(spreadsheet_id, worksheet_name)
        values: List[List[object]] = []
        next_sr = self._next_sr_no(worksheet) if auto_serial else None
        for idx, row in enumerate(rows):
            clean_row = dict(row)
            if auto_serial and next_sr is not None:
                clean_row["SR NO"] = next_sr + idx
            values.append([clean_row.get(header, "") for header in headers])
        worksheet.append_rows(values, value_input_option="USER_ENTERED")
        return len(values)
