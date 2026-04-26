# Worktime Tracker

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![Validate](https://github.com/ottoherdy/worktime-tracker/actions/workflows/validate.yml/badge.svg)](https://github.com/ottoherdy/worktime-tracker/actions/workflows/validate.yml)

En komplett **Home Assistant custom integration** för automatisk arbetstidsspårning. Allt sker i en enda integration — ingen flora av automationer, ingen handpåläggning. Konfigureras helt via UI:t.

## Vad du får

- **Automatisk tidsspårning** via en zon — ankomst och avresa registreras automatiskt
- **Lunch-push** med Ja/Nej-knappar — svaret påverkar planerad sluttid
- **Daglig logg till Google Sheets** med veckodag, tider, timmar och kvartsavrundning
- **Dashboard** med veckoöversikt, stapeldiagram (denna vs förra veckan) och de 5 senaste dagarna
- **Scriptable-widget** för iOS som visar tid kvar eller övertid som en cirkel

## Repo-innehåll

```
worktime-tracker/
├── custom_components/worktime_tracker/   ← själva integrationen (HACS installerar denna)
├── dashboards/dashboard.yaml             ← Lovelace-vy
├── scriptable/worktime_widget.js         ← iOS-widget
├── hacs.json                             ← HACS-metadata
└── .github/workflows/validate.yml        ← hassfest + HACS-validering
```

## Installation

### Steg 1 — Installera via HACS

1. Öppna HACS i Home Assistant
2. **Integrations** → tre prickar uppe till höger → **Custom repositories**
3. Lägg till URL: `https://github.com/ottoherdy/worktime-tracker`, kategori: **Integration**
4. Sök upp **Worktime Tracker** → **Download**
5. Starta om Home Assistant

### Steg 2 — Konfigurera

`Settings → Devices & Services → + Add Integration → "Worktime Tracker"`

| Fält | Exempel | Förklaring |
|---|---|---|
| Person eller device tracker | `person.your_name` | Den som spåras |
| Arbetszon | `zone.work` | När personen är i zonen räknas det som "på jobbet" |
| Notify-tjänst | `mobile_app_your_phone` | Utan `notify.`-prefix. Lämna tomt för ingen lunch-notis |
| Tid för lunch-check | `13:00` | När push-notisen om lunch skickas |
| Arbetsdagens längd | `8.5` | Inkl. lunch (8h netto + 0.5h lunch) |
| Lunchpaus | `0.5` | Dras av vid "Nej" på lunchfrågan |
| Veckomål | `40` | För övertids-beräkning |
| Anta lunch om inget svar | På | Vid avresa utan svar: räkna med lunch |

Allt går att ändra senare via **Configure** på integrationen.

### Steg 3 — Lägg in dashboarden

Öppna `dashboards/dashboard.yaml` och klistra in i en ny eller befintlig Lovelace-dashboard.

Kräver två HACS-frontendkort:
- [ApexCharts Card](https://github.com/RomRider/apexcharts-card)
- [Mushroom](https://github.com/piitaya/lovelace-mushroom)

### Steg 4 — Google Sheets (valfritt)

Kräver att du har installerat den officiella [Google Sheets-integrationen](https://www.home-assistant.io/integrations/google_sheets/) i Home Assistant.

1. Installera **Google Sheets** via `Settings → Devices & Services → + Add Integration`
2. Autentisera med ditt Google-konto
3. Gå till **Configure** på Worktime Tracker-integrationen
4. Ange **Config Entry ID** för Google Sheets-integrationen och ett **worksheet-namn**

Varje dag loggas automatiskt en rad med följande kolumner:

| Kolumn | Exempel |
|---|---|
| Datum | 2026-04-28 |
| Veckodag | Måndag |
| Ankomst | 08:12 |
| Planerad slut | 16:42 |
| Avresa | 16:38 |
| Lunch | yes |
| Timmar | 8.43 |
| Timmar (avrundat) | 8.5 |

### Steg 5 — Scriptable iOS-widget (valfritt)

1. Installera [Scriptable](https://apps.apple.com/se/app/scriptable/id1405459188)
2. Skapa nytt script och klistra in `scriptable/worktime_widget.js`
3. Ändra `HA_URL` och `HA_TOKEN` (skapa en Long-Lived Token: HA-profil → Security)
4. Lägg till en Scriptable-widget på hemskärmen, **Medium**-storlek

## Entiteter som skapas

| Entity | Vad |
|---|---|
| `sensor.worktime_tracker_arrival_time` | Ankomst (timestamp) |
| `sensor.worktime_tracker_planned_end_time` | Planerad sluttid |
| `sensor.worktime_tracker_departure_time` | Avresetid |
| `sensor.worktime_tracker_hours_today` | Timmar idag |
| `sensor.worktime_tracker_hours_week` | Veckosumma + attribut `this_week`, `last_week`, `recent_days` |
| `sensor.worktime_tracker_overtime_week` | Övertid mot veckomålet |
| `sensor.worktime_tracker_time_remaining` | Minuter kvar (+ `human_readable`-attribut) |
| `sensor.worktime_tracker_status` | `off_duty` / `at_work` / `done` / `overtime` |
| `sensor.worktime_tracker_lunch_status` | `yes` / `no` / `unknown` |
| `binary_sensor.worktime_tracker_at_work` | På jobbet just nu |
| `binary_sensor.worktime_tracker_day_complete` | Dagen avslutad |

## Tjänster

| Tjänst | Data | Vad |
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
arrival = now,  planned_end = arrival + arbetsdagens längd

Kl 13:00 om fortfarande på jobbet → push: [Ja, haft lunch] [Nej]
   "Nej" → planned_end -= lunchpaus
   Inget svar → "Anta lunch"-flaggan avgör vid avresa

Person lämnar zonen
        ↓
1) Beräkna jobbade timmar (minus lunch om "Ja")
2) Spara i lokal HA-storage
3) Lägg till rad i Google Sheets (om konfigurerat)
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
| Lunch-notisen kommer inte | Kontrollera att `notify_service` är angiven utan `notify.`-prefix |
| Sheets-rader hamnar inte in | Kontrollera att Google Sheets-integrationen är installerad och att Config Entry ID stämmer |
| ApexCharts är tom | Sensorn behöver minst en avslutad dag i historiken |
| Scriptable-widgeten visar fel | Kontrollera att `HA_URL` och `HA_TOKEN` är korrekt ifyllda |

## Bidra

PR välkomna. CI kör `hassfest`, HACS-validering och en Python-kompileringskontroll vid varje push.

## Licens

MIT — se [LICENSE](LICENSE).
