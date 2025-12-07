# 🚀 Backend Quick Reference

## Start/Stop/Restart

```bash
cd Backend

# Start (daemon mode - survives terminal closure)
./start_daemon.sh

# Stop
./stop_daemon.sh

# Restart
./restart.sh

# Status check
./status.sh

# Auto-restart on failure (monitors and restarts)
./run_with_auto_restart.sh
```

## Health Checks

```bash
# Basic health
curl http://localhost:5555/health

# API health
curl http://localhost:5555/api/health
```

## Logs

```bash
# Backend logs
tail -f logs/backend.log

# Application logs
tail -f logs/app.log

# Auto-restart logs
tail -f logs/auto_restart.log
```

## Troubleshooting

```bash
# Kill process on port
lsof -ti:5555 | xargs kill -9

# Check if running
lsof -i:5555

# Test database connection
source venv/bin/activate
python -c "from database.connection import test_connection; import asyncio; asyncio.run(test_connection())"
```

## Process Management

- **Daemon mode**: `./start_daemon.sh` - Simple, survives terminal closure
- **Auto-restart**: `./run_with_auto_restart.sh` - Monitors and restarts on failure
- **PM2** (recommended): See `ROBUST_BACKEND_GUIDE.md`
- **systemd**: See `ROBUST_BACKEND_GUIDE.md`






