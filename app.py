from __future__ import annotations

import json
import os
from typing import Dict, List

import pandas as pd
import streamlit as st

from extractor import (
    DOC_TYPE_HIGH,
    DOC_TYPE_LOW,
    HIGH_SIDE_HEADERS,
    LOW_SIDE_HEADERS,
    headers_for_doc_type,
    parse_pdf,
)
from settings_store import load_config, save_config
from sheets_client import GoogleSheetsClient, extract_spreadsheet_id

DEFAULT_SERVICE_ACCOUNT_EMAIL = "what-s-app-bot-v1@whats-app-bot-498305.iam.gserviceaccount.com"
WIDE_PREVIEW_COLUMNS = {
    "DESCRIPTION",
    "ITEM DESCRIPTION",
    "PROJECT NAME/ CLIENT NAME",
}


def service_account_email_from_config(config: Dict) -> str:
    service_json = config.get("service_account_json", "service_account.json") or "service_account.json"
    service_json = os.path.expanduser(service_json)
    try:
        with open(service_json, "r", encoding="utf-8") as fh:
            info = json.load(fh)
        return info.get("client_email") or DEFAULT_SERVICE_ACCOUNT_EMAIL
    except Exception:
        return DEFAULT_SERVICE_ACCOUNT_EMAIL


def _target_for_doc_type(config: Dict, doc_type: str) -> Dict:
    if doc_type == DOC_TYPE_HIGH:
        return config["targets"]["high_side"]
    if doc_type == DOC_TYPE_LOW:
        return config["targets"]["low_side"]
    raise ValueError("Unknown document type")


def _expected_headers(doc_type: str) -> List[str]:
    return HIGH_SIDE_HEADERS if doc_type == DOC_TYPE_HIGH else LOW_SIDE_HEADERS


def _preview_column_config(headers: List[str]) -> Dict:
    return {
        header: st.column_config.Column(
            header,
            width="large" if header in WIDE_PREVIEW_COLUMNS else "medium",
        )
        for header in headers
    }


def _preview_height(row_count: int) -> int:
    visible_rows = min(max(row_count, 6), 12)
    return 74 + (visible_rows * 35)


def _show_check_results(results) -> bool:
    all_ok = True
    for result in results:
        icon = "✅" if result.ok else "❌"
        title = result.spreadsheet_title or "Not connected"
        st.write(f"{icon} **{result.name}** - {result.message}")
        if result.spreadsheet_title:
            st.caption(f"Spreadsheet: {title} | Worksheet: {result.worksheet_name}")
        all_ok = all_ok and result.ok
    return all_ok


def check_connection(config: Dict) -> bool:
    try:
        client = GoogleSheetsClient(config.get("service_account_json", "service_account.json"))
        st.info(f"Using service account: {client.service_account_email or service_account_email_from_config(config)}")
        results = client.check_all(config)
        return _show_check_results(results)
    except Exception as exc:
        st.error(str(exc))
        return False


st.set_page_config(page_title="Purchase PDF to Google Sheets", layout="wide")
st.title("Purchase PDF to Google Sheets")
st.caption("OFN PDFs go to the High Side sheet. PO PDFs go to the Low Side sheet.")

if "sheets_ready" not in st.session_state:
    st.session_state.sheets_ready = False
if "config" not in st.session_state:
    st.session_state.config = load_config()

config = st.session_state.config
settings_tab, upload_tab, guide_tab = st.tabs(["Settings", "Upload PDF", "Guide"])

with settings_tab:
    st.subheader("1. Configure Google Sheets")
    st.write(
        "Paste the spreadsheet IDs or full Google Sheets URLs for the High Side and Low Side sheets. "
        "Run the Apps Script setup first so row 3 headers match the app."
    )

    with st.form("settings_form"):
        service_json = st.text_input(
            "Service account JSON path",
            value=config.get("service_account_json", "service_account.json"),
            help="Keep the JSON key file in this project folder, or paste the full path here.",
        )
        st.markdown("**High Side / OFN target**")
        high_sheet_id = st.text_input(
            "High Side spreadsheet ID or URL",
            value=config["targets"]["high_side"].get("spreadsheet_id", ""),
        )
        high_ws = st.text_input(
            "High Side worksheet name",
            value=config["targets"]["high_side"].get("worksheet_name", "HS ENTRY"),
        )
        st.markdown("**Low Side / PO target**")
        low_sheet_id = st.text_input(
            "Low Side spreadsheet ID or URL",
            value=config["targets"]["low_side"].get("spreadsheet_id", ""),
        )
        low_ws = st.text_input(
            "Low Side worksheet name",
            value=config["targets"]["low_side"].get("worksheet_name", "LS ENTRY"),
        )
        saved = st.form_submit_button("Save settings")

    if saved:
        config = {
            "service_account_json": service_json.strip() or "service_account.json",
            "targets": {
                "high_side": {
                    "spreadsheet_id": extract_spreadsheet_id(high_sheet_id),
                    "worksheet_name": high_ws.strip() or "HS ENTRY",
                },
                "low_side": {
                    "spreadsheet_id": extract_spreadsheet_id(low_sheet_id),
                    "worksheet_name": low_ws.strip() or "LS ENTRY",
                },
            },
        }
        save_config(config)
        st.session_state.config = config
        st.session_state.sheets_ready = False
        st.success("Settings saved. Now click Check connection.")

    st.divider()
    st.subheader("2. Check connection before upload")
    current_service_account_email = service_account_email_from_config(config)
    st.write(
        f"Share both Google Sheets with the service account from your JSON as **Editor**: "
        f"`{current_service_account_email}`."
    )
    if st.button("Check connection", type="primary"):
        st.session_state.sheets_ready = check_connection(st.session_state.config)
        if st.session_state.sheets_ready:
            st.success("Both sheets are connected and ready.")
        else:
            st.warning("Fix the items above before uploading PDFs.")

with upload_tab:
    st.subheader("Upload and extract")
    st.write("The upload control is enabled only after you select a document type and the sheet connection passes.")

    ready = bool(st.session_state.sheets_ready)
    if ready:
        st.success("Sheet connection is ready.")
    else:
        st.warning("Go to Settings, save sheet IDs, run Check connection, and then return here.")

    doc_type = st.selectbox(
        "Choose PDF type",
        options=["", DOC_TYPE_HIGH, DOC_TYPE_LOW],
        format_func=lambda x: "Select OFN or PO" if x == "" else x,
    )

    upload_enabled = ready and doc_type in (DOC_TYPE_HIGH, DOC_TYPE_LOW)
    pdf_file = st.file_uploader(
        "Upload PDF",
        type=["pdf"],
        disabled=not upload_enabled,
        help="Choose OFN or PO first. The file uploader stays disabled until the selected sheet is connected.",
    )

    if pdf_file is not None and upload_enabled:
        try:
            pdf_bytes = pdf_file.read()
            rows = parse_pdf(pdf_bytes, doc_type)
            headers = headers_for_doc_type(doc_type)
            df = pd.DataFrame(rows, columns=headers)
            st.success(f"Extracted {len(df)} line item rows from {pdf_file.name}.")
            st.write("Review and edit the preview before sending to Google Sheets.")
            edited_df = st.data_editor(
                df,
                num_rows="dynamic",
                use_container_width=True,
                hide_index=True,
                column_order=headers,
                column_config=_preview_column_config(headers),
                height=_preview_height(len(df)),
            )

            st.caption("SR NO will be auto-renumbered when appended, so it continues from the last row already in the sheet.")
            auto_serial = st.checkbox("Auto serial number in Google Sheet", value=True)
            append_clicked = st.button("Send to Google Sheet", type="primary")

            if append_clicked:
                client = GoogleSheetsClient(config.get("service_account_json", "service_account.json"))
                target = _target_for_doc_type(config, doc_type)
                append_rows = edited_df.fillna("").to_dict(orient="records")
                inserted = client.append_dict_rows(
                    spreadsheet_id=target.get("spreadsheet_id", ""),
                    worksheet_name=target.get("worksheet_name", ""),
                    rows=append_rows,
                    headers=_expected_headers(doc_type),
                    auto_serial=auto_serial,
                )
                st.success(f"Uploaded {inserted} rows to {target.get('worksheet_name')}.")
        except Exception as exc:
            st.error(str(exc))

with guide_tab:
    st.subheader("Quick operating guide")
    current_service_account_email = service_account_email_from_config(config)
    st.markdown(
        f"""
1. Put your service account JSON key in this folder as `service_account.json`, or set its path in **Settings**.
2. Share the High Side and Low Side Google Sheets with `{current_service_account_email}` as **Editor**.
3. In each Google Sheet, open **Extensions > Apps Script**, paste `appscript/setup_sheets.gs`, save, and run:
   - `setupHighSide()` for the High Side sheet.
   - `setupLowSide()` for the Low Side sheet.
   - `setupBothInCurrentSpreadsheet()` only if both tabs are in one spreadsheet.
4. Return to this app, paste sheet IDs, and click **Check connection**. Upload is locked until both sheets connect and row 3 headers match.
5. Select **OFN - High Side** or **PO - Low Side**, upload the PDF, review the extracted preview, then send it to Google Sheets.
        """
    )
