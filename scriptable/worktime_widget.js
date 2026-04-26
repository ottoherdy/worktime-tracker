// Arbetsdagens status widget
// Konfiguration
const HA_URL = "https://homeassistant.local:8123";
const HA_TOKEN = "YOUR_LONG_LIVED_ACCESS_TOKEN_HERE";

// Färgkonstanter
const COLORS = {
  atWork: "#3B82F6",
  done: "#10B981",
  overtime: "#F97316",
  offDuty: "#6B7280",
  darkBg: Color.dynamic(new Color("#1F2937"), new Color("#0F172A")),
  lightBg: new Color("#FFFFFF"),
  text: Color.dynamic(new Color("#F3F4F6"), new Color("#1F2937"))
};

// Hjälpfunktion: Hämta data från Home Assistant
async function fetchHA(entityId) {
  try {
    const url = `${HA_URL}/api/states/${entityId}`;
    const request = new Request(url);
    request.headers = {
      "Authorization": `Bearer ${HA_TOKEN}`,
      "Content-Type": "application/json"
    };

    const response = await request.loadJSON();
    return response;
  } catch (error) {
    console.error(`Fel vid hämtning av ${entityId}: ${error}`);
    return null;
  }
}

// Hjälpfunktion: Parsa tidsstämpel
function parseTime(timeStr) {
  if (!timeStr) return null;
  const parts = timeStr.split(":");
  if (parts.length >= 2) {
    return new Date(2000, 0, 1, parseInt(parts[0]), parseInt(parts[1]), 0);
  }
  return null;
}

// Hjälpfunktion: Beräkna progress procent
function calculateProgress(arrivalStr, plannedEndStr) {
  const arrival = parseTime(arrivalStr);
  const plannedEnd = parseTime(plannedEndStr);
  const now = new Date();

  if (!arrival || !plannedEnd) return 0;

  const startMs = arrival.getTime();
  const endMs = plannedEnd.getTime();
  const nowMs = now.getTime();

  if (nowMs < startMs) return 0;
  if (nowMs > endMs) return 1;

  return (nowMs - startMs) / (endMs - startMs);
}

// Hjälpfunktion: Formatera tid
function formatTime(minutes) {
  if (minutes < 0) minutes = 0;
  const hours = Math.floor(minutes / 60);
  const mins = minutes % 60;
  return `${hours}h ${mins.toString().padStart(2, "0")}m`;
}

// Huvudfunktion: Bygg widget
async function buildWidget() {
  const widget = new ListWidget();

  // Försök hämta all data
  const [
    arrivalData,
    plannedEndData,
    timeRemData,
    statusData,
    hoursTodayData
  ] = await Promise.all([
    fetchHA("sensor.worktime_tracker_arrival_time"),
    fetchHA("sensor.worktime_tracker_planned_end_time"),
    fetchHA("sensor.worktime_tracker_time_remaining"),
    fetchHA("sensor.worktime_tracker_status"),
    fetchHA("sensor.worktime_tracker_hours_today")
  ]);

  // Kontrollera om vi fick data
  if (!arrivalData || !statusData) {
    widget.backgroundColor = COLORS.darkBg;
    const errorText = widget.addText("⚠ Kan ej nå HA");
    errorText.textColor = new Color("#EF4444");
    errorText.font = Font.systemFont(16);
    errorText.centerAlignText();
    widget.setPadding(16, 16, 16, 16);
    return widget;
  }

  const status = statusData.state || "off_duty";
  const arrivalTime = arrivalData.state;
  const plannedEndTime = plannedEndData?.state;
  const timeRemaining = timeRemData?.state || "0";
  const hoursToday = hoursTodayData?.state || "0.0";

  widget.backgroundColor = COLORS.darkBg;
  widget.setPadding(16, 16, 16, 16);

  // Rita huvudinnehållet
  const container = widget.addStack();
  container.layoutVertically();
  container.spacing = 12;
  container.centerAlignContent();

  // Baserat på status
  if (status === "off_duty") {
    // Ej på jobbet
    const statusText = container.addText("Ej på jobbet");
    statusText.textColor = new Color(COLORS.offDuty);
    statusText.font = Font.boldSystemFont(24);
    statusText.centerAlignText();

  } else if (status === "done") {
    // Arbetsdag avslutad
    const statusText = container.addText("Klar! ✓");
    statusText.textColor = new Color(COLORS.done);
    statusText.font = Font.boldSystemFont(28);
    statusText.centerAlignText();

  } else if (status === "overtime") {
    // Övertid
    const ctx = new DrawContext();
    ctx.size = new Size(200, 200);
    ctx.opaque = false;

    // Rita cirkel (orange)
    const circleRect = new Rect(25, 25, 150, 150);
    ctx.setLineWidth(12);
    ctx.setStrokeColor(new Color(COLORS.overtime));
    ctx.strokeEllipse(circleRect);

    // Fyll cirkeln helt med orange
    ctx.setFillColor(new Color(COLORS.overtime).withAlpha(0.2));
    ctx.fillEllipse(circleRect);

    // Text i mitten
    const overtimeMinutes = parseInt(timeRemaining) || 0;
    const overtimeText = formatTime(overtimeMinutes);

    ctx.drawText(
      overtimeText,
      new Point(100, 90),
      new Font("San Francisco", 18),
      new Color(COLORS.overtime)
    );

    const canvasImg = ctx.getImage();
    const imgStack = container.addImage(canvasImg);
    imgStack.centerAlignImage();

  } else if (status === "at_work") {
    // Arbetar
    const progress = calculateProgress(arrivalTime, plannedEndTime);
    const ctx = new DrawContext();
    ctx.size = new Size(200, 200);
    ctx.opaque = false;

    // Rita bakgrund cirkel
    const circleRect = new Rect(25, 25, 150, 150);
    ctx.setLineWidth(12);
    ctx.setStrokeColor(new Color(COLORS.atWork).withAlpha(0.3));
    ctx.strokeEllipse(circleRect);

    // Rita progress båge
    ctx.setLineWidth(12);
    ctx.setStrokeColor(new Color(COLORS.atWork));

    const startAngle = -Math.PI / 2;
    const endAngle = startAngle + (Math.PI * 2 * progress);

    const centerX = 100;
    const centerY = 100;
    const radius = 75;

    const path = new Path();
    path.addArc(
      new Point(centerX, centerY),
      radius,
      startAngle,
      endAngle,
      true
    );
    ctx.addPath(path);
    ctx.strokePath();

    // Text i mitten: tid kvar
    const remainingMinutes = parseInt(timeRemaining) || 0;
    const remainingText = formatTime(remainingMinutes);

    ctx.drawText(
      remainingText,
      new Point(100, 85),
      new Font("San Francisco", 20),
      new Color(COLORS.text)
    );

    const canvasImg = ctx.getImage();
    const imgStack = container.addImage(canvasImg);
    imgStack.centerAlignImage();
  }

  // Text under cirkeln: Idag: X.Xh
  const hoursText = container.addText(`Idag: ${hoursToday}h`);
  hoursText.textColor = COLORS.text;
  hoursText.font = Font.systemFont(14);
  hoursText.centerAlignText();

  return widget;
}

// Huvud
const widget = await buildWidget();

if (config.runsInWidget) {
  Script.setWidget(widget);
} else {
  widget.presentMedium();
}

widget.refreshAfterDate = new Date(Date.now() + 5 * 60 * 1000);
Script.complete();
