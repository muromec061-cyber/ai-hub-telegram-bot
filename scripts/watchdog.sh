#!/usr/bin/env bash
# Watchdog: перезапускает бота если упал
cd /workspace/ai-startup
LOG=/workspace/ai-startup/bot_run.log
PIDFILE=/workspace/ai-startup/bot.pid

# Kill old bot if pid file points to dead process
if [ -f $PIDFILE ]; then
    OLD_PID=$(cat $PIDFILE)
    if ! kill -0 $OLD_PID 2>/dev/null; then
        echo "[$(date)] Old bot (pid=$OLD_PID) dead. Starting new one." >> $LOG
        rm -f $PIDFILE
    fi
fi

# Start if no pid file
if [ ! -f $PIDFILE ]; then
    setsid .venv/bin/python -u main.py --mode polling >> $LOG 2>&1 < /dev/null &
    echo $! > $PIDFILE
    disown
    echo "[$(date)] Started bot (pid=$!)" >> $LOG
fi
