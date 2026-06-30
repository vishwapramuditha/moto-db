# MotoDB - Data for every motorsport

<p align="center">
  <img src="public/hero-car.svg" alt="Moto-DB F1 Dotted Car Banner" width="480">
</p>

An open-source, developer-friendly database of schedules, **race weekend session timetables**, race results, driver profiles, and track metadata for major motorsports—hosted entirely on GitHub and accessible for **$0** in hosting costs with infinite scale.

---

## 🛠️ Architecture: Git-as-a-Database

Instead of maintaining a complex, expensive database server (which has API rate limits, server maintenance overhead, and latency spikes), Moto-DB runs entirely on a **Git-as-a-Database** model:

1. **Automated Collection**: GitHub Actions trigger Python scraping scripts (located in `/scripts`) on cron schedules (hourly/daily).
2. **Schema Validation**: Crawled datasets are parsed and validated against our strict JSON schema specifications to prevent schema drift.
3. **Decentralized Storage**: Validated JSON files are committed directly back to the public repository under the `/data` directory.
4. **Edge CDN Delivery**: Developers fetch the data directly via the `jsDelivr` CDN. Files are cached globally across edge networks (Cloudflare, Fastly, BunnyCDN), resulting in response times under 50ms worldwide and zero hosting fees.

---

## 🚀 How to use the API (jsDelivr CDN Endpoints)

You can query Moto-DB directly in your client-side (React, Vue, Swift, Android) or server-side (Node, Python, Go) applications using standard HTTP GET requests.

### Global Metadata

*   **F1 Drivers**:
    `https://cdn.jsdelivr.net/gh/vishwapramuditha/moto-db@main/data/f1/drivers.json`
*   **F1 Circuits**:
    `https://cdn.jsdelivr.net/gh/vishwapramuditha/moto-db@main/data/f1/tracks.json`
*   **MotoGP Riders**:
    `https://cdn.jsdelivr.net/gh/vishwapramuditha/moto-db@main/data/motogp/drivers.json`
*   **MotoGP Circuits**:
    `https://cdn.jsdelivr.net/gh/vishwapramuditha/moto-db@main/data/motogp/tracks.json`
*   **NASCAR Drivers**:
    `https://cdn.jsdelivr.net/gh/vishwapramuditha/moto-db@main/data/nascar/drivers.json`
*   **NASCAR Tracks**:
    `https://cdn.jsdelivr.net/gh/vishwapramuditha/moto-db@main/data/nascar/tracks.json`

### Season & Race Data

*   **F1 Schedule (e.g. 2025)**:
    `https://cdn.jsdelivr.net/gh/vishwapramuditha/moto-db@main/data/f1/2025/schedule.json`
*   **F1 Results (e.g. 2025 Round 1)**:
    `https://cdn.jsdelivr.net/gh/vishwapramuditha/moto-db@main/data/f1/2025/results_1.json`
*   **MotoGP Schedule (e.g. 2025)**:
    `https://cdn.jsdelivr.net/gh/vishwapramuditha/moto-db@main/data/motogp/2025/schedule.json`
*   **MotoGP Results (e.g. 2025 Thailand GP MotoGP Main Race)**:
    `https://cdn.jsdelivr.net/gh/vishwapramuditha/moto-db@main/data/motogp/2025/THA/motogp_RAC.json`
*   **NASCAR Schedule (e.g. 2025)**:
    `https://cdn.jsdelivr.net/gh/vishwapramuditha/moto-db@main/data/nascar/2025/schedule.json`
*   **NASCAR Results (e.g. 2024 Cup Series Event 5385)**:
    `https://cdn.jsdelivr.net/gh/vishwapramuditha/moto-db@main/data/nascar/2024/cup/results_5385.json`
*   **IndyCar Schedule (e.g. 2025)**:
    `https://cdn.jsdelivr.net/gh/vishwapramuditha/moto-db@main/data/indycar/2025/schedule.json`
*   **IndyCar Results (e.g. 2024 GP of St. Petersburg)**:
    `https://cdn.jsdelivr.net/gh/vishwapramuditha/moto-db@main/data/indycar/2024/results_202403100104.json`
*   **WEC Schedule (e.g. 2025)**:
    `https://cdn.jsdelivr.net/gh/vishwapramuditha/moto-db@main/data/wec/2025/schedule.json`
*   **WEC Results (e.g. 2025)**:
    `https://cdn.jsdelivr.net/gh/vishwapramuditha/moto-db@main/data/wec/2025/results.json`
*   **WEC Standings (e.g. 2025)**:
    `https://cdn.jsdelivr.net/gh/vishwapramuditha/moto-db@main/data/wec/2025/standings.json`
*   **Formula E Schedule (e.g. 2025)**:
    `https://cdn.jsdelivr.net/gh/vishwapramuditha/moto-db@main/data/formula_e/2025/schedule.json`
*   **Formula E Results (e.g. 2025)**:
    `https://cdn.jsdelivr.net/gh/vishwapramuditha/moto-db@main/data/formula_e/2025/results.json`
*   **WRC Schedule (e.g. 2025)**:
    `https://cdn.jsdelivr.net/gh/vishwapramuditha/moto-db@main/data/wrc/2025/schedule.json`
*   **WRC Results (e.g. 2025)**:
    `https://cdn.jsdelivr.net/gh/vishwapramuditha/moto-db@main/data/wrc/2025/results.json`

---

## 📖 Best Practices for Developers

### 1. Commit Version Pinning
Using `@main` in URLs serves the latest database commits instantly. However, for production workloads, it is recommended to replace `@main` with a specific commit hash (e.g. `@32d4a1b`) or release tag. This secures version locking, protecting your applications from breaking changes if schemas evolve.
```text
https://cdn.jsdelivr.net/gh/vishwapramuditha/moto-db@<commit-hash>/data/f1/2025/schedule.json
```

### 2. CORS & Client-Side Loading
All jsDelivr responses are fully CORS-enabled. You can request endpoints directly from single-page web applications without having to configure proxy routing or API CORS headers on your own backend.

---

## 📁 Repository Structure

```text
moto-db/
├── data/
│   ├── f1/
│   │   ├── drivers.json           # Active and historical F1 drivers
│   │   ├── tracks.json            # F1 circuits around the world
│   │   └── {year}/
│   │       ├── schedule.json      # Full season schedule with sessions[] (FP1, FP2, FP3, SQ, Sprint, Qualifying, Race)
│   │       └── results_{round}.json
│   ├── motogp/
│   │   ├── drivers.json           # Active and historical MotoGP riders
│   │   ├── tracks.json            # MotoGP circuits around the world
│   │   └── {year}/
│   │       ├── schedule.json      # Season schedule with sessions[] (FP, Q1, Q2, Sprint, Warm-Up, Race per class)
│   │       └── {event_short_name}/
│   │               ├── motogp_RAC.json # Main Grand Prix Race results
│   │               └── motogp_SPR.json # Sprint Race results (if applicable)
│   ├── nascar/
│   │   ├── drivers.json           # Active and historical NASCAR drivers
│   │   ├── tracks.json            # NASCAR tracks around the world
│   │   └── {year}/
│   │       ├── schedule.json      # Season schedule (Cup, Xfinity, Truck)
│   │       └── {series_name}/
│   │           └── results_{race_id}.json # Race results (e.g. cup, xfinity, truck)
│   ├── indycar/
│   │   └── {year}/
│   │       ├── schedule.json      # Season schedule
│   │       └── results_{event_id}.json # Race results
│   └── wec/
│       └── {year}/
│           ├── schedule.json      # WEC season schedule
│           ├── results.json       # WEC Wikipedia scraped results
│           └── standings.json     # Compiled WEC standings
│   ├── formula_e/
│   │   └── {year}/
│   │       ├── schedule.json      # Formula E season schedule
│   │       └── results.json       # Wikipedia scraped FE results
│   └── wrc/
│       └── {year}/
│           ├── schedule.json      # WRC season schedule
│           └── results.json       # Wikipedia scraped WRC results
├── scripts/
│   ├── scrape_f1.py               # Python scraper for F1 (Jolpica)
│   ├── scrape_motogp.py           # Python scraper for MotoGP (Pulse Live API)
│   ├── scrape_nascar.py           # Python scraper for NASCAR (Cup/Xfinity/Truck)
│   ├── scrape_indycar.py          # Python scraper for IndyCar (ESPN Scoreboard)
│   ├── scrape_wec.py              # Python scraper for WEC (fiawec.com LD-JSON)
│   ├── scrape_formula_e.py        # Python scraper for Formula E (Wiki HTML Tables)
│   ├── scrape_wrc.py              # Python scraper for WRC (Wiki HTML Tables)
│   └── generate_sessions.py       # Populates sessions[] in all schedule.json files
└── .github/workflows/
    ├── scrape_f1.yml              # Daily scraping workflow for F1
    ├── scrape_motogp.yml          # Daily scraping workflow for MotoGP
    ├── scrape_nascar.yml          # Daily scraping workflow for NASCAR
    ├── scrape_indycar.yml         # Daily scraping workflow for IndyCar
    ├── scrape_wec.yml             # Daily scraping workflow for WEC
    ├── scrape_formula_e.yml       # Daily scraping workflow for Formula E
    └── scrape_wrc.yml             # Weekly scraping workflow for WRC
```

---

## 💻 Local Setup & Development

The scrapers are lightweight Python 3 scripts that run without external dependencies (no `requests` or `BeautifulSoup` required) by utilizing Python's native modules like `urllib`.

### 1. Clone the repository
```bash
git clone https://github.com/vishwapramuditha/moto-db.git
cd moto-db
```

### 2. Run the Scrapers
#### Formula 1
By default, F1 pulls data for the current and previous year:
```bash
python scripts/scrape_f1.py
```
To scrape specific F1 years:
```bash
python scripts/scrape_f1.py --years 2024,2025
```

#### MotoGP
By default, MotoGP pulls data for the current year:
```bash
python scripts/scrape_motogp.py
```
To scrape specific MotoGP years:
```bash
python scripts/scrape_motogp.py --years 2024,2025
```

#### NASCAR
By default, NASCAR pulls data for the current year:
```bash
python scripts/scrape_nascar.py
```
To scrape specific NASCAR years:
```bash
python scripts/scrape_nascar.py --years 2024,2025
```

#### IndyCar
By default, IndyCar pulls data for the current year:
```bash
python scripts/scrape_indycar.py
```
To scrape specific IndyCar years:
```bash
python scripts/scrape_indycar.py --years 2024,2025
```

#### WEC
By default, WEC pulls data for the current and previous year:
```bash
python scripts/scrape_wec.py
```
To scrape specific WEC years:
```bash
python scripts/scrape_wec.py --years 2025,2026
```

#### Formula E
To scrape a specific Formula E year (e.g., 2024-2025 season):
```bash
python scripts/scrape_formula_e.py --year 2025
```

#### WRC
By default, WRC pulls data for the current and previous year:
```bash
python scripts/scrape_wrc.py
```
To scrape specific WRC years:
```bash
python scripts/scrape_wrc.py --years 2024,2025
```

### 3. Generate Session Schedules

All `schedule.json` files contain a `sessions[]` array listing every on-track event in the race week (practices, qualifying, sprint, race) with accurate UTC times. Run `generate_sessions.py` after scraping to refresh the session data:

```bash
# Regenerate session schedules for all sports
python scripts/generate_sessions.py --sports f1,motogp,indycar,wrc,formula_e --years 2025,2026

# Refresh MotoGP only (fetches live times from Pulse Live API)
python scripts/generate_sessions.py --sports motogp --years 2026
```

**Session schema** (used in `schedule.json` for all sports):
```json
"sessions": [
  { "type": "FP1",        "name": "Free Practice 1", "date": "2026-03-06", "time": "01:30:00Z" },
  { "type": "FP2",        "name": "Free Practice 2", "date": "2026-03-06", "time": "05:00:00Z" },
  { "type": "FP3",        "name": "Free Practice 3", "date": "2026-03-07", "time": "01:30:00Z" },
  { "type": "Qualifying", "name": "Qualifying",       "date": "2026-03-07", "time": "05:00:00Z" },
  { "type": "Race",       "name": "Race",             "date": "2026-03-08", "time": "04:00:00Z" }
]
```

**Sprint weekend sessions** (F1):
`FP1 → Sprint Qualifying (SQ) → Sprint → Qualifying → Race`

**MotoGP weekend sessions** (per class — MotoGP, Moto2, Moto3):
`FP → Practice → Q1 → Q2 → Sprint Race (MotoGP only) → Warm-Up → Race`

**WRC rally sessions**:
`Shakedown → Day 1 Super Special Stage → Friday Stages → Saturday Stages → Sunday Power Stage`

---

## 🛣️ Roadmap: All Motorsports 🏍️🏎️

*   [x] **Formula 1** (Complete - powered by Jolpica-F1 / Ergast API successor)
*   [x] **MotoGP** (Complete - powered by Pulse Live MotoGP API)
*   [x] **NASCAR** (Complete - powered by NASCAR cacher API)
*   [x] **IndyCar** (Complete - powered by ESPN IRL scoreboard API)
*   [x] **WEC** (Complete - Schedule via fiawec.com, Results/Standings via Wiki table parsing)
*   [x] **Formula E** (Complete - Wiki HTML table parsing)
*   [x] **World Rally Championship (WRC)** (Complete - Wiki HTML table parsing)

Contributions are highly encouraged! If you want to build a scraper for WRC, integrate a new series, or correct data typos, feel free to open a Pull Request.

---

## ⚖️ Disclaimer

This is a community-driven, unofficial open-source project. It is **not** associated with, affiliated with, or endorsed by Formula One World Championship Limited, MotoGP/Dorna Sports, NASCAR, IndyCar, or any other motorsport organization. All trademarks are the property of their respective owners. Data is gathered from public sources for non-commercial educational purposes only.
