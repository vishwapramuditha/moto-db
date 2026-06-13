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

*   **F1 Drivers List**:
    `https://cdn.jsdelivr.net/gh/vishwapramuditha/moto-db@main/data/f1/drivers.json`
*   **F1 Circuits / Tracks List**:
    `https://cdn.jsdelivr.net/gh/vishwapramuditha/moto-db@main/data/f1/tracks.json`

### Season & Race Data

*   **F1 Schedule (e.g., 2025)**:
    `https://cdn.jsdelivr.net/gh/vishwapramuditha/moto-db@main/data/f1/2025/schedule.json`
*   **F1 Round Results (e.g., 2025 Round 1)**:
    `https://cdn.jsdelivr.net/gh/vishwapramuditha/moto-db@main/data/f1/2025/results_1.json`

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
│   │       ├── schedule.json      # Full season schedule (dates, times, rounds)
│   │       ├── results_1.json     # Race results for Round 1
│   │       └── results_2.json     # Race results for Round 2
├── scripts/
│   └── scrape_f1.py               # Python crawler script
└── .github/workflows/
    └── scrape_f1.yml              # Automated scraping action
```

---

## 💻 Local Setup & Development

To run the scrapers locally, you only need Python 3 installed. No external packages (like `requests`) are needed as the scripts use Python's built-in `urllib` module.

### 1. Clone the repository
```bash
git clone https://github.com/vishwapramuditha/moto-db.git
cd moto-db
```

### 2. Run the F1 Scraper
By default, the scraper pulls data for the current and previous year to minimize API loads:
```bash
python scripts/scrape_f1.py
```

To scrape specific years:
```bash
python scripts/scrape_f1.py --years 2024,2025
```

To scrape all historical data from 1950 to the present:
```bash
python scripts/scrape_f1.py --all-time
```

---

## 🛣️ Roadmap: All Motorsports 🏍️🏎️

We started with **Formula 1**, but the road map includes adding other professional motorsport categories:
- [ ] **Formula 1** (Complete - powered by Jolpica-F1 / Ergast API)
- [ ] **NASCAR** (Schedules, results, standings)
- [ ] **MotoGP** (Driver bios, tracks, results)
- [ ] **IndyCar** (Schedules and results)
- [ ] **Formula E & WEC** (Schedules, team sheets, results)

Contributions are welcome! If you want to write a scraper or fix a typo, feel free to open a Pull Request.

---

## ⚖️ Disclaimer

This is a community-driven, unofficial open-source project. It is **not** associated with, affiliated with, or endorsed by Formula One World Championship Limited, MotoGP/Dorna Sports, NASCAR, IndyCar, or any other motorsport organization. All trademarks are the property of their respective owners. Data is gathered from public sources for non-commercial educational purposes only.
