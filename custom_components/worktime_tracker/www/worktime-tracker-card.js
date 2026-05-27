/**
 * Worktime Tracker Lovelace Card
 * Vanilla Web Component — no build step, no external dependencies.
 * Auto-loaded via frontend.add_extra_js_url in __init__.py
 *
 * Config options (all optional, all default to true unless noted):
 *   show_header: bool          - card title + status badge
 *   show_times: bool           - arrival / planned / hours big row
 *   show_progress: bool        - progress bar
 *   show_lunch_status: bool    - lunch badge + remaining/overtime line
 *   show_actions: bool         - log arrival/departure/lunch buttons
 *   show_auto_departure: bool  - auto-departure toggle + reset
 *   show_week: bool            - week summary line
 *   show_recent: bool          - recent days table
 *   show_edit: bool            - tap a row in recent days to edit
 *   recent_days_limit: number  - rows in recent days table (default 7)
 */

const ENTITY_TODAY = "sensor.today_hours_today";
const ENTITY_WEEK = "sensor.this_week_hours_this_week";
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
  // Recent_days arrival/departure are "HH:MM" or "—" — return "" for blank.
  if (!val || val === "—") return "";
  return val;
}

class WorktimeTrackerCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._hass = null;
    this._intervalId = null;
    this._editing = null; // {date, arrival, departure, lunch, type, hours} or null
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
    return 5;
  }

  _cfg(key, fallback = true) {
    if (!this._config || !(key in this._config)) return fallback;
    return this._config[key];
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

  _render() {
    const hass = this._hass;
    if (!hass) return;

    const todayState = hass.states[ENTITY_TODAY];
    const weekState = hass.states[ENTITY_WEEK];
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

    const lunchBadge = lunch === "yes"
      ? `<span class="badge lunch-yes">🍽 Lunch: yes</span>`
      : lunch === "no"
      ? `<span class="badge lunch-no">🍽 Lunch: no</span>`
      : `<span class="badge lunch-unknown">🍽 Lunch: ?</span>`;

    const limit = parseInt(this._cfg("recent_days_limit", 7), 10) || 7;
    const recent = (attr.recent_days || []).slice(0, limit);
    const editable = this._cfg("show_edit", true);
    const recentRows = recent.map((d, i) => {
      const isSick = d.type === "sick";
      const isOff = d.type === "off";
      const missingPunch = d.punch_out_missing;
      const typeIcon = isSick ? " 🤒" : isOff ? " 🌴" : missingPunch ? " ⚠" : "";
      const hoursCell = isSick ? "sick" : isOff ? "off" : (d.human_readable || "—");
      return `
        <tr data-row="${i}" class="${editable ? "clickable" : ""}">
          <td>${d.date || "—"}</td>
          <td>${d.weekday || "—"}</td>
          <td style="text-align:right">${hoursCell}${typeIcon}</td>
        </tr>`;
    }).join("");

    // Departure display — show actual departure if done, else planned end
    const depDisplay = status === "done" ? departure : plannedEnd;

    // Section visibility flags
    const showHeader = this._cfg("show_header");
    const showTimes = this._cfg("show_times");
    const showProgress = this._cfg("show_progress");
    const showLunchLine = this._cfg("show_lunch_status");
    const showActions = this._cfg("show_actions");
    const showAutoDep = this._cfg("show_auto_departure");
    const showWeek = this._cfg("show_week");
    const showRecent = this._cfg("show_recent");

    // Modal (only rendered when editing)
    const editing = this._editing;
    const modalHtml = editing ? this._renderModal(editing) : "";

    const html = `
      <style>
        :host {
          --wt-radius: 12px;
          --wt-gap: 12px;
        }
        ha-card {
          padding: 16px;
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
          color: var(--primary-text-color);
        }
        .badge {
          display: inline-block;
          padding: 3px 10px;
          border-radius: 20px;
          font-size: 0.82em;
          font-weight: 500;
        }
        .status-badge {
          background: ${statusColor};
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
          color: var(--primary-text-color);
        }
        .hours-big {
          font-size: 2em;
          font-weight: 800;
          color: ${statusColor};
          margin: 4px 0;
        }
        .progress-wrap {
          background: var(--divider-color, #e0e0e0);
          border-radius: 6px;
          height: 8px;
          overflow: hidden;
          margin: 8px 0 12px;
        }
        .progress-fill {
          height: 100%;
          background: ${statusColor};
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
          background: var(--primary-color, #03a9f4);
          color: #fff;
          font-size: 0.85em;
          font-weight: 600;
          cursor: pointer;
          min-width: 80px;
        }
        button:active { opacity: 0.8; }
        button.secondary {
          background: var(--secondary-background-color, #f5f5f5);
          color: var(--primary-text-color);
          border: 1px solid var(--divider-color, #e0e0e0);
        }
        button.danger {
          background: var(--error-color, #f44336);
        }
        button.on {
          background: var(--success-color, #4caf50);
        }
        .divider {
          height: 1px;
          background: var(--divider-color, #e0e0e0);
          margin: 12px 0;
        }
        .week-row {
          display: flex;
          justify-content: space-between;
          font-size: 0.9em;
          color: var(--secondary-text-color);
          margin-bottom: 8px;
        }
        .week-row span b {
          color: var(--primary-text-color);
        }
        table {
          width: 100%;
          border-collapse: collapse;
          font-size: 0.82em;
          margin-top: 6px;
        }
        thead th {
          color: var(--secondary-text-color);
          text-align: left;
          font-weight: 500;
          padding: 2px 4px;
          border-bottom: 1px solid var(--divider-color, #e0e0e0);
        }
        tbody td {
          padding: 3px 4px;
          color: var(--primary-text-color);
        }
        tbody tr:nth-child(even) td {
          background: var(--secondary-background-color, rgba(0,0,0,0.03));
        }
        tbody tr.clickable { cursor: pointer; }
        tbody tr.clickable:hover td {
          background: var(--primary-color, #03a9f4);
          color: #fff;
        }
        .remaining-label {
          font-size: 0.8em;
          color: var(--secondary-text-color);
          margin-top: 2px;
        }

        /* Edit modal */
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
        .modal h3 {
          margin: 0 0 12px;
          font-size: 1.1em;
        }
        .modal .field {
          display: flex;
          flex-direction: column;
          gap: 4px;
          margin-bottom: 12px;
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
          border: 1px solid var(--divider-color, #ccc);
          border-radius: 6px;
          background: var(--card-background-color, #fff);
          color: var(--primary-text-color);
        }
        .modal .row-actions {
          display: flex;
          gap: 8px;
          justify-content: flex-end;
          margin-top: 8px;
        }
        .modal .row-actions button {
          flex: 0 0 auto;
          min-width: 90px;
        }
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
          <div class="progress-wrap">
            <div class="progress-fill"></div>
          </div>` : ""}

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

        ${(showActions || showAutoDep) && (showWeek || showRecent) ? `<div class="divider"></div>` : ""}

        ${showWeek ? `
          <div class="week-row">
            <span>This week: <b>${weekHours.toFixed(2)}h</b></span>
            <span>Overtime: <b>${_sign(weekOvertime)}</b></span>
            <span>Target: <b>${weekTarget}h</b></span>
          </div>` : ""}

        ${showWeek && showRecent ? `<div class="divider"></div>` : ""}

        ${showRecent ? `
          <table>
            <thead>
              <tr>
                <th>Date</th>
                <th>Day</th>
                <th style="text-align:right">Hours</th>
              </tr>
            </thead>
            <tbody id="recent-tbody">
              ${recentRows || '<tr><td colspan="3" style="text-align:center;color:var(--secondary-text-color)">No history yet</td></tr>'}
            </tbody>
          </table>` : ""}
      </ha-card>
      ${modalHtml}`;

    this.shadowRoot.innerHTML = html;
    this._wireEvents(recent, editable);
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

  _wireEvents(recent, editable) {
    const $ = (id) => this.shadowRoot.getElementById(id);

    $("btn-arrival")?.addEventListener("click", () => this._callService("log_arrival"));
    $("btn-departure")?.addEventListener("click", () => this._callService("log_departure"));
    $("btn-lunch-yes")?.addEventListener("click", () => this._callService("set_lunch", { had_lunch: true }));
    $("btn-lunch-no")?.addEventListener("click", () => this._callService("set_lunch", { had_lunch: false }));
    $("btn-switch")?.addEventListener("click", () => this._toggleSwitch());
    $("btn-reset")?.addEventListener("click", () => {
      if (confirm("Reset today's tracking?")) this._callService("reset_today");
    });

    if (editable) {
      this.shadowRoot.querySelectorAll("tr[data-row]").forEach((row) => {
        row.addEventListener("click", () => {
          const idx = parseInt(row.getAttribute("data-row"), 10);
          const day = recent[idx];
          if (day) this._openEdit(day);
        });
      });
    }

    // Modal wiring
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

  static getStubConfig() {
    return {};
  }

  static getConfigElement() {
    return null;
  }
}

customElements.define("worktime-tracker-card", WorktimeTrackerCard);

window.customCards = window.customCards || [];
window.customCards.push({
  type: "worktime-tracker-card",
  name: "Worktime Tracker",
  description: "Daily work time tracker with arrival, departure, lunch and weekly overview.",
  preview: false,
  documentationURL: "https://github.com/ottoherdy/worktime-tracker",
});
