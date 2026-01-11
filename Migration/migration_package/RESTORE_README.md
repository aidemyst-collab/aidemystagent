# AgentStudio Database Migration Package

This package contains everything needed to restore the AgentStudio database on a new machine.

## Contents

| File | Description |
|------|-------------|
| `agentstudio_backup_20260104.dump` | PostgreSQL custom format backup (recommended) |
| `agentstudio_backup_20260104.sql` | SQL text backup (human readable) |
| `backend.env` | Backend environment variables |
| `frontend.env` | Frontend environment variables |
| `restore-db.sh` | Automated restore script |

## Quick Restore (Recommended)

### Step 1: Clone the repository on new laptop

```bash
git clone https://github.com/aidemyst-collab/aidemystagent.git
cd aidemystagent
git checkout development
```

### Step 2: Copy migration files

Copy this entire `migration_package` folder to the new laptop.

### Step 3: Restore environment files

```bash
cp migration_package/backend.env backend/.env
cp migration_package/frontend.env frontend/.env
```

### Step 4: Start Docker services

```bash
docker-compose up -d postgres redis
```

### Step 5: Wait for PostgreSQL to be ready

```bash
sleep 10
docker exec agentstudio_postgres pg_isready -U postgres
```

### Step 6: Restore the database

**Option A - Using custom format (recommended):**
```bash
docker cp migration_package/agentstudio_backup_20260104.dump agentstudio_postgres:/tmp/backup.dump
docker exec agentstudio_postgres pg_restore -U postgres -d agentstudio --clean --if-exists /tmp/backup.dump
```

**Option B - Using SQL format:**
```bash
docker exec -i agentstudio_postgres psql -U postgres -d agentstudio < migration_package/agentstudio_backup_20260104.sql
```

### Step 7: Start all services

```bash
docker-compose up -d
```

### Step 8: Verify

```bash
# Check backend
curl http://localhost:8000/health

# Check frontend
open http://localhost:5173
```

## Manual Restore Steps

If the automated script doesn't work:

1. Ensure Docker Desktop is running
2. Create the database if it doesn't exist:
   ```bash
   docker exec agentstudio_postgres createdb -U postgres agentstudio
   ```
3. Restore from backup:
   ```bash
   docker exec -i agentstudio_postgres psql -U postgres -d agentstudio < agentstudio_backup_20260104.sql
   ```

## Troubleshooting

### "database does not exist"
```bash
docker exec agentstudio_postgres createdb -U postgres agentstudio
```

### "role does not exist"
The backup uses the 'postgres' user which should exist by default.

### Permission errors
Ensure Docker Desktop has access to the folder containing the files.

---

**Backup Date**: January 4, 2026
**Source**: Development laptop
