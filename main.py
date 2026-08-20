"""
main.py
-------
Command-line entry point for the Weather Data Pipeline System.

Usage:
    python main.py --setup-db                 Create/verify the database schema
    python main.py --run-once                 Run one ETL cycle (live API)
    python main.py --run-once --demo          Run one ETL cycle (offline mock data)
    python main.py --backfill --demo --days 30  Backfill N days of demo history
    python main.py --schedule                  Start the recurring scheduler (live API)
    python main.py --schedule --demo --cycles 3  Run scheduler for N cycles (demo)
    python main.py --report                    Generate a snapshot report
    python main.py --health                    Print a health-check summary
"""

import argparse
import json
import sys

from src.config import Config
from src.database import setup_database
from src.etl_pipeline import run_pipeline
from src.scheduler import start_scheduler
from src.reporter import generate_daily_report, build_report_text
from src.monitor import health_check
from src.logger_setup import get_logger

logger = get_logger("main")


def get_client(demo: bool):
    if demo:
        from src.mock_data import MockWeatherAPIClient
        return MockWeatherAPIClient()
    from src.api_client import WeatherAPIClient
    return WeatherAPIClient()


def cmd_backfill(days: int, demo: bool):
    if not demo:
        print("Backfill currently supports --demo mode only (synthetic history).")
        sys.exit(1)
    from src.mock_data import generate_historical_backfill
    from src.etl_pipeline import transform, load

    records = generate_historical_backfill(Config.CITIES, days=days)
    inserted = 0
    for raw in records:
        clean, errors = transform(raw)
        if clean:
            if load(clean):
                inserted += 1
    print(f"Backfill complete: {inserted} historical records inserted "
          f"across {len(Config.CITIES)} cities over {days} days.")


def main():
    parser = argparse.ArgumentParser(description="Weather Data Pipeline System")
    parser.add_argument("--setup-db", action="store_true", help="Create/verify database schema")
    parser.add_argument("--run-once", action="store_true", help="Run a single ETL cycle")
    parser.add_argument("--schedule", action="store_true", help="Start the recurring scheduler")
    parser.add_argument("--backfill", action="store_true", help="Backfill historical demo data")
    parser.add_argument("--report", action="store_true", help="Generate a snapshot report")
    parser.add_argument("--health", action="store_true", help="Print a health-check summary")
    parser.add_argument("--demo", action="store_true", help="Use offline synthetic data instead of the live API")
    parser.add_argument("--days", type=int, default=30, help="Days of history for --backfill")
    parser.add_argument("--cycles", type=int, default=None, help="Limit --schedule to N cycles (testing)")
    parser.add_argument("--interval", type=int, default=None, help="Override collection interval (minutes)")
    args = parser.parse_args()

    if args.setup_db:
        setup_database()
        print(f"Database ready at {Config.DB_PATH}")

    if args.backfill:
        setup_database()
        cmd_backfill(args.days, args.demo)

    if args.run_once:
        setup_database()
        client = get_client(args.demo)
        summary = run_pipeline(Config.CITIES, client=client)
        print(json.dumps(summary, indent=2))

    if args.schedule:
        setup_database()
        if args.demo:
            import src.scheduler as sched_mod
            from src.mock_data import MockWeatherAPIClient
            from src.etl_pipeline import run_pipeline as _rp

            def _demo_run_pipeline(cities, client=None):
                return _rp(cities, client=MockWeatherAPIClient())
            sched_mod.run_pipeline = _demo_run_pipeline
        start_scheduler(interval_minutes=args.interval or 1, max_cycles=args.cycles)

    if args.report:
        setup_database()
        path = generate_daily_report()
        print(f"Report written to: {path}")
        print()
        print(build_report_text())

    if args.health:
        setup_database()
        print(json.dumps(health_check(), indent=2))

    if not any(vars(args).values()):
        parser.print_help()


if __name__ == "__main__":
    main()
