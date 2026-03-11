"""
多轮对话模拟：使用 qwen-agent + MCP 执行蓝图，收集完整轨迹。

蓝图为 goals + possible_tool_calls 格式；无 system_message，Assistant 仅注册 MCP 工具。
User Agent 根据 goals 与对话历史生成用户消息，与 Assistant 交互直到 [TASK_END] 或安全上限（20 轮）。

流程：
- 若指定 --tools-path：子进程启动 astra run_light_mcp（按 tools.jsonl 启 MCP），合成后自动关闭 MCP。
- 否则可启动 prediction-trader MCP Docker 容器，或 --no-docker 仅检查 MCP 是否可达。
- 创建 qwen-agent Assistant（无系统提示，仅 MCP 工具）-> User Agent 逐轮生成消息 -> 收集轨迹。

依赖：
- pip install "qwen-agent[mcp]" openai python-dotenv
- 项目根 .env：OPENAI_API_KEY、OPENAI_MODEL、OPENAI_BASE_URL（可选）

运行（在项目根目录）：
  python exps/data-synthesis-workflow/agent_demo/run_agent_simulation.py [--blueprint out_blueprint.json]
  python exps/data-synthesis-workflow/agent_demo/run_agent_simulation.py --tools-path exps/data-synthesis-workflow/synthesized_envs/2515_stock-monitor/tools.jsonl
"""

from __future__ import annotations

import argparse
import atexit
import json
import os
import re
import subprocess
import sys
import time
import uuid
from contextlib import contextmanager, nullcontext
from pathlib import Path

from dotenv import load_dotenv

# 路径
SCRIPT_DIR = Path(__file__).resolve().parent
import astra.config
PROJECT_ROOT = astra.config.get_project_root()

# 默认蓝图路径（从参数传入，这里不需要默认）
DEFAULT_BLUEPRINT = None
# MCP SSE 端点（本地轻量 MCP）
MCP_SSE_URL = "http://localhost:8000/sse"
# User Agent 提示词（pipeline1 本地）
USER_AGENT_PROMPT_PATH = SCRIPT_DIR.parent / "prompts" / "user_agent.md"

TASK_END_MARKER = "[TASK_END]"


def load_env() -> None:
    """从项目根加载 .env"""
    astra.config.load_env()


def _mcp_reachable() -> bool:
    """检查 MCP SSE 端点是否可连接。"""
    try:
        from urllib.request import urlopen

        with urlopen(MCP_SSE_URL, timeout=3):
            return True
    except Exception:
        return False


def _mcp_reachable_with_url(url: str) -> bool:
    """检查指定 MCP SSE 端点是否可连接。"""
    try:
        from urllib.request import urlopen

        with urlopen(url, timeout=3):
            return True
    except Exception:
        return False


def ensure_mcp_running() -> bool:
    """检查 MCP 服务是否可达，若未运行则尝试启动 Docker，并轮询直到就绪或超时。"""
    if _mcp_reachable():
        return True

    # 尝试启动 Docker
    compose_path = PREDICTION_TRADER / "docker" / "docker-compose.yaml"
    if not compose_path.exists():
        print("未找到 docker-compose.yaml；若为 tools-only 环境请使用 --tools-path 指定 tools.jsonl 路径")
        return False

    print("正在启动 prediction-trader MCP 容器...")
    try:
        subprocess.run(
            ["docker", "compose", "-f", str(compose_path), "up", "-d"],
            cwd=PREDICTION_TRADER,
            check=True,
        )
    except subprocess.CalledProcessError as e:
        print(f"Docker 启动失败: {e}")
        return False

    # 轮询等待服务就绪（首次 uv sync 可能需 30–60 秒）
    max_wait = 90
    interval = 3
    elapsed = 0
    while elapsed < max_wait:
        time.sleep(interval)
        elapsed += interval
        if _mcp_reachable():
            print(f"MCP 服务已就绪（等待约 {elapsed}s）")
            return True
        print(f"  等待 MCP 就绪... ({elapsed}s)")

    print("MCP 服务超时未就绪。可运行以下命令排查：")
    print("  docker ps -a --filter name=prediction-trader")
    print("  docker logs prediction-trader-mcp")
    return False


# 子进程启动的 MCP 进程句柄，用于 --tools-path 时结束时终止
_light_mcp_proc: subprocess.Popen | None = None


@contextmanager
def start_light_mcp_subprocess(tools_path: Path):
    """
    通过 astra run_light_mcp 子进程启动 MCP（SSE），就绪后 yield，退出时终止子进程。
    tools_path 需为绝对路径或相对于项目根。
    """
    global _light_mcp_proc
    tools_abs = tools_path.resolve() if not tools_path.is_absolute() else tools_path
    if not tools_abs.exists():
        raise FileNotFoundError(f"tools_path 不存在: {tools_abs}")

    cmd = [
        "uv", "run", "-m", "astra.scripts.run_light_mcp",
        f"tools_path={tools_abs}",
        "transport=sse",
    ]
    print("正在启动轻量 MCP 子进程:", " ".join(cmd))
    _light_mcp_proc = subprocess.Popen(
        cmd,
        cwd=PROJECT_ROOT,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    atexit.register(lambda: _light_mcp_proc and _light_mcp_proc.poll() is None and _light_mcp_proc.terminate())

    max_wait = 60
    interval = 2
    elapsed = 0
    while elapsed < max_wait:
        if _light_mcp_proc.poll() is not None:
            raise RuntimeError("轻量 MCP 子进程已退出")
        time.sleep(interval)
        elapsed += interval
        if _mcp_reachable():
            print(f"MCP 子进程已就绪（约 {elapsed}s）")
            try:
                yield
            finally:
                if _light_mcp_proc and _light_mcp_proc.poll() is None:
                    _light_mcp_proc.terminate()
                    _light_mcp_proc.wait(timeout=5)
                _light_mcp_proc = None
            return

    _light_mcp_proc.terminate()
    _light_mcp_proc.wait(timeout=5)
    _light_mcp_proc = None
    raise RuntimeError("MCP 子进程启动超时，SSE 未就绪")


def load_blueprint(path: Path) -> dict:
    """
    加载任务蓝图。格式：goals、possible_tool_calls、user_agent_config、end_condition。
    """
    data = json.loads(path.read_text(encoding="utf-8"))
    for f in ("goals", "user_agent_config", "end_condition"):
        if f not in data:
            raise ValueError(f"蓝图中缺少 {f} 字段")
    if not isinstance(data.get("goals"), list) or len(data["goals"]) == 0:
        raise ValueError("goals 必须为非空数组")
    return data


def build_llm_config() -> dict:
    """根据 .env 构建 LLM 配置（OpenAI 兼容）"""
    return astra.config.get_llm_config()


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


def build_mcp_config(mcp_url: str | None = None) -> dict:
    """构建 MCP 配置，连接 prediction-trader SSE 服务。若传入 mcp_url 则使用，否则用默认 MCP_SSE_URL。"""
    url = mcp_url or MCP_SSE_URL
    return {
        "mcpServers": {
            "prediction-trader": {"url": url, "timeout": 30000}
        }
    }


def _patch_mcp_tool_params():
    """对 qwen_agent MCP 工具的 call 做容错：空/非法 params 规范为 "{}"。"""
    try:
        from qwen_agent.tools import mcp_manager
        import json as _json

        _orig_create = mcp_manager.MCPManager.create_tool_class

        def _normalize_tool_params(params) -> dict:
            """将 params 规范为 dict；MCP 协议要求 arguments 为 dict，非 dict 的解析结果（如字符串 'kwargs'）视为空。"""
            if params is None:
                return {}
            if isinstance(params, dict):
                return params
            s = params if isinstance(params, str) else str(params)
            s = (s or "").strip()
            if not s:
                return {}
            try:
                parsed = _json.loads(s)
            except _json.JSONDecodeError:
                return {}
            if not isinstance(parsed, dict):
                return {}
            return parsed

        def _patched_create_tool_class(self, register_name, register_client_id, tool_name, tool_desc, tool_parameters):
            tool_instance = _orig_create(self, register_name, register_client_id, tool_name, tool_desc, tool_parameters)
            orig_call = tool_instance.call

            def _call(params, **kwargs):
                tool_args = _normalize_tool_params(params)
                return orig_call(_json.dumps(tool_args), **kwargs)

            tool_instance.call = _call
            return tool_instance

        mcp_manager.MCPManager.create_tool_class = _patched_create_tool_class
    except Exception as e:
        import warnings
        warnings.warn(f"MCP params 容错 patch 未生效: {e}", RuntimeWarning)


def create_agent(mcp_url: str | None = None) -> tuple:
    """创建 qwen-agent Assistant，仅 MCP 工具，无系统提示。返回 (agent, tools)。"""
    from qwen_agent.agents import Assistant

    llm_cfg = build_llm_config()
    mcp_cfg = build_mcp_config(mcp_url)
    agent = Assistant(llm=llm_cfg, system_message="", function_list=[mcp_cfg])
    tools = list(agent.function_map.keys())
    return agent, tools


def build_default_output_path(run_id: str) -> Path:
    """为每条轨迹构造独立输出目录（输出到 trajectories/<i>/）。"""
    return SCRIPT_DIR.parent / "trajectories" / run_id.replace("pipeline1_", "") / "out_trajectory.json"


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


def generate_user_message(blueprint: dict, messages: list[dict]) -> str:
    """
    调用 User Agent LLM，根据 goals、user_agent_config 与对话历史生成下一句 user 消息。
    返回已剥离 <think> 的用户可见消息；若应结束则返回 TASK_END_MARKER。
    """
    from openai import OpenAI

    api_key = astra.config.get_openai_api_key()
    model = astra.config.get_openai_model()
    base_url = astra.config.get_openai_base_url()

    prompt_text = USER_AGENT_PROMPT_PATH.read_text(encoding="utf-8")
    goals = blueprint.get("goals") or []
    goals_str = "\n".join(f"{i}. {g}" for i, g in enumerate(goals, 1)) if goals else "(无目标)"
    prompt_text = prompt_text.replace("{GOALS}", goals_str.strip())
    prompt_text = prompt_text.replace(
        "{USER_AGENT_CONFIG}",
        json.dumps(blueprint.get("user_agent_config", {}), ensure_ascii=False),
    )
    prompt_text = prompt_text.replace(
        "{CONVERSATION_HISTORY}",
        _format_conversation_for_user_agent(messages),
    )
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

    # 不保存 assistant_thinking；assistant_message 只保存剥离 <think> 后的用户可见内容
    _, message_only = _extract_reasoning(final_assistant_content)
    turn["assistant_thinking"] = ""
    turn["assistant_message"] = (message_only or final_assistant_content).strip()
    turn["tool_calls"] = tool_calls
    return turn


# 动态模式安全上限，防止无限循环
MAX_TURNS_SAFETY = 20


def run_dynamic_simulation(agent, blueprint: dict) -> list[dict]:
    """
    User Agent 逐轮生成 user 消息，与 Assistant 交互直到 [TASK_END] 或达到安全上限。
    返回 turn 列表。
    """
    messages: list[dict] = []
    turns: list[dict] = []

    for turn_idx in range(1, MAX_TURNS_SAFETY + 1):
        start_time = time.perf_counter()
        user_msg = generate_user_message(blueprint, messages)
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

    # 返回 assistant agent 实际看到的消息列表（messages）
    return messages


def save_trajectory(
    messages: list[dict],
    blueprint: dict,
    out_path: Path,
    tools: list,
    run_id: str,
    validation_result: dict | None = None,
    tools_jsonl_content: list[dict] | None = None,
) -> None:
    """保存轨迹及元数据（精简版：只保留元信息与 messages 列表）。"""
    out = {
        "run_id": run_id,
        "trajectory_id": str(uuid.uuid4()),
        "blueprint_id": blueprint.get("blueprint_id", ""),
        "skill_name": blueprint.get("skill_name", ""),
        "persona_id": blueprint.get("persona_id", ""),
        "tools": tools,
        "messages": messages,
    }
    # 保存完整的 tools.jsonl 内容（如果有）
    if tools_jsonl_content:
        out["tools_jsonl"] = tools_jsonl_content
    if validation_result:
        out["validation"] = validation_result
    out_path.parent.mkdir(parents=True, exist_ok=True)
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
        help="输出轨迹 JSON 路径（默认: agent_demo/runs/<run_id>/out_trajectory.json）",
    )
    parser.add_argument("--no-docker", action="store_true", help="不自动启动 Docker，仅检查 MCP 是否可达")
    parser.add_argument(
        "--tools-path",
        type=Path,
        default=None,
        help="tools.jsonl 路径：指定则子进程启动 astra run_light_mcp，合成后自动关闭；不指定则用 Docker 或已有 MCP",
    )
    parser.add_argument("--run-id", type=str, default="", help="本次轨迹采集的运行 ID；默认自动生成")
    parser.add_argument(
        "--mcp-url",
        type=str,
        default=None,
        help="MCP SSE 端点 URL。若指定则直接连接，不自动启动 MCP（适用于 pipeline1 复用单个 MCP 实例）",
    )
    args = parser.parse_args()

    load_env()

    blueprint_path = args.blueprint
    if not blueprint_path.is_absolute():
        blueprint_path = SCRIPT_DIR / blueprint_path
    if not blueprint_path.exists():
        raise SystemExit(f"蓝图文件不存在: {blueprint_path}")

    blueprint = load_blueprint(blueprint_path)
    run_id = args.run_id.strip() or str(uuid.uuid4())
    print(f"加载蓝图: {blueprint_path}, goals={len(blueprint.get('goals', []))}")

    # 加载 tools.jsonl 内容（供后续保存到轨迹）
    tools_jsonl_content: list[dict] = []
    if args.tools_path is not None:
        tools_path = args.tools_path if args.tools_path.is_absolute() else (PROJECT_ROOT / args.tools_path)
        if tools_path.exists():
            for line in tools_path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    try:
                        tools_jsonl_content.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
        mcp_ctx = start_light_mcp_subprocess(tools_path)
    else:
        mcp_ctx = nullcontext()

    # 若传入了 mcp_url，直接连接已有 MCP，不自动启动
    if args.mcp_url is not None:
        mcp_ctx = nullcontext()
        # 验证 mcp_url 可达
        if not _mcp_reachable_with_url(args.mcp_url):
            raise SystemExit(f"MCP 服务不可达: {args.mcp_url}")

    if args.tools_path is None and args.mcp_url is None and not args.no_docker and not ensure_mcp_running():
        raise SystemExit("无法连接到 MCP 服务，请确保 prediction-trader 容器已启动或使用 --tools-path / --mcp-url。")

    _patch_mcp_tool_params()

    out_path = args.output or build_default_output_path(run_id)
    if not out_path.is_absolute():
        out_path = SCRIPT_DIR / out_path

    with mcp_ctx:
        try:
            agent, tools = create_agent(mcp_url=args.mcp_url)
            print("Agent 已创建，MCP 工具已加载")

            # 仍保留 agent_system_prompt 获取逻辑，方便必要时调试，但不写入轨迹
            _ = get_agent_system_prompt(agent)

            messages = run_dynamic_simulation(agent, blueprint)

            # 轻量 prediction-trader 环境不导出结构化状态，仅做基于输出的简单验证
            last_assistant_msg = ""
            for m in reversed(messages):
                if m.get("role") == "assistant":
                    last_assistant_msg = (m.get("content") or "").strip()
                    if last_assistant_msg:
                        break
            validation_result = {
                "output_based": {
                    "passed": bool(last_assistant_msg) and "[Error]" not in last_assistant_msg,
                    "reason": "助手已生成最终回复" if last_assistant_msg and "[Error]" not in last_assistant_msg else "最终回复异常或为空",
                }
            }
            print("\n轨迹验证:")
            print("  输出验证:", validation_result["output_based"]["passed"], "-", validation_result["output_based"]["reason"])

            save_trajectory(
                messages,
                blueprint,
                out_path,
                tools,
                run_id,
                validation_result=validation_result,
                tools_jsonl_content=tools_jsonl_content if tools_jsonl_content else None,
            )
        except Exception as e:
            raise


if __name__ == "__main__":
    main()
