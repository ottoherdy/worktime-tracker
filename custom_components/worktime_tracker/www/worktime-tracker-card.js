/**
 * Worktime Tracker Lovelace Card — v2.4.3
 * Vanilla Web Component, no build step. Auto-loaded via add_extra_js_url.
 *
 * Config (all optional, defaults shown):
 *   show_topbar: true        // centered date
 *   show_today: true         // Today card with elapsed time and actions
 *   show_this_week: true     // This week list with totals
 *   show_last_week: true     // Last week list
 *   show_this_month: false   // This month summary
 *   show_last_month: false   // Last month summary
 *   show_history: true       // History compact list
 *   show_footer: true        // "Saved locally" + Export/Sheets links
 *   show_edit: true          // edit pencil + row-tap → modal
 *   history_limit: 10        // rows in history
 *   padding: 14              // outer padding in px
 *   max_width: 420           // max card width in px (0 = fluid / fill container)
 *   entity_prefix: ""        // for multi-instance, e.g. "home"; reads
 *                            // sensor.home_today_hours_today instead
 *                            // of sensor.today_hours_today
 *
 * Styling: every visual token is a CSS variable on :host. Override via
 * card_mod or a theme. See README.md for the full list.
 */

const DOMAIN = "worktime_tracker";

function _entities(prefix) {
  const p = prefix ? `${prefix}_` : "";
  return {
    today: `sensor.${p}today_hours_today`,
    week: `sensor.${p}this_week_hours_this_week`,
    last_week: `sensor.${p}last_week_hours_last_week`,
    this_month: `sensor.${p}this_month_hours_this_month`,
    last_month: `sensor.${p}last_month_hours_last_month`,
    sw: `switch.${p}today_auto_departure`,
  };
}

const DEFAULTS = {
  show_topbar: false,
  show_today: true,
  show_this_week: true,
  show_last_week: true,
  show_this_month: false,
  show_last_month: false,
  show_history: true,
  show_footer: true,
  show_edit: true,
  history_limit: 10,
  padding: 14,
  max_width: 420,
  entity_prefix: "",
};

const SECTIONS = [
  ["show_topbar", "Topbar (date)"],
  ["show_today", "Today card"],
  ["show_this_week", "This week list"],
  ["show_last_week", "Last week list"],
  ["show_this_month", "This month summary"],
  ["show_last_month", "Last month summary"],
  ["show_history", "History list"],
  ["show_footer", "Footer (Export / Sheets)"],
  ["show_edit", "Inline edit (pencil + row-tap)"],
];

const ICON = {
  briefcase: `<svg viewBox="0 0 24 24"><rect x="3" y="7" width="18" height="13" rx="2"/><path d="M8 7V5a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>`,
  reset: `<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><path d="M3 12a9 9 0 1 0 3-6.7"/><path d="M3 4v5h5"/></svg>`,
  arrowRight: `<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h13M13 7l5 5-5 5"/></svg>`,
  arrowLeft: `<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><path d="M19 12H6M11 7l-5 5 5 5"/></svg>`,
  lunch: `<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><path d="M7 2v8a3 3 0 1 0 6 0V2"/><path d="M10 14v8"/><path d="M17 2c2 4 2 8 0 12v8"/></svg>`,
  clock: `<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></svg>`,
  pencil: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" width="13" height="13"><path d="M14.7 4.3l4.9 4.9L8.6 20.3 3.7 21l.7-4.9z"/></svg>`,
};

function _todayIso() {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

function _formatTopbarDate() {
  return new Intl.DateTimeFormat(undefined, {
    weekday: "short", month: "short", day: "numeric",
  }).format(new Date()).replace(",", " ·");
}

function _hoursToHM(hours) {
  if (hours == null || isNaN(parseFloat(hours))) return { h: 0, m: 0 };
  const total = Math.max(0, Math.round(parseFloat(hours) * 60));
  return { h: Math.floor(total / 60), m: total % 60 };
}

function _fmtHM(hours) {
  const { h, m } = _hoursToHM(hours);
  return `${h}h ${String(m).padStart(2, "0")}m`;
}

function _fmtDeltaHours(diff) {
  if (diff == null || isNaN(parseFloat(diff))) return "0.00h";
  const d = parseFloat(diff);
  const sign = d >= 0 ? "+" : "−";
  return `${sign}${Math.abs(d).toFixed(2)}h`;
}

function _isoToMMDD(iso) {
  if (!iso) return "";
  const parts = iso.split("-");
  if (parts.length !== 3) return iso;
  return `${parts[1]}-${parts[2]}`;
}

function _miniBarPct(hours, target = 8) {
  const h = parseFloat(hours) || 0;
  if (h <= 0) return 0;
  const max = target * 1.5;
  return Math.min(100, Math.round((h / max) * 100));
}

function _timeForInput(val) {
  if (!val || val === "—") return "";
  return val;
}

function _lunchLabel(status) {
  if (status === "yes") return "yes";
  if (status === "no") return "no";
  return "—";
}

class WorktimeTrackerCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._hass = null;
    this._tick = null;
    this._editing = null;
  }

  set hass(hass) {
    this._hass = hass;
    this._render();
  }

  connectedCallback() {
    this._tick = setInterval(() => this._render(), 1000);
  }

  disconnectedCallback() {
    if (this._tick) { clearInterval(this._tick); this._tick = null; }
  }

  setConfig(config) {
    this._config = config || {};
  }

  getCardSize() { return 8; }

  _cfg(key) {
    if (this._config && key in this._config) return this._config[key];
    return DEFAULTS[key];
  }

  _entityIds() {
    return _entities(this._cfg("entity_prefix") || "");
  }

  _callService(service, data = {}) {
    if (!this._hass) return;
    const prefix = this._cfg("entity_prefix") || "";
    const payload = { ...data };
    if (prefix) payload.entry_prefix = prefix;
    this._hass.callService(DOMAIN, service, payload);
  }

  _toggleSwitch() {
    if (!this._hass) return;
    const ids = this._entityIds();
    const swState = this._hass.states[ids.sw];
    if (!swState) return;
    const svc = swState.state === "on" ? "turn_off" : "turn_on";
    this._hass.callService("switch", svc, { entity_id: ids.sw });
  }

  _openEdit(day) {
    if (!day) return;
    this._editing = {
      date: day.date,
      arrival: _timeForInput(day.arrival),
      departure: _timeForInput(day.departure),
      lunch: day.lunch && day.lunch !== "—" ? day.lunch : "",
      type: day.type === "none" ? "normal" : (day.type || "normal"),
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
    // While the edit modal is open, skip re-renders so the open time
    // picker, focused input, and partially-typed values survive the
    // 1s tick and incoming hass state updates. _closeEdit/_saveEdit
    // clear this._editing and call _render() to resume normal updates.
    if (this._editing && this.shadowRoot.getElementById("modal-backdrop")) return;

    const ids = this._entityIds();
    const todayState = hass.states[ids.today];
    const weekState = hass.states[ids.week];
    const lastWeekState = hass.states[ids.last_week];
    const monthState = hass.states[ids.this_month];
    const lastMonthState = hass.states[ids.last_month];
    const switchState = hass.states[ids.sw];

    if (!todayState) {
      this.shadowRoot.innerHTML = `
        <ha-card>
          <div style="padding:16px;color:var(--primary-text-color)">
            Worktime Tracker entities not found
            ${this._cfg("entity_prefix") ? `for prefix "${this._cfg("entity_prefix")}"` : ""}.
            Check Settings → Devices & Services → Worktime Tracker.
          </div>
        </ha-card>`;
      return;
    }

    const attr = todayState.attributes || {};
    const weekAttr = weekState ? weekState.attributes || {} : {};
    const lastWeekAttr = lastWeekState ? lastWeekState.attributes || {} : {};
    const monthAttr = monthState ? monthState.attributes || {} : {};
    const lastMonthAttr = lastMonthState ? lastMonthState.attributes || {} : {};

    const status = attr.status || "off_duty";
    const onClock = status === "at_work" || status === "overtime";
    const done = status === "done";

    const hours = parseFloat(attr.hours) || 0;
    const target = parseFloat(attr.daily_net_target) || 8.0;
    const overTarget = hours > target;
    const overAmount = hours - target;

    const { h: elapsedH, m: elapsedM } = _hoursToHM(hours);
    const progressPct = Math.min(100, (hours / target) * 100);

    const arrival = attr.arrival || "—";
    const departure = attr.departure || (onClock ? (attr.planned_end || "—") : "—");
    const lunchStatus = attr.lunch || "unknown";
    const lunchOn = lunchStatus === "yes" || (lunchStatus === "unknown" && !!attr.auto_lunch_default);

    const autoOn = switchState && switchState.state === "on";
    const autoOutTimeRaw = attr.auto_departure_time || "15:00";
    const autoOutTime = autoOutTimeRaw.slice(0, 5);

    const weekHours = weekState ? parseFloat(weekState.state) || 0 : 0;
    const weekOvertime = parseFloat(weekAttr.overtime) || 0;
    const weekTarget = parseFloat(weekAttr.weekly_target) || 40;
    const weekDays = weekAttr.days || [];
    const weekFilled = weekDays.filter((d) => d && d.type !== "none" && parseFloat(d.hours) > 0);
    const weekAvgH = weekFilled.length ? weekHours / weekFilled.length : 0;

    const lastWeekHours = lastWeekState ? parseFloat(lastWeekState.state) || 0 : 0;
    const lastWeekOvertime = parseFloat(lastWeekAttr.overtime) || 0;
    const lastWeekDays = lastWeekAttr.days || [];
    const lastWeekFilled = lastWeekDays.filter((d) => d && d.type !== "none" && parseFloat(d.hours) > 0);
    const lastWeekAvgH = lastWeekFilled.length ? lastWeekHours / lastWeekFilled.length : 0;

    const monthHours = monthState ? parseFloat(monthState.state) || 0 : 0;
    const monthOvertime = parseFloat(monthAttr.overtime) || 0;
    const monthLabel = monthAttr.month || "This month";

    const lastMonthHours = lastMonthState ? parseFloat(lastMonthState.state) || 0 : 0;
    const lastMonthOvertime = parseFloat(lastMonthAttr.overtime) || 0;
    const lastMonthLabel = lastMonthAttr.month || "Last month";

    const historyLimit = parseInt(this._cfg("history_limit"), 10) || 10;
    const history = (attr.recent_days || []).slice(0, historyLimit);
    const historyAvgHours = history.length
      ? history.reduce((s, d) => s + (parseFloat(d.hours) || 0), 0) / history.length
      : 0;

    const editable = !!this._cfg("show_edit");
    const showTopbar = !!this._cfg("show_topbar");
    const showToday = !!this._cfg("show_today");
    const showThisWeek = !!this._cfg("show_this_week");
    const showLastWeek = !!this._cfg("show_last_week");
    const showThisMonth = !!this._cfg("show_this_month");
    const showLastMonth = !!this._cfg("show_last_month");
    const showHistory = !!this._cfg("show_history");
    const showFooter = !!this._cfg("show_footer");

    const padding = parseInt(this._cfg("padding"), 10) || 14;
    const maxWidthRaw = parseInt(this._cfg("max_width"), 10);
    const maxWidthCss = !isNaN(maxWidthRaw) && maxWidthRaw > 0 ? `${maxWidthRaw}px` : "none";

    this._dayTables = {
      this_week: weekDays,
      last_week: lastWeekDays,
      history: history,
    };

    const elapsedHtml = `
      <span>${elapsedH}</span><span class="unit">h</span>
      <span>${String(elapsedM).padStart(2, "0")}</span><span class="unit">m</span>`;

    const pillHtml = onClock
      ? `<span class="pill on-clock"><span class="pulse"></span> On the clock</span>`
      : done
      ? `<span class="pill done">Done</span>`
      : `<span class="pill off">Off duty</span>`;

    const subOverHtml = hours > 0
      ? (overTarget
          ? `<span class="dot"></span><span class="delta over">+${_fmtHM(overAmount)} over</span>`
          : `<span class="dot"></span><span class="delta under">−${_fmtHM(target - hours)} to go</span>`)
      : "";

    const weekListHtml = this._renderWeekList(weekDays, target);
    const lastWeekListHtml = this._renderWeekList(lastWeekDays, target);
    const historyListHtml = this._renderHistoryList(history, target);

    const modalHtml = this._editing ? this._renderModal(this._editing) : "";

    this.shadowRoot.innerHTML = `
      <style>${this._styles(padding)}</style>
      <ha-card>
        <div class="app" style="--wt-pad:${padding}px;--wt-maxw:${maxWidthCss}">
          ${showTopbar ? `
            <header class="topbar">
              <span class="mono date">${_formatTopbarDate()}</span>
            </header>` : ""}

          ${showToday ? `
            <section class="today">
              <div class="today-head">
                <div class="left">
                  <span class="badge-icon">${ICON.briefcase}</span>
                  Today
                </div>
                <div class="right">${pillHtml}</div>
              </div>

              <div class="elapsed mono">${elapsedHtml}</div>
              <div class="elapsed-sub">
                <span>Target <span class="mono">${_fmtHM(target)}</span></span>
                ${subOverHtml}
              </div>

              <div class="track">
                <div class="fill ${overTarget ? "over" : ""}" style="width:${progressPct}%"></div>
                <div class="mark" style="left:100%"></div>
              </div>

              <div class="io">
                <div>
                  <div class="io-label">Arrival</div>
                  <div class="io-value mono ${arrival === "—" ? "dim" : ""}">${arrival}</div>
                </div>
                <div>
                  <div class="io-label">${done ? "Departed" : "Departure"}</div>
                  <div class="io-value mono ${departure === "—" ? "dim" : ""}">${departure}</div>
                </div>
                <div>
                  <div class="io-label">Lunch</div>
                  <div class="io-value mono ${lunchStatus === "yes" || lunchStatus === "no" ? "" : "dim"}">${_lunchLabel(lunchStatus)}</div>
                </div>
              </div>

              <div class="actions actions-3">
                <button class="btn" id="btn-arrival">
                  ${ICON.arrowRight}
                  Arrival
                </button>
                <button class="btn" id="btn-reset" title="Reset today">
                  ${ICON.reset}
                  Reset
                </button>
                <button class="btn" id="btn-departure">
                  ${ICON.arrowLeft}
                  Departure
                </button>
              </div>
              <div class="actions-grid">
                <button class="btn toggle" id="btn-lunch" aria-pressed="${lunchOn}">
                  ${ICON.lunch}
                  Lunch<span class="meta">${lunchOn ? "yes" : "no"}</span>
                </button>
                <button class="btn toggle" id="btn-auto" aria-pressed="${autoOn}">
                  ${ICON.clock}
                  Auto-out<span class="meta">${autoOutTime}</span>
                </button>
              </div>
            </section>` : ""}

          ${showThisWeek ? `
            <section class="section">
              <div class="section-head">
                <div class="section-title">This week</div>
              </div>
              <div class="list">
                ${weekListHtml}
                <div class="totals">
                  <span>${weekFilled.length} ${weekFilled.length === 1 ? "day" : "days"} · avg <b class="mono">${_fmtHM(weekAvgH)}</b></span>
                </div>
              </div>
            </section>` : ""}

          ${showLastWeek ? `
            <section class="section">
              <div class="section-head">
                <div class="section-title">Last week</div>
              </div>
              <div class="list">
                ${lastWeekListHtml}
                <div class="totals">
                  <span>${lastWeekFilled.length} ${lastWeekFilled.length === 1 ? "day" : "days"} · avg <b class="mono">${_fmtHM(lastWeekAvgH)}</b></span>
                </div>
              </div>
            </section>` : ""}

          ${showThisMonth ? this._renderMonthBlock("This month", monthLabel, monthHours, monthOvertime) : ""}
          ${showLastMonth ? this._renderMonthBlock("Last month", lastMonthLabel, lastMonthHours, lastMonthOvertime) : ""}

          ${showHistory ? `
            <section class="section">
              <div class="section-head">
                <div class="section-title">History</div>
              </div>
              <div class="list">${historyListHtml}</div>
            </section>` : ""}

          ${showFooter ? `
            <footer class="foot">
              <span>Saved locally</span>
              <span class="foot-links">
                <a href="#" id="link-export">Export</a>
                <a href="#" id="link-sheets">Sheets</a>
              </span>
            </footer>` : ""}
        </div>
      </ha-card>
      ${modalHtml}`;

    this._wireEvents();
  }

  _renderMonthBlock(label, monthName, hours, overtime) {
    return `
      <section class="section">
        <div class="section-head">
          <div class="section-title">${label}<span class="title-meta mono">${monthName}</span></div>
        </div>
        <div class="month-card">
          <div class="month-row">
            <span class="month-k">Hours</span>
            <span class="month-v mono">${hours.toFixed(2)}h</span>
          </div>
          <div class="month-row">
            <span class="month-k">Overtime</span>
            <span class="month-v mono ${overtime >= 0 ? "pos" : "neg"}">${_fmtDeltaHours(overtime)}</span>
          </div>
        </div>
      </section>`;
  }

  _renderWeekList(days, target) {
    if (!days || days.length === 0) return `<div class="row empty"><div class="day">—</div><div class="times">No data</div><div class="hours">—</div><div></div></div>`;
    const todayIso = _todayIso();
    const editable = !!this._cfg("show_edit");
    return days.map((d, i) => {
      const empty = d.type === "none" || (d.arrival === "—" && d.hours === 0);
      const isToday = d.date === todayIso;
      const hoursNum = parseFloat(d.hours) || 0;
      const overClass = hoursNum > target ? "over" : "under";
      const rowClasses = ["row"];
      if (empty) rowClasses.push("empty");
      if (isToday) rowClasses.push("today");
      const timesHtml = empty
        ? `—`
        : `${d.arrival || "—"}<span class="sep">→</span>${d.departure || "—"}`;
      const hoursHtml = empty ? "—" : (d.type === "sick" ? "sick" : d.type === "off" ? "off" : _fmtHM(hoursNum));
      const editCell = editable
        ? `<div class="edit" data-row="${i}" title="Edit">${ICON.pencil}</div>`
        : `<div></div>`;
      return `
        <div class="${rowClasses.join(" ")}" data-row="${i}">
          <div class="day">${d.weekday || "—"}<span class="date">${_isoToMMDD(d.date)}</span></div>
          <div class="times">${timesHtml}</div>
          <div class="hours ${overClass}">${hoursHtml}</div>
          ${editCell}
        </div>`;
    }).join("");
  }

  _renderHistoryList(days, target) {
    if (!days || days.length === 0) return `<div class="history-row"><div class="date">—</div><div class="day">—</div><div class="mini"></div><div class="hours">—</div></div>`;
    const editable = !!this._cfg("show_edit");
    return days.map((d, i) => {
      const hoursNum = parseFloat(d.hours) || 0;
      const pct = _miniBarPct(hoursNum, target);
      const overTarget = hoursNum > target;
      const editClass = editable ? "editable" : "";
      return `
        <div class="history-row ${editClass}" data-row="${i}">
          <div class="date">${d.date || "—"}</div>
          <div class="day">${d.weekday || "—"}</div>
          <div class="mini"><span class="${overTarget ? "over" : ""}" style="width:${pct}%"></span></div>
          <div class="hours">${d.type === "sick" ? "sick" : d.type === "off" ? "off" : _fmtHM(hoursNum)}</div>
        </div>`;
    }).join("");
  }

  _renderModal(e) {
    const isLeave = e.type === "sick" || e.type === "off";
    return `
      <div class="modal-backdrop" id="modal-backdrop">
        <div class="modal">
          <h3>Edit ${e.date}</h3>

          <div class="field">
            <label>Type</label>
            <select id="ed-type">
              <option value="normal" ${e.type === "normal" ? "selected" : ""}>Normal</option>
              <option value="sick" ${e.type === "sick" ? "selected" : ""}>Sick</option>
              <option value="off" ${e.type === "off" ? "selected" : ""}>Off / vacation</option>
            </select>
          </div>

          <div class="field" id="ed-field-arrival" style="${isLeave ? "display:none" : ""}">
            <label>Arrival</label>
            <input type="time" id="ed-arrival" value="${e.arrival}">
          </div>

          <div class="field" id="ed-field-departure" style="${isLeave ? "display:none" : ""}">
            <label>Departure</label>
            <input type="time" id="ed-departure" value="${e.departure}">
          </div>

          <div class="field" id="ed-field-lunch" style="${isLeave ? "display:none" : ""}">
            <label>Lunch</label>
            <select id="ed-lunch">
              <option value="" ${!e.lunch ? "selected" : ""}>— (keep current)</option>
              <option value="yes" ${e.lunch === "yes" ? "selected" : ""}>Yes</option>
              <option value="no" ${e.lunch === "no" ? "selected" : ""}>No</option>
            </select>
          </div>

          <div class="field" id="ed-field-hours" style="${isLeave ? "" : "display:none"}">
            <label>Hours (blank = default)</label>
            <input type="number" id="ed-hours" min="0" max="24" step="0.5" value="${e.hours}">
          </div>

          <div class="row-actions">
            <button class="btn" id="ed-cancel">Cancel</button>
            <button class="btn primary" id="ed-save">Save</button>
          </div>
        </div>
      </div>`;
  }

  _wireEvents() {
    const $ = (id) => this.shadowRoot.getElementById(id);

    $("btn-arrival")?.addEventListener("click", () => this._callService("log_arrival"));
    $("btn-departure")?.addEventListener("click", () => this._callService("log_departure"));
    $("btn-reset")?.addEventListener("click", () => {
      if (confirm("Reset today's tracking?")) this._callService("reset_today");
    });
    $("btn-lunch")?.addEventListener("click", (ev) => {
      const on = ev.currentTarget.getAttribute("aria-pressed") === "true";
      this._callService("set_lunch", { had_lunch: !on });
    });
    $("btn-auto")?.addEventListener("click", () => this._toggleSwitch());
    $("link-export")?.addEventListener("click", (ev) => {
      ev.preventDefault();
      this._callService("export_today");
    });
    $("link-sheets")?.addEventListener("click", (ev) => {
      ev.preventDefault();
      this._callService("export_today");
    });

    const editable = !!this._cfg("show_edit");
    if (editable) {
      const lists = this.shadowRoot.querySelectorAll("section.section");
      const tableKeysInOrder = [];
      if (this._cfg("show_this_week")) tableKeysInOrder.push("this_week");
      if (this._cfg("show_last_week")) tableKeysInOrder.push("last_week");
      if (this._cfg("show_this_month")) tableKeysInOrder.push(null);
      if (this._cfg("show_last_month")) tableKeysInOrder.push(null);
      if (this._cfg("show_history")) tableKeysInOrder.push("history");
      lists.forEach((sec, idx) => {
        const key = tableKeysInOrder[idx];
        if (!key) return;
        sec.querySelectorAll(".row, .history-row").forEach((row) => {
          row.style.cursor = "pointer";
          row.addEventListener("click", () => {
            const i = parseInt(row.getAttribute("data-row"), 10);
            const day = (this._dayTables[key] || [])[i];
            this._openEdit(day);
          });
        });
      });
    }

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

  _styles(padding) {
    return `
      @import url('https://fonts.googleapis.com/css2?family=Geist:wght@400;500;600;700&family=Geist+Mono:wght@400;500;600&display=swap');

      :host {
        --wt-bg:       #f4f3ee;
        --wt-paper:    #fbfaf6;
        --wt-card:     #ffffff;
        --wt-ink:      #15151a;
        --wt-ink-2:    #3a3a44;
        --wt-muted:    #8a8a94;
        --wt-muted-2:  #b6b6be;
        --wt-line:     #e7e5dd;
        --wt-line-2:   #efede6;
        --wt-accent:       #4338ca;
        --wt-accent-soft:  #ecebff;
        --wt-good:         #1f8a5b;
        --wt-warn:         #b45309;
        --wt-danger:       #b91c1c;
        display: block;
      }
      ha-card {
        background: var(--wt-bg);
        border: none;
        border-radius: 0;
        padding: 0;
        box-shadow: none;
        color: var(--wt-ink);
        font-family: 'Geist', -apple-system, BlinkMacSystemFont, system-ui, sans-serif;
        font-size: 14px;
        letter-spacing: -0.005em;
        -webkit-font-smoothing: antialiased;
      }
      .app {
        max-width: var(--wt-maxw, 420px);
        margin: 0 auto;
        padding: var(--wt-pad, 14px) var(--wt-pad, 14px) calc(var(--wt-pad, 14px) * 2);
      }
      .mono { font-family: 'Geist Mono', ui-monospace, 'SF Mono', Menlo, monospace; font-feature-settings: 'tnum', 'zero'; }

      /* Topbar — date only, centered */
      .topbar {
        display: flex;
        align-items: center;
        justify-content: center;
        padding: 6px 6px 14px;
      }
      .topbar .date {
        font-size: 12px;
        color: var(--wt-muted);
      }

      /* TODAY */
      .today {
        background: var(--wt-card);
        border: 1px solid var(--wt-line);
        border-radius: 18px;
        padding: 14px 14px 12px;
      }
      .today-head {
        display: flex; align-items: center; justify-content: space-between;
        margin-bottom: 10px;
      }
      .today-head .left {
        display: flex; align-items: center; gap: 8px;
        font-size: 13px; font-weight: 600; color: var(--wt-ink);
      }
      .badge-icon {
        width: 26px; height: 26px;
        border-radius: 8px;
        background: var(--wt-ink);
        color: #fff;
        display: inline-flex; align-items: center; justify-content: center;
      }
      .badge-icon svg { width: 14px; height: 14px; stroke: currentColor; fill: none; stroke-width: 1.75; stroke-linecap: round; stroke-linejoin: round; }
      .today-head .right { display: flex; align-items: center; gap: 8px; }

      /* On-the-clock pill — sized to match the "Today" label badge */
      .pill {
        display: inline-flex; align-items: center; gap: 8px;
        height: 26px; padding: 0 12px; border-radius: 999px;
        font-size: 13px; font-weight: 500;
      }
      .pill.on-clock { background: var(--wt-accent-soft); color: var(--wt-accent); }
      .pill.done { background: var(--wt-paper); color: var(--wt-ink-2); border: 1px solid var(--wt-line); }
      .pill.off { background: var(--wt-paper); color: var(--wt-muted); border: 1px solid var(--wt-line); }
      .pulse {
        width: 7px; height: 7px; border-radius: 50%;
        background: var(--wt-accent);
        box-shadow: 0 0 0 0 rgba(67,56,202,.5);
        animation: wt-pulse 1.8s infinite;
      }
      @keyframes wt-pulse {
        0% { box-shadow: 0 0 0 0 rgba(67,56,202,.5); }
        70% { box-shadow: 0 0 0 7px rgba(67,56,202,0); }
        100% { box-shadow: 0 0 0 0 rgba(67,56,202,0); }
      }

      .elapsed {
        display: flex; align-items: baseline; gap: 4px;
        font-weight: 500; font-size: 46px; line-height: 1;
        letter-spacing: -0.03em;
        padding: 4px 2px 6px;
      }
      .elapsed .unit {
        font-family: 'Geist', sans-serif;
        font-size: 14px; color: var(--wt-muted);
        margin-left: 4px; margin-right: 6px;
        font-weight: 400; letter-spacing: 0;
      }
      .elapsed-sub {
        font-size: 12px; color: var(--wt-muted);
        display: flex; gap: 10px; align-items: center;
        padding: 0 2px;
      }
      .elapsed-sub .delta.over { color: var(--wt-warn); font-weight: 500; }
      .elapsed-sub .delta.under { color: var(--wt-muted); font-weight: 500; }
      .elapsed-sub .dot { width: 3px; height: 3px; border-radius: 50%; background: var(--wt-muted-2); }

      .track {
        margin: 12px 0 12px;
        height: 6px; border-radius: 999px;
        background: var(--wt-line-2);
        position: relative;
        overflow: visible;
      }
      .fill {
        height: 100%; border-radius: 999px;
        background: var(--wt-ink);
        transition: width .5s cubic-bezier(.2,.7,.2,1);
      }
      .fill.over { background: var(--wt-warn); }
      .mark {
        position: absolute; top: -3px; bottom: -3px;
        width: 1px; background: rgba(0,0,0,.18);
      }

      .io {
        display: grid;
        grid-template-columns: 1fr 1fr 1fr;
        border: 1px solid var(--wt-line);
        border-radius: 12px;
        overflow: hidden;
        background: var(--wt-paper);
      }
      .io > div { padding: 9px 10px; border-right: 1px solid var(--wt-line-2); }
      .io > div:last-child { border-right: none; }
      .io-label {
        font-size: 10px; text-transform: uppercase; letter-spacing: 0.1em;
        color: var(--wt-muted); font-weight: 500;
        margin-bottom: 2px;
      }
      .io-value {
        font-weight: 500; font-size: 16px;
        letter-spacing: -0.01em;
      }
      .io-value.dim { color: var(--wt-muted); }

      .actions { margin-top: 10px; display: grid; gap: 8px; }
      .actions-3 { grid-template-columns: 1fr 1fr 1fr; }
      .actions-grid { margin-top: 8px; display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
      .btn {
        display: inline-flex; align-items: center; justify-content: center; gap: 8px;
        height: 44px; padding: 0 12px;
        border-radius: 12px;
        border: 1px solid var(--wt-line);
        background: var(--wt-card);
        font-family: inherit; font-size: 14px; font-weight: 500;
        color: var(--wt-ink); cursor: pointer;
        transition: transform .08s ease, background .12s ease, border-color .12s ease;
        letter-spacing: -0.005em;
      }
      .btn:active { transform: translateY(1px); }
      .btn.primary { background: var(--wt-ink); color: #fff; border-color: var(--wt-ink); }
      .btn .icon { width: 16px; height: 16px; flex-shrink: 0; }
      .btn .meta { color: var(--wt-muted); font-size: 12px; margin-left: 2px; }
      .btn.toggle[aria-pressed="true"] .meta {
        color: var(--wt-ink);
        font-weight: 600;
      }
      .btn.toggle[aria-pressed="true"] .meta::before {
        content: "";
        display: inline-block;
        width: 6px; height: 6px; border-radius: 50%;
        background: var(--wt-accent);
        margin-right: 5px; vertical-align: middle;
      }

      /* Sections */
      .section { margin-top: 20px; }
      .section-head {
        display: flex; justify-content: space-between; align-items: baseline;
        padding: 0 2px;
        margin-bottom: 8px;
      }
      .section-title { font-size: 13px; font-weight: 600; letter-spacing: -0.01em; }
      .section-title .title-meta {
        color: var(--wt-muted); font-weight: 500; font-size: 11px;
        margin-left: 8px;
      }
      .section-meta {
        font-size: 11px; color: var(--wt-muted);
        display: flex; gap: 10px; align-items: baseline;
      }
      .section-meta b { color: var(--wt-ink); font-weight: 600; }
      .section-meta .pos { color: var(--wt-good); font-weight: 500; }
      .section-meta .neg { color: var(--wt-warn); font-weight: 500; }

      .list {
        background: var(--wt-card);
        border: 1px solid var(--wt-line);
        border-radius: 14px;
        overflow: hidden;
      }
      .row {
        display: grid;
        grid-template-columns: 44px 1fr auto 24px;
        align-items: center;
        padding: 11px 14px;
        border-bottom: 1px solid var(--wt-line-2);
        gap: 10px;
        font-size: 14px;
      }
      .row:last-child { border-bottom: none; }
      .row .day { font-weight: 500; font-size: 14px; }
      .row .day .date {
        display: block; font-size: 10px; color: var(--wt-muted); margin-top: 1px;
        font-family: 'Geist Mono', monospace; letter-spacing: 0;
      }
      .row .times {
        font-family: 'Geist Mono', monospace; font-size: 13px;
        color: var(--wt-ink-2);
        letter-spacing: -0.005em;
      }
      .row .times .sep { color: var(--wt-muted-2); margin: 0 4px; }
      .row .hours {
        font-family: 'Geist Mono', monospace; font-weight: 500; font-size: 14px;
        text-align: right;
      }
      .row .hours.over { color: var(--wt-warn); }
      .row .hours.under { color: var(--wt-ink); }
      .row .edit {
        color: var(--wt-muted-2);
        display: inline-flex; align-items: center; justify-content: center;
        cursor: pointer;
        height: 24px; width: 24px;
        border-radius: 6px;
      }
      .row .edit:hover { color: var(--wt-ink); background: var(--wt-line-2); }
      .row.today { background: rgba(67, 56, 202, 0.045); }
      .row.today .day { color: var(--wt-accent); }
      .row.empty .times,
      .row.empty .hours { color: var(--wt-muted-2); }

      .totals {
        display: flex; align-items: center;
        padding: 11px 14px;
        background: var(--wt-paper);
        border-top: 1px solid var(--wt-line);
        font-size: 12px;
        color: var(--wt-muted);
      }
      .totals b { color: var(--wt-ink); font-weight: 600; font-family: 'Geist Mono', monospace; }

      /* Month summary card */
      .month-card {
        background: var(--wt-card);
        border: 1px solid var(--wt-line);
        border-radius: 14px;
        padding: 10px 14px;
      }
      .month-row {
        display: flex; justify-content: space-between; align-items: center;
        padding: 6px 0;
      }
      .month-row + .month-row { border-top: 1px solid var(--wt-line-2); }
      .month-k { font-size: 12px; color: var(--wt-muted); }
      .month-v { font-size: 15px; font-weight: 500; }
      .month-v.pos { color: var(--wt-good); }
      .month-v.neg { color: var(--wt-warn); }

      /* History compact */
      .history-row {
        display: grid;
        grid-template-columns: 86px 36px 1fr auto;
        padding: 10px 14px;
        align-items: center;
        border-bottom: 1px solid var(--wt-line-2);
        gap: 10px;
        font-size: 13px;
      }
      .history-row:last-child { border-bottom: none; }
      .history-row.editable { cursor: pointer; }
      .history-row .date { font-family: 'Geist Mono', monospace; font-size: 12px; color: var(--wt-ink-2); }
      .history-row .day { font-size: 12px; color: var(--wt-muted); }
      .history-row .mini { height: 3px; background: var(--wt-line-2); border-radius: 999px; overflow: hidden; }
      .history-row .mini > span { display: block; height: 100%; background: var(--wt-ink); border-radius: 999px; }
      .history-row .mini > span.over { background: var(--wt-warn); }
      .history-row .hours { font-family: 'Geist Mono', monospace; font-weight: 500; text-align: right; }

      .foot {
        margin-top: 20px;
        display: flex; justify-content: space-between; align-items: center;
        color: var(--wt-muted); font-size: 11px;
        padding: 0 4px;
      }
      .foot a { color: var(--wt-muted); text-decoration: none; cursor: pointer; }
      .foot a:hover { color: var(--wt-ink); }
      .foot-links { display: flex; gap: 14px; }

      @media (max-width: 360px) { .elapsed { font-size: 40px; } }

      /* Modal */
      .modal-backdrop {
        position: fixed; inset: 0;
        background: rgba(0,0,0,0.55);
        display: flex; align-items: center; justify-content: center;
        z-index: 999;
      }
      .modal {
        background: var(--wt-card); color: var(--wt-ink);
        border-radius: 18px; padding: 20px;
        width: min(420px, 92vw); max-height: 90vh;
        overflow-y: auto;
        box-shadow: 0 8px 24px rgba(0,0,0,0.3);
      }
      .modal h3 { margin: 0 0 12px; font-size: 1.05em; font-weight: 600; }
      .modal .field { display: flex; flex-direction: column; gap: 4px; margin-bottom: 12px; }
      .modal .field label {
        font-size: 10px; color: var(--wt-muted);
        text-transform: uppercase; letter-spacing: 0.1em; font-weight: 500;
      }
      .modal input, .modal select {
        padding: 10px; font-size: 14px; font-family: inherit;
        border: 1px solid var(--wt-line); border-radius: 10px;
        background: var(--wt-card); color: var(--wt-ink);
      }
      .modal .row-actions { display: flex; gap: 8px; justify-content: flex-end; margin-top: 8px; }
      .modal .row-actions .btn { flex: 0 0 auto; min-width: 90px; }`;
  }

  static getStubConfig() { return {}; }
  static getConfigElement() {
    return document.createElement("worktime-tracker-card-editor");
  }
}

/* Visual editor */
class WorktimeTrackerCardEditor extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._config = {};
  }

  setConfig(config) { this._config = { ...config }; this._render(); }
  set hass(hass) { this._hass = hass; }

  _emit() {
    this.dispatchEvent(new CustomEvent("config-changed", {
      detail: { config: this._config }, bubbles: true, composed: true,
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
        .row { display: flex; align-items: center; gap: 10px; padding: 4px 0; cursor: pointer; }
        .row input { transform: scale(1.1); }
        .num-row { display: flex; align-items: center; gap: 10px; padding: 4px 0; }
        input[type="number"], input[type="text"] {
          padding: 6px 8px;
          border: 1px solid var(--divider-color, #ccc);
          border-radius: 6px;
          background: var(--card-background-color, #fff);
          color: var(--primary-text-color);
          width: 120px;
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
        <div class="group-title">History rows</div>
        <div class="num-row">
          <input id="ed-limit" type="number" min="1" max="60" value="${this._get("history_limit")}">
        </div>
      </div>
      <div class="group">
        <div class="group-title">Padding (px)</div>
        <div class="num-row">
          <input id="ed-padding" type="number" min="0" max="60" value="${this._get("padding")}">
        </div>
      </div>
      <div class="group">
        <div class="group-title">Max width (px, 0 = fluid)</div>
        <div class="num-row">
          <input id="ed-maxw" type="number" min="0" max="1200" value="${this._get("max_width")}">
        </div>
        <div class="hint">
          Default <code>420</code> (phone-sized). Increase to use more of
          a wide column. Set <code>0</code> to fill the container.
        </div>
      </div>
      <div class="group">
        <div class="group-title">Entity prefix (multi-instance)</div>
        <div class="num-row">
          <input id="ed-prefix" type="text" placeholder="e.g. home" value="${this._get("entity_prefix") || ""}">
        </div>
        <div class="hint">
          Leave blank for the default instance. Set to e.g. <code>home</code>
          to point at <code>sensor.home_today_hours_today</code> (entities of
          a second Worktime Tracker config entry).
        </div>
      </div>
      <div class="hint">
        Theming: override <code>--wt-bg</code>, <code>--wt-card</code>,
        <code>--wt-ink</code>, <code>--wt-accent</code>, <code>--wt-warn</code>
        on <code>:host</code> via card_mod or your theme.
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
        this._config = { ...this._config, history_limit: n };
        this._emit();
      }
    });
    this.shadowRoot.getElementById("ed-padding")?.addEventListener("input", (ev) => {
      const n = parseInt(ev.target.value, 10);
      if (!isNaN(n) && n >= 0) {
        this._config = { ...this._config, padding: n };
        this._emit();
      }
    });
    this.shadowRoot.getElementById("ed-maxw")?.addEventListener("input", (ev) => {
      const n = parseInt(ev.target.value, 10);
      if (!isNaN(n) && n >= 0) {
        this._config = { ...this._config, max_width: n };
        this._emit();
      }
    });
    this.shadowRoot.getElementById("ed-prefix")?.addEventListener("input", (ev) => {
      const v = (ev.target.value || "").trim().replace(/[^a-z0-9_]/gi, "_");
      this._config = { ...this._config, entity_prefix: v };
      this._emit();
    });
  }
}

customElements.define("worktime-tracker-card-editor", WorktimeTrackerCardEditor);
customElements.define("worktime-tracker-card", WorktimeTrackerCard);

window.customCards = window.customCards || [];
window.customCards.push({
  type: "worktime-tracker-card",
  name: "Worktime Tracker",
  description: "Phone-first work-time tracker with Today / week / month / history.",
  preview: false,
  documentationURL: "https://github.com/ottoherdy/worktime-tracker",
});
