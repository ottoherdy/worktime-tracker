/*
 * Home Assistant - Google Sheets Webhook Integration
 *
 * Instruktioner för installation:
 * 1. Gå till script.google.com och skapa ett nytt projekt
 * 2. Klistra in denna kod i script-editorn
 * 3. Spara projektet (Ctrl+S)
 * 4. Klicka på "Deploy" > "New deployment"
 * 5. Välj typ: "Web app"
 * 6. Ställ in:
 *    - Execute as: Me (din Google-konto)
 *    - Who has access: Anyone
 * 7. Klicka "Deploy" och kopiera den genererade URL:en
 * 8. Använd denna URL som "Sheets webhook URL" i Home Assistant-integreringen
 *
 * Webhook förväntar JSON-data med följande fält:
 * {
 *   "date": "2026-04-25",
 *   "arrival": "2026-04-25T09:00:00+02:00",
 *   "planned_end": "2026-04-25T17:00:00+02:00",
 *   "departure": "2026-04-25T17:30:00+02:00",
 *   "lunch": 0.5,
 *   "hours": 7.5
 * }
 */

/**
 * Webhook POST-mottagare från Home Assistant
 * Tar emot arbetsdata och lagrar/uppdaterar dem i "Worktime"-arket
 */
function doPost(e) {
  try {
    // Parsa inkommande JSON-data
    const requestBody = e.postData.contents;
    const data = JSON.parse(requestBody);

    // Validera obligatoriska fält
    if (!data.date || !data.arrival || !data.planned_end || !data.departure) {
      return createResponse(false, "Saknade obligatoriska fält: date, arrival, planned_end, departure");
    }

    // Hämta eller skapa "Worktime"-arket
    const sheet = getOrCreateWorksheet();

    // Konvertera ISO-tidstämplar till HH:MM-format
    const arrivalTime = extractTime(data.arrival);
    const plannedEndTime = extractTime(data.planned_end);
    const departureTime = extractTime(data.departure);

    // Hämta alla befintliga rader
    const range = sheet.getDataRange();
    const values = range.getValues();

    // Kontrollera om arket är tomt (endast headers eller helt tomt)
    let headerRowIndex = -1;
    let dateColumnIndex = 0;

    if (values.length === 0) {
      // Arket är tomt, lägg till headers
      const headers = ["Datum", "Ankomst", "Planerad slut", "Avresa", "Lunch", "Timmar"];
      sheet.appendRow(headers);
      headerRowIndex = 1;
    } else {
      // Hitta header-raden (första raden)
      const headers = values[0];
      headerRowIndex = 1;

      // Validera att headers finns, annars skapa dem
      if (headers[0] !== "Datum") {
        const expectedHeaders = ["Datum", "Ankomst", "Planerad slut", "Avresa", "Lunch", "Timmar"];
        sheet.insertRowBefore(1);
        sheet.getRange(1, 1, 1, expectedHeaders.length).setValues([expectedHeaders]);
        headerRowIndex = 1;
        // Läs om värden efter header-infogning
        const updatedRange = sheet.getDataRange();
        const updatedValues = updatedRange.getValues();
        values.length = 0;
        values.push(...updatedValues);
      }
    }

    // Sök efter befintlig rad med samma datum
    let existingRowIndex = -1;
    const dateToFind = data.date;

    for (let i = 1; i < values.length; i++) {
      if (values[i][0] === dateToFind) {
        existingRowIndex = i + 1; // Google Sheets använder 1-baserad indexering
        break;
      }
    }

    // Förbered data för uppdatering
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
      // Uppdatera befintlig rad
      sheet.getRange(existingRowIndex, 1, 1, newRow.length).setValues([newRow]);
      action = "updated";
    } else {
      // Lägg till ny rad
      sheet.appendRow(newRow);
      action = "inserted";
    }

    return createResponse(true, null, action);

  } catch (error) {
    return createResponse(false, "Serverfel: " + error.message);
  }
}

/**
 * Hämtar "Worktime"-arket från den aktiva spreadsheeten.
 * Skapar det om det inte finns.
 */
function getOrCreateWorksheet() {
  const spreadsheet = SpreadsheetApp.getActiveSpreadsheet();
  let sheet = spreadsheet.getSheetByName("Worktime");

  if (!sheet) {
    // Arket existerar inte, skapa det
    sheet = spreadsheet.insertSheet("Worktime");
  }

  return sheet;
}

/**
 * Extraherar tid i HH:MM-format från en ISO 8601 tidstämpel
 * Exempel: "2026-04-25T09:30:00+02:00" -> "09:30"
 */
function extractTime(isoString) {
  if (!isoString) {
    return "";
  }

  try {
    // Ta ut tiden-delen (HH:MM:SS)
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
 * Skapar ett standardiserat JSON-svar
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
