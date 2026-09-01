"""Securely inspect and configure CheapVibeCode on the production VPS.

The API key is accepted only through hidden local input and is transferred to
the VPS only through SSH stdin. It is never included in command arguments or
printed by this script.
"""

import argparse
import getpass
import json
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List


DEFAULT_BASE_URL = "https://cheapvibecode.ru/v1"
DEFAULT_MODEL = "qwen3.8-max"
PUBLIC_PRICING_URL = "https://ru.cheapvibecode.ru/api/public/pricing"
DEFAULT_HOST = "root@82.38.96.250"
DEFAULT_IDENTITY = Path.home() / ".ssh" / "cline_pyaterochka_ed25519"
DEFAULT_APP_PATH = "/opt/telegram-crypto-news"
DEFAULT_SERVICE = "telegram-crypto-news.service"


def build_ssh_command(args: argparse.Namespace, remote_command: str) -> List[str]:
    return [
        "ssh",
        "-i",
        str(args.identity_file),
        "-o",
        "BatchMode=yes",
        "-o",
        "IdentitiesOnly=yes",
        "-o",
        "ConnectTimeout=12",
        args.host,
        remote_command,
    ]


def run_remote_python(
    args: argparse.Namespace,
    source: str,
    payload: Dict[str, Any],
) -> str:
    remote_command = f"python3 -c {shlex.quote(source)}"
    result = subprocess.run(
        build_ssh_command(args, remote_command),
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        timeout=90,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(f"Remote command failed (exit {result.returncode})")
    return result.stdout.strip()


def fetch_models(args: argparse.Namespace, api_key: str) -> List[Dict[str, Any]]:
    source = r'''
import json
import sys
import urllib.error
import urllib.request

payload = json.load(sys.stdin)
url = payload["base_url"].rstrip("/") + "/models"
request = urllib.request.Request(
    url,
    headers={
        "Authorization": "Bearer " + payload["api_key"],
        "Accept": "application/json",
        "User-Agent": "telegram-crypto-news-config/1.0",
    },
)
try:
    with urllib.request.urlopen(request, timeout=20) as response:
        data = json.load(response)
except urllib.error.HTTPError as error:
    raise SystemExit("MODEL_REQUEST_HTTP_" + str(error.code))

models = data.get("data", data if isinstance(data, list) else [])
safe_models = []
allowed = {
    "id", "name", "owned_by", "context_length", "max_context_length",
    "pricing", "prompt_price", "completion_price", "input_price",
    "output_price",
}
for model in models:
    if not isinstance(model, dict) or not model.get("id"):
        continue
    safe_models.append({key: model[key] for key in allowed if key in model})
print(json.dumps(safe_models, ensure_ascii=False))
'''
    output = run_remote_python(
        args,
        source,
        {"api_key": api_key, "base_url": args.base_url},
    )
    models = json.loads(output)
    if not isinstance(models, list):
        raise RuntimeError("Unexpected model catalog response")
    return sorted(models, key=lambda item: item["id"])


def fetch_public_pricing() -> List[Dict[str, Any]]:
    import urllib.request

    request = urllib.request.Request(
        PUBLIC_PRICING_URL,
        headers={
            "Accept": "application/json",
            "User-Agent": "telegram-crypto-news-config/1.0",
        },
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        payload = json.load(response)

    models = []
    for item in payload.get("pricing_tiers", []):
        if not isinstance(item, dict) or not item.get("model"):
            continue
        multiplier = float(item["multiplier"])
        models.append({
            "id": item["model"],
            "multiplier": multiplier,
            "cost_rub_per_1m_min_topup": round(multiplier * 3.2, 6),
            "supports_vision": bool(item.get("supports_vision")),
            "input_modalities": item.get("input_modalities", []),
        })
    return sorted(models, key=lambda item: (item["multiplier"], item["id"]))


def print_models(models: List[Dict[str, Any]]) -> None:
    if not models:
        print("Провайдер вернул пустой список моделей.")
        return

    print("Доступные модели CheapVibeCode:")
    for index, model in enumerate(models, start=1):
        details = []
        for key in (
            "context_length",
            "max_context_length",
            "prompt_price",
            "completion_price",
            "input_price",
            "output_price",
            "pricing",
            "multiplier",
            "cost_rub_per_1m_min_topup",
            "supports_vision",
            "input_modalities",
        ):
            if key in model:
                details.append(f"{key}={model[key]}")
        suffix = f" ({', '.join(details)})" if details else ""
        print(f"{index:>2}. {model['id']}{suffix}")


def connectivity_check(
    args: argparse.Namespace,
    api_key: str,
    model: str,
) -> None:
    source = r'''
import json
import sys
import urllib.error
import urllib.request

payload = json.load(sys.stdin)
url = payload["base_url"].rstrip("/") + "/chat/completions"
body = json.dumps({
    "model": payload["model"],
    "messages": [{"role": "user", "content": "Reply with OK."}],
    "temperature": 0,
    "max_tokens": 5,
}).encode("utf-8")
request = urllib.request.Request(
    url,
    data=body,
    headers={
        "Authorization": "Bearer " + payload["api_key"],
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "telegram-crypto-news-config/1.0",
    },
    method="POST",
)
try:
    with urllib.request.urlopen(request, timeout=30) as response:
        data = json.load(response)
except urllib.error.HTTPError as error:
    raise SystemExit("CONNECTIVITY_HTTP_" + str(error.code))
if not data.get("choices"):
    raise SystemExit("CONNECTIVITY_INVALID_RESPONSE")
print("CONNECTIVITY_OK")
'''
    output = run_remote_python(
        args,
        source,
        {
            "api_key": api_key,
            "base_url": args.base_url,
            "model": model,
        },
    )
    if output != "CONNECTIVITY_OK":
        raise RuntimeError("Unexpected connectivity-check result")


def update_remote_environment(
    args: argparse.Namespace,
    api_key: str,
    model: str,
) -> str:
    source = r'''
import json
import os
import shutil
import sys
import tempfile
import time

payload = json.load(sys.stdin)
env_path = os.path.join(payload["app_path"], ".env")
backup_dir = os.path.join(payload["app_path"], "backups")
os.makedirs(backup_dir, exist_ok=True)
backup_path = os.path.join(
    backup_dir,
    ".env.pre-cheapvibecode-" + str(int(time.time())),
)
shutil.copy2(env_path, backup_path)
os.chmod(backup_path, 0o600)
updates = {
    "CHEAPVIBECODE_API_KEY": payload["api_key"],
    "CHEAPVIBECODE_BASE_URL": payload["base_url"],
    "CHEAPVIBECODE_MODEL": payload["model"],
    "AI_MAX_RETRIES": "3",
    "AI_BACKOFF_FACTOR": "2",
    "AI_TIMEOUT": "60",
    "AI_MAX_TOKENS": "500",
    "AI_TRANSLATION_MAX_TOKENS": "800",
    "AI_TEMPERATURE": "0.3",
}
with open(env_path, "r", encoding="utf-8") as handle:
    lines = handle.read().splitlines()

written = set()
result = []
for line in lines:
    stripped = line.lstrip()
    if not stripped or stripped.startswith("#") or "=" not in line:
        result.append(line)
        continue
    key = line.split("=", 1)[0].strip()
    if key in updates:
        result.append(key + "=" + json.dumps(updates[key]))
        written.add(key)
    else:
        result.append(line)
for key, value in updates.items():
    if key not in written:
        result.append(key + "=" + json.dumps(value))

directory = os.path.dirname(env_path)
fd, temporary_path = tempfile.mkstemp(prefix=".env.", dir=directory, text=True)
try:
    os.fchmod(fd, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write("\n".join(result) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary_path, env_path)
    os.chmod(env_path, 0o600)
finally:
    if os.path.exists(temporary_path):
        os.unlink(temporary_path)
print(json.dumps({"status": "ENV_UPDATED", "backup_path": backup_path}))
'''
    output = run_remote_python(
        args,
        source,
        {
            "api_key": api_key,
            "base_url": args.base_url,
            "model": model,
            "app_path": args.app_path,
        },
    )
    result = json.loads(output)
    if result.get("status") != "ENV_UPDATED":
        raise RuntimeError("Unexpected environment-update result")
    return result["backup_path"]


def restart_and_check(args: argparse.Namespace, backup_path: str) -> None:
    remote = (
        "set -e; "
        f"systemctl restart {shlex.quote(args.service)}; "
        "sleep 12; "
        f"systemctl is-active --quiet {shlex.quote(args.service)}; "
        "test \"$(curl -sS -o /dev/null -w '%{http_code}' --max-time 5 "
        "http://127.0.0.1:8000/health)\" = 200; "
        "test \"$(curl -sS -o /dev/null -w '%{http_code}' --max-time 5 "
        "http://127.0.0.1:9090/health)\" = 200; "
        "echo SERVICE_HEALTHY"
    )
    result = subprocess.run(
        build_ssh_command(args, remote),
        text=True,
        capture_output=True,
        timeout=60,
        check=False,
    )
    if result.returncode == 0 and result.stdout.strip() == "SERVICE_HEALTHY":
        return

    rollback = (
        "set -e; "
        f"cp {shlex.quote(backup_path)} "
        f"{shlex.quote(args.app_path + '/.env')}; "
        f"chmod 600 {shlex.quote(args.app_path + '/.env')}; "
        f"systemctl restart {shlex.quote(args.service)}; "
        "echo ROLLBACK_COMPLETE"
    )
    subprocess.run(
        build_ssh_command(args, rollback),
        text=True,
        capture_output=True,
        timeout=60,
        check=False,
    )
    raise RuntimeError("Service health check failed; previous environment restored")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--list-models", action="store_true")
    mode.add_argument("--configure", action="store_true")
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help=f"Exact model ID (default: {DEFAULT_MODEL})",
    )
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--identity-file", type=Path, default=DEFAULT_IDENTITY)
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--app-path", default=DEFAULT_APP_PATH)
    parser.add_argument("--service", default=DEFAULT_SERVICE)
    args = parser.parse_args()
    return args


def main() -> int:
    args = parse_args()
    if args.list_models:
        print_models(fetch_public_pricing())
        return 0

    if not args.identity_file.is_file():
        raise RuntimeError(f"SSH identity file not found: {args.identity_file}")

    api_key = getpass.getpass("CheapVibeCode API key (hidden): ").strip()
    if not api_key:
        raise RuntimeError("API key is empty")

    models = fetch_models(args, api_key)

    model_ids = {item["id"] for item in models}
    if args.model not in model_ids:
        raise RuntimeError("Selected model is not present in the provider catalog")

    connectivity_check(args, api_key, args.model)
    print("Connectivity check: OK")
    backup_path = update_remote_environment(args, api_key, args.model)
    restart_and_check(args, backup_path)
    print(f"Configured model: {args.model}")
    print("Service health: OK")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RuntimeError, subprocess.SubprocessError, json.JSONDecodeError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        raise SystemExit(1)