from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any


def to_jsonable(obj: Any) -> Any:
    """
    将 dataclass / Path / 基础容器递归转换为可 JSON 序列化的对象。
    """
    if is_dataclass(obj):
        return to_jsonable(asdict(obj))

    if isinstance(obj, Path):
        return str(obj)

    if isinstance(obj, dict):
        return {str(k): to_jsonable(v) for k, v in obj.items()}

    if isinstance(obj, list):
        return [to_jsonable(x) for x in obj]

    if isinstance(obj, tuple):
        return [to_jsonable(x) for x in obj]

    return obj


class ArtifactStore:
    """
    统一管理 batch artifacts 的落盘。

    约定：
    - output_root / {sample_index} / blueprint.json
    - output_root / {sample_index} / trajectory.json
    - output_root / {sample_index} / evaluation.json
    - output_root / manifest.jsonl
    - output_root / summary.json
    """

    def __init__(self, output_root: Path):
        self.output_root = output_root.resolve()
        self.output_root.mkdir(parents=True, exist_ok=True)
        self.manifest_path = self.output_root / "manifest.jsonl"
        self.summary_path = self.output_root / "summary.json"

    def sample_dir(self, sample_index: int) -> Path:
        path = self.output_root / str(sample_index)
        path.mkdir(parents=True, exist_ok=True)
        return path

    def write_blueprint(self, sample_index: int, blueprint: Any) -> Path:
        path = self.sample_dir(sample_index) / "blueprint.json"
        self._write_json(path, blueprint)
        return path

    def write_trajectory(self, sample_index: int, trajectory: Any) -> Path:
        path = self.sample_dir(sample_index) / "trajectory.json"
        self._write_json(path, trajectory)
        return path

    def write_evaluation(self, sample_index: int, evaluation: Any) -> Path:
        path = self.sample_dir(sample_index) / "evaluation.json"
        self._write_json(path, evaluation)
        return path

    def append_manifest_record(self, record: dict[str, Any]) -> None:
        self.manifest_path.parent.mkdir(parents=True, exist_ok=True)
        with self.manifest_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(to_jsonable(record), ensure_ascii=False) + "\n")

    def write_summary(self, summary: Any) -> Path:
        self._write_json(self.summary_path, summary)
        return self.summary_path

    def _write_json(self, path: Path, data: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(to_jsonable(data), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )