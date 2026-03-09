"""
多轮对话模拟：使用 qwen-agent + prediction-trader MCP 执行蓝图中的查询，收集完整轨迹。

流程：
1. 启动 prediction-trader MCP Docker 容器（需事先运行）
2. 创建 qwen-agent Assistant，连接 MCP 与工具
3. 按蓝图 queries 逐轮模拟 user 发问，agent 调用工具解决问题
4. 收集所有轮次的轨迹并保存为 JSON

依赖：
- pip install "qwen-agent[mcp]" openai python-dotenv
- 项目根 .env：OPENAI_API_KEY、OPENAI_MODEL、OPENAI_BASE_URL（可选）

运行（在项目根目录）：
  python exps/data-synthesis-workflow/agent_demo/run_agent_simulation.py [--blueprint out_blueprint.json]
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
from pathlib import Path

from dotenv import load_dotenv

# 路径
SCRIPT_DIR = Path(__file__).resolve().parent
WORKFLOW_DIR = SCRIPT_DIR.parent
PROJECT_ROOT = WORKFLOW_DIR.parent.parent
BLUEPRINT_DEMO = WORKFLOW_DIR / "blueprint_demo"
PREDICTION_TRADER = WORKFLOW_DIR / "prediction-trader"

# 默认蓝图路径
DEFAULT_BLUEPRINT = BLUEPRINT_DEMO / "out_blueprint.json"
# MCP SSE 端点（prediction-trader 容器默认）
MCP_SSE_URL = "http://localhost:8000/sse"


def load_env() -> None:
    """从项目根加载 .env"""
    load_dotenv(PROJECT_ROOT / ".env")


def ensure_mcp_running() -> bool:
    """检查 MCP 服务是否可达，若未运行则尝试启动 Docker。"""
    try:
        from urllib.request import urlopen

        with urlopen(MCP_SSE_URL, timeout=3):
            return True
    except Exception:
        pass

    # 尝试启动 Docker
    compose_path = PREDICTION_TRADER / "docker" / "docker-compose.yaml"
    if not compose_path.exists():
        print("未找到 docker-compose.yaml，请手动启动 prediction-trader 容器")
        return False

    print("正在启动 prediction-trader MCP 容器...")
    try:
        subprocess.run(
            ["docker", "compose", "-f", str(compose_path), "up", "-d"],
            cwd=PREDICTION_TRADER,
            check=True,
        )
        import time

        time.sleep(5)  # 等待服务就绪
    except subprocess.CalledProcessError as e:
        print(f"Docker 启动失败: {e}")
        return False

    return True


def load_blueprint(path: Path) -> dict:
    """加载任务蓝图（须含 system_message 与 queries）"""
    data = json.loads(path.read_text(encoding="utf-8"))
    if "system_message" not in data:
        raise ValueError("蓝图中缺少 system_message 字段")
    if "queries" not in data:
        raise ValueError("蓝图中缺少 queries 字段")
    return data


def build_llm_config() -> dict:
    """根据 .env 构建 LLM 配置（OpenAI 兼容）"""
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    model = os.environ.get("OPENAI_MODEL", "").strip()
    base_url = os.environ.get("OPENAI_BASE_URL", "").strip() or None
    if not api_key or not model:
        raise SystemExit("请在项目根 .env 中配置 OPENAI_API_KEY 和 OPENAI_MODEL")
    cfg = {
        "model": model,
        "model_type": "oai",
        "model_server": base_url or "https://api.openai.com/v1",
        "api_key": api_key,
    }
    return cfg


def _content_to_text(content) -> str:
    """从 Message.content（str 或 List[ContentItem]）提取纯文本"""
    if isinstance(content, str):
        return content or ""
    if isinstance(content, list):
        return "".join(
            (getattr(item, "text", None) or "") for item in content
        )
    return ""


def get_agent_system_prompt(agent) -> str:
    """调用 qwen-agent LLM 的 _preprocess_messages，得到 agent 实际看到的完整系统提示词（含注入的工具描述）。"""
    from qwen_agent.llm.schema import SYSTEM, ContentItem, Message

    system_message = getattr(agent, "system_message", "") or ""
    functions = [func.function for func in agent.function_map.values()]
    messages = [
        Message(role=SYSTEM, content=[ContentItem(text=system_message)])
    ]
    generate_cfg = {
        "parallel_function_calls": True,
        "function_choice": "auto",
    }
    if functions and hasattr(agent.llm, "_preprocess_messages"):
        messages = agent.llm._preprocess_messages(
            messages=messages,
            lang="en",
            generate_cfg=generate_cfg,
            functions=functions,
        )
    if not messages or messages[0].role != SYSTEM:
        return system_message
    return _content_to_text(messages[0].content)


def build_mcp_config() -> dict:
    """构建 MCP 配置，连接 prediction-trader SSE 服务"""
    return {
        "mcpServers": {
            "prediction-trader": {
                "url": MCP_SSE_URL,
                "timeout": 30000,
            }
        }
    }


def create_agent(system_message: str) -> tuple:
    """创建 qwen-agent Assistant，带 MCP 工具。system_message 来自蓝图。返回 (agent, system_message, tools)。"""
    from qwen_agent.agents import Assistant

    msg = system_message.strip()
    llm_cfg = build_llm_config()
    mcp_cfg = build_mcp_config()

    agent = Assistant(
        llm=llm_cfg,
        system_message=msg,
        function_list=[mcp_cfg],
    )
    tools = list(agent.function_map.keys())
    return agent, msg, tools


def run_multi_turn_simulation(agent, blueprint: dict) -> list[dict]:
    """
    按蓝图 queries 逐轮模拟对话，收集完整轨迹。
    返回 trajectory 列表，每项为 {"role", "content", ...}。
    """
    messages: list[dict] = []
    trajectory: list[dict] = []

    for i, item in enumerate(blueprint["queries"]):
        query = item.get("query", "")
        if not query:
            continue

        # 追加 user 消息
        user_msg = {"role": "user", "content": query}
        messages.append(user_msg)
        trajectory.append({"role": "user", "content": query})

        print(f"\n[Turn {i + 1}] User: {query[:80]}...")

        # 调用 agent；run() 迭代产生消息列表，最后一轮为完整新消息
        try:
            last_response: list = []
            for response in agent.run(messages=messages):
                last_response = response if isinstance(response, list) else [response]

            # 将 assistant/function 消息加入 messages 与 trajectory
            for msg in last_response:
                msgs_dict = _message_to_dict(msg)
                if msgs_dict:
                    messages.append(msgs_dict)
                    trajectory.append(msgs_dict)

            # 打印简要进度
            for m in last_response:
                role = m.get("role", "")
                if role == "assistant" and m.get("content"):
                    print(f"  Assistant: {str(m['content'])[:120]}...")
                elif role == "function":
                    print(f"  Tool: {m.get('name', '')} -> {len(str(m.get('content', '')))} chars")

        except Exception as e:
            print(f"  Error: {e}")
            trajectory.append({"role": "assistant", "content": f"[Error] {e}"})

    return trajectory


def _extract_reasoning(content: str) -> tuple[str, str]:
    """从 assistant content 中提取 think 标签内的思考部分，返回 (reasoning, 剩余 content)。"""
    text = content or ""
    reasoning_parts: list[str] = []
    # 匹配 <think>...</think>
    pattern = r"<think>(.*?)</think>"
    for m in re.finditer(pattern, text, re.DOTALL):
        reasoning_parts.append(m.group(1).strip())
    if reasoning_parts:
        reasoning = "\n\n".join(reasoning_parts)
        clean_content = re.sub(pattern, "", text, flags=re.DOTALL).strip()
        return reasoning, clean_content
    return "", text


def _message_to_dict(msg) -> dict | None:
    """将 qwen-agent Message 转为可序列化的 dict，assistant 的 content 若含思考则提取为 reasoning_content"""
    if isinstance(msg, dict):
        d = dict(msg)
    else:
        d = getattr(msg, "__dict__", {}) or {}
        if hasattr(msg, "get"):
            d = dict(msg)
    role = d.get("role")
    if not role:
        return None
    raw_content = d.get("content", "") or ""
    out: dict = {"role": role, "content": raw_content}
    if role == "assistant" and raw_content:
        reasoning, clean_content = _extract_reasoning(raw_content)
        if reasoning:
            out["reasoning_content"] = reasoning
            out["content"] = clean_content
    if "function_call" in d and d["function_call"]:
        out["function_call"] = d["function_call"]
    if "name" in d and d["name"]:
        out["name"] = d["name"]
    return out


def save_trajectory(
    trajectory: list[dict],
    blueprint: dict,
    out_path: Path,
    system_message: str,
    agent_system_prompt: str,
    tools: list,
) -> None:
    """保存轨迹及元数据：原始 system_message、qwen-agent 处理后 agent 看到的 system_prompt、tools、turns"""
    out = {
        "blueprint_id": blueprint.get("blueprint_id", ""),
        "skill_name": blueprint.get("skill_name", ""),
        "persona_id": blueprint.get("persona_id", ""),
        "system_message": system_message,
        "agent_system_prompt": agent_system_prompt,
        "tools": tools,
        "turns": trajectory,
    }
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n轨迹已保存到: {out_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="多轮对话模拟：qwen-agent + prediction-trader MCP")
    parser.add_argument(
        "--blueprint",
        type=Path,
        default=DEFAULT_BLUEPRINT,
        help=f"蓝图 JSON 路径（默认: {DEFAULT_BLUEPRINT}）",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=None,
        help="输出轨迹 JSON 路径（默认: agent_demo/out_trajectory.json）",
    )
    parser.add_argument("--no-docker", action="store_true", help="不自动启动 Docker，仅检查 MCP 是否可达")
    args = parser.parse_args()

    load_env()

    blueprint_path = args.blueprint
    if not blueprint_path.is_absolute():
        blueprint_path = SCRIPT_DIR / blueprint_path
    if not blueprint_path.exists():
        raise SystemExit(f"蓝图文件不存在: {blueprint_path}")

    blueprint = load_blueprint(blueprint_path)
    print(f"加载蓝图: {blueprint_path}, 共 {len(blueprint['queries'])} 轮查询")

    if not args.no_docker and not ensure_mcp_running():
        raise SystemExit("无法连接到 MCP 服务，请确保 prediction-trader 容器已启动。")

    agent, system_message, tools = create_agent(
        system_message=blueprint["system_message"],
    )
    print("Agent 已创建，MCP 工具已加载")

    agent_system_prompt = get_agent_system_prompt(agent)

    trajectory = run_multi_turn_simulation(agent, blueprint)

    out_path = args.output or (SCRIPT_DIR / "out_trajectory.json")
    if not out_path.is_absolute():
        out_path = SCRIPT_DIR / out_path
    save_trajectory(
        trajectory, blueprint, out_path,
        system_message, agent_system_prompt, tools,
    )


if __name__ == "__main__":
    main()
