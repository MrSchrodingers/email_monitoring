import os
import uuid
from typing import List, Dict

import structlog
from sqlalchemy import (
    Column, Float, Integer, String, DateTime, Boolean, Date,
    create_engine, select, Index, UniqueConstraint, func, ForeignKey,
)
from sqlalchemy.dialects.postgresql import insert as pg_insert, UUID, ARRAY
from sqlalchemy.orm import declarative_base, sessionmaker

from domain.model.email import Email
from domain.model.metrics import EmailMetrics
from ports.persistence import EmailRepositoryPort, MetricsRepositoryPort

logger = structlog.get_logger(__name__)
Base = declarative_base()
CHUNK_SIZE = int(os.getenv("BULK_CHUNK_SIZE", 300))

class AccountORM(Base):
    __tablename__ = "accounts"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email_address = Column(String, unique=True, nullable=False)

class EmailORM(Base):
    __tablename__ = "emails"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    recipient_addresses = Column(ARRAY(String), nullable=False)
    account_id = Column(UUID(as_uuid=True), ForeignKey("accounts.id"), nullable=False, index=True)
    message_id = Column(String, nullable=False)
    conversation_id = Column(String, nullable=False)
    subject = Column(String)
    sent_datetime = Column(DateTime)
    is_read = Column(Boolean)
    has_attachments = Column(Boolean)
    is_bounced = Column(Boolean, nullable=False, default=False)
    is_replied = Column(Boolean, nullable=False, default=False)
    importance = Column(String, nullable=True)
    internet_message_id = Column(String, nullable=True, index=True)
    is_read_receipt_requested = Column(Boolean, default=False)
    
    temperature_label = Column(String, nullable=False, default="frio")
    reply_latency_sec = Column(Float, nullable=True)
    engagement_score = Column(Integer, nullable=False, default=0)

    __table_args__ = (
        UniqueConstraint("account_id", "message_id", "conversation_id", name="uix_account_msg_conv"),
    )

class MetricsORM(Base):
    __tablename__ = "metrics"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_id = Column(UUID(as_uuid=True), ForeignKey("accounts.id"), nullable=False, index=True)
    run_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    date = Column(Date, index=True)

    # cleansed
    total_sent = Column(Integer, nullable=False)
    total_delivered = Column(Integer, nullable=False)
    total_bounced = Column(Integer, nullable=False)
    total_replied = Column(Integer, nullable=False)
    total_no_reply = Column(Integer, nullable=False)

    # raw
    raw_total_sent = Column(Integer, nullable=False)
    raw_total_delivered = Column(Integer, nullable=False)
    raw_total_bounced = Column(Integer, nullable=False)
    raw_total_replied = Column(Integer, nullable=False)
    raw_total_no_reply = Column(Integer, nullable=False)

    # aggregated
    delivery_rate = Column(Integer, nullable=False)
    reply_rate = Column(Integer, nullable=False)
    avg_reply_latency_sec = Column(Float, nullable=True)
    temperature_label = Column(String, nullable=False)

    __table_args__ = (
        Index("ix_metrics_acc_run_brin", "account_id", "run_at", postgresql_using="brin"),
    )

class PgEmailRepository(EmailRepositoryPort, MetricsRepositoryPort):
    def __init__(self, db_url: str):
        self.engine = create_engine(db_url)
        self.Session = sessionmaker(bind=self.engine, expire_on_commit=False)
        Base.metadata.create_all(self.engine)

    def save_all(self, account_email: str, emails: List[Email]) -> None:
        if not emails:
            logger.info("email_repo.save_all.skip", reason="empty_batch")
            return
        log = logger.bind(account=account_email, total=len(emails))
        session = self.Session()
        try:
            acc_id = self._ensure_account(session, account_email)
            for i in range(0, len(emails), CHUNK_SIZE):
                self._upsert_batch(session, acc_id, emails[i : i + CHUNK_SIZE])
            session.commit()
            log.info("email_repo.save_all.success")
        except Exception:
            session.rollback()
            log.exception("email_repo.save_all.error")
            raise
        finally:
            session.close()

    def save(self, metrics: EmailMetrics, account_email: str) -> None:
        session = self.Session()
        log = logger.bind(id=str(metrics.id), account=account_email)
        try:
            acc_id = self._ensure_account(session, account_email)
            session.add(
                MetricsORM(
                    id=metrics.id,
                    account_id=acc_id,
                    run_at=metrics.run_at,
                    date=metrics.date,
                    total_sent=metrics.total_sent,
                    total_delivered=metrics.total_delivered,
                    total_bounced=metrics.total_bounced,
                    total_replied=metrics.total_replied,
                    total_no_reply=metrics.total_no_reply,
                    raw_total_sent=metrics.raw_total_sent,
                    raw_total_delivered=metrics.raw_total_delivered,
                    raw_total_bounced=metrics.raw_total_bounced,
                    raw_total_replied=metrics.raw_total_replied,
                    raw_total_no_reply=metrics.raw_total_no_reply,
                    delivery_rate=int(metrics.delivery_rate * 10_000),
                    reply_rate=int(metrics.reply_rate * 10_000),
                    temperature_label=metrics.temperature_label,
                    avg_reply_latency_sec=metrics.avg_reply_latency_sec,
                )
            )
            session.commit()
            log.info("metrics_repo.insert.success")
        except Exception:
            session.rollback()
            log.exception("metrics_repo.insert.error")
            raise
        finally:
            session.close()

    def _ensure_account(self, session, email: str) -> uuid.UUID:
        stmt = (
            pg_insert(AccountORM)
            .values(id=uuid.uuid4(), email_address=email)
            .on_conflict_do_nothing()
            .returning(AccountORM.id)
        )
        acc_id = session.execute(stmt).scalar()
        if acc_id is None:
            acc_id = session.execute(
                select(AccountORM.id).where(AccountORM.email_address == email)
            ).scalar_one()
        return acc_id

    @staticmethod
    def _build_email_dict(acc_id: uuid.UUID, e: Email) -> Dict:
        return {
            "id": e.id,
            "recipient_addresses": e.to_addresses,
            "account_id": acc_id,
            "message_id": e.message_id,
            "conversation_id": e.conversation_id,
            "subject": e.subject,
            "sent_datetime": e.sent_datetime,
            "is_read": e.is_read,
            "has_attachments": e.has_attachments,
            "is_bounced": e.is_bounced,
            "is_replied": e.is_replied,
            "importance": e.importance,
            "internet_message_id": e.internet_message_id,
            "is_read_receipt_requested": e.is_read_receipt_requested,
            "reply_latency_sec": e.reply_latency_sec,
            "engagement_score": e.engagement_score,
            "temperature_label": e.temperature_label,
        }

    def _upsert_batch(self, session, acc_id: uuid.UUID, batch: List[Email]) -> None:
        insert_stmt = pg_insert(EmailORM).values([self._build_email_dict(acc_id, e) for e in batch])
        stmt = insert_stmt.on_conflict_do_update(
            index_elements=["account_id", "message_id", "conversation_id"],
            set_={
                c.name: insert_stmt.excluded[c.name]
                for c in EmailORM.__table__.columns
                if c.name not in ("id", "account_id")
            },
        )
        session.execute(stmt)