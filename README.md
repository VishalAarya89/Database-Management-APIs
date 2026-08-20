# 🌤️ Weather Data Pipeline System

An end-to-end data engineering pipeline that extracts real-time weather data from the OpenWeatherMap API, validates and transforms it, loads it into a normalized SQLite database, and produces automated reports, alerts, and health monitoring.

Built as Task 3 (Month 3: Database Management & APIs) — Standard/Advanced tier: multiple cities on a scheduled collection loop, with threshold-based alerting and a health-check endpoint.

![Tests passing](assets/screenshot_tests.png)

## 1. Project Overview & Objectives

Manual weather tracking doesn't scale past a handful of cities, and one-off API calls give you a snapshot with no history. This project turns raw OpenWeatherMap responses into a queryable, monitored dataset by:

- Collecting current weather for a configurable list of cities on a recurring schedule
- Cleaning and validating every reading before it reaches the database
- Storing readings in a normalized SQLite schema (4 tables) with a full audit trail of every pipeline run
- Raising alerts when temperature, humidity, or wind exceed configured thresholds
- Answering historical questions (trends, correlations, extremes, peak hours) via a query layer
- Reporting system health so failures are visible instead of silent

## 2. Architecture

```
                 ┌─────────────────────┐
                 │  OpenWeatherMap API  │
                 └──────────┬───────────┘
                             │  api_client.py (retries, timeouts, error handling)
                             ▼
                 ┌─────────────────────┐
                 │   etl_pipeline.py    │   Extract → Transform → Load
                 │  (per-city, isolated  │
                 │   failure handling)   │
                 └──────────┬───────────┘
             validators.py  │  monitor.py (threshold checks)
                             ▼
                 ┌───────────────────────┐
                 │  SQLite (database.py) │  cities / weather_data /
                 │  weather_data.db      │  alerts / pipeline_runs
                 └──────────┬────────────┘
              ┌─────────────┼─────────────┐
              ▼             ▼             ▼
        reporter.py   scripts/analysis   monitor.py
        (snapshot      _demo.py          (--health)
         reports)      (query system)
              │
              ▼
       scheduler.py (recurring interval loop, graceful shutdown)
```

See `docs/ARCHITECTURE.md` for a fuller walkthrough of each component.

## 3. Setup & Installation

```bash
# 1. Clone and enter the project
git clone <your-repo-url>
cd weather-pipeline

# 2. Create a virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure your API key
cp .env.example .env
# Edit .env and set OPENWEATHER_API_KEY=<your key from openweathermap.org/api>

# 5. Initialize the database
python main.py --setup-db

# 6. Run one collection cycle
python main.py --run-once
```

No API key yet, or no network access? Every command supports `--demo`, which swaps in a realistic offline data generator (`src/mock_data.py`) so you can exercise the full pipeline immediately:

```bash
python main.py --run-once --demo
python main.py --backfill --demo --days 30      # generate 30 days of history
python main.py --report
python main.py --health
```

Full step-by-step instructions: `docs/SETUP.md`.

## 4. Usage

| Command | What it does |
|---|---|
| `python main.py --setup-db` | Create/verify the database schema |
| `python main.py --run-once` | Run a single ETL cycle against the live API |
| `python main.py --run-once --demo` | Run a single ETL cycle with offline mock data |
| `python main.py --backfill --demo --days 30` | Generate 30 days of synthetic history |
| `python main.py --schedule` | Start the recurring collection loop (live API) |
| `python main.py --schedule --demo --cycles 3` | Run the scheduler for 3 cycles (demo) |
| `python main.py --report` | Generate a snapshot report to `reports/` |
| `python main.py --health` | Print a JSON health-check summary |
| `python scripts/analysis_demo.py` | Answer the project's analysis questions from the DB |

## 5. Code Structure

```
weather-pipeline/
├── main.py                  # CLI entry point
├── src/
│   ├── config.py             # Environment-driven configuration
│   ├── logger_setup.py       # Shared logging configuration
│   ├── database.py           # Schema, connections, CRUD, analytics queries
│   ├── api_client.py         # OpenWeatherMap client (retries, error handling)
│   ├── mock_data.py          # Offline data generator (demo/testing only)
│   ├── validators.py         # Data quality checks
│   ├── etl_pipeline.py       # Extract → Transform → Load orchestration
│   ├── monitor.py            # Alert thresholds + health checks
│   ├── scheduler.py          # Recurring interval scheduler
│   └── reporter.py           # Snapshot report generation
├── scripts/
│   └── analysis_demo.py      # Demonstrates the historical query system
├── tests/                    # unittest suite (18 tests, see docs/TESTING.md)
├── config/
│   └── .env.example          # Configuration template
├── database/                 # SQLite file lives here (gitignored)
├── docs/                     # Full documentation set (see below)
├── logs/                     # Rotating log files (gitignored)
├── reports/                  # Generated snapshot reports (gitignored)
└── assets/                   # ER diagram, screenshots
```

## 6. Database Schema

4 normalized tables: `cities` → `weather_data` (1:N), `cities` → `alerts` (1:N), plus `pipeline_runs` as an independent audit log. Full details and ER diagram: `docs/DATABASE_SCHEMA.md`.

![ER Diagram](assets/er_diagram.png)

## 7. How This Meets the Technical Requirements

| Requirement | Where it's implemented |
|---|---|
| SQLite database, 3+ normalized tables | `src/database.py` — 4 tables (`cities`, `weather_data`, `alerts`, `pipeline_runs`), FK-linked, indexed |
| API client for OpenWeatherMap | `src/api_client.py` — real HTTP integration with timeouts, retries, structured errors |
| Complete ETL pipeline with error handling & logging | `src/etl_pipeline.py` + `src/logger_setup.py` — per-city isolation, full audit trail |
| Data validation / quality assurance | `src/validators.py` — range checks on every numeric field before load |
| Automated scheduling | `src/scheduler.py` — interval loop with graceful shutdown |
| Historical query system | `src/database.py` analytics functions + `scripts/analysis_demo.py` |
| Automated reports and alerts | `src/reporter.py`, `src/monitor.py` (threshold-based alerts written to `alerts` table) |
| Monitoring / health checks | `src/monitor.py::health_check()`, exposed via `python main.py --health` |

## 8. Analysis Questions — Answered

Run `python scripts/analysis_demo.py` after backfilling data. See `docs/ANALYSIS.md` for the methodology and sample output for all five questions (highest average temperature, 30-day trends, humidity/condition correlation, most extreme cities, peak temperature hour).

## 9. Testing

18 unit/integration tests across validators, database, and the API client (HTTP mocked — no network required). See `docs/TESTING.md`.

```bash
python -m unittest discover -s tests -v
```

## 10. Project Options Implemented

This build targets **Option 3 (Advanced): real-time monitoring with alerts**, layered on top of Option 2's multi-city scheduled collection — the multi-database / cloud-deployment scope of Option 4 is intentionally out of scope. See `docs/DEPLOYMENT.md` for how to extend toward it.

## License

Built for educational/coursework submission.
