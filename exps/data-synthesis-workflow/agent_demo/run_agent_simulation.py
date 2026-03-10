"""
多轮对话模拟：使用 qwen-agent + prediction-trader MCP 执行蓝图，收集完整轨迹。

支持两种蓝图格式：
1. **动态模式**（新）：蓝图为任务配置 + 交互生成配置，无 queries。由 User Agent 根据对话上下文
   逐轮生成用户消息，与助手 Agent 多轮交互直到任务完成或达到 max_turns。
2. **静态模式**（兼容）：蓝图为 system_message + queries 数组。按 queries 逐轮发送预定义 user 消息。

流程：
1. 启动 prediction-trader MCP Docker 容器（需事先运行）
2. 创建 qwen-agent Assistant，连接 MCP 与工具
3. 动态模式：User Agent 生成 user 消息 -> Assistant 响应 -> 循环直到 [TASK_END] 或 max_turns
   静态模式：按 queries 逐轮发送 user 消息
4. 收集所有轮次的轨迹（turn 结构），并尝试获取 final_state_snapshot

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
import sys
import time
import uuid
from pathlib import Path

from dotenv import load_dotenv

# 路径
SCRIPT_DIR = Path(__file__).resolve().parent
WORKFLOW_DIR = SCRIPT_DIR.parent
PROJECT_ROOT = WORKFLOW_DIR.parent.parent
BLUEPRINT_DEMO = WORKFLOW_DIR / "blueprint_demo"
PREDICTION_TRADER = WORKFLOW_DIR / "opencode_demo" / "env_2896_prediction-trader"

# 默认蓝图路径
DEFAULT_BLUEPRINT = BLUEPRINT_DEMO / "out_blueprint.json"
# MCP SSE 端点（prediction-trader 容器默认）
MCP_SSE_URL = "http://localhost:8000/sse"
# User Agent 提示词
USER_AGENT_PROMPT_PATH = WORKFLOW_DIR / "prompts" / "user_agent.md"

TASK_END_MARKER = "[TASK_END]"


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
        time.sleep(5)  # 等待服务就绪
    except subprocess.CalledProcessError as e:
        print(f"Docker 启动失败: {e}")
        return False

    return True


def load_blueprint(path: Path) -> dict:
    """
    加载任务蓝图。支持两种格式：
    - 新格式：user_intent、user_agent_config、max_turns、end_condition、system_message（无 queries）
    - 旧格式：system_message、queries 数组
    """
    data = json.loads(path.read_text(encoding="utf-8"))
    if "system_message" not in data:
        raise ValueError("蓝图中缺少 system_message 字段")
    # 新格式：动态用户模拟
    if "queries" not in data:
        for f in ("user_intent", "user_agent_config", "max_turns", "end_condition"):
            if f not in data:
                raise ValueError(f"新格式蓝图中缺少 {f} 字段")
        data["_mode"] = "dynamic"
    else:
        data["_mode"] = "static"
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
        return "".join((getattr(item, "text", None) or "") for item in content)
    return ""


def get_agent_system_prompt(agent) -> str:
    """调用 qwen-agent LLM 的 _preprocess_messages，得到 agent 实际看到的完整系统提示词。"""
    from qwen_agent.llm.schema import SYSTEM, ContentItem, Message

    system_message = getattr(agent, "system_message", "") or ""
    functions = [func.function for func in agent.function_map.values()]
    messages = [Message(role=SYSTEM, content=[ContentItem(text=system_message)])]
    generate_cfg = {"parallel_function_calls": True, "function_choice": "auto"}
    if functions and hasattr(agent.llm, "_preprocess_messages"):
        messages = agent.llm._preprocess_messages(
            messages=messages, lang="en", generate_cfg=generate_cfg, functions=functions
        )
    if not messages or messages[0].role != SYSTEM:
        return system_message
    return _content_to_text(messages[0].content)


def build_mcp_config() -> dict:
    """构建 MCP 配置，连接 prediction-trader SSE 服务"""
    return {
        "mcpServers": {
            "prediction-trader": {"url": MCP_SSE_URL, "timeout": 30000}
        }
    }


def _patch_mcp_tool_params():
    """对 qwen_agent MCP 工具的 call 做容错：空/非法 params 规范为 "{}"。"""
    try:
        from qwen_agent.tools import mcp_manager
        import json as _json

        _orig_create = mcp_manager.MCPManager.create_tool_class

        def _normalize_tool_params(params) -> dict:
            if params is None:
                return {}
            if isinstance(params, dict):
                return params
            s = params if isinstance(params, str) else str(params)
            s = (s or "").strip()
            if not s:
                return {}
            try:
                return _json.loads(s)
            except _json.JSONDecodeError:
                return {}

        def _patched_create_tool_class(self, register_name, register_client_id, tool_name, tool_desc, tool_parameters):
            tool_instance = _orig_create(self, register_name, register_client_id, tool_name, tool_desc, tool_parameters)
            orig_call = tool_instance.call

            def _call(params, **kwargs):
                tool_args = _normalize_tool_params(params)
                return orig_call(_json.dumps(tool_args) if tool_args is not None else "{}", **kwargs)

            tool_instance.call = _call
            return tool_instance

        mcp_manager.MCPManager.create_tool_class = _patched_create_tool_class
    except Exception as e:
        import warnings
        warnings.warn(f"MCP params 容错 patch 未生效: {e}", RuntimeWarning)


def create_agent(system_message: str) -> tuple:
    """创建 qwen-agent Assistant，带 MCP 工具。返回 (agent, system_message, tools)。"""
    from qwen_agent.agents import Assistant

    msg = system_message.strip()
    llm_cfg = build_llm_config()
    mcp_cfg = build_mcp_config()
    agent = Assistant(llm=llm_cfg, system_message=msg, function_list=[mcp_cfg])
    tools = list(agent.function_map.keys())
    return agent, msg, tools


def _format_conversation_for_user_agent(messages: list[dict]) -> str:
    """将 messages 格式化为 User Agent 可读的对话历史。"""
    lines: list[str] = []
    for m in messages:
        role = m.get("role", "")
        content = (m.get("content") or "").strip()
        if role == "user":
            lines.append(f"User: {content}")
        elif role == "assistant":
            # 截断过长的 tool 返回
            if len(content) > 1500:
                content = content[:1500] + "\n... [truncated]"
            lines.append(f"Assistant: {content}")
        elif role == "function":
            name = m.get("name", "tool")
            if len(content) > 800:
                content = content[:800] + "\n... [truncated]"
            lines.append(f"[Tool {name}]: {content}")
    return "\n\n".join(lines) if lines else "(No messages yet)"


def generate_user_message(blueprint: dict, messages: list[dict], current_turn: int) -> str:
    """
    调用 User Agent LLM，根据 user_intent、user_agent_config 与对话历史生成下一句 user 消息。
    返回已剥离 <think> 的用户可见消息；若应结束则返回 TASK_END_MARKER。不返回思考内容，轨迹也不保存。
    """
    from openai import OpenAI

    load_dotenv(PROJECT_ROOT / ".env")
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    model = os.environ.get("OPENAI_MODEL", "").strip()
    base_url = os.environ.get("OPENAI_BASE_URL", "").strip() or None
    if not api_key or not model:
        raise SystemExit("请在项目根 .env 中配置 OPENAI_API_KEY 和 OPENAI_MODEL")

    prompt_text = USER_AGENT_PROMPT_PATH.read_text(encoding="utf-8")
    prompt_text = prompt_text.replace("{USER_INTENT}", blueprint.get("user_intent", ""))
    prompt_text = prompt_text.replace(
        "{USER_AGENT_CONFIG}",
        json.dumps(blueprint.get("user_agent_config", {}), ensure_ascii=False),
    )
    prompt_text = prompt_text.replace(
        "{CONVERSATION_HISTORY}",
        _format_conversation_for_user_agent(messages),
    )
    prompt_text = prompt_text.replace("{CURRENT_TURN}", str(current_turn))
    prompt_text = prompt_text.replace("{MAX_TURNS}", str(blueprint.get("max_turns", 8)))
    prompt_text = prompt_text.replace("{END_CONDITION}", blueprint.get("end_condition", ""))

    client = OpenAI(api_key=api_key, base_url=base_url)
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt_text}],
        temperature=0.5,
    )
    raw = (resp.choices[0].message.content or "").strip()
    if TASK_END_MARKER in raw:
        return TASK_END_MARKER
    # 剥离 <think>，只保留用户可见消息；思考内容不保存到轨迹
    cleaned, _ = _strip_think_from_user_agent(raw)
    return cleaned


def _strip_think_from_user_agent(text: str) -> tuple[str, str]:
    """
    从 User Agent 的原始输出中剥离 <think>...</think>，返回 (用户可见消息, 思考内容)。
    若模型把 chain-of-thought 放进回复，避免写入 user_message 污染轨迹。
    """
    if not text:
        return "", ""
    pattern = r"<think>(.*?)</think>"
    thinking_parts: list[str] = []
    for m in re.finditer(pattern, text, re.DOTALL):
        thinking_parts.append(m.group(1).strip())
    if thinking_parts:
        thinking = "\n\n".join(thinking_parts)
        clean = re.sub(pattern, "", text, flags=re.DOTALL).strip()
        return clean, thinking
    return text, ""


def _extract_reasoning(content: str) -> tuple[str, str]:
    """从 assistant content 中提取 think 标签内的思考部分。"""
    text = content or ""
    reasoning_parts: list[str] = []
    pattern = r"<think>(.*?)</think>"
    for m in re.finditer(pattern, text, re.DOTALL):
        reasoning_parts.append(m.group(1).strip())
    if reasoning_parts:
        reasoning = "\n\n".join(reasoning_parts)
        clean_content = re.sub(pattern, "", text, flags=re.DOTALL).strip()
        return reasoning, clean_content
    return "", text


def _message_to_dict(msg) -> dict | None:
    """将 qwen-agent Message 转为可序列化的 dict。"""
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


def _assistant_response_to_turn(
    user_message: str,
    last_response: list,
    start_time: float,
) -> dict:
    """将一轮 user + assistant 响应转换为 turn 结构。不保存 User Agent 的思考内容。"""
    turn: dict = {
        "user_message": user_message,
        "execution_time_ms": int((time.perf_counter() - start_time) * 1000),
    }

    tool_calls: list[dict] = []
    final_assistant_content = ""
    final_reasoning = ""

    i = 0
    while i < len(last_response):
        m = last_response[i]
        md = _message_to_dict(m) if not isinstance(m, dict) else m
        if not md:
            i += 1
            continue
        role = md.get("role", "")
        if role == "assistant":
            final_reasoning = md.get("reasoning_content", "") or ""
            final_assistant_content = md.get("content", "") or ""
            fc = md.get("function_call")
            if fc:
                name = fc.get("name", "")
                args = fc.get("arguments", "{}")
                # 找对应的 function 返回
                result = ""
                for j in range(i + 1, len(last_response)):
                    nm = last_response[j]
                    nd = _message_to_dict(nm) if not isinstance(nm, dict) else nm
                    if nd and nd.get("role") == "function" and nd.get("name") == name:
                        result = nd.get("content", "") or ""
                        break
                tool_calls.append({"name": name, "arguments": args, "result": result[:500]})
        i += 1

    turn["assistant_thinking"] = final_reasoning
    turn["assistant_message"] = final_assistant_content
    turn["tool_calls"] = tool_calls
    return turn


def run_dynamic_simulation(agent, blueprint: dict) -> list[dict]:
    """
    动态模式：User Agent 逐轮生成 user 消息，与 Assistant 交互直到 [TASK_END] 或 max_turns。
    返回 turn 列表。
    """
    messages: list[dict] = []
    turns: list[dict] = []
    max_turns = int(blueprint.get("max_turns", 8))

    for turn_idx in range(1, max_turns + 1):
        start_time = time.perf_counter()
        user_msg = generate_user_message(blueprint, messages, turn_idx)
        if user_msg == TASK_END_MARKER:
            print(f"\n[Turn {turn_idx}] User Agent 结束任务")
            break

        print(f"\n[Turn {turn_idx}] User: {user_msg[:80]}...")
        # Assistant 只允许看到“用户说出的话”（user_msg），绝不能看到 user_thinking
        user_dict = {"role": "user", "content": user_msg}
        messages.append(user_dict)

        try:
            last_response: list = []
            for response in agent.run(messages=messages):
                last_response = response if isinstance(response, list) else [response]

            for msg in last_response:
                msgs_dict = _message_to_dict(msg)
                if msgs_dict:
                    messages.append(msgs_dict)

            for m in last_response:
                role = m.get("role", "")
                if role == "assistant" and m.get("content"):
                    print(f"  Assistant: {str(m['content'])[:120]}...")
                elif role == "function":
                    print(f"  Tool: {m.get('name', '')} -> {len(str(m.get('content', '')))} chars")

            turn = _assistant_response_to_turn(user_msg, last_response, start_time)
            turn["turn_index"] = turn_idx
            turns.append(turn)

        except Exception as e:
            print(f"  Error: {e}")
            turn = {
                "turn_index": turn_idx,
                "user_message": user_msg,
                "assistant_thinking": "",
                "assistant_message": f"[Error] {e}",
                "tool_calls": [],
                "execution_time_ms": int((time.perf_counter() - start_time) * 1000),
            }
            turns.append(turn)

    return turns


def run_static_simulation(agent, blueprint: dict) -> list[dict]:
    """
    静态模式：按 queries 逐轮发送 user 消息，收集 assistant 响应。
    返回 turn 列表（与动态模式结构一致）。
    """
    messages: list[dict] = []
    turns: list[dict] = []

    for i, item in enumerate(blueprint["queries"]):
        query = item.get("query", "")
        if not query:
            continue

        start_time = time.perf_counter()
        user_dict = {"role": "user", "content": query}
        messages.append(user_dict)

        print(f"\n[Turn {i + 1}] User: {query[:80]}...")

        try:
            last_response: list = []
            for response in agent.run(messages=messages):
                last_response = response if isinstance(response, list) else [response]

            for msg in last_response:
                msgs_dict = _message_to_dict(msg)
                if msgs_dict:
                    messages.append(msgs_dict)

            for m in last_response:
                role = m.get("role", "")
                if role == "assistant" and m.get("content"):
                    print(f"  Assistant: {str(m['content'])[:120]}...")
                elif role == "function":
                    print(f"  Tool: {m.get('name', '')} -> {len(str(m.get('content', '')))} chars")

            turn = _assistant_response_to_turn(query, last_response, start_time)
            turn["turn_index"] = i + 1
            turns.append(turn)

        except Exception as e:
            print(f"  Error: {e}")
            turn = {
                "turn_index": i + 1,
                "user_message": query,
                "assistant_thinking": "",
                "assistant_message": f"[Error] {e}",
                "tool_calls": [],
                "execution_time_ms": int((time.perf_counter() - start_time) * 1000),
            }
            turns.append(turn)

    return turns


def validate_trajectory(
    turns: list[dict],
    blueprint: dict,
    final_state_snapshot: dict | None,
) -> dict:
    """
    轨迹验证：基于输出与可选的基于状态的检查。
    返回 {"output_based": {"passed": bool, "reason": str}, "state_based": {"passed": bool|None, "reason": str}}
    """
    result: dict = {
        "output_based": {"passed": False, "reason": ""},
        "state_based": {"passed": None, "reason": "skipped"},
    }

    # 基于输出的验证
    expected_output = blueprint.get("expected_output", "")
    last_assistant_msg = ""
    if turns:
        last_assistant_msg = turns[-1].get("assistant_message", "")
    if expected_output:
        # 简单检查：最终回复非空且非错误
        if last_assistant_msg and "[Error]" not in last_assistant_msg:
            result["output_based"]["passed"] = True
            result["output_based"]["reason"] = "助手已生成最终回复，可与 expected_output 人工对比"
        else:
            result["output_based"]["passed"] = False
            result["output_based"]["reason"] = f"最终回复异常或为空。expected_output: {expected_output[:100]}..."
    else:
        result["output_based"]["passed"] = True
        result["output_based"]["reason"] = "蓝图无 expected_output，跳过"

    # 基于状态的验证（需 expected_final_state 与 final_state_snapshot）
    if blueprint.get("expected_final_state") and final_state_snapshot:
        # 仅做存在性检查；严格比对需验证函数
        result["state_based"]["passed"] = True
        result["state_based"]["reason"] = f"已获取状态快照，包含 {list(final_state_snapshot.keys())} 表"
    elif final_state_snapshot is None:
        result["state_based"]["reason"] = "无法获取 final_state_snapshot（可能环境在容器内）"

    return result


def get_final_state_snapshot() -> dict | None:
    """尝试从 env 的 data/state.db 读取状态快照；无法读取时返回 None。"""
    db_path = PREDICTION_TRADER / "data" / "state.db"
    if not db_path.exists():
        return None
    try:
        import sqlite3
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
        tables = [r[0] for r in cur.fetchall()]
        snapshot: dict = {}
        for t in tables:
            cur.execute(f"SELECT * FROM {t}")
            rows = cur.fetchall()
            snapshot[t] = [dict(r) for r in rows]
        conn.close()
        return snapshot
    except Exception:
        return None


def save_trajectory(
    turns: list[dict],
    blueprint: dict,
    out_path: Path,
    system_message: str,
    agent_system_prompt: str,
    tools: list,
    final_state_snapshot: dict | None = None,
    validation_result: dict | None = None,
) -> None:
    """保存轨迹及元数据。"""
    out = {
        "trajectory_id": str(uuid.uuid4()),
        "blueprint_id": blueprint.get("blueprint_id", ""),
        "skill_name": blueprint.get("skill_name", ""),
        "persona_id": blueprint.get("persona_id", ""),
        "system_message": system_message,
        "agent_system_prompt": agent_system_prompt,
        "tools": tools,
        "turns": turns,
        "final_state_snapshot": final_state_snapshot,
        "expected_output": blueprint.get("expected_output"),
        "expected_final_state": blueprint.get("expected_final_state"),
    }
    if validation_result:
        out["validation"] = validation_result
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
    mode = blueprint.get("_mode", "static")
    if mode == "dynamic":
        print(f"加载蓝图（动态模式）: {blueprint_path}, max_turns={blueprint.get('max_turns', 8)}")
    else:
        print(f"加载蓝图（静态模式）: {blueprint_path}, 共 {len(blueprint['queries'])} 轮查询")

    if not args.no_docker and not ensure_mcp_running():
        raise SystemExit("无法连接到 MCP 服务，请确保 prediction-trader 容器已启动。")

    _patch_mcp_tool_params()

    agent, system_message, tools = create_agent(system_message=blueprint["system_message"])
    print("Agent 已创建，MCP 工具已加载")

    agent_system_prompt = get_agent_system_prompt(agent)

    if mode == "dynamic":
        turns = run_dynamic_simulation(agent, blueprint)
    else:
        turns = run_static_simulation(agent, blueprint)

    final_state_snapshot = get_final_state_snapshot()
    if final_state_snapshot is None:
        print("(未获取到 final_state_snapshot，可能环境在容器内运行)")

    validation_result = validate_trajectory(turns, blueprint, final_state_snapshot)
    print("\n轨迹验证:")
    print("  输出验证:", validation_result["output_based"]["passed"], "-", validation_result["output_based"]["reason"])
    print("  状态验证:", validation_result["state_based"]["reason"])

    out_path = args.output or (SCRIPT_DIR / "out_trajectory.json")
    if not out_path.is_absolute():
        out_path = SCRIPT_DIR / out_path
    save_trajectory(
        turns,
        blueprint,
        out_path,
        system_message,
        agent_system_prompt,
        tools,
        final_state_snapshot=final_state_snapshot,
        validation_result=validation_result,
    )


if __name__ == "__main__":
    main()
