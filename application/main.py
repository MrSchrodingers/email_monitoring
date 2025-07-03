import argparse
from adapters.graph.graph_api_client import GraphApiClient
from adapters.repository.sql_email_repository import PgEmailRepository
from adapters.scheduling.cron_scheduler import CronScheduler
from application.usecase.fetch_and_store_metrics import FetchAndStoreMetrics
from domain.service.email_metrics_service import EmailMetricsService
from config.settings import DB_URL
from config.logging import configure_logging
configure_logging()  

import structlog  # noqa: E402
logger = structlog.get_logger(__name__)

def make_job():
    logger.info("boot.make_job")
    
    graph_client    = GraphApiClient()
    email_repo      = PgEmailRepository(DB_URL)
    metrics_repo    = email_repo
    metrics_service = EmailMetricsService(graph_client)
    return FetchAndStoreMetrics(graph_client, email_repo, metrics_repo, metrics_service)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--once",
        action="store_true",
        help="Executa apenas uma vez e sai (sem scheduler)."
    )
    args = parser.parse_args()

    job = make_job()

    if args.once:
        job.execute()
    else:
        scheduler = CronScheduler(job)
        scheduler.start()
