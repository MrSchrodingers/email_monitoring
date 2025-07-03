from dataclasses import asdict
from typing import List
from sqlalchemy import create_engine, Column, String, Integer, DateTime, Boolean, Date, inspect
from sqlalchemy.orm import declarative_base, sessionmaker
from ports.persistence import EmailRepositoryPort, MetricsRepositoryPort
from domain.model.email import Email
from domain.model.metrics import EmailMetrics
from sqlalchemy.dialects.postgresql import insert
import structlog

logger = structlog.get_logger(__name__)
Base = declarative_base()

class EmailORM(Base):
    __tablename__ = "emails"

    id              = Column(String, primary_key=True)
    message_id      = Column(String)
    subject         = Column(String)
    sent_datetime   = Column(DateTime)
    is_read         = Column(Boolean, index=True)
    conversation_id = Column(String)
    has_attachments = Column(Boolean, index=True)

    is_bounced = Column(Boolean, default=False, nullable=False, index=True)
    is_replied = Column(Boolean, default=False, nullable=False, index=True)

class MetricsORM(Base):
    __tablename__ = "metrics"

    date            = Column(Date, primary_key=True)
    total_sent      = Column(Integer, nullable=False)
    total_delivered = Column(Integer, nullable=False)
    total_bounced   = Column(Integer, nullable=False)
    total_replied   = Column(Integer, nullable=False)
    total_no_reply  = Column(Integer, nullable=False)

    delivery_rate   = Column(Integer, nullable=False)   # armazenamos ×10 000 (permite inteiro)
    reply_rate      = Column(Integer, nullable=False)   # idem

class PgEmailRepository(EmailRepositoryPort, MetricsRepositoryPort):
    def __init__(self, db_url: str):
        self.engine = create_engine(db_url)
        self.Session = sessionmaker(bind=self.engine)
        self._ensure_tables()

    def list_bounced(self) -> List[EmailORM]:
        with self.Session() as s:
            return (
                s.query(EmailORM)
                .filter(EmailORM.is_bounced.is_(True))
                .order_by(EmailORM.sent_datetime.desc())
                .all()
            )
        
    def _ensure_tables(self):
        # Só cria se não existir
        inspector = inspect(self.engine)
        tables = inspector.get_table_names()
        if "emails" not in tables or "metrics" not in tables:
            Base.metadata.create_all(self.engine)

    def save_all(self, emails: List[Email]):
        log = logger.bind(total=len(emails))
        session = self.Session()
        try:
            for e in emails:
                email_orm = EmailORM(
                    id=str(e.id),
                    message_id=e.message_id,
                    subject=e.subject,
                    sent_datetime=e.sent_datetime,
                    is_read=bool(e.is_read),
                    conversation_id=e.conversation_id,
                    has_attachments=bool(e.has_attachments),
                    is_bounced=getattr(e, "is_bounced", False),
                    is_replied=getattr(e, "is_replied", False),
                )
                # UPSERT para Postgres
                session.merge(email_orm)
            session.commit()
            log.info("email_repo.save_all.success")
        except Exception:
            log.exception("email_repo.save_all.error")
            raise
        finally:
            session.close()

    def save(self, metrics: EmailMetrics) -> None:
        log = logger.bind(date=str(metrics.date))
        session = self.Session()

        try:
            stmt = insert(MetricsORM).values(
                date=metrics.date,
                total_sent=metrics.total_sent,
                total_delivered=metrics.total_delivered,
                total_bounced=metrics.total_bounced,
                total_replied=metrics.total_replied,
                total_no_reply=metrics.total_no_reply,
                delivery_rate=int(metrics.delivery_rate * 10_000),
                reply_rate=int(metrics.reply_rate * 10_000),
            ).on_conflict_do_update(
                index_elements=[MetricsORM.date],
                set_={
                    "total_sent":      metrics.total_sent,
                    "total_delivered": metrics.total_delivered,
                    "total_bounced":   metrics.total_bounced,
                    "total_replied":   metrics.total_replied,
                    "total_no_reply":  metrics.total_no_reply,
                    "delivery_rate":   int(metrics.delivery_rate * 10_000),
                    "reply_rate":      int(metrics.reply_rate * 10_000),
                },
            )

            session.execute(stmt)
            session.commit()
            log.info("metrics_repo.save.success", **asdict(metrics))

        except Exception:
            log.exception("metrics_repo.save.error")
            session.rollback()
            raise

        finally:
            session.close()