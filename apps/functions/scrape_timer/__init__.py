"""
Azure Functions Timer trigger za scraping cbcg.me.
"""
import azure.functions as func
import logging
from .scraper import run_scrape
import os
from dotenv import load_dotenv

load_dotenv()

app = func.FunctionApp()


@app.function_name(name="scrape_timer")
@app.schedule(
    schedule=os.environ.get("SCRAPER_CRON", "0 30 3 * * *"),
    arg_name="mytimer",
    run_on_startup=False,
    use_monitor=True
)
def main(mytimer: func.TimerRequest) -> None:
    logging.info("CBCG scrape started")
    try:
        run_scrape()
        logging.info("CBCG scrape completed successfully")
    except Exception as e:
        logging.error(f"CBCG scrape failed: {e}", exc_info=True)
        raise

