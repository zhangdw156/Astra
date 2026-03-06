"""领域摘要：从 NDJSON 构建或从预生成文件读取。"""

from pathlib import Path

from loguru import logger

DOMAIN_SUMMARY_FILENAME = "domain_summary.txt"


def get_domain_summary(data_dir: Path | None = None) -> str:
    """
    读取domain_summary.txt
    """
    if data_dir:
        data_dir = data_dir.resolve()
        summary_in_data = data_dir / DOMAIN_SUMMARY_FILENAME
        if summary_in_data.is_file():
            try:
                return summary_in_data.read_text(encoding="utf-8").strip()
            except OSError:
                pass
    logger.warning("未找到 {}，请检查 prompts_dir 是否包含该文件", DOMAIN_SUMMARY_FILENAME)
    return ""
