"""
Get Risk Breakdown Tool - 获取详细风险分解

获取投资组合的详细风险分解，包括资产类别风险、协议风险、集中度风险等。
"""

import json
import os
import urllib.request

TOOL_SCHEMA = {
    "name": "get_risk_breakdown",
    "description": "Get detailed risk breakdown for a crypto portfolio. "
    "Returns asset class exposure, protocol risk scores, concentration risk, "
    "and impermanent loss analysis for LP positions. "
    "Use this for in-depth risk assessment beyond the basic score.",
    "inputSchema": {
        "type": "object",
        "properties": {"wallet": {"type": "string", "description": "Wallet address to analyze"}},
        "required": ["wallet"],
    },
}

PORTFOLIO_API_BASE = os.environ.get("PORTFOLIO_API_BASE", "http://localhost:8001")


def execute(wallet: str) -> str:
    """
    获取详细风险分解

    Args:
        wallet: 钱包地址

    Returns:
        格式化的风险分解结果
    """
    try:
        url = f"{PORTFOLIO_API_BASE}/api/risk-breakdown?wallet={wallet}"

        with urllib.request.urlopen(url, timeout=30) as response:
            data = json.loads(response.read().decode())

        if "error" in data:
            return f"Error: {data['error']}"

        output = f"## Risk Breakdown: {wallet[:6]}...{wallet[-4:]}\n\n"

        output += "### Asset Class Exposure\n\n"
        asset_exposure = data.get("assetClassExposure", {})
        for asset_class, pct in asset_exposure.items():
            bar = "█" * int(pct / 5) + "░" * (20 - int(pct / 5))
            output += f"- {asset_class.title():15} {bar} {pct}%\n"

        output += "\n### Protocol Risk\n\n"
        protocol_risk = data.get("protocolRisk", {})
        for protocol, risk_info in protocol_risk.items():
            score = risk_info.get("score", 0)
            emoji = "🟢" if score < 30 else "🟡" if score < 60 else "🔴"
            audit = "✅ Audited" if risk_info.get("audited") else "⚠️ Not Audited"
            output += f"- **{protocol}**: {emoji} Risk Score: {score} | {audit}\n"
            output += (
                f"  TVL: ${risk_info.get('tvl', 0):,.0f} | Age: {risk_info.get('age', 'N/A')}\n"
            )

        output += "\n### Concentration Risk\n\n"
        conc = data.get("concentrationRisk", {})
        output += f"- **Top 5 Holdings**: {conc.get('top5Percent', 0)}%\n"
        output += f"- **Diversification Score**: {conc.get('diversificationScore', 0)}/100\n"
        output += f"- **Largest Position**: {conc.get('largestPosition', 0)}%\n"

        output += "\n### Impermanent Loss\n\n"
        il_positions = data.get("impermanentLoss", [])
        if il_positions:
            for pos in il_positions:
                output += f"- **{pos['pool']}**: IL: {pos['ilPercent']:.2f}%\n"
        else:
            output += "- No LP positions detected\n"

        return output

    except Exception as e:
        return f"Error fetching risk breakdown: {str(e)}"


if __name__ == "__main__":
    print(execute("0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb"))
