"""
Run Stress Test Tool - 运行压力测试

对投资组合进行压力测试，模拟市场崩盘、清算风险和高gas费等场景。
"""

import json
import os
import urllib.request
import urllib.parse

TOOL_SCHEMA = {
    "name": "run_stress_test",
    "description": "Run stress test scenarios on a crypto portfolio. "
    "Simulates market crash scenarios (-20%, -50%, -80%), "
    "liquidation risk analysis, and high gas cost impact. "
    "Use this to understand portfolio vulnerability to adverse conditions.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "wallet": {"type": "string", "description": "Wallet address to stress test"},
            "scenario": {
                "type": "string",
                "default": "crash",
                "description": "Scenario type: crash, liquidation, or gas",
            },
            "drop": {
                "type": "integer",
                "default": 50,
                "description": "Percentage drop for crash scenario (20, 50, or 80)",
            },
        },
        "required": ["wallet", "scenario"],
    },
}

PORTFOLIO_API_BASE = os.environ.get("PORTFOLIO_API_BASE", "http://localhost:8001")


def execute(wallet: str, scenario: str = "crash", drop: int = 50) -> str:
    """
    运行压力测试

    Args:
        wallet: 钱包地址
        scenario: 场景类型 (crash, liquidation, gas)
        drop: 崩盘百分比

    Returns:
        格式化的压力测试结果
    """
    try:
        params = urllib.parse.urlencode({"wallet": wallet, "scenario": scenario, "drop": drop})
        url = f"{PORTFOLIO_API_BASE}/api/stress-test?{params}"

        with urllib.request.urlopen(url, timeout=30) as response:
            data = json.loads(response.read().decode())

        if "error" in data:
            return f"Error: {data['error']}"

        output = f"## Stress Test: {wallet[:6]}...{wallet[-4:]}\n\n"
        output += f"**Scenario:** {scenario.title()} | **Drop:** {drop}%\n\n"

        if scenario == "crash":
            output += "### Market Crash Impact\n\n"
            crash = data.get("crashImpact", {})
            output += (
                f"- **Portfolio Value After Crash**: ${crash.get('valueAfterCrash', 0):,.2f}\n"
            )
            output += f"- **Loss Amount**: ${crash.get('lossAmount', 0):,.2f} ({crash.get('lossPercent', 0)}%)\n"
            output += f"- **Recovery Price**: {crash.get('recoveryPrice', 'N/A')}%\n"

            output += "\n### Asset Impact\n\n"
            for asset, impact in crash.get("assetImpact", {}).items():
                output += f"- **{asset}**: ${impact.get('value', 0):,.2f} → ${impact.get('newValue', 0):,.2f}\n"

            output += "\n### Correlation Analysis\n\n"
            for corr in crash.get("correlationAnalysis", []):
                output += f"- {corr['asset1']} vs {corr['asset2']}: {corr['correlation']:.2f}\n"

        elif scenario == "liquidation":
            output += "### Liquidation Risk\n\n"
            liq = data.get("liquidationRisk", {})
            output += f"- **Current Collateral Ratio**: {liq.get('collateralRatio', 0)}%\n"
            output += f"- **Liquidation Price**: ${liq.get('liquidationPrice', 0):,.2f}\n"
            output += f"- **Distance to Liquidation**: {liq.get('distanceToLiquidation', 0)}%\n"
            output += f"- **Liquidation Risk Score**: {liq.get('riskScore', 0)}/100\n"

            output += "\n### Positions at Risk\n\n"
            for pos in liq.get("positionsAtRisk", []):
                output += f"- **{pos['protocol']}**: {pos['asset']} - {pos['risk']}\n"

        elif scenario == "gas":
            output += "### Gas Cost Impact\n\n"
            gas = data.get("gasImpact", {})
            output += f"- **Current Avg Gas**: ${gas.get('currentGas', 0):,.2f}\n"
            output += f"- **High Gas Scenario**: ${gas.get('highGas', 0):,.2f}\n"
            output += f"- **Exit Cost (Current)**: ${gas.get('exitCostCurrent', 0):,.2f}\n"
            output += f"- **Exit Cost (High Gas)**: ${gas.get('exitCostHigh', 0):,.2f}\n"
            output += f"- **Exit Cost as % of Portfolio**: {gas.get('exitCostPercent', 0)}%\n"

        output += "\n### Recommendations\n\n"
        for rec in data.get("recommendations", []):
            output += f"- {rec}\n"

        return output

    except Exception as e:
        return f"Error running stress test: {str(e)}"


if __name__ == "__main__":
    print(execute("0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb", "crash", 50))
