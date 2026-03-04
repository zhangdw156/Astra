# Astra — Agentic Skill & TRAce

A data factory for generating high-quality multi-turn tool-use conversation trajectories. These trajectories are used to fine-tune small language models to improve their agentic capabilities.

## Overview

- **Skill Registry**: Collect and standardize Skills (Anthropic-style tool definitions)
- **Blueprint Engine**: Create mission blueprints (context, requirements, planned tool sequences)
- **Execution & Trace**: Teacher agent executes blueprints against mock environments
- **Optimization**: Filter and refine traces into fine-tuning datasets

## Project Structure

```
Astra/
├── src/astra/          # Core package
│   └── configs/        # Hydra configuration
├── exps/               # Experiments (early-stage logic)
├── skillshub/          # Collected skills (raw)
├── skills/             # Curated skills for use
├── artifacts/          # Generated blueprints & traces
├── docs/               # Documentation
└── tests/              # Test suite
```

## Quick Start

```bash
# Install with uv
uv sync

# Run the CLI (Hydra + Rich + Loguru)
uv run astra

# Override config from CLI
uv run astra skill.validation.strict_schema=false
```

## Development

```bash
uv sync --all-groups   # Include dev dependencies
uv run pytest          # Run tests
uv run ruff check .    # Lint
```

## License

MIT
