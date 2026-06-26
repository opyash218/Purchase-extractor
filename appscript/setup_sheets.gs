/**
 * Google Sheets setup for the Python Purchase PDF Upload system.
 *
 * How to use:
 * 1. Open the Google Sheet.
 * 2. Extensions > Apps Script.
 * 3. Paste this full script and Save.
 * 4. Run setupHighSide() in the High Side spreadsheet.
 * 5. Run setupLowSide() in the Low Side spreadsheet.
 * 6. Share the spreadsheet with this service account as Editor:
 *    what-s-app-bot-v1@whats-app-bot-498305.iam.gserviceaccount.com
 */

const SERVICE_ACCOUNT_EMAIL = 'what-s-app-bot-v1@whats-app-bot-498305.iam.gserviceaccount.com';

const HIGH_SIDE = {
  sheetName: 'HS ENTRY',
  title: 'HIGH SIDE PURCHASE ENTRY 2026',
  headers: [
    'SR NO',
    'OFN NO',
    'PURCHASE DATE',
    'VRV/ NON VRV/ RA',
    'ITEM DESCRIPTION',
    'PROJECT NAME/ CLIENT NAME',
    'UNIT',
    'QUANTITY',
    'PURCHASE RATE',
    'PURCHASE AMOUNT'
  ],
  widths: [70, 190, 130, 150, 320, 260, 110, 120, 145, 150],
  dateColumns: [3],
  numberColumns: [8],
  currencyColumns: [9, 10]
};

const LOW_SIDE = {
  sheetName: 'LS ENTRY',
  title: 'LOW SIDE PURCHASE ENTRY 2026',
  headers: [
    'SR NO',
    'PO NO',
    'PO DATE',
    'DESCRIPTION',
    'PROJECT NAME/ CLIENT NAME',
    'UNIT',
    'QTY',
    'RATE',
    'AMOUNT'
  ],
  widths: [70, 170, 130, 420, 340, 110, 110, 120, 140],
  dateColumns: [3],
  numberColumns: [7, 8, 9],
  currencyColumns: []
};

function onOpen() {
  SpreadsheetApp.getUi()
    .createMenu('Purchase Entry Setup')
    .addItem('Setup High Side sheet', 'setupHighSide')
    .addItem('Setup Low Side sheet', 'setupLowSide')
    .addItem('Setup both tabs in this spreadsheet', 'setupBothInCurrentSpreadsheet')
    .addToUi();
}

function setupHighSide() {
  setupSheet_(HIGH_SIDE);
  showDone_('High Side');
}

function setupLowSide() {
  setupSheet_(LOW_SIDE);
  showDone_('Low Side');
}

function setupBothInCurrentSpreadsheet() {
  setupSheet_(HIGH_SIDE);
  setupSheet_(LOW_SIDE);
  showDone_('High Side and Low Side');
}

function setupSheet_(config) {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  let sheet = ss.getSheetByName(config.sheetName);
  if (!sheet) {
    sheet = ss.insertSheet(config.sheetName);
  }

  const colCount = config.headers.length;
  ensureSize_(sheet, 1000, colCount);

  // Row 1 title, row 2 spacer, row 3 headers.
  const titleRange = sheet.getRange(1, 1, 1, colCount);
  titleRange.breakApart();
  titleRange.merge();
  titleRange.setValue(config.title);
  titleRange
    .setFontFamily('Cambria')
    .setFontSize(12)
    .setFontWeight('bold')
    .setHorizontalAlignment('center')
    .setVerticalAlignment('middle')
    .setBackground('#ead8bd')
    .setFontColor('#002060')
    .setBorder(true, true, true, true, true, true, '#000000', SpreadsheetApp.BorderStyle.SOLID);

  sheet.getRange(2, 1, 1, colCount).clearContent().setBackground('#ffffff');

  const headerRange = sheet.getRange(3, 1, 1, colCount);
  headerRange.setValues([config.headers]);
  headerRange
    .setFontFamily('Cambria')
    .setFontSize(10)
    .setFontWeight('bold')
    .setHorizontalAlignment('center')
    .setVerticalAlignment('middle')
    .setBackground('#d9d9d9')
    .setWrap(true)
    .setBorder(true, true, true, true, true, true, '#000000', SpreadsheetApp.BorderStyle.SOLID);

  const bodyRange = sheet.getRange(4, 1, sheet.getMaxRows() - 3, colCount);
  bodyRange
    .setFontFamily('Cambria')
    .setFontSize(10)
    .setVerticalAlignment('middle')
    .setBorder(true, true, true, true, true, true, '#000000', SpreadsheetApp.BorderStyle.SOLID);

  // Alignments similar to the screenshots.
  sheet.getRange(4, 1, sheet.getMaxRows() - 3, 1).setHorizontalAlignment('center');
  sheet.getRange(4, 2, sheet.getMaxRows() - 3, 2).setHorizontalAlignment('center');
  sheet.getRange(4, colCount - 3, sheet.getMaxRows() - 3, 4).setHorizontalAlignment('center');

  config.widths.forEach(function(width, index) {
    sheet.setColumnWidth(index + 1, width);
  });
  sheet.setRowHeight(1, 34);
  sheet.setRowHeight(2, 22);
  sheet.setRowHeight(3, 38);
  sheet.setFrozenRows(3);

  config.dateColumns.forEach(function(column) {
    sheet.getRange(4, column, sheet.getMaxRows() - 3, 1).setNumberFormat('dd/mm/yyyy');
  });
  config.numberColumns.forEach(function(column) {
    sheet.getRange(4, column, sheet.getMaxRows() - 3, 1).setNumberFormat('#,##0.00');
  });
  config.currencyColumns.forEach(function(column) {
    sheet.getRange(4, column, sheet.getMaxRows() - 3, 1).setNumberFormat('\u20B9#,##0.00');
  });

  // Add validation for OFN VRV type column.
  if (config.sheetName === HIGH_SIDE.sheetName) {
    const rule = SpreadsheetApp.newDataValidation()
      .requireValueInList(['VRV', 'NON VRV', 'RA'], true)
      .setAllowInvalid(true)
      .build();
    sheet.getRange(4, 4, sheet.getMaxRows() - 3, 1).setDataValidation(rule);
  }

  sheet.getRange(1, 1).setNote(
    'Prepared for Python PDF uploader. Share this spreadsheet with ' + SERVICE_ACCOUNT_EMAIL + ' as Editor.'
  );
}

function ensureSize_(sheet, minRows, minCols) {
  if (sheet.getMaxRows() < minRows) {
    sheet.insertRowsAfter(sheet.getMaxRows(), minRows - sheet.getMaxRows());
  }
  if (sheet.getMaxColumns() < minCols) {
    sheet.insertColumnsAfter(sheet.getMaxColumns(), minCols - sheet.getMaxColumns());
  }
}

function showDone_(name) {
  SpreadsheetApp.getUi().alert(
    name + ' setup complete. Now share this spreadsheet with ' + SERVICE_ACCOUNT_EMAIL + ' as Editor, then use Check connection in the Python app.'
  );
}
