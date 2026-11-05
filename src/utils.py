import json
import logging
import os
import random
import uuid
from datetime import datetime
from pathlib import Path

import numpy as np
import torch

_LOGGER = logging.getLogger("medsovereign")
_LOG_FORMAT = "[%(name)s] [%(asctime)s] %(message)s"
_DATE_FORMAT = "%m/%d - %H:%M"


def configure_logging(level=logging.INFO):
    """Configure the package logger once, without duplicating handlers on reload."""
    if _LOGGER.handlers:
        return

    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(_LOG_FORMAT, datefmt=_DATE_FORMAT))
    _LOGGER.addHandler(handler)
    _LOGGER.setLevel(level)
    _LOGGER.propagate = False


def set_determinism(seed=42):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False


def log_message(category, message, log_file=None):
    formatted_message = f"[{category.upper()}] {message}"
    _LOGGER.info(formatted_message)

    if log_file:
        Path(log_file).parent.mkdir(parents=True, exist_ok=True)
        with open(log_file, "a", encoding="utf-8") as handle:
            handle.write(f"{datetime.now().isoformat()} {formatted_message}\n")


def new_trace_path(output_dir):
    """Return a collision-free trace path (time alone breaks under concurrency)."""
    timestamp = int(datetime.now().timestamp() * 1000)
    return os.path.join(str(output_dir), f"trace_{timestamp}_{uuid.uuid4().hex[:8]}.json")


def serialize_trace(trace_dict, out_path):
    """Write a trace atomically so a crash cannot leave a truncated JSON file."""
    path = Path(out_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_suffix(path.suffix + ".tmp")

    with open(temporary_path, "w", encoding="utf-8") as handle:
        json.dump(trace_dict, handle, indent=4, ensure_ascii=False)
        handle.flush()
        os.fsync(handle.fileno())

    os.replace(temporary_path, path)


def prune_traces(output_dir, keep=200):
    """Keep the most recent `keep` trace files and delete the rest."""
    directory = Path(output_dir)
    if not directory.is_dir():
        return

    traces = sorted(
        directory.glob("trace_*.json"),
        key=lambda item: item.stat().st_mtime,
        reverse=True,
    )

    for stale_trace in traces[keep:]:
        try:
            stale_trace.unlink()
        except OSError as exc:
            _LOGGER.warning("Could not delete old trace %s: %s", stale_trace, exc)
