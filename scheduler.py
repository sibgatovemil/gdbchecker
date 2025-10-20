"""Background scheduler for periodic domain checks"""

import os
import logging
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.interval import IntervalTrigger
from checker import DomainChecker
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def run_check():
    """Run domain check"""
    logger.info("=" * 60)
    logger.info("Starting scheduled domain check...")
    logger.info("=" * 60)

    try:
        checker = DomainChecker()
        checker.check_all_domains()
        logger.info("Scheduled check completed successfully")
    except Exception as e:
        logger.error(f"Error in scheduled check: {str(e)}")


if __name__ == '__main__':
    check_interval_hours = int(os.getenv('CHECK_INTERVAL_HOURS', 8))

    logger.info(f"Starting GDBChecker Scheduler (check interval: {check_interval_hours} hours)")
    logger.info(f"Current time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")

    # Run initial check
    logger.info("Running initial domain check...")
    run_check()

    # Setup scheduler
    scheduler = BlockingScheduler()
    scheduler.add_job(
        run_check,
        trigger=IntervalTrigger(hours=check_interval_hours),
        id='domain_check',
        name='Check all domains',
        replace_existing=True
    )

    try:
        logger.info(f"Scheduler started. Next check in {check_interval_hours} hours.")
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Scheduler stopped by user")
        scheduler.shutdown()
