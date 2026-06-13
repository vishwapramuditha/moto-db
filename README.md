# MotoDB - Data for every motorsport

<p align="center">
  <img src="website/public/hero-car.svg" alt="Moto-DB F1 Dotted Car Banner" width="480">
</p>

An open-source, developer-friendly database of schedules, race results, driver profiles, and track metadata for major motorsports—hosted entirely on GitHub and accessible for **$0** in hosting costs with infinite scale.

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
*   **Formula E Schedule (e.g. 2025)**:
    `https://cdn.jsdelivr.net/gh/vishwapramuditha/moto-db@main/data/formula_e/2025/schedule.json`
*   **Formula E Results (e.g. 2025)**:
    `https://cdn.jsdelivr.net/gh/vishwapramuditha/moto-db@main/data/formula_e/2025/results.json`

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
│   │       ├── schedule.json      # Full season schedule
│   │       └── results_{round}.json
│   ├── motogp/
│   │   ├── drivers.json           # Active and historical MotoGP riders
│   │   ├── tracks.json            # MotoGP circuits around the world
│   │   └── {year}/
│   │       ├── schedule.json      # Season schedule
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
│           └── schedule.json      # WEC season schedule
│   └── formula_e/
│       └── {year}/
│           ├── schedule.json      # Formula E season schedule
│           └── results.json       # Wikipedia scraped FE results
├── scripts/
│   ├── scrape_f1.py               # Python scraper for F1 (Jolpica)
│   ├── scrape_motogp.py           # Python scraper for MotoGP (Pulse Live API)
│   ├── scrape_nascar.py           # Python scraper for NASCAR (Cup/Xfinity/Truck)
│   ├── scrape_indycar.py          # Python scraper for IndyCar (ESPN Scoreboard)
│   ├── scrape_wec.py              # Python scraper for WEC (fiawec.com LD-JSON)
│   └── scrape_formula_e.py        # Python scraper for Formula E (Wiki HTML Tables)
└── .github/workflows/
    ├── scrape_f1.yml              # Daily scraping workflow for F1
    ├── scrape_motogp.yml          # Daily scraping workflow for MotoGP
    ├── scrape_nascar.yml          # Daily scraping workflow for NASCAR
    ├── scrape_indycar.yml         # Daily scraping workflow for IndyCar
    ├── scrape_wec.yml             # Daily scraping workflow for WEC
    └── scrape_formula_e.yml       # Daily scraping workflow for Formula E
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

---

## 🛣️ Roadmap: All Motorsports 🏍️🏎️

*   [x] **Formula 1** (Complete - powered by Jolpica-F1 / Ergast API successor)
*   [x] **MotoGP** (Complete - powered by Pulse Live MotoGP API)
*   [x] **NASCAR** (Complete - powered by NASCAR cacher API)
*   [x] **IndyCar** (Complete - powered by ESPN IRL scoreboard API)
*   [x] **WEC** (Partial - Schedule only, powered by fiawec.com JSON-LD)
*   [x] **Formula E** (Complete - Wiki HTML table parsing)
*   [ ] **World Rally Championship (WRC)** (Upcoming integration)

Contributions are highly encouraged! If you want to build a scraper for WRC, integrate a new series, or correct data typos, feel free to open a Pull Request.

---

## ⚖️ Disclaimer

This is a community-driven, unofficial open-source project. It is **not** associated with, affiliated with, or endorsed by Formula One World Championship Limited, MotoGP/Dorna Sports, NASCAR, IndyCar, or any other motorsport organization. All trademarks are the property of their respective owners. Data is gathered from public sources for non-commercial educational purposes only.
