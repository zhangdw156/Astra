# OpenCode 环境生成 Demo

根据 skill 目录，调用本地 OpenCode CLI 的 `run` 命令，使用 `prompts/skill_to_environment.md` 提示词，生成可运行的 MCP 环境目录。任务会显式指示 OpenCode **先阅读参考示例**（skill → env 的生成前后目录对），再按相同模式生成目标环境。

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

### 参数说明

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--ref-skill-dir` | `opencode_demo/2896_prediction-trader` | 参考 skill 目录（OpenCode 需先阅读） |
| `--ref-env-dir` | `opencode_demo/env_2896_prediction-trader` | 参考 env 目录（生成的示例） |
| `--skill-dir` | `skills_demo/2515_stock-monitor` | 要转换的 skill 目录 |
| `--env-dir` | `exps/data-synthesis-workflow/env_2515_stock-monitor` | 生成环境的目标目录 |

### 自定义路径

```bash
python exps/data-synthesis-workflow/opencode_demo/run_opencode_env_gen.py \
  --ref-skill-dir opencode_demo/2896_prediction-trader \
  --ref-env-dir opencode_demo/env_2896_prediction-trader \
  --skill-dir /path/to/skill \
  --env-dir /path/to/output/env-dir
```

## 输入

- **提示词**：`exps/data-synthesis-workflow/prompts/skill_to_environment.md`
- **参考示例**（默认）：`opencode_demo/2896_prediction-trader` → `opencode_demo/env_2896_prediction-trader`
- **目标 skill**（默认）：`skills_demo/2515_stock-monitor`
- **目标 env**（默认）：`exps/data-synthesis-workflow/env_2515_stock-monitor`

脚本会替换 `{REF_SKILL_DIR}`、`{REF_ENV_DIR}`、`{SKILL_DIR}`、`{ENV_DIR}`，并在任务开头显式指示 OpenCode 先阅读参考目录，再生成。

## 输出

- OpenCode 以项目根为工作目录运行，便于访问参考目录与 `skills_demo`
- 按提示词约定，在 `--env-dir` 下生成 MCP 环境（mcp_server.py、tools/、tools.jsonl、docker/、mocks/ 等）
- 控制台输出 OpenCode 的实时输出与退出码

## 说明

- 脚本仅使用 Python 标准库（subprocess、pathlib、argparse），无额外依赖
- 若目标 env 目录已存在，OpenCode 可能在其中增删改文件；建议先备份或使用新建目录
- 生成耗时取决于 OpenCode 与 LLM 调用，请耐心等待
