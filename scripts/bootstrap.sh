#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
backend_dir="$repo_root/backend"
frontend_dir="$repo_root/frontend"
python_bin="${PYTHON_BIN:-python3}"
venv_dir="$backend_dir/.venv"
piper_default_voice="${PIPER_DEFAULT_VOICE:-en_US-lessac-medium}"
piper_voice_matrix="${PIPER_VOICE_MATRIX:-en_US-lessac-medium}"
voice_dir="$backend_dir/data/models/piper"
default_model_path="$voice_dir/default.onnx"
default_model_config_path="$voice_dir/default.onnx.json"
kokoro_dir="$backend_dir/data/models/kokoro"
kokoro_model_path="$kokoro_dir/kokoro-v1.0.onnx"
kokoro_voices_path="$kokoro_dir/voices-v1.0.bin"
kokoro_model_url="${KOKORO_MODEL_URL:-https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx}"
kokoro_voices_url="${KOKORO_VOICES_URL:-https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin}"

export DEBIAN_FRONTEND=noninteractive

apt_command=(apt-get)
if [[ "${EUID:-$(id -u)}" -ne 0 ]]; then
  if ! command -v sudo >/dev/null 2>&1; then
    echo "This setup needs root privileges to install system packages. Install sudo or rerun as root." >&2
    exit 1
  fi
  apt_command=(sudo apt-get)
fi

"${apt_command[@]}" update
"${apt_command[@]}" install -y python3-venv python3-pip ffmpeg libsndfile1 sox curl espeak-ng

if ! "$python_bin" -c 'import sys; raise SystemExit(0 if (3, 12) <= sys.version_info[:2] < (3, 15) else 1)'; then
  echo "Open Choice Reader requires Python 3.12 through 3.14. Set PYTHON_BIN to a supported interpreter." >&2
  exit 1
fi

if ! command -v node >/dev/null 2>&1 || ! command -v npm >/dev/null 2>&1; then
  echo "Node.js 22.12 or newer and npm are required. Install them before running this script." >&2
  exit 1
fi

if ! node -e 'const [major, minor] = process.versions.node.split(".").map(Number); process.exit(major > 22 || (major === 22 && minor >= 12) ? 0 : 1)'; then
  echo "Open Choice Reader requires Node.js 22.12 or newer; found $(node --version)." >&2
  exit 1
fi

"$python_bin" -m venv "$venv_dir"
source "$venv_dir/bin/activate"

python -m pip install --upgrade pip
backend_extras="${OPEN_CHOICE_READER_EXTRAS:-}"
backend_package="$backend_dir"
if [[ -n "$backend_extras" ]]; then
  backend_package="${backend_dir}[${backend_extras}]"
fi
python -m pip install -e "$backend_package"

download_if_missing() {
  local url="$1"
  local output_path="$2"
  if [[ -f "$output_path" ]]; then
    return 0
  fi

  mkdir -p "$(dirname "$output_path")"
  curl --fail --location --retry 3 "$url" -o "$output_path"
}

mkdir -p "$voice_dir"
IFS=',' read -r -a piper_voices <<< "$piper_voice_matrix"
for voice_name in "${piper_voices[@]}"; do
  python -m piper.download_voices --download-dir "$voice_dir" "$voice_name"
done
ln -sfn "${piper_default_voice}.onnx" "$default_model_path"
ln -sfn "${piper_default_voice}.onnx.json" "$default_model_config_path"

if [[ "${DOWNLOAD_KOKORO_MODELS:-0}" == "1" ]]; then
  mkdir -p "$kokoro_dir"
  download_if_missing "$kokoro_model_url" "$kokoro_model_path"
  download_if_missing "$kokoro_voices_url" "$kokoro_voices_path"
fi

(
  cd "$frontend_dir"
  npm ci
)

echo "Open Choice Reader bootstrap complete."
echo "Backend venv: $venv_dir"
echo "Piper voices: ${piper_voices[*]}"
echo "Default model path: $default_model_path"
if [[ "${DOWNLOAD_KOKORO_MODELS:-0}" == "1" ]]; then
  echo "Kokoro model path: $kokoro_model_path"
  echo "Kokoro voices path: $kokoro_voices_path"
fi
