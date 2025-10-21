#!/bin/bash
# Fix script to hardcode environment variables in docker-compose.yml

set -e

echo "Fixing docker-compose.yml with hardcoded credentials..."

cd /opt/gdbchecker

# Backup original
cp docker-compose.yml docker-compose.yml.backup

# Create new docker-compose.yml with hardcoded values
cat > docker-compose.yml << 'EOFCOMPOSE'
version: '3.8'

services:
  db:
    image: postgres:16-alpine
    container_name: gdbchecker_db
    restart: always
    environment:
      POSTGRES_DB: gdbchecker
      POSTGRES_USER: gdbchecker
      POSTGRES_PASSWORD: GDBSecurePass2025!
    volumes:
      - postgres_data:/var/lib/postgresql/data
    networks:
      - gdbchecker_network
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U gdbchecker"]
      interval: 10s
      timeout: 5s
      retries: 5

  web:
    build: .
    container_name: gdbchecker_web
    restart: always
    ports:
      - "8080:8080"
    environment:
      - DATABASE_URL=postgresql://gdbchecker:GDBSecurePass2025!@db:5432/gdbchecker
      - GOOGLE_API_KEY=AIzaSyCbtVAfxF89vL1SypaPMgBrOmuAt-G2o7E
      - TELEGRAM_BOT_TOKEN=7839039906:AAFOVJPsCq1zI4psDz93RQ5tFrxhwJoLM9c
      - TELEGRAM_CHAT_ID=-1002999204995
      - FLASK_ENV=production
      - CHECK_INTERVAL_HOURS=8
    volumes:
      - ./logs:/app/logs
    depends_on:
      db:
        condition: service_healthy
    networks:
      - gdbchecker_network
    command: >
      sh -c "python init_db.py &&
             gunicorn -w 4 -b 0.0.0.0:8080 --access-logfile logs/access.log --error-logfile logs/error.log app:app &
             python scheduler.py"

volumes:
  postgres_data:

networks:
  gdbchecker_network:
    driver: bridge
EOFCOMPOSE

echo "Fixed docker-compose.yml!"
echo ""
echo "Now restarting containers..."

# Stop existing containers
docker compose down

# Remove old volumes to start fresh
docker volume rm gdbchecker_postgres_data 2>/dev/null || true

# Start containers
docker compose up -d

echo ""
echo "Waiting for containers to start..."
sleep 10

echo ""
echo "Checking status..."
docker compose ps

echo ""
echo "Checking logs..."
docker compose logs web | tail -20

echo ""
echo "============================================"
echo "Done! Check if containers are running above."
echo "Web interface: http://5.223.77.236:8080"
echo "============================================"
