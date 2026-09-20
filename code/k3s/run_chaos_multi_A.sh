#!/bin/bash
# Machine-A multi-schedule chaos wrapper (ROBUST). Chi MOT instance duoc chay (lockfile).
# Dong bo voi may B qua BASE. Luu results_chaos_A_<seed>.json moi schedule.
# Dung sach: touch STOP_CHAOS de dung giua cac schedule.
cd ".3s" || exit 1
LOCK=".chaos_A.lock"; STOP="STOP_CHAOS"
# --- GUARD: chi mot instance ---
if [ -f "$LOCK" ] && kill -0 "$(cat "$LOCK" 2>/dev/null)" 2>/dev/null; then
  echo "[A-WRAP] ABORT: da co instance dang chay (PID $(cat "$LOCK"))"; exit 1
fi
echo $$ > "$LOCK"; rm -f "$STOP"
trap 'rm -f "$LOCK"' EXIT
# --- GUARD: kill moi chaos_A python con sot ---
for p in $(wmic process where "name='python.exe'" get ProcessId,CommandLine 2>/dev/null | grep -i chaos_A | grep -oE '[0-9]+$'); do taskkill //F //PID "$p" >/dev/null 2>&1; done

BASE=${1:?need BASE epoch}; DUR=${2:-10800}; GAP=${3:-300}
SEEDS="211 212 213 214 215"
i=0
for SEED in $SEEDS; do
  [ -f "$STOP" ] && { echo "[A-WRAP] STOP flag -> halt"; break; }
  ST=$((BASE + i*(DUR+GAP)))
  echo "[A-WRAP] === seed=$SEED START=$ST ($(date -d @$ST '+%d/%m %H:%M' 2>/dev/null)) ==="
  # reset: uncordon + roles=48 + cho khoe
  for n in $(kubectl get nodes --no-headers 2>/dev/null | grep SchedulingDisabled | awk '{print $1}'); do kubectl uncordon "$n" >/dev/null 2>&1; done
  kubectl -n certiheal scale deploy roles --replicas=48 >/dev/null 2>&1
  for w in $(seq 1 24); do R=$(kubectl -n certiheal get pods -l app=role --no-headers 2>/dev/null | grep -c Running); [ "$R" -ge 44 ] 2>/dev/null && break; sleep 5; done
  # chay chaos cho seed nay (chaos_A.py tu cho START roi kill DUR giay)
  python -u chaos_A.py "$SEED" "$ST" "$DUR" > "_chaosA_$SEED.log" 2>&1
  cp -f results_chaos_A.json "results_chaos_A_$SEED.json" 2>/dev/null
  echo "[A-WRAP] seed=$SEED done -> results_chaos_A_$SEED.json ($(wc -c < results_chaos_A_$SEED.json 2>/dev/null) bytes)"
  i=$((i+1))
done
echo "[A-WRAP] ALL DONE ($i schedules)"
rm -f "$LOCK"
