"""领域摘要：从 NDJSON 构建或从预生成文件读取。"""

import json
from pathlib import Path

from loguru import logger

DOMAIN_SUMMARY_FILENAME = "domain_summary.txt"


def get_domain_summary(data_dir: Path | None = None) -> str:
    """
    读取domain_summary.txt
    """
    artifacts_dir = artifacts_dir.resolve()
    if data_dir:
        data_dir = data_dir.resolve()
        summary_in_data = data_dir / DOMAIN_SUMMARY_FILENAME
        if summary_in_data.is_file():
            try:
                return summary_in_data.read_text(encoding="utf-8").strip()
            except OSError:
                pass
    summary_file = artifacts_dir / DOMAIN_SUMMARY_FILENAME
    if summary_file.is_file():
        try:
            return summary_file.read_text(encoding="utf-8").strip()
        except OSError:
            pass
