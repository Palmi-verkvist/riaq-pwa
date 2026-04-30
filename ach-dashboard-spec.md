# RIAQ PWA — App Specification
_Version: 1.0 | Created: 2026-04-30_
_Owner: VERKVIST / Pálmi_
_Status: Ready to build_

---

## Overview

A bilingual (English / Icelandic) Streamlit web app that processes CO2 sensor data (CSV upload) and produces a
multi-building ventilation dashboard. Built for VERKVIST internal use first,
designed for white-label / handover to other parties later.

**Core method:** CO2 decay analysis — exponential curve fitting to natural CO2
decay periods to extract Air Changes per Hour (ACH) per building.

**Placeholder name:** RIAQ PWA
_Note: "PWA" is an internal codename — this is a Streamlit web app, not a
Progressive Web App technically. Rename before any commercial launch._

---

## Language / i18n

App is **bilingual from day one** — English and Icelandic.

- Language toggle in sidebar (EN / IS)
- All UI strings stored in a `translations.py` dictionary — never hardcoded
- Default language: English
- Charts and labels switch with the toggle
- Analysis engine output (numbers, values) is language-neutral

```python
# translations.py pattern
STRINGS = {
    "en": {
        "upload_title": "Upload CO2 Data",
        "run_analysis": "Run Analysis",
        "mean_ach": "Mean ACH",
        # ...
    },
    "is": {
        "upload_title": "Hlaða upp CO2 gögnum",
        "run_analysis": "Keyra greiningu",
        "mean_ach": "Meðal ACH",
        # ...
    }
}
```

---

## Stack

| Layer | Technology |
|-------|-----------|
| App framework | Streamlit |
| Language | Python 3.11+ |
| Data processing | pandas, numpy, scipy |
| Charts | matplotlib / plotly |
| Deployment | Streamlit Cloud (via GitHub) |
| Version control | GitHub |
| Dev environment | Claude Code |

---

## Input Data Format

**File type:** CSV upload via browser

**Expected columns (based on Stofa_CO2.csv):**

| Column | Type | Notes |
|--------|------|-------|
| `HouseNo.` | string | Building identifier e.g. `RIAQ_ICE_001` |
| `RoomType` | string | e.g. `Living room` |
| `dtm` | datetime string | Format: `09-Feb-2026 10:12:00+00:00` |
| `co2, ppm` | integer | CO2 concentration in ppm |
| `pm25, μg/m³` | float | Particulate matter (optional) |
| `ch2o, ppm` | float | Formaldehyde (optional) |
| `RetrofitStatus` | string | Building retrofit state (optional) |

**Column mapping:** App auto-detects columns on upload. If format differs,
user can manually map columns via dropdowns (resilient to different sensor exports).

---

## Core Analysis Engine

Adapted from University of Galway notebook (`aer_python_script.ipynb`).

### Method: CO2 Exponential Decay

```
C(t) = (C0 - C_ambient) × e^(-ACH × t) + C_ambient
```

Where:
- `C(t)` = CO2 at time t (ppm)
- `C0` = CO2 at start of decay (ppm)
- `C_ambient` = baseline outdoor CO2 (default: 420 ppm, configurable)
- `ACH` = air changes per hour (the output we want)

### Quality Control Filters (from notebook, keep as-is)

| Parameter | Default | Description |
|-----------|---------|-------------|
| `MIN_FINAL_CO2` | 500 ppm | Reject if decay ends too close to baseline |
| `MIN_DECAY_FRACTION` | 0.63 | Must decay at least 63% of starting value |
| `MIN_R_SQUARED` | 0.70 | Model fit quality threshold |
| `MIN_ACH` | 0.05 h⁻¹ | Minimum reasonable ventilation |
| `MAX_ACH_NORMAL` | 1.2 h⁻¹ | Purge detection threshold |
| `MAX_DECAY_RATE` | 500 ppm/h | Secondary purge detection |
| `MAX_INCREASES` | 3 | Monotonicity tolerance |

All parameters exposed in a sidebar so users can adjust without touching code.

---

## App Structure

### Page 1 — Upload & Overview
- CSV file uploader
- Auto-detect columns, show preview (first 10 rows)
- Manual column mapping if needed
- Dataset summary: houses detected, date range, total records
- "Run Analysis" button

### Page 2 — Dashboard (main view)

**KPI row (top)**
- Total buildings analysed
- Mean ACH across all buildings
- % decay events accepted vs rejected
- Date range of data

**Chart 1 — ACH Distribution (all buildings)**
- Histogram of all ACH values
- Mean + median lines
- Purge threshold line at 1.2 h⁻¹

**Chart 2 — ACH by Building (box plot)**
- One box per building
- Sorted by median ACH
- Purge threshold line

**Chart 3 — CO2 Timeline**
- Select building from dropdown
- Raw CO2 over time
- Detected decay periods highlighted

**Chart 4 — ACH vs Initial Decay Rate (scatter)**
- Coloured by R² quality
- Purge threshold lines
- Mirrors the diagnostic PNG your colleague produced

### Page 3 — IAQ Overview (bonus, easy win)
- PM2.5 and CH2O averages per building (data already in CSV)
- Simple bar charts
- WHO / Icelandic reference lines for context

### Page 4 — Data Export
- Download results as Excel (ACH per building per decay event)
- Download filtered/rejected breakdown
- (PDF report — Phase 2)

---

## Sidebar Controls

- Ambient CO2 baseline (default 420 ppm)
- QC parameter adjustments (collapsible, advanced)
- Building filter (select which houses to include)
- Date range filter

---

## Phases

### Phase 1 — Build now
- CSV upload + column detection
- Full ACH analysis engine
- Dashboard (Charts 1, 2, 3, 4)
- Excel export
- Deploy on Streamlit Cloud

### Phase 2 — Add later (easy)
- PDF report output
- IAQ overview page (PM2.5, CH2O)
- Multi-file upload (combine datasets)

### Phase 3 — When selling / scaling
- User authentication / login
- White-label branding (logo, colours)
- Direct sensor API integrations (Aranet, Netatmo, etc.)
- Move to own server (inhouse) if needed

---

## File Structure

```
ach-dashboard/
├── app.py                  # Main Streamlit app
├── analysis/
│   ├── decay_engine.py     # Core ACH calculation (adapted from notebook)
│   ├── qc_filters.py       # Quality control logic
│   └── purge_detection.py  # Window purge detection
├── components/
│   ├── charts.py           # All chart functions
│   ├── dashboard.py        # Dashboard page
│   └── upload.py           # Upload + column mapping
├── utils/
│   └── export.py           # Excel/CSV export
├── translations.py             # All UI strings in EN + IS
├── requirements.txt
├── .env                    # API keys (if needed later)
├── .gitignore              # Must include .env
└── README.md
```

---

## Handoff Note for Claude Code

**Start prompt:**
> "I am building a Streamlit app called RIAQ PWA that processes CO2 sensor
> CSV data and calculates Air Changes per Hour (ACH) using CO2 decay analysis.
> Read this spec file (ach-dashboard-spec.md) and the reference notebook
> (aer_python_script.ipynb) which contains the core analysis logic we are
> adapting. The CSV data format is in Stofa_CO2.csv. Start by setting up the
> project structure and requirements.txt, then build the analysis engine in
> analysis/decay_engine.py adapted to our column names (dtm, co2, ppm, HouseNo.).
> The app is bilingual (English/Icelandic) — all UI strings must go in
> translations.py, never hardcoded. Do not build the UI yet — get the engine
> working and tested first."

---

## Open Questions (decide before or during build)

1. **App name** — placeholder for now, easy to change
2. **Language** — English UI or Icelandic? (recommendation: English for sellability)
3. **Branding** — VERKVIST colours for now, white-label later
4. **Authentication** — none for Phase 1 (Streamlit Cloud has basic password protection)
