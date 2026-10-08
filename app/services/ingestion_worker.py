"""Durable PostgreSQL-backed document ingestion worker."""

import logging
import time
from datetime import timedelta

import psycopg2
from psycopg2.extras import Json

from app.config import get_settings
from app.services.document_ingestion import get_ingestion_service
from app.services.document_storage import get_document_storage
from app.services.vector_store import get_vector_store

logger = logging.getLogger(__name__)


class IngestionWorker:
    def __init__(self, worker_id: str):
        self.settings = get_settings()
        self.worker_id = worker_id
        self.storage = get_document_storage()

    def _connect(self):
        return psycopg2.connect(self.settings.database_url)

    def claim_job(self):
        """Claim one available job without competing with another worker."""
        conn = self._connect()
        try:
            with conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        WITH candidate AS (
                            SELECT id
                            FROM ingestion_jobs
                            WHERE status = 'pending'
                              AND available_at <= NOW()
                            ORDER BY available_at, created_at
                            FOR UPDATE SKIP LOCKED
                            LIMIT 1
                        )
                        UPDATE ingestion_jobs AS job
                        SET status = 'processing',
                            attempt_count = attempt_count + 1,
                            started_at = NOW(),
                            locked_at = NOW(),
                            locked_by = %s,
                            error_code = NULL,
                            error_detail = NULL
                        FROM candidate
                        WHERE job.id = candidate.id
                        RETURNING
                            job.id, job.company_id, job.document_id,
                            job.attempt_count, job.max_attempts
                    """, (self.worker_id,))
                    job = cursor.fetchone()
                    if not job:
                        return None

                    cursor.execute("""
                        UPDATE documents
                        SET ingestion_status = 'processing',
                            ingestion_error = NULL
                        WHERE id = %s AND company_id = %s
                    """, (job[2], job[1]))
                    return {
                        "id": job[0],
                        "company_id": job[1],
                        "document_id": job[2],
                        "attempt_count": job[3],
                        "max_attempts": job[4],
                    }
        finally:
            conn.close()

    def _load_document(self, job):
        conn = self._connect()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT storage_key, original_filename, media_type
                    FROM documents
                    WHERE id = %s
                      AND company_id = %s
                      AND is_active = true
                """, (job["document_id"], job["company_id"]))
                row = cursor.fetchone()
                if not row:
                    raise ValueError("Document is missing or inactive")
                return row
        finally:
            conn.close()

    def complete_job(self, job, result):
        vector_store = get_vector_store()
        vector_store.delete_document_chunks(
            job["document_id"],
            job["company_id"],
        )
        vector_store.store_document_chunks(
            document_id=job["document_id"],
            company_id=job["company_id"],
            chunks=result["chunks"],
            embeddings=result["embeddings"],
            embedding_model=self.settings.embedding_model,
            chunk_metadata=result["chunk_metadata"],
        )

        conn = self._connect()
        try:
            with conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        UPDATE documents
                        SET content = %s,
                            ingestion_status = 'completed',
                            ingestion_error = NULL,
                            completed_at = NOW(),
                            metadata = metadata || %s
                        WHERE id = %s AND company_id = %s
                    """, (
                        " ".join(result["chunks"][:3]),
                        Json({"num_chunks": result["num_chunks"]}),
                        job["document_id"],
                        job["company_id"],
                    ))
                    cursor.execute("""
                        UPDATE ingestion_jobs
                        SET status = 'completed',
                            completed_at = NOW(),
                            locked_at = NULL,
                            locked_by = NULL
                        WHERE id = %s
                    """, (str(job["id"]),))
        finally:
            conn.close()

    def fail_job(self, job, exc: Exception):
        retryable = job["attempt_count"] < job["max_attempts"]
        next_status = "pending" if retryable else "failed"
        delay_seconds = min(60, 2 ** job["attempt_count"])
        safe_error = type(exc).__name__

        conn = self._connect()
        try:
            with conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        UPDATE ingestion_jobs
                        SET status = %s,
                            available_at = NOW() + %s,
                            completed_at = CASE
                                WHEN %s = 'failed' THEN NOW()
                                ELSE NULL
                            END,
                            locked_at = NULL,
                            locked_by = NULL,
                            error_code = %s,
                            error_detail = %s
                        WHERE id = %s
                    """, (
                        next_status,
                        timedelta(seconds=delay_seconds),
                        next_status,
                        safe_error,
                        "Document processing failed",
                        str(job["id"]),
                    ))
                    cursor.execute("""
                        UPDATE documents
                        SET ingestion_status = %s,
                            ingestion_error = %s
                        WHERE id = %s AND company_id = %s
                    """, (
                        next_status,
                        "Document processing failed" if not retryable else None,
                        job["document_id"],
                        job["company_id"],
                    ))
        finally:
            conn.close()

    def process_next_job(self) -> bool:
        job = self.claim_job()
        if not job:
            return False

        try:
            storage_key, original_filename, _ = self._load_document(job)
            extension = (original_filename or "").rsplit(".", 1)[-1].lower()
            path = self.storage.resolve(storage_key)
            result = get_ingestion_service().process_document(
                str(path),
                extension,
                metadata={"filename": original_filename},
            )
            if not result["chunks"]:
                raise ValueError("Document produced no searchable text")
            self.complete_job(job, result)
            logger.info(
                "Ingestion completed",
                extra={
                    "company_id": job["company_id"],
                    "document_id": job["document_id"],
                    "chunk_count": result["num_chunks"],
                },
            )
        except Exception as exc:
            logger.exception(
                "Ingestion failed",
                extra={
                    "company_id": job["company_id"],
                    "document_id": job["document_id"],
                },
            )
            self.fail_job(job, exc)
        return True

    def run_forever(self):
        logger.info("Ingestion worker started", extra={"worker_id": self.worker_id})
        while True:
            processed = self.process_next_job()
            if not processed:
                time.sleep(self.settings.ingestion_poll_seconds)
