from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Protocol

from ...utils import logger


class OpenCodeExecutor(Protocol):
    """
    OpenCode 执行器协议。
    """

    def run(self, task_text: str, cwd: Path, verbose: bool = False) -> int:
        """
        执行 opencode run <task_text>，返回 exit code。
        """
        ...


class SubprocessOpenCodeExecutor:
    """
    默认执行器：基于 subprocess 调用本地 opencode CLI。
    """

    def run(self, task_text: str, cwd: Path, verbose: bool = False) -> int:
        """
        verbose=True:
            - 子进程直接继承终端输出，适合调试
        verbose=False:
            - 捕获 stdout/stderr，仅在失败时通过 logger 输出
        """
        if verbose:
            logger.debug("Running opencode in verbose mode, cwd={}", cwd)
            result = subprocess.run(
                ["opencode", "run", task_text],
                cwd=str(cwd),
                capture_output=False,
                text=True,
                check=False,
            )
            logger.debug("OpenCode finished with exit code={}", result.returncode)
            return result.returncode

        logger.debug("Running opencode, cwd={}", cwd)
        result = subprocess.run(
            ["opencode", "run", task_text],
            cwd=str(cwd),
            capture_output=True,
            text=True,
            check=False,
        )

        logger.debug("OpenCode finished with exit code={}", result.returncode)

        if result.returncode != 0:
        stdout = result.stdout.strip()
        stderr = result.stderr.strip()

        logger.error("OpenCode failed with exit code={}", result.returncode)

        if stdout:
            logger.warning("OpenCode stdout:\n{}", stdout)
        if stderr:
            logger.error("OpenCode stderr:\n{}", stderr)

        return result.returncode