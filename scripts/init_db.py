#!/usr/bin/env python3
"""
Database initialization script.
Creates tables and enables pgvector extension.
"""

import psycopg2
import sys
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://postgres:postgres@localhost:5432/enterprise_ai')


def init_database():
    """Initialize database with required tables and extensions."""
    
    try:
        # Connect to database
        print(f"Connecting to database...")
        conn = psycopg2.connect(DATABASE_URL)
        conn.autocommit = True
        cursor = conn.cursor()
        
        # Enable pgvector extension
        print("Enabling pgvector extension...")
        cursor.execute("CREATE EXTENSION IF NOT EXISTS vector;")
        
        # Create documents table
        print("Creating documents table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                id SERIAL PRIMARY KEY,
                title VARCHAR(500) NOT NULL,
                content TEXT,
                metadata JSONB,
                created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMP NOT NULL DEFAULT NOW()
            );
        """)
        
        # Create document_chunks table with vector embeddings
        print("Creating document_chunks table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS document_chunks (
                id SERIAL PRIMARY KEY,
                document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
                chunk_text TEXT NOT NULL,
                chunk_index INTEGER NOT NULL,
                embedding vector(384),
                created_at TIMESTAMP NOT NULL DEFAULT NOW()
            );
        """)
        
        # Create index for vector similarity search
        print("Creating vector similarity index...")
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS document_chunks_embedding_idx 
            ON document_chunks 
            USING ivfflat (embedding vector_cosine_ops)
            WITH (lists = 100);
        """)
        
        # Create query_logs table
        print("Creating query_logs table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS query_logs (
                id SERIAL PRIMARY KEY,
                question TEXT NOT NULL,
                answer TEXT NOT NULL,
                sources JSONB,
                query_time FLOAT,
                created_at TIMESTAMP NOT NULL DEFAULT NOW()
            );
        """)
        
        # Create workflows table
        print("Creating workflows table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS workflows (
                id SERIAL PRIMARY KEY,
                workflow_type VARCHAR(100) NOT NULL,
                parameters JSONB,
                status VARCHAR(50) NOT NULL,
                result JSONB,
                error TEXT,
                created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                completed_at TIMESTAMP
            );
        """)
        
        print("✅ Database initialization completed successfully!")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Error initializing database: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    init_database()
