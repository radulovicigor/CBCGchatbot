"""
Automatski scheduler za dnevno skrejpovanje cbcg.me.
Koristi APScheduler za planning.
"""
import sys
from pathlib import Path
from datetime import datetime

# Add root to path
sys.path.insert(0, str(Path(__file__).parent))

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import time

from apps.functions.local_scraper import scrape_cbcg


def run_scraper():
    """Pokreni scraper i logiraj rezultat."""
    print(f"\n[{datetime.now()}] Running daily scraper...")
    try:
        count = scrape_cbcg()
        print(f"[{datetime.now()}] ✓ Scraping complete: {count} articles")
    except Exception as e:
        print(f"[{datetime.now()}] ✗ Scraping failed: {e}")


def main():
    """Pokreni scheduler."""
    print("Starting CBCG scraper scheduler...")
    print("Will run daily at 2 AM")
    
    scheduler = BackgroundScheduler()
    
    # Pokreni svaki dan u 2:00 AM
    scheduler.add_job(
        run_scraper,
        trigger=CronTrigger(hour=2, minute=0),
        id='daily_cbcg_scraper',
        name='Daily CBCG.me scraper',
        replace_existing=True
    )
    
    # OPCIJONO: Pokreni i sada (za test)
    print("\nRunning initial scrape now...")
    run_scraper()
    
    scheduler.start()
    
    try:
        print("\nScheduler running. Press Ctrl+C to stop.")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping scheduler...")
        scheduler.shutdown()


if __name__ == "__main__":
    main()

