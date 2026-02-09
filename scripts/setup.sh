#!/bin/bash

# Setup script for Enterprise AI Assistant
# This script helps you get started quickly

set -e

echo "🚀 Enterprise AI Assistant - Setup Script"
echo "=========================================="
echo ""

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    exit 1
fi

# Check if Docker Compose is installed (v2 or legacy)
if command -v docker-compose &> /dev/null; then
    COMPOSE="docker-compose"
elif docker compose version &> /dev/null; then
    COMPOSE="docker compose"
else
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi


echo "✅ Docker and Docker Compose are installed"
echo ""

# Check if .env file exists
if [ ! -f .env ]; then
    echo "📝 Creating .env file from .env.example..."
    cp .env.example .env
    echo "⚠️  Please edit .env and add your Groq API key before continuing!"
    echo ""
    echo "Get your Groq API key from: https://console.groq.com"
    echo ""
    read -p "Press Enter after you've updated the .env file..."
else
    echo "✅ .env file already exists"
fi

echo ""
echo "🐳 Starting Docker containers..."
cd docker
$COMPOSE up -d

echo ""
echo "⏳ Waiting for database to be ready..."
sleep 10

echo ""
echo "🗄️  Initializing database..."
$COMPOSE exec -T app python scripts/init_db.py

echo ""
echo "✅ Setup complete!"
echo ""
echo "📚 Next steps:"
echo "  1. Upload sample documents:"
echo "     ./scripts/upload_samples.sh"
echo ""
echo "  2. Test the API:"
echo "     curl http://localhost:8000/health"
echo ""
echo "  3. View API documentation:"
echo "     http://localhost:8000/docs"
echo ""
echo "  4. View logs:"
echo "     cd docker && docker-compose logs -f app"
echo ""
