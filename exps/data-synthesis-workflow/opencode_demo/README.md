# OpenCode 环境生成 Demo

根据 skill 目录，调用本地 OpenCode CLI 的 `run` 命令，使用 `prompts/skill_to_environment.md` 提示词，生成可运行的 MCP 环境目录。

## 前置条件

1. **安装 OpenCode CLI**：
   ```bash
   curl -fsSL https://opencode.ai/install | bash
   # 或：npm install -g opencode-ai
   # 或：bun install -g opencode-ai
   ```
2. **验证安装**：`opencode --version`
3. **完成认证**：`opencode auth login`（配置至少一个 LLM 提供商）

## 运行

在项目根目录执行：

```bash
uv run python exps/data-synthesis-workflow/opencode_demo/run_opencode_env_gen.py
```

或使用 `python` 直接运行（需确保在正确虚拟环境中）：

```bash
python exps/data-synthesis-workflow/opencode_demo/run_opencode_env_gen.py
```

### 自定义路径

```bash
python exps/data-synthesis-workflow/opencode_demo/run_opencode_env_gen.py \
  --skill-dir /path/to/your/skill-dir \
  --env-dir /path/to/output/env-dir
```

## 输入

- **提示词**：`exps/data-synthesis-workflow/prompts/skill_to_environment.md`
- **Skill 目录**（默认）：`exps/data-synthesis-workflow/2896_prediction-trader`
- **目标环境目录**（默认）：`exps/data-synthesis-workflow/prediction-trader`

脚本会将提示词中的 `{SKILL_DIR}`、`{ENV_DIR}` 占位符替换为实际路径，构造任务后调用 `opencode run`。

## 输出

- OpenCode 在 `--env-dir` 的父目录下作为工作目录运行
- 按提示词约定，在 `--env-dir` 下生成 MCP 环境（mcp_server.py、tools/、tools.jsonl、docker/、mocks/ 等）
- 控制台输出 OpenCode 的实时输出与退出码

## 说明

- 脚本仅使用 Python 标准库（subprocess、pathlib、argparse），无额外依赖
- 若目标 env 目录已存在，OpenCode 可能在其中增删改文件；建议先备份或使用新建目录
- 生成耗时取决于 OpenCode 与 LLM 调用，请耐心等待
