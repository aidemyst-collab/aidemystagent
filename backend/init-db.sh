#!/bin/bash
set -e

echo "Waiting for postgres..."
while ! pg_isready -h postgres -U postgres; do
    sleep 1
done

echo "Running migrations..."
alembic upgrade head

echo "Database initialized successfully!"
