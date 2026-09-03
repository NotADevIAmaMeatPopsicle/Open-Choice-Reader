#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
pid_dir="$repo_root/.runtime/pids"
worker_ready_file="$repo_root/.runtime/worker.ready"
frontend_pid_file="$pid_dir/frontend.pid"
backend_unit="open-choice-reader-backend.service"
worker_unit="open-choice-reader-worker.service"

systemd_runner_available() {
  [[ "${EUID:-$(id -u)}" -eq 0 ]] &&
    [[ -d /run/systemd/system ]] &&
    command -v systemctl >/dev/null 2>&1 &&
    systemctl show-environment >/dev/null 2>&1
}

find_matching_pids() {
  if ! command -v ps >/dev/null 2>&1; then
    return 0
  fi

  local pid args matches fragment

  while read -r pid args; do
    matches=1

    for fragment in "$@"; do
      if [[ "$args" != *"$fragment"* ]]; then
        matches=0
        break
      fi
    done

    if [[ "$matches" -eq 1 ]] && [[ -n "$pid" ]] && [[ "$pid" != "$$" ]]; then
      printf '%s\n' "$pid"
    fi
  done < <(ps -ww -eo pid=,args=)
}

stop_matching_processes() {
  local name="$1"
  shift

  local pids=()
  while IFS= read -r pid; do
    if [[ -n "$pid" ]]; then
      pids+=("$pid")
    fi
  done < <(find_matching_pids "$@" | sort -u)

  if [[ "${#pids[@]}" -eq 0 ]]; then
    return 0
  fi

  local pid
  for pid in "${pids[@]}"; do
    if kill -0 "$pid" >/dev/null 2>&1; then
      kill "$pid" >/dev/null 2>&1 || true
      echo "Stopped orphaned $name (PID $pid)."
    fi
  done
}

stop_from_pid_file() {
  local name="$1"
  local pid_file="$2"

  if [[ ! -f "$pid_file" ]]; then
    echo "$name was not started by this script."
    return 0
  fi

  local pid
  pid="$(cat "$pid_file")"

  if kill -0 "$pid" >/dev/null 2>&1; then
    kill "$pid" >/dev/null 2>&1 || true
    echo "Stopped $name (PID $pid)."
  else
    echo "$name PID $pid is not running."
  fi

  rm -f "$pid_file"
}

stop_from_pid_file "frontend" "$frontend_pid_file"

if systemd_runner_available; then
  if systemctl is-active --quiet "$backend_unit"; then
    systemctl stop "$backend_unit"
    echo "Stopped backend systemd unit ($backend_unit)."
  fi
  if systemctl is-active --quiet "$worker_unit"; then
    systemctl stop "$worker_unit"
    echo "Stopped worker systemd unit ($worker_unit)."
  fi
  systemctl reset-failed "$backend_unit" >/dev/null 2>&1 || true
  systemctl reset-failed "$worker_unit" >/dev/null 2>&1 || true
fi

stop_from_pid_file "backend" "$pid_dir/backend.pid"
stop_from_pid_file "worker" "$pid_dir/worker.pid"
stop_matching_processes "frontend process" "$repo_root/frontend" "--host 0.0.0.0 --port 5173"
stop_matching_processes "backend process" "$repo_root/backend/.venv/bin/python -m uvicorn app.main:app"
stop_matching_processes "worker process" "$repo_root/backend" "app.worker.runner"
rm -f "$worker_ready_file"
