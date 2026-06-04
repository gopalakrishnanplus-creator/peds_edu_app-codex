from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from django.conf import settings
from django.utils import timezone


TRUE_VALUES = {"1", "true", "yes", "on"}
FALSE_VALUES = {"0", "false", "no", "off"}


def v2_switch_path() -> Path:
    configured = os.getenv("PE_V2_SWITCH_FILE", "").strip()
    if configured:
        return Path(configured).expanduser().resolve()
    return Path(settings.BASE_DIR) / "output" / "pe_v2_runtime_switch.json"


def is_v2_enabled() -> bool:
    env_value = os.getenv("PE_USE_V2_TABLES", "").strip().lower()
    if env_value in TRUE_VALUES:
        return True
    if env_value in FALSE_VALUES:
        return False

    path = v2_switch_path()
    if not path.exists():
        return False
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return False
    return bool(payload.get("enabled"))


def activate_v2_tables(
    *,
    batch_id: str,
    database_name: str,
    report_dir: str,
    activated_by: str,
) -> Path:
    path = v2_switch_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload: dict[str, Any] = {
        "enabled": True,
        "batch_id": batch_id,
        "database_name": database_name,
        "report_dir": report_dir,
        "activated_by": activated_by,
        "activated_at": timezone.now().isoformat(),
    }
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    tmp_path.replace(path)
    return path
