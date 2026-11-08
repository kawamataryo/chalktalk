#!/bin/bash
# 使い方: rec.sh <出力.mp4>。$V/raw/stop ができたら止める。開始時刻を <出力>.start に残す
V=$(dirname "$0"); OUT=$1
xcrun simctl io BE215C09-AB3A-478D-93D5-6D82ECB03BB7 recordVideo --codec=h264 --force "$OUT" &
PID=$!
python3 -c 'import time;print(f"{time.time():.3f}")' > "$OUT.start"
while [ ! -f "$V/raw/stop" ]; do sleep 0.3; done
kill -INT $PID; wait $PID; rm -f "$V/raw/stop"; echo done
