# 🚀 Running Backend as Independent Daemon

This guide shows how to run the backend independently so it won't be killed when you stop the frontend or close terminals.

## Quick Start

### Start Backend (Daemon Mode)
```bash
cd Backend
./start_daemon.sh
```

The backend will:
- ✅ Run in the background (survives terminal closure)
- ✅ Auto-restart on code changes (--reload)
- ✅ Log to `logs/backend.log`
- ✅ Save PID to `logs/backend.pid`

### Check Status
```bash
cd Backend
./status.sh
```

### Stop Backend
```bash
cd Backend
./stop_daemon.sh
```

## Alternative Methods

### Method 1: Using `nohup` (Manual)
```bash
cd Backend
source venv/bin/activate
nohup uvicorn main:app --host 0.0.0.0 --port 5555 --reload > logs/backend.log 2>&1 &
```

### Method 2: Using `screen` (Recommended for Development)
```bash
# Install screen (if not installed)
# macOS: brew install screen

# Start a screen session
screen -S backend

# Inside screen, start backend
cd Backend
source venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 5555 --reload

# Detach: Press Ctrl+A, then D
# Reattach: screen -r backend
# Kill: screen -S backend -X quit
```

### Method 3: Using `tmux` (Alternative to screen)
```bash
# Install tmux (if not installed)
# macOS: brew install tmux

# Start a tmux session
tmux new -s backend

# Inside tmux, start backend
cd Backend
source venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 5555 --reload

# Detach: Press Ctrl+B, then D
# Reattach: tmux attach -t backend
# Kill: tmux kill-session -t backend
```

### Method 4: Using PM2 (Process Manager)
```bash
# Install PM2
npm install -g pm2

# Start backend with PM2
cd Backend
source venv/bin/activate
pm2 start "uvicorn main:app --host 0.0.0.0 --port 5555 --reload" --name mediaposter-backend

# Check status
pm2 status

# View logs
pm2 logs mediaposter-backend

# Stop
pm2 stop mediaposter-backend

# Restart
pm2 restart mediaposter-backend
```

## Benefits of Daemon Mode

1. **Independent Operation**: Backend runs separately from frontend
2. **Survives Terminal Closure**: Backend keeps running even if you close the terminal
3. **Easy Management**: Simple start/stop/status commands
4. **Logging**: All output goes to `logs/backend.log`
5. **Auto-Reload**: Still supports code changes with `--reload` flag

## Troubleshooting

### Backend won't start
```bash
# Check if port is in use
lsof -ti:5555

# Kill process on port
lsof -ti:5555 | xargs kill -9

# Check logs
tail -f Backend/logs/backend.log
```

### Backend is running but not responding
```bash
# Check if it's actually listening
lsof -i:5555

# Restart
cd Backend
./stop_daemon.sh
./start_daemon.sh
```

### View real-time logs
```bash
tail -f Backend/logs/backend.log
```






