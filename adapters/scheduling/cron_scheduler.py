import schedule
import time
from ports.scheduler import SchedulerPort
from application.usecase.fetch_and_store_metrics import FetchAndStoreMetrics
import structlog
logger = structlog.get_logger(__name__)

class CronScheduler(SchedulerPort):
    def __init__(self, job: FetchAndStoreMetrics):
        self.job = job

    def start(self):
        # Executa todo dia, às 02:00 AM
        logger.info("cron.tick")
        schedule.every().day.at("02:00").do(self.job.execute)
        while True:
            schedule.run_pending()
            time.sleep(30)
