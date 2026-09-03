#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
backend_dir="$repo_root/backend"
runtime_dir="$repo_root/.runtime"
log_dir="$runtime_dir/logs"
pid_dir="$runtime_dir/pids"
backend_unit="open-choice-reader-backend.service"
worker_unit="open-choice-reader-worker.service"
server_host="${OPEN_CHOICE_READER_HOST:-127.0.0.1}"
server_port="${OPEN_CHOICE_READER_PORT:-8000}"

mkdir -p "$log_dir" "$pid_dir"

backend_pid_file="$pid_dir/backend.pid"
worker_pid_file="$pid_dir/worker.pid"
worker_ready_file="$runtime_dir/worker.ready"
backend_log="$log_dir/backend.log"
worker_log="$log_dir/worker.log"

resolve_python() {
  if [[ -n "${PYTHON_BIN:-}" ]]; then
    printf '%s\n' "$PYTHON_BIN"
    return 0
  fi

  if [[ -x "$backend_dir/.venv/bin/python" ]]; then
    printf '%s\n' "$backend_dir/.venv/bin/python"
    return 0
  fi

  if [[ -x "$backend_dir/.venv/bin/python3" ]]; then
    printf '%s\n' "$backend_dir/.venv/bin/python3"
    return 0
  fi

  return 1
}

systemd_runner_available() {
  [[ "${EUID:-$(id -u)}" -eq 0 ]] &&
    [[ -d /run/systemd/system ]] &&
    command -v systemd-run >/dev/null 2>&1 &&
    command -v systemctl >/dev/null 2>&1 &&
    systemctl show-environment >/dev/null 2>&1
}

write_unit_pid_file() {
  local unit_name="$1"
  local pid_file="$2"
  local pid
  pid="$(systemctl show -P MainPID "$unit_name" 2>/dev/null || true)"
  if [[ -n "$pid" ]] && [[ "$pid" != "0" ]]; then
    printf '%s\n' "$pid" >"$pid_file"
  fi
}

confirm_systemd_unit_started() {
  local name="$1"
  local unit_name="$2"
  local pid_file="$3"
  local log_file="$4"

  sleep 1

  if ! systemctl is-active --quiet "$unit_name"; then
    echo "$name failed to stay running. Recent journal output:" >&2
    journalctl -u "$unit_name" -n 20 --no-pager >&2 || true
    tail -n 20 "$log_file" >&2 || true
    rm -f "$pid_file"
    exit 1
  fi

  write_unit_pid_file "$unit_name" "$pid_file"
}

confirm_process_started() {
  local name="$1"
  local pid_file="$2"
  local log_file="$3"

  sleep 1

  if [[ ! -f "$pid_file" ]]; then
    echo "$name did not create a PID file." >&2
    exit 1
  fi

  local pid
  pid="$(cat "$pid_file")"

  if ! kill -0 "$pid" >/dev/null 2>&1; then
    echo "$name failed to stay running. Recent log output:" >&2
    tail -n 20 "$log_file" >&2 || true
    rm -f "$pid_file"
    exit 1
  fi
}

confirm_worker_started() {
  local pid_file="$1"
  local ready_file="$2"
  local log_file="$3"
  local wait_seconds=10
  local pid
  pid="$(cat "$pid_file")"

  for ((i = 0; i < wait_seconds; i++)); do
    if [[ -f "$ready_file" ]]; then
      return 0
    fi

    if ! kill -0 "$pid" >/dev/null 2>&1; then
      echo "Worker exited before completing the first run_once() iteration. Recent log output:" >&2
      tail -n 20 "$log_file" >&2 || true
      rm -f "$pid_file"
      exit 1
    fi

    sleep 1
  done

  echo "Worker did not complete a successful run_once() iteration within ${wait_seconds}s. Recent log output:" >&2
  tail -n 20 "$log_file" >&2 || true
  exit 1
}

python_bin="$(resolve_python)" || {
  echo "Unable to find a backend virtualenv Python interpreter. Create backend/.venv or set PYTHON_BIN explicitly." >&2
  exit 1
}
python_bin_dir="$(dirname "$python_bin")"
export PATH="$python_bin_dir:$PATH"

(
  cd "$backend_dir"
  "$python_bin" -m alembic upgrade head
)

use_systemd_runner=0
if systemd_runner_available; then
  use_systemd_runner=1
fi

if [[ -f "$backend_pid_file" ]]; then
  existing_pid="$(cat "$backend_pid_file")"
  if kill -0 "$existing_pid" >/dev/null 2>&1; then
    echo "Backend already running with PID $existing_pid."
  else
    rm -f "$backend_pid_file"
  fi
fi

if [[ "$use_systemd_runner" -eq 1 ]]; then
  if systemctl is-active --quiet "$backend_unit"; then
    write_unit_pid_file "$backend_unit" "$backend_pid_file"
    echo "Backend already running under systemd unit $backend_unit with PID $(cat "$backend_pid_file")."
  else
    systemctl reset-failed "$backend_unit" >/dev/null 2>&1 || true
    systemd-run \
      --unit "$backend_unit" \
      --collect \
      --property "WorkingDirectory=$backend_dir" \
      /bin/bash -lc "exec '$python_bin' -m uvicorn app.main:app --host '$server_host' --port '$server_port' >>'$backend_log' 2>&1" >/dev/null
    confirm_systemd_unit_started "Backend" "$backend_unit" "$backend_pid_file" "$backend_log"
    echo "Backend started under systemd unit $backend_unit with PID $(cat "$backend_pid_file"). Log: $backend_log"
  fi
elif [[ ! -f "$backend_pid_file" ]]; then
  (
    cd "$backend_dir"
    nohup "$python_bin" -m uvicorn app.main:app --host "$server_host" --port "$server_port" >>"$backend_log" 2>&1 &
    echo $! >"$backend_pid_file"
  )
  confirm_process_started "Backend" "$backend_pid_file" "$backend_log"
  echo "Backend started with PID $(cat "$backend_pid_file"). Log: $backend_log"
fi

if [[ -f "$worker_pid_file" ]]; then
  existing_pid="$(cat "$worker_pid_file")"
  if kill -0 "$existing_pid" >/dev/null 2>&1; then
    if [[ -f "$worker_ready_file" ]]; then
      echo "Worker already running with PID $existing_pid."
    else
      echo "Worker wrapper is running with PID $existing_pid but readiness is missing. Restarting worker." >&2
      kill "$existing_pid" >/dev/null 2>&1 || true
      rm -f "$worker_pid_file" "$worker_ready_file"
    fi
  else
    rm -f "$worker_pid_file" "$worker_ready_file"
  fi
fi

if [[ "$use_systemd_runner" -eq 1 ]]; then
  if systemctl is-active --quiet "$worker_unit"; then
    write_unit_pid_file "$worker_unit" "$worker_pid_file"
    if [[ -f "$worker_ready_file" ]]; then
      echo "Worker already running under systemd unit $worker_unit with PID $(cat "$worker_pid_file")."
    else
      echo "Worker systemd unit is active but readiness is missing. Restarting worker." >&2
      systemctl stop "$worker_unit" >/dev/null 2>&1 || true
      systemctl reset-failed "$worker_unit" >/dev/null 2>&1 || true
      rm -f "$worker_pid_file" "$worker_ready_file"
    fi
  fi
fi

if [[ ! -f "$worker_pid_file" ]]; then
  rm -f "$worker_ready_file"
  printf -v worker_command 'cd %q && ready_file=%q && while true; do if %q -c %q >>%q 2>&1; then touch "$ready_file"; else rm -f "$ready_file"; fi; sleep 5; done' \
    "$backend_dir" \
    "$worker_ready_file" \
    "$python_bin" \
    'from app.worker.runner import run_once; run_once()' \
    "$worker_log"

  if [[ "$use_systemd_runner" -eq 1 ]]; then
    systemctl reset-failed "$worker_unit" >/dev/null 2>&1 || true
    systemd-run \
      --unit "$worker_unit" \
      --collect \
      --property "WorkingDirectory=$backend_dir" \
      /bin/bash -lc "$worker_command" >/dev/null
    confirm_systemd_unit_started "Worker wrapper" "$worker_unit" "$worker_pid_file" "$worker_log"
  else
    nohup bash -lc "$worker_command" >/dev/null 2>&1 &
    echo $! >"$worker_pid_file"
    confirm_process_started "Worker wrapper" "$worker_pid_file" "$worker_log"
  fi

  confirm_worker_started "$worker_pid_file" "$worker_ready_file" "$worker_log"
  {
    printf '[%s] Worker loop started as a compatibility shim that explicitly invokes app.worker.runner.run_once().\n' "$(date -Iseconds)"
    printf '[%s] Replace this shell loop once the Python worker becomes a persistent daemon.\n' "$(date -Iseconds)"
  } >>"$worker_log"
  if [[ "$use_systemd_runner" -eq 1 ]]; then
    echo "Worker started under systemd unit $worker_unit with PID $(cat "$worker_pid_file"). Log: $worker_log"
  else
    echo "Worker started with PID $(cat "$worker_pid_file"). Log: $worker_log"
  fi
fi

frontend_dist_dir="$repo_root/frontend/dist"
if [[ -f "$frontend_dist_dir/index.html" ]]; then
  echo "Built frontend detected at $frontend_dist_dir. The backend will serve Open Choice Reader on $server_host:$server_port."
else
  echo "Frontend bundle not found at $frontend_dist_dir. Build it with 'cd frontend && npm run build' or use scripts/dev.ps1 for hot-reload development."
fi
