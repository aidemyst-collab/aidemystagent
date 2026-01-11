#!/bin/bash
# AgentStudio Database Restore Script
# Run this from the migration_package directory

set -e

echo "========================================="
echo "  AgentStudio Database Restore Script"
echo "========================================="

# Check if we're in the right directory
if [ ! -f "agentstudio_backup_20260104.dump" ]; then
    echo "Error: Backup file not found!"
    echo "Please run this script from the migration_package directory"
    exit 1
fi

# Get the parent directory (project root)
PROJECT_ROOT=$(dirname "$(pwd)")

echo ""
echo "Step 1: Copying environment files..."
if [ -f "backend.env" ]; then
    cp backend.env "$PROJECT_ROOT/backend/.env"
    echo "✓ Copied backend.env"
fi
if [ -f "frontend.env" ]; then
    cp frontend.env "$PROJECT_ROOT/frontend/.env"
    echo "✓ Copied frontend.env"
fi

echo ""
echo "Step 2: Starting PostgreSQL container..."
cd "$PROJECT_ROOT"
docker-compose up -d postgres

echo ""
echo "Step 3: Waiting for PostgreSQL to be ready..."
sleep 10
until docker exec agentstudio_postgres pg_isready -U postgres; do
    echo "Waiting for PostgreSQL..."
    sleep 2
done
echo "✓ PostgreSQL is ready"

echo ""
echo "Step 4: Creating database if not exists..."
docker exec agentstudio_postgres psql -U postgres -tc "SELECT 1 FROM pg_database WHERE datname = 'agentstudio'" | grep -q 1 || \
    docker exec agentstudio_postgres createdb -U postgres agentstudio
echo "✓ Database ready"

echo ""
echo "Step 5: Restoring database from backup..."
cd -
docker cp agentstudio_backup_20260104.dump agentstudio_postgres:/tmp/backup.dump
docker exec agentstudio_postgres pg_restore -U postgres -d agentstudio --clean --if-exists /tmp/backup.dump 2>/dev/null || true
echo "✓ Database restored"

echo ""
echo "Step 6: Starting all services..."
cd "$PROJECT_ROOT"
docker-compose up -d

echo ""
echo "========================================="
echo "  Restore Complete!"
echo "========================================="
echo ""
echo "Backend:  http://localhost:8000"
echo "Frontend: http://localhost:5173"
echo "API Docs: http://localhost:8000/docs"
echo ""
echo "Test with: curl http://localhost:8000/health"
