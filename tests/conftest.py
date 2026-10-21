"""Deterministic test configuration loaded before application modules."""

import os


os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/enterprise_ai_test")
os.environ.setdefault("GROQ_API_KEY", "test-key")
os.environ.setdefault("SECRET_KEY", "test-secret-key-that-is-at-least-32-characters")
