/**
 * Worktime Tracker Lovelace Card
 * Vanilla Web Component — no build step, no external dependencies.
 * Auto-loaded via frontend.add_extra_js_url in __init__.py
 *
 * Config (all optional, defaults shown):
 *   show_header: true            // card title + status badge
 *   show_times: true             // arrival / planned / hours big row
 *   show_progress: true          // progress bar
 *   show_lunch_status: true      // lunch badge + remaining/overtime line
 *   show_actions: true           // log arrival/departure/lunch buttons
 *   show_auto_departure: true    // auto-departure toggle + reset
 *   show_week: false             // one-line week summary (compact)
 *   show_this_week: true         // this-week breakdown table
 *   show_last_week: true         // last-week breakdown table
 *   show_recent: true            // rolling 7-day table
 *   show_edit: true              // edit pencil + row-tap → modal
 *   recent_days_limit: 7         // rows in recent days table
 *
 * Styling: override the CSS variables under :host in your theme or via card_mod.
 *   --wt-card-padding (16px)
 *   --wt-radius (12px)
 *   --wt-status-color (auto from state)
 *   --wt-row-hover-bg, --wt-row-hover-color
 *   --wt-button-bg, --wt-button-color
 *   --wt-table-header-color
 *   --wt-divider-color
 */

const ENTITY_TODAY = "sensor.today_hours_today";
const ENTITY_WEEK = "sensor.this_week_hours_this_week";
const ENTITY_LAST_WEEK = "sensor.last_week_hours_last_week";
const ENTITY_SWITCH = "switch.today_auto_departure";
const DOMAIN = "worktime_tracker";

const STATUS_COLOR = {
  at_work: "var(--success-color, #4caf50)",
  overtime: "var(--warning-color, #ff9800)",
  done: "var(--info-color, #2196f3)",
  off_duty: "var(--disabled-color, #9e9e9e)",
};

const STATUS_LABEL = {
  at_work: "At work",
  overtime: "Overtime",
  done: "Done",
  off_duty: "Off duty",
};

const SECTIONS = [
  ["show_header", "Header (title + status)"],
  ["show_times", "Time row (arrival/planned/hours)"],
  ["show_progress", "Progress bar"],
  ["show_lunch_status", "Lunch + remaining line"],
  ["show_actions", "Action buttons"],
  ["show_auto_departure", "Auto-depart toggle + reset"],
  ["show_week", "Week summary (one-line)"],
  ["show_this_week", "This-week table"],
  ["show_last_week", "Last-week table"],
  ["show_recent", "Recent days table"],
  ["show_edit", "Inline edit (pencil + row-tap)"],
];

const DEFAULTS = {
  show_header: true,
  show_times: true,
  show_progress: true,
  show_lunch_status: true,
  show_actions: true,
  show_auto_departure: true,
  show_week: false,
  show_this_week: true,
  show_last_week: true,
  show_recent: true,
  show_edit: true,
  recent_days_limit: 7,
};

function _fmt(val) {
  return val !== undefined && val !== null && val !== "—" && val !== "" ? val : "—";
}

function _sign(num) {
  if (num === undefined || num === null) return "—";
  const n = parseFloat(num);
  if (isNaN(n)) return "—";
  return (n >= 0 ? "+" : "") + n.toFixed(2) + "h";
}

function _hoursHuman(hours) {
  if (hours === undefined || hours === null) return "—";
  const h = parseFloat(hours);
  if (isNaN(h) || h === 0) return "—";
  const totalMin = Math.round(h * 60);
  const hh = Math.floor(totalMin / 60);
  const mm = totalMin % 60;
  return `${hh}h ${String(mm).padStart(2, "0")}m`;
}

function _progressPct(hours, target) {
  if (!target || !hours) return 0;
  return Math.min(100, Math.round((parseFloat(hours) / parseFloat(target)) * 100));
}

function _timeForInput(val) {
  if (!val || val === "—") return "";
  return val;
}

function _typeIcon(d) {
  if (d.type === "sick") return " 🤒";
  if (d.type === "off") return " 🌴";
  if (d.punch_out_missing) return " ⚠";
  return "";
}

function _hoursCell(d) {
  if (d.type === "sick") return "sick";
  if (d.type === "off") return "off";
  return d.human_readable || "—";
}

class WorktimeTrackerCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._hass = null;
    this._intervalId = null;
    this._editing = null;
  }

  set hass(hass) {
    this._hass = hass;
    this._render();
  }

  connectedCallback() {
    this._intervalId = setInterval(() => this._render(), 30000);
  }

  disconnectedCallback() {
    if (this._intervalId) {
      clearInterval(this._intervalId);
      this._intervalId = null;
    }
  }

  setConfig(config) {
    this._config = config || {};
  }

  getCardSize() {
    return 6;
  }

  _cfg(key) {
    if (this._config && key in this._config) return this._config[key];
    return DEFAULTS[key];
  }

  _callService(service, data = {}) {
    if (!this._hass) return;
    this._hass.callService(DOMAIN, service, data);
  }

  _toggleSwitch() {
    if (!this._hass) return;
    const swState = this._hass.states[ENTITY_SWITCH];
    if (!swState) return;
    const svc = swState.state === "on" ? "turn_off" : "turn_on";
    this._hass.callService("switch", svc, { entity_id: ENTITY_SWITCH });
  }

  _openEdit(day) {
    if (!day) return;
    this._editing = {
      date: day.date,
      arrival: _timeForInput(day.arrival),
      departure: _timeForInput(day.departure),
      lunch: day.lunch && day.lunch !== "—" ? day.lunch : "",
      type: day.type || "normal",
      hours: day.hours != null ? String(day.hours) : "",
    };
    this._render();
  }

  _closeEdit() {
    this._editing = null;
    this._render();
  }

  _saveEdit() {
    if (!this._editing) return;
    const e = this._editing;
    const payload = { date: e.date, type: e.type };
    if (e.type === "normal") {
      if (e.arrival) payload.arrival = e.arrival;
      if (e.departure) payload.departure = e.departure;
      if (e.lunch) payload.lunch = e.lunch;
    } else if (e.hours !== "") {
      payload.hours = parseFloat(e.hours);
    }
    this._callService("edit_day", payload);
    this._closeEdit();
  }

  _renderDayTable(opts) {
    // opts: {id, title, days, totals, columns:['date'|'weekday','arrival','departure','hours'], editable}
    const { id, title, days, totals, columns, editable } = opts;
    if (!days || days.length === 0) {
      return `
        <div class="block">
          ${title ? `<div class="block-title">${title}</div>` : ""}
          <div class="empty">No data</div>
        </div>`;
    }
    const head = columns.map((c) => {
      if (c === "date") return `<th>Date</th>`;
      if (c === "weekday") return `<th>Day</th>`;
      if (c === "arrival") return `<th>In</th>`;
      if (c === "departure") return `<th>Out</th>`;
      if (c === "hours") return `<th style="text-align:right">Hours</th>`;
      return "<th></th>";
    }).join("");

    const rowsHtml = days.map((d, i) => {
      const cells = columns.map((c) => {
        if (c === "date") return `<td>${d.date || "—"}</td>`;
        if (c === "weekday") return `<td>${d.weekday || "—"}</td>`;
        if (c === "arrival") return `<td>${d.arrival || "—"}</td>`;
        if (c === "departure") return `<td>${d.departure || "—"}</td>`;
        if (c === "hours") return `<td style="text-align:right">${_hoursCell(d)}${_typeIcon(d)}</td>`;
        return "<td></td>";
      }).join("");
      const editCell = editable
        ? `<td class="edit-cell" data-table="${id}" data-row="${i}" title="Edit">✏️</td>`
        : "";
      const rowClass = editable ? "clickable" : "";
      return `<tr class="${rowClass}" data-table="${id}" data-row="${i}">${cells}${editCell}</tr>`;
    }).join("");

    const colspan = columns.length + (editable ? 1 : 0);
    const footHtml = totals ? `
      <tfoot>
        <tr>
          <td colspan="${colspan}" class="foot">
            <span>Total: <b>${totals.hours.toFixed(2)}h</b></span>
            <span>Overtime: <b>${_sign(totals.overtime)}</b></span>
            <span>vs ${totals.target}h: <b>${_sign(totals.hours - totals.target)}</b></span>
          </td>
        </tr>
      </tfoot>` : "";

    return `
      <div class="block">
        ${title ? `<div class="block-title">${title}</div>` : ""}
        <table>
          <thead><tr>${head}${editable ? "<th></th>" : ""}</tr></thead>
          <tbody>${rowsHtml}</tbody>
          ${footHtml}
        </table>
      </div>`;
  }

  _render() {
    const hass = this._hass;
    if (!hass) return;

    const todayState = hass.states[ENTITY_TODAY];
    const weekState = hass.states[ENTITY_WEEK];
    const lastWeekState = hass.states[ENTITY_LAST_WEEK];
    const switchState = hass.states[ENTITY_SWITCH];

    if (!todayState) {
      this.shadowRoot.innerHTML = `
        <ha-card>
          <div style="padding:16px;color:var(--primary-text-color)">
            Integration not found — check that Worktime Tracker is installed.
          </div>
        </ha-card>`;
      return;
    }

    const attr = todayState.attributes || {};
    const weekAttr = weekState ? weekState.attributes || {} : {};
    const lastWeekAttr = lastWeekState ? lastWeekState.attributes || {} : {};
    const swOn = switchState ? switchState.state === "on" : false;

    const status = attr.status || "off_duty";
    const statusColor = STATUS_COLOR[status] || STATUS_COLOR.off_duty;
    const statusLabel = STATUS_LABEL[status] || status;

    const arrival = _fmt(attr.arrival);
    const plannedEnd = _fmt(attr.planned_end);
    const departure = _fmt(attr.departure);
    const lunch = attr.lunch || "";
    const hours = parseFloat(attr.hours) || 0;
    const overtime = parseFloat(attr.overtime) || 0;
    const timeRemaining = _fmt(attr.time_remaining);
    const dailyTarget = parseFloat(attr.daily_net_target) || 8.0;
    const pct = _progressPct(hours, dailyTarget);

    const weekHours = weekState ? parseFloat(weekState.state) || 0 : 0;
    const weekTarget = parseFloat(weekAttr.weekly_target) || 40;
    const weekOvertime = parseFloat(weekAttr.overtime) || 0;
    const weekDays = weekAttr.days || [];

    const lastWeekHours = lastWeekState ? parseFloat(lastWeekState.state) || 0 : 0;
    const lastWeekOvertime = parseFloat(lastWeekAttr.overtime) || 0;
    const lastWeekTarget = parseFloat(lastWeekAttr.weekly_target) || weekTarget;
    const lastWeekDays = lastWeekAttr.days || [];

    const lunchBadge = lunch === "yes"
      ? `<span class="badge lunch-yes">🍽 Lunch: yes</span>`
      : lunch === "no"
      ? `<span class="badge lunch-no">🍽 Lunch: no</span>`
      : `<span class="badge lunch-unknown">🍽 Lunch: ?</span>`;

    const limit = parseInt(this._cfg("recent_days_limit"), 10) || 7;
    const recent = (attr.recent_days || []).slice(0, limit);
    const editable = !!this._cfg("show_edit");

    const showHeader = !!this._cfg("show_header");
    const showTimes = !!this._cfg("show_times");
    const showProgress = !!this._cfg("show_progress");
    const showLunchLine = !!this._cfg("show_lunch_status");
    const showActions = !!this._cfg("show_actions");
    const showAutoDep = !!this._cfg("show_auto_departure");
    const showWeek = !!this._cfg("show_week");
    const showThisWeek = !!this._cfg("show_this_week");
    const showLastWeek = !!this._cfg("show_last_week");
    const showRecent = !!this._cfg("show_recent");

    const depDisplay = status === "done" ? departure : plannedEnd;

    const editing = this._editing;
    const modalHtml = editing ? this._renderModal(editing) : "";

    // Cache the day arrays so click handlers can look them up
    this._dayTables = {
      this_week: weekDays,
      last_week: lastWeekDays,
      recent: recent,
    };

    const thisWeekTable = showThisWeek ? this._renderDayTable({
      id: "this_week",
      title: "This week",
      days: weekDays,
      totals: { hours: weekHours, overtime: weekOvertime, target: weekTarget },
      columns: ["weekday", "arrival", "departure", "hours"],
      editable,
    }) : "";

    const lastWeekTable = showLastWeek ? this._renderDayTable({
      id: "last_week",
      title: "Last week",
      days: lastWeekDays,
      totals: { hours: lastWeekHours, overtime: lastWeekOvertime, target: lastWeekTarget },
      columns: ["weekday", "arrival", "departure", "hours"],
      editable,
    }) : "";

    const recentTable = showRecent ? this._renderDayTable({
      id: "recent",
      title: "Recent days",
      days: recent,
      totals: null,
      columns: ["date", "weekday", "hours"],
      editable,
    }) : "";

    const html = `
      <style>
        :host {
          --wt-radius: 12px;
          --wt-card-padding: 16px;
          --wt-status-color: ${statusColor};
          --wt-row-hover-bg: var(--primary-color, #03a9f4);
          --wt-row-hover-color: #fff;
          --wt-button-bg: var(--primary-color, #03a9f4);
          --wt-button-color: #fff;
          --wt-table-header-color: var(--secondary-text-color);
          --wt-divider-color: var(--divider-color, #e0e0e0);
        }
        ha-card {
          padding: var(--wt-card-padding);
          background: var(--card-background-color);
          color: var(--primary-text-color);
          font-family: var(--paper-font-body1_-_font-family, sans-serif);
        }
        .header {
          display: flex;
          align-items: center;
          justify-content: space-between;
          margin-bottom: 12px;
        }
        .title {
          font-size: 1.1em;
          font-weight: 600;
        }
        .badge {
          display: inline-block;
          padding: 3px 10px;
          border-radius: 20px;
          font-size: 0.82em;
          font-weight: 500;
        }
        .status-badge {
          background: var(--wt-status-color);
          color: #fff;
        }
        .lunch-yes { background: var(--success-color, #4caf50); color: #fff; }
        .lunch-no  { background: var(--error-color, #f44336); color: #fff; }
        .lunch-unknown { background: var(--disabled-color, #9e9e9e); color: #fff; }

        .time-row {
          display: flex;
          gap: 16px;
          flex-wrap: wrap;
          margin-bottom: 10px;
        }
        .time-item {
          display: flex;
          flex-direction: column;
          align-items: center;
        }
        .time-label {
          font-size: 0.72em;
          color: var(--secondary-text-color);
          text-transform: uppercase;
          letter-spacing: 0.05em;
        }
        .time-value {
          font-size: 1.3em;
          font-weight: 700;
        }
        .hours-big {
          font-size: 2em;
          font-weight: 800;
          color: var(--wt-status-color);
          margin: 4px 0;
        }
        .progress-wrap {
          background: var(--wt-divider-color);
          border-radius: 6px;
          height: 8px;
          overflow: hidden;
          margin: 8px 0 12px;
        }
        .progress-fill {
          height: 100%;
          background: var(--wt-status-color);
          width: ${pct}%;
          transition: width 0.4s ease;
          border-radius: 6px;
        }
        .buttons {
          display: flex;
          gap: 8px;
          flex-wrap: wrap;
          margin: 10px 0;
        }
        button {
          flex: 1 1 calc(50% - 8px);
          padding: 8px 4px;
          border: none;
          border-radius: var(--wt-radius);
          background: var(--wt-button-bg);
          color: var(--wt-button-color);
          font-size: 0.85em;
          font-weight: 600;
          cursor: pointer;
          min-width: 80px;
        }
        button:active { opacity: 0.8; }
        button.secondary {
          background: var(--secondary-background-color, #f5f5f5);
          color: var(--primary-text-color);
          border: 1px solid var(--wt-divider-color);
        }
        button.danger { background: var(--error-color, #f44336); }
        button.on { background: var(--success-color, #4caf50); }

        .divider {
          height: 1px;
          background: var(--wt-divider-color);
          margin: 12px 0;
        }
        .week-row {
          display: flex;
          justify-content: space-between;
          font-size: 0.9em;
          color: var(--secondary-text-color);
          margin-bottom: 8px;
        }
        .week-row span b { color: var(--primary-text-color); }

        .block { margin-top: 14px; }
        .block-title {
          font-size: 0.9em;
          font-weight: 600;
          margin-bottom: 4px;
          color: var(--primary-text-color);
        }
        .empty {
          font-size: 0.85em;
          color: var(--secondary-text-color);
          padding: 6px 0;
        }
        table {
          width: 100%;
          border-collapse: collapse;
          font-size: 0.82em;
        }
        thead th {
          color: var(--wt-table-header-color);
          text-align: left;
          font-weight: 500;
          padding: 4px 4px;
          border-bottom: 1px solid var(--wt-divider-color);
        }
        tbody td {
          padding: 4px 4px;
          color: var(--primary-text-color);
        }
        tbody tr:nth-child(even) td {
          background: var(--secondary-background-color, rgba(0,0,0,0.03));
        }
        tbody tr.clickable { cursor: pointer; }
        tbody tr.clickable:hover td {
          background: var(--wt-row-hover-bg);
          color: var(--wt-row-hover-color);
        }
        td.edit-cell {
          text-align: center;
          cursor: pointer;
          width: 1.6em;
          user-select: none;
        }
        td.edit-cell:hover { opacity: 0.7; }
        tfoot td.foot {
          padding-top: 6px;
          border-top: 1px solid var(--wt-divider-color);
          display: flex;
          justify-content: space-between;
          gap: 8px;
          font-size: 0.85em;
          color: var(--secondary-text-color);
        }
        tfoot td.foot b { color: var(--primary-text-color); }
        .remaining-label {
          font-size: 0.8em;
          color: var(--secondary-text-color);
        }

        /* Modal */
        .modal-backdrop {
          position: fixed;
          inset: 0;
          background: rgba(0,0,0,0.55);
          display: flex;
          align-items: center;
          justify-content: center;
          z-index: 999;
        }
        .modal {
          background: var(--card-background-color, #fff);
          color: var(--primary-text-color);
          border-radius: var(--wt-radius);
          padding: 20px;
          width: min(420px, 92vw);
          max-height: 90vh;
          overflow-y: auto;
          box-shadow: 0 8px 24px rgba(0,0,0,0.3);
        }
        .modal h3 { margin: 0 0 12px; font-size: 1.1em; }
        .modal .field {
          display: flex; flex-direction: column; gap: 4px; margin-bottom: 12px;
        }
        .modal .field label {
          font-size: 0.78em;
          color: var(--secondary-text-color);
          text-transform: uppercase;
          letter-spacing: 0.05em;
        }
        .modal input, .modal select {
          padding: 8px;
          font-size: 1em;
          border: 1px solid var(--wt-divider-color);
          border-radius: 6px;
          background: var(--card-background-color, #fff);
          color: var(--primary-text-color);
        }
        .modal .row-actions {
          display: flex; gap: 8px; justify-content: flex-end; margin-top: 8px;
        }
        .modal .row-actions button { flex: 0 0 auto; min-width: 90px; }
      </style>

      <ha-card>
        ${showHeader ? `
          <div class="header">
            <span class="title">Worktime Tracker</span>
            <span class="badge status-badge">${statusLabel}</span>
          </div>` : ""}

        ${showTimes ? `
          <div class="time-row">
            <div class="time-item">
              <span class="time-label">Arrival</span>
              <span class="time-value">${arrival}</span>
            </div>
            <div class="time-item">
              <span class="time-label">${status === "done" ? "Departed" : "Planned end"}</span>
              <span class="time-value">${depDisplay}</span>
            </div>
            <div class="time-item">
              <span class="time-label">Hours worked</span>
              <span class="hours-big">${_hoursHuman(hours)}</span>
            </div>
          </div>` : ""}

        ${showProgress ? `
          <div class="progress-wrap"><div class="progress-fill"></div></div>` : ""}

        ${showLunchLine ? `
          <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:8px">
            ${lunchBadge}
            <span class="remaining-label">
              ${status === "off_duty"
                ? "Not at work"
                : status === "done"
                ? `Overtime: ${_sign(overtime)}`
                : `Remaining: ${timeRemaining}`}
            </span>
          </div>` : ""}

        ${showActions ? `
          <div class="buttons">
            <button id="btn-arrival">✅ Log Arrival</button>
            <button id="btn-departure" class="secondary">🚪 Log Departure</button>
            <button id="btn-lunch-yes" class="secondary">🍽 Lunch ✓</button>
            <button id="btn-lunch-no" class="danger">🚫 No Lunch</button>
          </div>` : ""}

        ${showAutoDep ? `
          <div style="display:flex;gap:8px;margin-bottom:8px">
            <button id="btn-switch" class="${swOn ? "on" : "secondary"}" style="flex:1">
              ${swOn ? "🔔 Auto-depart: ON" : "🔕 Auto-depart: OFF"}
            </button>
            <button id="btn-reset" class="danger" style="flex:0 0 auto;min-width:60px">Reset</button>
          </div>` : ""}

        ${showWeek ? `
          <div class="divider"></div>
          <div class="week-row">
            <span>This week: <b>${weekHours.toFixed(2)}h</b></span>
            <span>Overtime: <b>${_sign(weekOvertime)}</b></span>
            <span>Target: <b>${weekTarget}h</b></span>
          </div>` : ""}

        ${thisWeekTable}
        ${lastWeekTable}
        ${recentTable}
      </ha-card>
      ${modalHtml}`;

    this.shadowRoot.innerHTML = html;
    this._wireEvents();
  }

  _renderModal(e) {
    const isLeave = e.type === "sick" || e.type === "off";
    return `
      <div class="modal-backdrop" id="modal-backdrop">
        <div class="modal" id="modal">
          <h3>Edit ${e.date}</h3>

          <div class="field">
            <label for="ed-type">Type</label>
            <select id="ed-type">
              <option value="normal" ${e.type === "normal" ? "selected" : ""}>Normal</option>
              <option value="sick" ${e.type === "sick" ? "selected" : ""}>Sick</option>
              <option value="off" ${e.type === "off" ? "selected" : ""}>Off / vacation</option>
            </select>
          </div>

          <div class="field" id="ed-field-arrival" style="${isLeave ? "display:none" : ""}">
            <label for="ed-arrival">Arrival</label>
            <input type="time" id="ed-arrival" value="${e.arrival}">
          </div>

          <div class="field" id="ed-field-departure" style="${isLeave ? "display:none" : ""}">
            <label for="ed-departure">Departure</label>
            <input type="time" id="ed-departure" value="${e.departure}">
          </div>

          <div class="field" id="ed-field-lunch" style="${isLeave ? "display:none" : ""}">
            <label for="ed-lunch">Lunch</label>
            <select id="ed-lunch">
              <option value="" ${!e.lunch ? "selected" : ""}>— (keep current)</option>
              <option value="yes" ${e.lunch === "yes" ? "selected" : ""}>Yes</option>
              <option value="no" ${e.lunch === "no" ? "selected" : ""}>No</option>
            </select>
          </div>

          <div class="field" id="ed-field-hours" style="${isLeave ? "" : "display:none"}">
            <label for="ed-hours">Hours (leave blank for default)</label>
            <input type="number" id="ed-hours" min="0" max="24" step="0.5" value="${e.hours}">
          </div>

          <div class="row-actions">
            <button id="ed-cancel" class="secondary">Cancel</button>
            <button id="ed-save">Save</button>
          </div>
        </div>
      </div>`;
  }

  _wireEvents() {
    const $ = (id) => this.shadowRoot.getElementById(id);

    $("btn-arrival")?.addEventListener("click", () => this._callService("log_arrival"));
    $("btn-departure")?.addEventListener("click", () => this._callService("log_departure"));
    $("btn-lunch-yes")?.addEventListener("click", () => this._callService("set_lunch", { had_lunch: true }));
    $("btn-lunch-no")?.addEventListener("click", () => this._callService("set_lunch", { had_lunch: false }));
    $("btn-switch")?.addEventListener("click", () => this._toggleSwitch());
    $("btn-reset")?.addEventListener("click", () => {
      if (confirm("Reset today's tracking?")) this._callService("reset_today");
    });

    // Row & edit-pencil clicks across all day tables
    this.shadowRoot.querySelectorAll("tr.clickable").forEach((row) => {
      row.addEventListener("click", (ev) => {
        // Edit pencil cell handles its own click; row-level fires for blank area too
        const tableId = row.getAttribute("data-table");
        const idx = parseInt(row.getAttribute("data-row"), 10);
        const day = (this._dayTables?.[tableId] || [])[idx];
        this._openEdit(day);
      });
    });
    this.shadowRoot.querySelectorAll("td.edit-cell").forEach((cell) => {
      cell.addEventListener("click", (ev) => {
        ev.stopPropagation();
        const tableId = cell.getAttribute("data-table");
        const idx = parseInt(cell.getAttribute("data-row"), 10);
        const day = (this._dayTables?.[tableId] || [])[idx];
        this._openEdit(day);
      });
    });

    if (this._editing) {
      $("ed-cancel")?.addEventListener("click", () => this._closeEdit());
      $("modal-backdrop")?.addEventListener("click", (ev) => {
        if (ev.target.id === "modal-backdrop") this._closeEdit();
      });
      $("ed-save")?.addEventListener("click", () => {
        const e = this._editing;
        e.type = $("ed-type").value;
        e.arrival = $("ed-arrival")?.value || "";
        e.departure = $("ed-departure")?.value || "";
        e.lunch = $("ed-lunch")?.value || "";
        e.hours = $("ed-hours")?.value || "";
        this._saveEdit();
      });
      $("ed-type")?.addEventListener("change", (ev) => {
        const isLeave = ev.target.value !== "normal";
        $("ed-field-arrival").style.display = isLeave ? "none" : "";
        $("ed-field-departure").style.display = isLeave ? "none" : "";
        $("ed-field-lunch").style.display = isLeave ? "none" : "";
        $("ed-field-hours").style.display = isLeave ? "" : "none";
      });
    }
  }

  static getStubConfig() { return {}; }
  static getConfigElement() {
    return document.createElement("worktime-tracker-card-editor");
  }
}

/* -----------------------------------------------------------------
   Visual editor — checkboxes for every show_* + recent_days_limit
   ----------------------------------------------------------------- */
class WorktimeTrackerCardEditor extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._config = {};
  }

  setConfig(config) {
    this._config = { ...config };
    this._render();
  }

  set hass(hass) { this._hass = hass; }

  _emit() {
    this.dispatchEvent(new CustomEvent("config-changed", {
      detail: { config: this._config },
      bubbles: true,
      composed: true,
    }));
  }

  _get(key) {
    if (key in this._config) return this._config[key];
    return DEFAULTS[key];
  }

  _render() {
    const sectionRows = SECTIONS.map(([key, label]) => `
      <label class="row">
        <input type="checkbox" data-key="${key}" ${this._get(key) ? "checked" : ""}>
        <span>${label}</span>
      </label>`).join("");

    this.shadowRoot.innerHTML = `
      <style>
        :host { display: block; padding: 8px 0; color: var(--primary-text-color); }
        .group { margin-bottom: 14px; }
        .group-title {
          font-size: 0.85em; font-weight: 600;
          color: var(--secondary-text-color);
          text-transform: uppercase;
          letter-spacing: 0.05em;
          margin-bottom: 6px;
        }
        .row {
          display: flex; align-items: center; gap: 10px;
          padding: 4px 0;
          cursor: pointer;
        }
        .row input { transform: scale(1.1); }
        .num-row {
          display: flex; align-items: center; gap: 10px;
          padding: 4px 0;
        }
        input[type="number"] {
          padding: 6px 8px;
          border: 1px solid var(--divider-color, #ccc);
          border-radius: 6px;
          background: var(--card-background-color, #fff);
          color: var(--primary-text-color);
          width: 80px;
        }
        .hint {
          font-size: 0.8em;
          color: var(--secondary-text-color);
          margin-top: 8px;
        }
      </style>
      <div class="group">
        <div class="group-title">Sections</div>
        ${sectionRows}
      </div>
      <div class="group">
        <div class="group-title">Recent days table</div>
        <div class="num-row">
          <label for="ed-limit">Rows:</label>
          <input id="ed-limit" type="number" min="1" max="60"
                 value="${this._get("recent_days_limit")}">
        </div>
      </div>
      <div class="hint">
        Styling: override CSS variables under <code>:host</code> with
        card_mod or your theme — <code>--wt-card-padding</code>,
        <code>--wt-radius</code>, <code>--wt-status-color</code>,
        <code>--wt-row-hover-bg</code>, etc.
      </div>`;

    this.shadowRoot.querySelectorAll("input[type=checkbox]").forEach((cb) => {
      cb.addEventListener("change", () => {
        const key = cb.getAttribute("data-key");
        this._config = { ...this._config, [key]: cb.checked };
        this._emit();
      });
    });
    this.shadowRoot.getElementById("ed-limit")?.addEventListener("input", (ev) => {
      const n = parseInt(ev.target.value, 10);
      if (!isNaN(n) && n > 0) {
        this._config = { ...this._config, recent_days_limit: n };
        this._emit();
      }
    });
  }
}

customElements.define("worktime-tracker-card-editor", WorktimeTrackerCardEditor);
customElements.define("worktime-tracker-card", WorktimeTrackerCard);

window.customCards = window.customCards || [];
window.customCards.push({
  type: "worktime-tracker-card",
  name: "Worktime Tracker",
  description: "Daily work time tracker with arrival, departure, lunch and weekly overview.",
  preview: false,
  documentationURL: "https://github.com/ottoherdy/worktime-tracker",
});
