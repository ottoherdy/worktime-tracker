/*
 * Home Assistant — Google Sheets webhook receiver for Worktime Tracker
 *
 * Installation:
 * 1. Open the Google Sheet you want to write to
 * 2. Extensions > Apps Script — this binds the script to that sheet
 * 3. Paste this code into the editor, replacing anything already there
 * 4. Save (Ctrl+S / Cmd+S)
 * 5. Deploy > New deployment
 * 6. Type: "Web app", then set:
 *      Execute as:     Me (your Google account)
 *      Who has access: Anyone
 * 7. Deploy, then copy the generated web app URL
 * 8. Paste that URL as "Sheets webhook URL" in the Home Assistant integration
 *
 * The webhook expects JSON with these fields:
 * {
 *   "date": "2026-04-25",
 *   "arrival": "2026-04-25T09:00:00+02:00",
 *   "planned_end": "2026-04-25T17:00:00+02:00",
 *   "departure": "2026-04-25T17:30:00+02:00",
 *   "lunch": 0.5,
 *   "hours": 7.5
 * }
 *
 * Rows are keyed by date: posting the same date twice updates the existing row
 * rather than appending a duplicate.
 */

// ---------------------------------------------------------------------------
// Configuration — adjust these to taste
// ---------------------------------------------------------------------------

// Worksheet (tab) to write to. Must match the "Sheets worksheet" setting in the
// Home Assistant integration. Created automatically if it does not exist.
const SHEET_NAME = "Worktime";

// Column headers, written to row 1 when the sheet is still empty. Translate
// these freely — they are only used to seed a fresh sheet. An existing sheet
// keeps whatever headers it already has; the script never rewrites them.
// Column order is what matters: date, arrival, planned end, departure, lunch, hours.
const HEADERS = ["Date", "Arrival", "Planned end", "Departure", "Lunch", "Hours"];

/**
 * Webhook POST receiver for Home Assistant.
 * Stores or updates one row per workday in the configured worksheet.
 */
function doPost(e) {
  try {
    // Parse the incoming JSON payload
    const requestBody = e.postData.contents;
    const data = JSON.parse(requestBody);

    // Validate required fields
    if (!data.date || !data.arrival || !data.planned_end || !data.departure) {
      return createResponse(false, "Missing required fields: date, arrival, planned_end, departure");
    }

    // Get the target worksheet, creating it if needed
    const sheet = getOrCreateWorksheet();

    // Convert ISO timestamps to HH:MM
    const arrivalTime = extractTime(data.arrival);
    const plannedEndTime = extractTime(data.planned_end);
    const departureTime = extractTime(data.departure);

    // Read every existing row
    const range = sheet.getDataRange();
    const values = range.getValues();

    // Seed headers only on a genuinely empty sheet. A sheet that already has
    // content keeps its own row 1 — whatever language it is in — so this never
    // shifts or overwrites existing data.
    const isEmpty = values.length === 0 ||
      (values.length === 1 && values[0].every(cell => cell === ""));

    if (isEmpty) {
      sheet.getRange(1, 1, 1, HEADERS.length).setValues([HEADERS]);
      values.length = 0;
      values.push(HEADERS);
    }

    // Look for an existing row with the same date
    let existingRowIndex = -1;
    const dateToFind = data.date;

    for (let i = 1; i < values.length; i++) {
      if (values[i][0] === dateToFind) {
        existingRowIndex = i + 1; // Google Sheets rows are 1-based
        break;
      }
    }

    // Build the row to write
    const newRow = [
      data.date,
      arrivalTime,
      plannedEndTime,
      departureTime,
      data.lunch || 0,
      data.hours || 0
    ];

    let action = "inserted";

    if (existingRowIndex > 0) {
      // Overwrite the existing row for this date
      sheet.getRange(existingRowIndex, 1, 1, newRow.length).setValues([newRow]);
      action = "updated";
    } else {
      // Append a new row
      sheet.appendRow(newRow);
      action = "inserted";
    }

    return createResponse(true, null, action);

  } catch (error) {
    return createResponse(false, "Server error: " + error.message);
  }
}

/**
 * Returns the worksheet named by SHEET_NAME, creating it if missing.
 */
function getOrCreateWorksheet() {
  const spreadsheet = SpreadsheetApp.getActiveSpreadsheet();
  let sheet = spreadsheet.getSheetByName(SHEET_NAME);

  if (!sheet) {
    sheet = spreadsheet.insertSheet(SHEET_NAME);
  }

  return sheet;
}

/**
 * Extracts HH:MM from an ISO 8601 timestamp.
 * Example: "2026-04-25T09:30:00+02:00" -> "09:30"
 */
function extractTime(isoString) {
  if (!isoString) {
    return "";
  }

  try {
    // Pull out the time portion (HH:MM:SS)
    const timeMatch = isoString.match(/T(\d{2}):(\d{2}):/);
    if (timeMatch) {
      return timeMatch[1] + ":" + timeMatch[2];
    }
    return "";
  } catch (e) {
    return "";
  }
}

/**
 * Builds a standard JSON response.
 */
function createResponse(ok, error = null, action = null) {
  const response = {
    ok: ok
  };

  if (error) {
    response.error = error;
  }

  if (action) {
    response.action = action;
  }

  return ContentService
    .createTextOutput(JSON.stringify(response))
    .setMimeType(ContentService.MimeType.JSON);
}
