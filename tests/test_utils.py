import json
import os
import time

from src.utils import new_trace_path, prune_traces, serialize_trace


def test_serialize_trace_writes_valid_json(tmp_path):
    output_path = tmp_path / "nested" / "trace_1.json"

    serialize_trace({"status": "SUCCESS"}, output_path)

    assert json.loads(output_path.read_text(encoding="utf-8")) == {"status": "SUCCESS"}
    assert not output_path.with_suffix(".json.tmp").exists()


def test_new_trace_path_is_unique(tmp_path):
    paths = {new_trace_path(tmp_path) for _ in range(50)}

    assert len(paths) == 50
    assert all(path.startswith(str(tmp_path)) for path in paths)


def test_prune_traces_keeps_most_recent(tmp_path):
    for index in range(5):
        path = tmp_path / f"trace_{index}.json"
        path.write_text("{}", encoding="utf-8")
        timestamp = time.time() - (10 - index)
        os.utime(path, (timestamp, timestamp))

    prune_traces(tmp_path, keep=2)

    remaining = sorted(path.name for path in tmp_path.glob("trace_*.json"))
    assert remaining == ["trace_3.json", "trace_4.json"]
