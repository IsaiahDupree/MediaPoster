# 🛡️ Robust Backend Guide

This guide explains how to make the backend more resilient to failures and how to manage restarts.

## 🔄 Restart Scripts

### Quick Restart
```bash
cd Backend
./restart.sh
```
Stops the current backend and starts a new instance.

### Auto-Restart on Failure
```bash
cd Backend
./run_with_auto_restart.sh
```
Monitors the backend and automatically restarts it if it crashes (up to 10 times).

## 🏥 Health Checks

The backend now includes enhanced health checks that actually test database connectivity:

```bash
# Basic health check
curl http://localhost:5555/health

# API health check
curl http://localhost:5555/api/health
```

Health checks return:
- `200 OK` if all services are operational
- `503 Service Unavailable` if any service is degraded

## 🛡️ Error Recovery Features

### 1. Database Connection Recovery
- Automatic reconnection on connection loss
- Retry logic with exponential backoff
- Connection pooling with `pool_pre_ping=True` (tests connections before use)

### 2. Graceful Shutdown
- Proper cleanup of database connections
- Handles SIGTERM and SIGINT signals
- Closes WebSocket connections gracefully

### 3. Error Handling
- Global exception handler catches unhandled errors
- Detailed error logging
- CORS headers maintained even on errors

### 4. Startup Retry Logic
- Database initialization retries up to 5 times
- Exponential backoff between retries
- Continues even if database fails (degraded mode)

## 📊 Monitoring

### Check Backend Status
```bash
cd Backend
./status.sh
```

### View Logs
```bash
# Real-time logs
tail -f Backend/logs/backend.log

# Auto-restart logs
tail -f Backend/logs/auto_restart.log

# Application logs
tail -f Backend/logs/app.log
```

### Check Process
```bash
# Find backend process
lsof -ti:5555

# Check if process is running
ps aux | grep uvicorn
```

## 🔧 Process Management Options

### Option 1: Daemon Mode (Current)
```bash
./start_daemon.sh    # Start
./stop_daemon.sh     # Stop
./restart.sh         # Restart
./status.sh          # Status
```

**Pros:**
- Simple
- Survives terminal closure
- Easy to manage

**Cons:**
- No automatic restart on failure
- Manual monitoring required

### Option 2: Auto-Restart Wrapper
```bash
./run_with_auto_restart.sh
```

**Pros:**
- Automatic restart on failure
- Health check monitoring
- Max restart limits prevent infinite loops

**Cons:**
- Requires terminal to stay open (use `screen` or `tmux`)
- More resource intensive

### Option 3: PM2 (Recommended for Production)
```bash
# Install PM2
npm install -g pm2

# Start with PM2
cd Backend
source venv/bin/activate
pm2 start "uvicorn main:app --host 0.0.0.0 --port 5555" --name mediaposter-backend

# Monitor
pm2 status
pm2 logs mediaposter-backend

# Auto-restart on failure
pm2 startup  # Set up PM2 to start on system boot
pm2 save     # Save current process list

# Restart
pm2 restart mediaposter-backend

# Stop
pm2 stop mediaposter-backend
```

**Pros:**
- Automatic restart on failure
- Log management
- Process monitoring
- Startup on boot
- Cluster mode support

**Cons:**
- Requires Node.js/npm
- Additional dependency

### Option 4: systemd (Linux/macOS)
Create `/etc/systemd/system/mediaposter-backend.service`:

```ini
[Unit]
Description=MediaPoster Backend API
After=network.target

[Service]
Type=simple
User=your-username
WorkingDirectory=/path/to/MediaPoster/Backend
Environment="PATH=/path/to/MediaPoster/Backend/venv/bin"
ExecStart=/path/to/MediaPoster/Backend/venv/bin/uvicorn main:app --host 0.0.0.0 --port 5555
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Then:
```bash
sudo systemctl daemon-reload
sudo systemctl enable mediaposter-backend
sudo systemctl start mediaposter-backend
sudo systemctl status mediaposter-backend
```

**Pros:**
- Native OS integration
- Automatic restart
- Startup on boot
- Log management via journald

**Cons:**
- Requires root access
- Platform-specific

## 🚨 Failure Scenarios & Recovery

### Database Connection Lost
**What happens:**
- Health check detects failure
- Endpoints return 503 if database is required
- Connection retry logic attempts reconnection

**Recovery:**
- Automatic reconnection with exponential backoff
- Manual restart: `./restart.sh`

### Process Crashes
**What happens:**
- Process exits
- Port becomes available

**Recovery:**
- Auto-restart script: `./run_with_auto_restart.sh`
- PM2: Automatically restarts
- Manual: `./restart.sh`

### Port Already in Use
**What happens:**
- Startup fails with "Address already in use"

**Recovery:**
```bash
# Kill process on port
lsof -ti:5555 | xargs kill -9

# Or use stop script
./stop_daemon.sh
```

### Memory/Resource Issues
**What happens:**
- Process may be killed by OS (OOM killer)
- Performance degradation

**Recovery:**
- Check logs for memory errors
- Restart: `./restart.sh`
- Consider increasing system resources

## 📝 Best Practices

1. **Always use health checks** before assuming backend is ready
2. **Monitor logs** regularly for errors
3. **Set up alerts** for repeated failures
4. **Use PM2 or systemd** for production deployments
5. **Keep logs** for debugging (current: 10 days retention)
6. **Test restart procedures** regularly

## 🔍 Troubleshooting

### Backend won't start
```bash
# Check logs
tail -50 Backend/logs/backend.log

# Check if port is in use
lsof -i:5555

# Check database connection
cd Backend
source venv/bin/activate
python -c "from database.connection import test_connection; import asyncio; asyncio.run(test_connection())"
```

### Backend keeps crashing
```bash
# Check for errors in logs
grep -i error Backend/logs/backend.log | tail -20

# Check system resources
top
df -h

# Try manual start to see errors
cd Backend
source venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 5555
```

### Health check fails
```bash
# Test database directly
curl http://localhost:5555/health

# Check database connection
cd Backend
source venv/bin/activate
python -c "from database.connection import test_connection; import asyncio; asyncio.run(test_connection())"
```

## 📚 Additional Resources

- [FastAPI Deployment](https://fastapi.tiangolo.com/deployment/)
- [Uvicorn Settings](https://www.uvicorn.org/settings/)
- [PM2 Documentation](https://pm2.keymetrics.io/docs/usage/quick-start/)
- [systemd Service Files](https://www.freedesktop.org/software/systemd/man/systemd.service.html)






