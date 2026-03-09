"""
Analyze Portfolio Tool - 分析钱包投资组合

对钱包地址进行完整的投资组合分析，包括资产配置、风险评分、敞口分析等。
"""

import json
import os
import urllib.request
import urllib.parse

TOOL_SCHEMA = {
    "name": "analyze_portfolio",
    "description": "Perform a comprehensive portfolio risk analysis for a cryptocurrency wallet. "
    "Scans multi-chain holdings (Ethereum, Base, Polygon, Arbitrum, Optimism), "
    "calculates risk scores, asset breakdown, and provides optimization recommendations. "
    "Use this for full portfolio analysis.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "wallet": {"type": "string", "description": "Wallet address to analyze (0x...)"},
            "chain": {
                "type": "string",
                "default": "all",
                "description": "Chain to analyze: ethereum, base, polygon, arbitrum, optimism, or all",
            },
        },
        "required": ["wallet"],
    },
}

PORTFOLIO_API_BASE = os.environ.get("PORTFOLIO_API_BASE", "http://localhost:8001")


def execute(wallet: str, chain: str = "all") -> str:
    """
    分析钱包投资组合

    Args:
        wallet: 钱包地址
        chain: 区块链 (默认 all)

    Returns:
        格式化的投资组合分析结果
    """
    try:
        url = f"{PORTFOLIO_API_BASE}/api/analyze?wallet={wallet}&chain={chain}"

        with urllib.request.urlopen(url, timeout=30) as response:
            data = json.loads(response.read().decode())

        if "error" in data:
            return f"Error: {data['error']}"

        output = f"## Portfolio Analysis: {wallet[:6]}...{wallet[-4:]}\n\n"
        output += f"**Total Value:** ${data.get('totalValue', 0):,.2f}\n"
        output += f"**Risk Score:** {data.get('riskScore', 'N/A')}/100\n\n"

        output += "### Asset Breakdown\n\n"
        breakdown = data.get("breakdown", {})
        for asset_class, value in breakdown.items():
            pct = (value / data.get("totalValue", 1)) * 100
            output += f"- **{asset_class.title()}**: ${value:,.2f} ({pct:.1f}%)\n"

        output += "\n### Risk Assessment\n\n"
        risks = data.get("risks", {})
        for risk_type, score in risks.items():
            emoji = "🟢" if score < 30 else "🟡" if score < 60 else "🔴"
            output += f"- {emoji} **{risk_type.title()} Risk**: {score}/100\n"

        output += "\n### Top Exposures\n\n"
        exposures = data.get("exposures", {})
        for asset, pct in sorted(exposures.items(), key=lambda x: x[1], reverse=True)[:5]:
            output += f"- {asset}: {pct}%\n"

        if data.get("recommendations"):
            output += "\n### Recommendations\n\n"
            for rec in data["recommendations"]:
                output += f"- {rec}\n"

        return output

    except Exception as e:
        return f"Error analyzing portfolio: {str(e)}"


if __name__ == "__main__":
    print(execute("0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb"))
