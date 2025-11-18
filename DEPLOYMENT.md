# Production Deployment Guide

## Prerequisites

- Docker and Docker Compose installed
- PostgreSQL 15+ (if not using Docker)
- Redis 7+ (if not using Docker)
- Domain name with SSL certificate
- Minimum 2GB RAM, 2 CPU cores

## Environment Configuration

### Backend (.env)

Create `/backend/.env` with:

```env
# Application
APP_NAME=AgentStudio
APP_VERSION=1.0.0
DEBUG=false

# Database
DATABASE_URL=postgresql+asyncpg://user:password@postgres:5432/agentstudio

# Redis
REDIS_URL=redis://redis:6379/0

# Security
SECRET_KEY=<generate-secure-random-key>
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# CORS
CORS_ORIGINS=["https://yourdomain.com"]

# LLM APIs (Optional)
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...

# Monitoring
SENTRY_DSN=<your-sentry-dsn>
LOG_LEVEL=INFO
```

### Frontend (.env)

Create `/frontend/.env.production` with:

```env
VITE_API_BASE_URL=https://api.yourdomain.com
VITE_APP_VERSION=1.0.0
```

## Docker Deployment

### 1. Build Images

```bash
# Build backend
docker build -t agentstudio-backend:latest ./backend

# Build frontend for production
cd frontend
npm run build
docker build -t agentstudio-frontend:latest .
```

### 2. Production Docker Compose

Create `docker-compose.prod.yml`:

```yaml
version: '3.8'

services:
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: agentstudio
      POSTGRES_USER: ${DB_USER}
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped
    networks:
      - backend

  redis:
    image: redis:7-alpine
    command: redis-server --requirepass ${REDIS_PASSWORD}
    volumes:
      - redis_data:/data
    restart: unless-stopped
    networks:
      - backend

  backend:
    image: agentstudio-backend:latest
    env_file:
      - ./backend/.env
    depends_on:
      - postgres
      - redis
    volumes:
      - ./backend/logs:/app/logs
    restart: unless-stopped
    networks:
      - backend
      - frontend
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  frontend:
    image: agentstudio-frontend:latest
    depends_on:
      - backend
    restart: unless-stopped
    networks:
      - frontend

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./ssl:/etc/nginx/ssl:ro
    depends_on:
      - backend
      - frontend
    restart: unless-stopped
    networks:
      - frontend

volumes:
  postgres_data:
  redis_data:

networks:
  backend:
  frontend:
```

### 3. Nginx Configuration

Create `nginx.conf`:

```nginx
events {
    worker_connections 1024;
}

http {
    upstream backend {
        server backend:8000;
    }

    upstream frontend {
        server frontend:80;
    }

    # Redirect HTTP to HTTPS
    server {
        listen 80;
        server_name yourdomain.com;
        return 301 https://$server_name$request_uri;
    }

    # HTTPS Server
    server {
        listen 443 ssl http2;
        server_name yourdomain.com;

        ssl_certificate /etc/nginx/ssl/fullchain.pem;
        ssl_certificate_key /etc/nginx/ssl/privkey.pem;
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers HIGH:!aNULL:!MD5;

        # API
        location /api {
            proxy_pass http://backend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        # API Documentation
        location /docs {
            proxy_pass http://backend;
            proxy_set_header Host $host;
        }

        location /redoc {
            proxy_pass http://backend;
            proxy_set_header Host $host;
        }

        # Frontend
        location / {
            proxy_pass http://frontend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
        }
    }
}
```

### 4. Start Services

```bash
# Set environment variables
export DB_USER=agentstudio
export DB_PASSWORD=<secure-password>
export REDIS_PASSWORD=<secure-password>

# Start services
docker-compose -f docker-compose.prod.yml up -d

# Run migrations
docker-compose exec backend alembic upgrade head

# Check logs
docker-compose logs -f
```

## Database Migrations

```bash
# Create migration
docker-compose exec backend alembic revision --autogenerate -m "Description"

# Apply migrations
docker-compose exec backend alembic upgrade head

# Rollback migration
docker-compose exec backend alembic downgrade -1
```

## Monitoring

### Application Logs

```bash
# View backend logs
docker-compose logs -f backend

# View all logs
docker-compose logs -f
```

### Health Checks

```bash
# Backend health
curl https://api.yourdomain.com/health

# Database connection
docker-compose exec backend python -c "from app.core.database import engine; print('OK')"
```

### Metrics

- API response times: Check logs or integrate APM (Application Performance Monitoring)
- Error rates: Monitor error logs
- Database performance: Use PostgreSQL monitoring tools

## Backup and Recovery

### Database Backup

```bash
# Create backup
docker-compose exec postgres pg_dump -U agentstudio agentstudio > backup_$(date +%Y%m%d_%H%M%S).sql

# Restore backup
docker-compose exec -T postgres psql -U agentstudio agentstudio < backup.sql
```

### Volume Backup

```bash
# Backup volumes
docker run --rm -v postgres_data:/data -v $(pwd):/backup alpine tar czf /backup/postgres_backup.tar.gz -C /data .
docker run --rm -v redis_data:/data -v $(pwd):/backup alpine tar czf /backup/redis_backup.tar.gz -C /data .
```

## Security Checklist

- [ ] Use strong SECRET_KEY (min 32 characters)
- [ ] Enable HTTPS with valid SSL certificate
- [ ] Set DEBUG=false in production
- [ ] Restrict CORS_ORIGINS to your domain
- [ ] Use strong database passwords
- [ ] Enable Redis password authentication
- [ ] Regularly update dependencies
- [ ] Implement rate limiting (consider nginx)
- [ ] Enable firewall rules
- [ ] Regular security audits
- [ ] Backup data regularly
- [ ] Monitor logs for suspicious activity

## Performance Optimization

### Backend

1. **Database Connection Pooling**
   - Already configured in SQLAlchemy
   - Adjust pool size based on load

2. **Redis Caching**
   - Cache frequently accessed data
   - Set appropriate TTL values

3. **Gunicorn Workers**
   - Increase workers: `gunicorn -w 4 -k uvicorn.workers.UvicornWorker`

### Frontend

1. **Build Optimization**
   ```bash
   npm run build -- --mode production
   ```

2. **Asset Compression**
   - Enable gzip in Nginx
   - Use CDN for static assets

3. **Code Splitting**
   - Already implemented with React lazy loading

### Database

1. **Indexing**
   - Add indexes for frequently queried fields
   - Monitor slow queries

2. **Query Optimization**
   - Use database query profiling
   - Optimize N+1 queries

## Scaling

### Horizontal Scaling

1. **Multiple Backend Instances**
   ```yaml
   backend:
     deploy:
       replicas: 3
   ```

2. **Load Balancer**
   - Use Nginx or cloud load balancer
   - Session affinity for WebSocket connections

3. **Database Read Replicas**
   - PostgreSQL streaming replication
   - Route read queries to replicas

### Vertical Scaling

- Increase RAM and CPU for containers
- Optimize PostgreSQL shared_buffers
- Increase Redis maxmemory

## Troubleshooting

### Backend Won't Start

1. Check environment variables
2. Verify database connection
3. Review logs: `docker-compose logs backend`

### Database Connection Errors

1. Ensure PostgreSQL is running
2. Check DATABASE_URL format
3. Verify network connectivity

### High Memory Usage

1. Monitor container stats: `docker stats`
2. Check for memory leaks in logs
3. Adjust worker count

### Slow API Responses

1. Enable query logging
2. Check database indexes
3. Monitor Redis hit rate
4. Review LLM API latency

## Maintenance

### Regular Tasks

- **Daily**: Monitor logs and metrics
- **Weekly**: Review error rates and performance
- **Monthly**: Update dependencies, backup database
- **Quarterly**: Security audit, performance review

### Updates

```bash
# Pull latest changes
git pull

# Rebuild images
docker-compose build

# Apply migrations
docker-compose exec backend alembic upgrade head

# Restart services with zero downtime
docker-compose up -d --no-deps --build backend
```

## Support

For production issues:
1. Check logs first
2. Review this documentation
3. Contact DevOps team
4. Escalate to engineering if needed
