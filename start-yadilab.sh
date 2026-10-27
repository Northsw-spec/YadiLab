#!/usr/bin/env bash
set -uo pipefail

ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
DIST="$ROOT/distribution/linux-x86_64"
LAUNCHER="$DIST/app-launcher"
PORT=${YADILAB_PORT:-18233}
URL="http://127.0.0.1:$PORT/"
MARKER=yadilab-v1.8.0-dev.11
RUNTIME_DIR=${XDG_RUNTIME_DIR:-/tmp}
[[ -d "$RUNTIME_DIR" && -w "$RUNTIME_DIR" ]] || RUNTIME_DIR=/tmp
PIDFILE="$RUNTIME_DIR/yadilab-$PORT.pid"
LAUNCHER_PID=""

fail() {
  printf '\nYadiLab kunde inte startas: %s\n' "$1" >&2
  printf 'Terminalen lämnas öppen så att felet kan läsas.\n' >&2
  if [[ -t 0 && ${YADILAB_TEST_ONCE:-0} != 1 ]]; then read -r -p 'Tryck Enter för att stänga… ' _; fi
  exit 1
}

cleanup_failed_start() {
  if [[ -n "$LAUNCHER_PID" ]]; then
    kill "$LAUNCHER_PID" 2>/dev/null || true
    wait "$LAUNCHER_PID" 2>/dev/null || true
  fi
  rm -f -- "$PIDFILE"
}

verify_marker() {
  local response
  response=$(curl -fsS --max-time 2 "${URL}build-marker.json" 2>/dev/null) || return 1
  grep -Fq '"formatId": "yadilab.browser-build-marker"' <<<"$response" &&
    grep -Fq '"version": "1.8.0-dev.11"' <<<"$response" &&
    grep -Fq '"marker": "yadilab-v1.8.0-dev.11"' <<<"$response"
}

[[ "$PORT" =~ ^[0-9]+$ ]] && (( PORT >= 1024 && PORT <= 65535 )) || fail "ogiltig port: $PORT"
[[ -x "$LAUNCHER" ]] || fail "körbar launcher saknas: $LAUNCHER"
[[ -r "$DIST/web/build-marker.json" ]] || fail "final build marker saknas i distributionen"
(cd "$DIST" && sha256sum -c SHA256SUMS.txt >/dev/null 2>&1) || fail "distributionens checksummor stämmer inte"

if [[ -r "$PIDFILE" ]]; then
  old_pid=$(<"$PIDFILE")
  if [[ "$old_pid" =~ ^[0-9]+$ ]] && kill -0 "$old_pid" 2>/dev/null; then
    old_exe=$(readlink -f "/proc/$old_pid/exe" 2>/dev/null || true)
    expected_exe=$(readlink -f "$LAUNCHER" 2>/dev/null || true)
    if [[ -n "$old_exe" && "$old_exe" == "$expected_exe" ]]; then
      kill "$old_pid" 2>/dev/null || fail "kunde inte stoppa tidigare YadiLab-process $old_pid"
      for _ in $(seq 1 30); do kill -0 "$old_pid" 2>/dev/null || break; sleep .1; done
    else
      fail "PID-filen pekar på en annan process ($old_pid); den stoppades inte"
    fi
  fi
  rm -f -- "$PIDFILE"
fi

stop_stale_port_owner() {
  local lines pids pid uid comm
  lines=$(ss -H -ltnp "sport = :$PORT" 2>/dev/null || true)
  [[ -n "$lines" ]] || return 0

  mapfile -t pids < <(grep -oE 'pid=[0-9]+' <<<"$lines" | cut -d= -f2 | sort -u)
  ((${#pids[@]} > 0)) || fail "port $PORT används redan men ägar-PID kunde inte fastställas ($lines)"

  for pid in "${pids[@]}"; do
    [[ -r "/proc/$pid/status" ]] || continue
    uid=$(awk '/^Uid:/ {print $2; exit}' "/proc/$pid/status" 2>/dev/null || true)
    comm=$(cat "/proc/$pid/comm" 2>/dev/null || true)
    if [[ "$uid" == "$(id -u)" && "$comm" == "app-launcher" ]]; then
      printf 'Stoppar gammal YadiLab app-launcher PID %s på port %s.\n' "$pid" "$PORT"
      kill -TERM "$pid" 2>/dev/null || true
      for _ in $(seq 1 40); do
        kill -0 "$pid" 2>/dev/null || break
        sleep .1
      done
      if kill -0 "$pid" 2>/dev/null; then
        printf 'Process %s svarade inte på SIGTERM; skickar SIGKILL.\n' "$pid"
        kill -KILL "$pid" 2>/dev/null || true
      fi
    else
      fail "port $PORT ägs av annan process och stoppas inte automatiskt (pid=$pid, uid=${uid:-?}, process=${comm:-?})"
    fi
  done

  for _ in $(seq 1 40); do
    ss -H -ltn "sport = :$PORT" 2>/dev/null | grep -q . || return 0
    sleep .1
  done
  lines=$(ss -H -ltnp "sport = :$PORT" 2>/dev/null | head -1 || true)
  fail "port $PORT är fortfarande upptagen efter stoppförsök (${lines:-ägare okänd})"
}

if ss -H -ltn "sport = :$PORT" 2>/dev/null | grep -q .; then
  if verify_marker; then
    printf 'En äldre/kvarvarande YadiLab-server svarar redan på port %s; startar om den så denna uppackning äger processen.\n' "$PORT"
  else
    printf 'Port %s används av en process med fel/ingen final marker; kontrollerar om det är en gammal YadiLab app-launcher.\n' "$PORT"
  fi
  stop_stale_port_owner
fi

"$LAUNCHER" --port "$PORT" >"$RUNTIME_DIR/yadilab-$PORT.log" 2>&1 &
LAUNCHER_PID=$!
printf '%s\n' "$LAUNCHER_PID" >"$PIDFILE"

ready=0
for _ in $(seq 1 100); do
  if ! kill -0 "$LAUNCHER_PID" 2>/dev/null; then cleanup_failed_start; fail "launchern avslutades före HTTP-verifieringen"; fi
  if verify_marker; then ready=1; break; fi
  sleep .1
done
[[ "$ready" == 1 ]] || { cleanup_failed_start; fail "HTTP-svaret verifierades inte som $MARKER"; }

printf 'Verifierad YadiLab %s på %s\n' "$MARKER" "$URL"
if [[ ${YADILAB_TEST_ONCE:-0} == 1 ]]; then cleanup_failed_start; exit 0; fi

browser=${YADILAB_BROWSER:-}
if [[ -z "$browser" ]]; then
  for candidate in google-chrome chromium chromium-browser; do
    if command -v "$candidate" >/dev/null 2>&1; then browser=$(command -v "$candidate"); break; fi
  done
fi
[[ -n "$browser" && -x "$browser" ]] || { cleanup_failed_start; fail "Google Chrome/Chromium hittades inte"; }
"$browser" --new-window "${URL}?build=1.8.0-dev.11" >/dev/null 2>&1 &
printf 'Browser öppnad. Låt terminalen vara öppen medan YadiLab används.\n'
wait "$LAUNCHER_PID"
status=$?
rm -f -- "$PIDFILE"
[[ "$status" == 0 ]] || fail "launchern avslutades med kod $status"
