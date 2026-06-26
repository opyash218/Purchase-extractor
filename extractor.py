from __future__ import annotations

import io
import re
from datetime import datetime
from typing import Dict, Iterable, List, Optional

import pdfplumber

HIGH_SIDE_HEADERS = [
    "SR NO",
    "OFN NO",
    "PURCHASE DATE",
    "VRV/ NON VRV/ RA",
    "ITEM DESCRIPTION",
    "PROJECT NAME/ CLIENT NAME",
    "UNIT",
    "QUANTITY",
    "PURCHASE RATE",
    "PURCHASE AMOUNT",
]

LOW_SIDE_HEADERS = [
    "SR NO",
    "PO NO",
    "PO DATE",
    "DESCRIPTION",
    "PROJECT NAME/ CLIENT NAME",
    "UNIT",
    "QTY",
    "RATE",
    "AMOUNT",
]

DOC_TYPE_HIGH = "OFN - High Side"
DOC_TYPE_LOW = "PO - Low Side"


def _clean(value: object) -> str:
    if value is None:
        return ""
    text = str(value)
    text = text.replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n+", " ", text)
    return text.strip()


def _clean_multiline(value: object) -> str:
    if value is None:
        return ""
    text = str(value)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\s*\n\s*", " ", text)
    return text.strip()


def _parse_number(value: object) -> Optional[float]:
    text = _clean(value)
    if not text:
        return None
    text = text.replace(",", "")
    text = text.replace("INR", "")
    text = text.replace("Rs.", "")
    text = text.replace("Rs", "")
    text = text.replace("₹", "")
    text = re.sub(r"[^0-9.\-]", "", text)
    if text in ("", ".", "-", "-."):
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _format_number(value: Optional[float]) -> object:
    if value is None:
        return ""
    if abs(value - int(value)) < 0.0000001:
        return int(value)
    return round(value, 2)


def _parse_date(value: str) -> str:
    value = _clean(value)
    for fmt in ("%d.%m.%Y", "%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d", "%d.%m.%y", "%d/%m/%y", "%d-%m-%y"):
        try:
            return datetime.strptime(value, fmt).strftime("%d/%m/%Y")
        except ValueError:
            pass
    return value


def _first_regex(pattern: str, text: str, flags: int = 0, default: str = "") -> str:
    match = re.search(pattern, text, flags)
    if not match:
        return default
    return _clean_multiline(match.group(1))


def _load_pdf(file_bytes: bytes) -> tuple[str, list[list[list[object]]]]:
    all_text: List[str] = []
    all_tables: list[list[list[object]]] = []
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            text = page.extract_text(x_tolerance=1, y_tolerance=3) or ""
            all_text.append(text)
            try:
                all_tables.extend(page.extract_tables() or [])
            except Exception:
                # Text fallback will still run.
                pass
    return "\n".join(all_text), all_tables


def _extract_ofn_project(text: str, tables: list[list[list[object]]]) -> str:
    # Prefer delivery address because high-side sheet wants project/client name.
    for table in tables:
        for row in table:
            cells = [_clean_multiline(c) for c in row]
            for idx, cell in enumerate(cells):
                if cell.lower() == "delivery address" and idx + 1 < len(cells):
                    value = cells[idx + 1]
                    if value:
                        return value
    value = _first_regex(r"Delivery Address\s+(.+?)(?:\nBilling Address|\n\( Mention Floor \)|\nContact Person|\nGSTIN)", text, re.I | re.S)
    if value:
        return value
    value = _first_regex(r"Consignee Name\s+(.+?)(?:\nDealer Name|\nDelivery Address|\nBilling Address)", text, re.I | re.S)
    return value


def _extract_ofn_vrv(text: str) -> str:
    special = _first_regex(r"DAIPL[-\s]+(VRV|NON[-\s]?VRV|RA)\b", text, re.I)
    if special:
        special = special.upper().replace(" ", "-")
        if "NON" in special:
            return "NON VRV"
        return special
    if re.search(r"\bNON[-\s]?VRV\b", text, re.I):
        return "NON VRV"
    if re.search(r"\bVRV\b", text, re.I):
        return "VRV"
    if re.search(r"\bRA\b", text):
        return "RA"
    return ""


def _table_has_words(row: Iterable[object], *words: str) -> bool:
    row_text = " ".join(_clean(c).upper() for c in row)
    return all(word.upper() in row_text for word in words)


def parse_ofn_pdf(file_bytes: bytes) -> List[Dict[str, object]]:
    text, tables = _load_pdf(file_bytes)
    order_no = _first_regex(r"Order\s*No\.?\s*([^\n]+)", text, re.I)
    purchase_date = _first_regex(r"(?:Ordering\s+Location\s+)?Date\s*[:\-]?\s*(\d{1,4}[./\-]\d{1,2}[./\-]\d{1,4})", text, re.I)
    purchase_date = _parse_date(purchase_date)
    project_name = _extract_ofn_project(text, tables)
    vrv_type = _extract_ofn_vrv(text)

    rows: List[Dict[str, object]] = []

    # Primary extraction through pdfplumber tables.
    for table in tables:
        header_index = None
        for i, row in enumerate(table):
            if _table_has_words(row, "Product", "Qty", "Rate", "Amount"):
                header_index = i
                break
        if header_index is None:
            continue

        for row in table[header_index + 1 :]:
            if len(row) < 5:
                continue
            sr = _parse_number(row[0])
            description = _clean_multiline(row[1]) if len(row) > 1 else ""
            qty = _parse_number(row[2]) if len(row) > 2 else None
            rate = _parse_number(row[3]) if len(row) > 3 else None
            amount = _parse_number(row[4]) if len(row) > 4 else None
            if sr is None or not description or qty is None:
                continue
            rows.append(
                {
                    "SR NO": int(sr),
                    "OFN NO": order_no,
                    "PURCHASE DATE": purchase_date,
                    "VRV/ NON VRV/ RA": vrv_type,
                    "ITEM DESCRIPTION": description,
                    "PROJECT NAME/ CLIENT NAME": project_name,
                    "UNIT": "NOS",
                    "QUANTITY": _format_number(qty),
                    "PURCHASE RATE": _format_number(rate),
                    "PURCHASE AMOUNT": _format_number(amount),
                }
            )
        if rows:
            break

    # Fallback for text-only cases.
    if not rows:
        pattern = re.compile(
            r"^\s*(\d+)\s+([A-Z0-9][A-Z0-9/_.\- ]*?)\s+(\d+(?:\.\d+)?)\s+([\d,]+(?:\.\d+)?)\s+([\d,]+(?:\.\d+)?)\b",
            re.M,
        )
        for m in pattern.finditer(text):
            rows.append(
                {
                    "SR NO": int(m.group(1)),
                    "OFN NO": order_no,
                    "PURCHASE DATE": purchase_date,
                    "VRV/ NON VRV/ RA": vrv_type,
                    "ITEM DESCRIPTION": _clean(m.group(2)),
                    "PROJECT NAME/ CLIENT NAME": project_name,
                    "UNIT": "NOS",
                    "QUANTITY": _format_number(_parse_number(m.group(3))),
                    "PURCHASE RATE": _format_number(_parse_number(m.group(4))),
                    "PURCHASE AMOUNT": _format_number(_parse_number(m.group(5))),
                }
            )

    return rows


def _extract_po_project(text: str, tables: list[list[list[object]]]) -> str:
    value = _first_regex(r"Project:\s*(.+?)(?:\nMODEL/|\nS/N|\n\d+\s+[A-Z])", text, re.I | re.S)
    if not value:
        for table in tables:
            for row in table:
                row_text = " ".join(_clean_multiline(c) for c in row if c)
                match = re.search(r"Project:\s*(.+)", row_text, re.I)
                if match:
                    value = _clean_multiline(match.group(1))
                    break
            if value:
                break
    value = re.sub(r"\s+VRV\s*-\s*LS\s*$", "", value, flags=re.I)
    value = re.sub(r"\s+LS\s*$", "", value, flags=re.I)
    return value.strip()


def parse_po_pdf(file_bytes: bytes) -> List[Dict[str, object]]:
    text, tables = _load_pdf(file_bytes)
    po_no = _first_regex(r"PO\s*No\s*[:\-]?\s*([^\n]+)", text, re.I)
    po_date = _first_regex(r"DATE\s*[:\-]?\s*(\d{1,4}[./\-]\d{1,2}[./\-]\d{1,4})", text, re.I)
    po_date = _parse_date(po_date)
    project_name = _extract_po_project(text, tables)

    rows: List[Dict[str, object]] = []

    for table in tables:
        header_index = None
        header = []
        for i, row in enumerate(table):
            if _table_has_words(row, "DESCRIPTION", "QTY", "UNIT", "PRICE", "TOTAL"):
                header_index = i
                header = [_clean(c).upper() for c in row]
                break
        if header_index is None:
            continue

        def find_col(name: str, default: int) -> int:
            for idx, cell in enumerate(header):
                if name in cell:
                    return idx
            return default

        sn_col = find_col("S/N", 0)
        desc_col = find_col("DESCRIPTION", 1)
        qty_col = find_col("QTY", 4)
        unit_col = find_col("UNIT", 5)
        price_col = find_col("PRICE", 7)
        total_col = find_col("TOTAL", 9)

        for row in table[header_index + 1 :]:
            if len(row) <= max(sn_col, desc_col, qty_col, unit_col, price_col, total_col):
                continue
            sr = _parse_number(row[sn_col])
            description = _clean_multiline(row[desc_col])
            qty = _parse_number(row[qty_col])
            unit = _clean_multiline(row[unit_col])
            rate = _parse_number(row[price_col])
            amount = _parse_number(row[total_col])
            if sr is None or not description or qty is None:
                continue
            rows.append(
                {
                    "SR NO": int(sr),
                    "PO NO": po_no,
                    "PO DATE": po_date,
                    "DESCRIPTION": description,
                    "PROJECT NAME/ CLIENT NAME": project_name,
                    "UNIT": unit,
                    "QTY": _format_number(qty),
                    "RATE": _format_number(rate),
                    "AMOUNT": _format_number(amount),
                }
            )
        if rows:
            break

    if not rows:
        line_pattern = re.compile(
            r"^\s*(\d+)\s+(.+?)\s+(\d+(?:\.\d+)?)\s+([A-Z]+)\s+([\d,]+(?:\.\d+)?)\s+[\d,]+(?:\.\d+)?\s+([\d,]+(?:\.\d+)?)\s*$",
            re.M,
        )
        for m in line_pattern.finditer(text):
            rows.append(
                {
                    "SR NO": int(m.group(1)),
                    "PO NO": po_no,
                    "PO DATE": po_date,
                    "DESCRIPTION": _clean(m.group(2)),
                    "PROJECT NAME/ CLIENT NAME": project_name,
                    "UNIT": m.group(4),
                    "QTY": _format_number(_parse_number(m.group(3))),
                    "RATE": _format_number(_parse_number(m.group(5))),
                    "AMOUNT": _format_number(_parse_number(m.group(6))),
                }
            )

    return rows


def parse_pdf(file_bytes: bytes, doc_type: str) -> List[Dict[str, object]]:
    if doc_type == DOC_TYPE_HIGH:
        rows = parse_ofn_pdf(file_bytes)
    elif doc_type == DOC_TYPE_LOW:
        rows = parse_po_pdf(file_bytes)
    else:
        raise ValueError("Choose either OFN - High Side or PO - Low Side before upload.")

    if not rows:
        raise ValueError("No line items were extracted. Check that the selected document type matches the uploaded PDF.")
    return rows


def headers_for_doc_type(doc_type: str) -> List[str]:
    if doc_type == DOC_TYPE_HIGH:
        return HIGH_SIDE_HEADERS
    if doc_type == DOC_TYPE_LOW:
        return LOW_SIDE_HEADERS
    raise ValueError(f"Unknown document type: {doc_type}")
