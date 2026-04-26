# Worktime Tracker

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![Validate](https://github.com/ottoherdy/worktime-tracker/actions/workflows/validate.yml/badge.svg)](https://github.com/ottoherdy/worktime-tracker/actions/workflows/validate.yml)

En komplett **Home Assistant custom integration** för automatisk arbetstidsspårning. Allt sker i en enda integration — ingen flora av automationer, ingen handpåläggning. Konfigureras helt via UI:t.

## Vad du får

- **Automatisk tidsspårning** via en zon (t.ex. `zone.otto_work`)
- **Lunch-push kl 13:00** med Ja/Nej-knappar — svaret påverkar planerad sluttid
- **Daglig logg till Google Sheets** via webhook (Apps Script)
- **Dashboard** med ApexCharts-jämförelse mellan denna och förra veckan
- **Scriptable-widget** för iOS som visar tid kvar / övertid

## Repo-innehåll

```
worktime-tracker/
├── custom_components/worktime_tracker/   ← själva integrationen (HACS installerar denna)
├── dashboards/dashboard.yaml             ← Lovelace-vy
├── scriptable/worktime_widget.js         ← iOS-widget
├── apps_script/google_apps_script.gs     ← Sheets-webhook
├── hacs.json                             ← HACS-metadata
└── .github/workflows/validate.yml        ← hassfest + HACS-validering
```

## Installation

### Steg 1 — Pusha repot till GitHub

Kör de kommandona som finns under [SETUP.md](SETUP.md), eller om du redan har repot uppe: hoppa direkt till steg 2.

### Steg 2 — Installera integrationen via HACS

1. Öppna HACS i Home Assistant
2. **Integrations** → tre prickar uppe till höger → **Custom repositories**
3. Lägg till URL: `https://github.com/ottoherdy/worktime-tracker`, kategori: **Integration**
4. Sök upp **Worktime Tracker** i listan → **Download**
5. Starta om Home Assistant

### Steg 3 — Konfigurera

`Settings → Devices & Services → + Add Integration → "Worktime Tracker"`

| Fält | Exempel | Förklaring |
|---|---|---|
| Person eller device tracker | `person.otto` | Den som spåras |
| Arbetszon | `zone.otto_work` | När personen är i zonen räknas det som "på jobbet" |
| Notify-tjänst | `mobile_app_otto_phone` | Utan `notify.`-prefix. Lämna tomt om du inte vill ha lunch-notisen |
| Tid för lunch-check | `13:00` | När push-notisen om lunch skickas |
| Arbetsdagens längd | `8.5` | Inkl. lunch (8h netto + 0.5h lunch) |
| Lunchpaus | `0.5` | Dras av vid "Nej" på lunchfrågan |
| Veckomål | `40` | För övertids-beräkning |
| Sheets webhook URL | (se nedan) | Lämna tomt om du inte använder Sheets |
| Anta lunch om inget svar | På | Vid avresa utan svar: räkna med lunch |

Allt går att ändra senare via **Configure** på integrationen.

### Steg 4 — Lägg in dashboarden

Öppna `dashboards/dashboard.yaml` och klistra in i en ny eller befintlig Lovelace-dashboard. Kräver två HACS-frontendkort: **ApexCharts Card** och **Mushroom**.

### Steg 5 — Google Sheets (valfritt)

1. Skapa ett tomt Google Sheet
2. `Extensions → Apps Script`
3. Klistra in `apps_script/google_apps_script.gs`
4. **Deploy → New deployment → Web app** (Execute as: Me, Who has access: Anyone)
5. Kopiera URL:en → **Configure** integrationen → klistra in i Sheets-fältet

### Steg 6 — Scriptable iOS-widget (valfritt)

1. Installera [Scriptable](https://apps.apple.com/se/app/scriptable/id1405459188)
2. Skapa nytt script, klistra in `scriptable/worktime_widget.js`
3. Ändra `HA_URL` och `HA_TOKEN` (skapa en Long-Lived Token: HA-profil → Security)
4. Lägg till en Scriptable-widget på hemskärmen, **Medium**-storlek

## Entiteter som skapas

| Entity | Vad |
|---|---|
| `sensor.worktime_tracker_arrival_time` | Ankomst (timestamp) |
| `sensor.worktime_tracker_planned_end_time` | Planerad sluttid |
| `sensor.worktime_tracker_departure_time` | Avresetid |
| `sensor.worktime_tracker_hours_today` | Timmar idag |
| `sensor.worktime_tracker_hours_this_week` | Veckosumma + attribut `this_week` / `last_week` |
| `sensor.worktime_tracker_overtime_this_week` | Övertid mot veckomålet |
| `sensor.worktime_tracker_time_remaining` | Minuter kvar (+ `human_readable`-attribut) |
| `sensor.worktime_tracker_status` | `off_duty` / `at_work` / `done` / `overtime` |
| `sensor.worktime_tracker_lunch_status` | `yes` / `no` / `unknown` |
| `binary_sensor.worktime_tracker_at_work` | På jobbet just nu |
| `binary_sensor.worktime_tracker_day_complete` | Dagen avslutad |

## Services

| Service | Data | Vad |
|---|---|---|
| `worktime_tracker.set_lunch` | `had_lunch: true/false` | Sätt lunchstatus |
| `worktime_tracker.log_arrival` | – | Manuellt registrera ankomst |
| `worktime_tracker.log_departure` | – | Manuellt registrera avresa |
| `worktime_tracker.reset_today` | – | Nollställ dagen |
| `worktime_tracker.export_history` | – | Skicka om dagens rad till Sheets |

## Hur logiken fungerar

```
Person går in i arbetszonen
        ↓
arrival = now,  planned_end = arrival + 8.5h

Kl 13:00 om fortfarande på jobbet → push: [Ja, haft lunch] [Nej]
   "Nej" → planned_end -= 30 min
   Inget svar → "Anta lunch"-flaggan avgör vid avresa

Person lämnar zonen
        ↓
1) Beräkna jobbade timmar (minus lunch om "Ja")
2) Spara i lokal HA-storage
3) POST till Google Sheets webhook
4) Uppdatera alla sensorer
```

### Status-värden

| Status | När |
|---|---|
| `off_duty` | Ingen ankomst registrerad idag |
| `at_work` | Ankommen, planerad sluttid ej passerad, ingen avresa |
| `overtime` | Kvar förbi planerad sluttid |
| `done` | Avresa registrerad |

## Felsökning

| Symptom | Lösning |
|---|---|
| Lunch-notisen kommer inte | Kolla att `notify_service` är angiven utan `notify.`-prefix |
| Sheets-rader hamnar inte in | Apps Script Executions → kolla loggar. Vanligaste felet: deployment är inte "Anyone"-åtkomlig |
| ApexCharts är tom | Sensorn behöver minst en avslutad dag i historiken |

## Bidra

PR välkomna. CI kör `hassfest`, HACS-validering och en Python-kompileringskontroll vid varje push.

## Licens

MIT — se [LICENSE](LICENSE).
