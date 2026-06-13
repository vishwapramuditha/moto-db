# Moto-DB 🏎️🏍️🏁

An open-source, developer-friendly database of schedules, race results, driver profiles, and track metadata for major motorsports—hosted entirely on GitHub and accessible for **$0** in hosting costs.

The goal of this project is to provide a clean, structured JSON API that developers can use to build dashboards, mobile apps, statistics sites, or calendar integrations without managing database servers.

---

## 🛠️ Architecture: Git-as-a-Database

Instead of hosting a database server (which has cost limits and maintenance overhead), this project uses GitHub as the primary data store. 

1. **Automation**: GitHub Actions runs Python scrapers periodically (e.g. after race weekends).
2. **Data Model**: Clean, formatted JSON files are committed directly into the repository.
3. **CDN Access**: Developers query the JSON files directly via a free CDN like `jsDelivr`, which offers fast response times, global caching, and unlimited scaling.

---

## 🚀 How to use the API (jsDelivr CDN)

You can query the files in this repository directly in your apps using standard HTTP requests:

### Global Metadata

*   **F1 Drivers**:
    `https://cdn.jsdelivr.net/gh/vishwapramuditha/moto-db@main/data/f1/drivers.json`
*   **F1 Circuits**:
    `https://cdn.jsdelivr.net/gh/vishwapramuditha/moto-db@main/data/f1/tracks.json`
*   **MotoGP Riders**:
    `https://cdn.jsdelivr.net/gh/vishwapramuditha/moto-db@main/data/motogp/drivers.json`
*   **MotoGP Circuits**:
    `https://cdn.jsdelivr.net/gh/vishwapramuditha/moto-db@main/data/motogp/tracks.json`

### Season & Race Data

*   **F1 Schedule (e.g., 2025)**:
    `https://cdn.jsdelivr.net/gh/vishwapramuditha/moto-db@main/data/f1/2025/schedule.json`
*   **F1 Round Results (e.g., 2025 Round 1)**:
    `https://cdn.jsdelivr.net/gh/vishwapramuditha/moto-db@main/data/f1/2025/results_1.json`
*   **MotoGP Schedule (e.g., 2025)**:
    `https://cdn.jsdelivr.net/gh/vishwapramuditha/moto-db@main/data/motogp/2025/schedule.json`
*   **MotoGP Race Results (e.g., 2025 Thailand GP MotoGP Main Race)**:
    `https://cdn.jsdelivr.net/gh/vishwapramuditha/moto-db@main/data/motogp/2025/THA/motogp_RAC.json`

*(Replace `main` with a specific commit hash or release tag in production to prevent unexpected layout changes if the schemas evolve).*

---

## 📁 Repository Structure

All data is structured in folders categorized by motorsport and year:

```text
moto-db/
├── data/
│   ├── f1/
│   │   ├── drivers.json           # Active and historical F1 drivers
│   │   ├── tracks.json            # F1 circuits around the world
│   │   └── {year}/
│   │       ├── schedule.json      # Full season schedule
│   │       └── results_{round}.json
│   └── motogp/
│       ├── drivers.json           # Active and historical MotoGP riders
│       ├── tracks.json            # MotoGP circuits around the world
│       └── {year}/
│           ├── schedule.json      # Season schedule
│           └── {event_short_name}/
│               ├── motogp_RAC.json # Main Grand Prix Race results
│               └── motogp_SPR.json # Sprint Race results (if applicable)
├── scripts/
│   ├── scrape_f1.py               # Python scraper for F1
│   └── scrape_motogp.py           # Python scraper for MotoGP
└── .github/workflows/
    ├── scrape_f1.yml              # Automated scraping action for F1
    └── scrape_motogp.yml          # Automated scraping action for MotoGP
```

---

## 💻 Local Setup & Development

To run the scrapers locally, you only need Python 3 installed. No external packages (like `requests`) are needed as the scripts use Python's built-in `urllib` module.

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

---

## 🛣️ Roadmap: All Motorsports 🏍️🏎️

We support:
- [x] **Formula 1** (Complete - powered by Jolpica-F1 / Ergast API successor)
- [x] **MotoGP** (Complete - powered by Pulse Live MotoGP API)
- [ ] **NASCAR** (Schedules and results)
- [ ] **IndyCar** (Schedules and results)
- [ ] **Formula E & WEC** (Schedules, team sheets, results)

Contributions are welcome! If you want to write a scraper or fix a typo, feel free to open a Pull Request.

---

## ⚖️ Disclaimer

This is a community-driven, unofficial open-source project. It is **not** associated with, affiliated with, or endorsed by Formula One World Championship Limited, MotoGP/Dorna Sports, NASCAR, IndyCar, or any other motorsport organization. All trademarks are the property of their respective owners. Data is gathered from public sources for non-commercial educational purposes only.
