# Purchase PDF to Google Sheets

This is a Streamlit Python UI for purchase-entry PDF upload.

- Choose **OFN - High Side** and upload an OFN PDF. Rows are appended to the High Side Google Sheet.
- Choose **PO - Low Side** and upload a PO PDF. Rows are appended to the Low Side Google Sheet.
- The upload button stays disabled until the settings are saved and the connection check confirms that both Google Sheets are accessible and have the correct headers.

## 1. Files in this package

```text
app.py                         Streamlit UI
extractor.py                   OFN/PO PDF extraction logic
sheets_client.py               Google Sheets connection and append logic
settings_store.py              Saves settings to app_config.json
requirements.txt               Python dependencies
app_config.example.json        Example settings file
appscript/setup_sheets.gs      Google Apps Script to create/format columns
run_app.bat                    Windows one-click setup/run helper
run_app.sh                     macOS/Linux setup/run helper
```

## 2. Google Sheet setup

You can use two separate spreadsheets or one spreadsheet with both tabs.

Recommended tab names:

- High Side worksheet/tab: `HS ENTRY`
- Low Side worksheet/tab: `LS ENTRY`

### High Side columns

The Apps Script creates these columns on row 3:

```text
SR NO | OFN NO | PURCHASE DATE | VRV/ NON VRV/ RA | ITEM DESCRIPTION | PROJECT NAME/ CLIENT NAME | UNIT | QUANTITY | PURCHASE RATE | PURCHASE AMOUNT
```

### Low Side columns

The Apps Script creates these columns on row 3:

```text
SR NO | PO NO | PO DATE | DESCRIPTION | PROJECT NAME/ CLIENT NAME | UNIT | QTY | RATE | AMOUNT
```

## 3. Run the Google Apps Script

Do this before using the Python app.

1. Open the High Side Google Sheet.
2. Click **Extensions > Apps Script**.
3. Paste the full script from `appscript/setup_sheets.gs`.
4. Click **Save**.
5. Select function `setupHighSide` and click **Run**.
6. Accept the authorization prompts.
7. Confirm that tab `HS ENTRY` was created/formatted.

Then repeat for the Low Side Google Sheet:

1. Open the Low Side Google Sheet.
2. Open **Extensions > Apps Script**.
3. Paste the same `appscript/setup_sheets.gs` script.
4. Run function `setupLowSide`.
5. Confirm that tab `LS ENTRY` was created/formatted.

If both High Side and Low Side tabs are in the same spreadsheet, you can run `setupBothInCurrentSpreadsheet` instead.

## 4. Share Google Sheets with the service account

Share both Google Sheets with the `client_email` from your service account JSON file as **Editor**.

The Settings page also shows the exact service account email the app is using.

Do not paste the private key into the app. Keep the JSON file on your computer only.

## 5. Add the service account JSON key

Put your service account JSON key in the project folder and name it:

```text
service_account.json
```

Or keep it anywhere and paste the full path in the app Settings tab.

Example Windows path:

```text
C:\Users\YourName\Downloads\service-account-key.json
```

Example macOS/Linux path:

```text
/Users/YourName/Downloads/service-account-key.json
```

## 6. Run the Python app

### Windows

Double-click or run:

```bat
run_app.bat
```

Manual commands:

```bat
python -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
streamlit run app.py
```

### macOS/Linux

```bash
./run_app.sh
```

Manual commands:

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
streamlit run app.py
```

## 7. Configure the app

1. Open the app in your browser.
2. Go to **Settings**.
3. Paste the High Side spreadsheet ID or full Google Sheets URL.
4. Paste the Low Side spreadsheet ID or full Google Sheets URL.
5. Keep worksheet names as `HS ENTRY` and `LS ENTRY`, unless you changed them in the Apps Script.
6. Click **Save settings**.
7. Click **Check connection**.

The app checks:

- The service account JSON exists.
- The service account can open both spreadsheets.
- The target worksheet tabs exist.
- Row 3 headers match the required columns.

Only after both checks pass is the upload screen ready.

## 8. Upload workflow

1. Go to **Upload PDF**.
2. Choose `OFN - High Side` or `PO - Low Side`.
3. Upload the matching PDF.
4. Review the extracted preview table.
5. Edit any field if needed.
6. Click **Send to Google Sheet**.

By default, `SR NO` is automatically renumbered based on the last serial number already in the Google Sheet.

## 9. Current PDF mappings

### OFN / High Side

- `OFN NO` comes from `Order No.`.
- `PURCHASE DATE` comes from `Date`.
- `VRV/ NON VRV/ RA` is detected from DAIPL special remarks or text.
- `ITEM DESCRIPTION`, `QUANTITY`, `PURCHASE RATE`, and `PURCHASE AMOUNT` come from the product table.
- `UNIT` defaults to `NOS` because the OFN sample product table does not include a unit column.
- `PROJECT NAME/ CLIENT NAME` is taken from the delivery address or consignee area and can be edited in the preview.

### PO / Low Side

- `PO NO` comes from `PO No`.
- `PO DATE` comes from `DATE`.
- `PROJECT NAME/ CLIENT NAME` comes from the `Project:` line.
- `DESCRIPTION`, `QTY`, `UNIT`, `RATE`, and `AMOUNT` come from the PO item table.

## 10. Troubleshooting

### Upload button is disabled

Run **Settings > Check connection**. It must show both sheets as connected and headers matching.

### Connected, but headers do not match

Run the Apps Script setup function again in that Google Sheet. The app expects the title on row 1, blank row 2, and exact headers on row 3.

### Permission error

Share the Google Sheet with the service account email as **Editor**. Also confirm that the JSON key file in the app belongs to the same service account.

### PDF extracts wrong project name

The UI preview table is editable. Correct the project/client name before clicking **Send to Google Sheet**. If you have more PDF formats, update the regex rules in `extractor.py`.

# Purchase-OFM-PO-Extractor
