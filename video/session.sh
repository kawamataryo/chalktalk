#!/bin/bash
# 使い方: session.sh <名前> [追加の起動引数...]。台本のセッションを録画し、「終わり」を言う直前にアプリを止める（ふり返りを本番に保存しない）
V=$(dirname "$0"); NAME=$1; shift
D=BE215C09-AB3A-478D-93D5-6D82ECB03BB7; APP=com.kawamataryo.HomeTeacher
C=$(xcrun simctl get_app_container $D $APP data)
rm -f "$C/Documents/session-selftest.txt" "$C/Documents/session-trace.txt"
xcrun simctl terminate $D $APP 2>/dev/null; sleep 1
"$V/rec.sh" "$V/raw/$NAME.mp4" &
sleep 1.5
xcrun simctl launch $D $APP -skipPermissionOnboarding ${MODE:--autoSessionDemo} -traceToFile "$@" >/dev/null
END=$(( $(date +%s) + 600 ))
while [ $(date +%s) -lt $END ]; do
  if grep -q "子ども: 「終わり」" "$C/Documents/session-selftest.txt" 2>/dev/null; then break; fi
  if [ -n "$STOP_AT" ] && grep -q "$STOP_AT" "$C/Documents/session-selftest.txt" 2>/dev/null; then sleep ${STOP_DELAY:-0}; break; fi
  if grep -q "自己テスト終了" "$C/Documents/session-selftest.txt" 2>/dev/null; then break; fi
  sleep 0.2
done
xcrun simctl terminate $D $APP
sleep 1; touch "$V/raw/stop"; wait
cp "$C/Documents/session-selftest.txt" "$V/raw/$NAME.selftest.txt"; cp "$C/Documents/session-trace.txt" "$V/raw/$NAME.trace.txt" 2>/dev/null
echo finished
