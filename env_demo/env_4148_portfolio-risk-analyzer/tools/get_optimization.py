"""
Get Optimization Tool - 获取优化建议

获取投资组合的优化建议，包括再平衡、对冲策略、收益优化等。
"""

import json
import os
import urllib.request

TOOL_SCHEMA = {
    "name": "get_optimization",
    "description": "Get portfolio optimization recommendations including rebalancing suggestions, "
    "hedging strategies, yield optimization opportunities, and tax-loss harvesting. "
    "Use this to get actionable advice to improve portfolio risk-adjusted returns.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "wallet": {"type": "string", "description": "Wallet address to optimize"},
            "focus": {
                "type": "string",
                "default": "all",
                "description": "Focus area: all, risk, yield, or tax",
            },
        },
        "required": ["wallet"],
    },
}

PORTFOLIO_API_BASE = os.environ.get("PORTFOLIO_API_BASE", "http://localhost:8001")


def execute(wallet: str, focus: str = "all") -> str:
    """
    获取优化建议

    Args:
        wallet: 钱包地址
        focus: 专注领域 (all, risk, yield, tax)

    Returns:
        格式化的优化建议
    """
    try:
        url = f"{PORTFOLIO_API_BASE}/api/optimize?wallet={wallet}&focus={focus}"

        with urllib.request.urlopen(url, timeout=30) as response:
            data = json.loads(response.read().decode())

        if "error" in data:
            return f"Error: {data['error']}"

        output = f"## Portfolio Optimization: {wallet[:6]}...{wallet[-4:]}\n\n"
        output += f"**Focus:** {focus.title()}\n\n"

        output += "### Rebalancing Suggestions\n\n"
        for rec in data.get("rebalancing", []):
            output += f"- {rec}\n"

        output += "\n### Hedging Strategies\n\n"
        for strat in data.get("hedging", []):
            output += f"- {strat}\n"

        output += "\n### Yield Optimization\n\n"
        for opt in data.get("yieldOptimization", []):
            output += f"- {opt}\n"

        if data.get("taxLossHarvesting"):
            output += "\n### Tax-Loss Harvesting\n\n"
            for op in data["taxLossHarvesting"]:
                output += f"- **{op['asset']}**: Realize loss of ${op['loss']:,.2f}\n"
                output += f"  Suggested replacement: {op['replacement']}\n"

        output += "\n### Expected Impact\n\n"
        impact = data.get("expectedImpact", {})
        output += f"- **Risk Reduction**: {impact.get('riskReduction', 0)}%\n"
        output += f"- **Yield Improvement**: {impact.get('yieldImprovement', 0)}% APY\n"
        output += f"- **Tax Savings**: ${impact.get('taxSavings', 0):,.2f}\n"

        return output

    except Exception as e:
        return f"Error fetching optimization: {str(e)}"


if __name__ == "__main__":
    print(execute("0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb"))
