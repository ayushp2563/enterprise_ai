#!/usr/bin/env python3
"""Run the document ingestion worker."""

import logging
import os
import socket

from app.services.ingestion_worker import IngestionWorker


if __name__ == "__main__":
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    worker_id = os.getenv("WORKER_ID", socket.gethostname())
    IngestionWorker(worker_id).run_forever()
