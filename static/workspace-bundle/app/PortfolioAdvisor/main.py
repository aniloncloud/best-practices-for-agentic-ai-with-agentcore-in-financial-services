import json
import logging
import uuid

from strands import Agent, tool
from strands.models.bedrock import BedrockModel

logger = logging.getLogger(__name__)

STOCKS = {
    "AAPL": {"name": "Apple Inc.", "price": 178.52, "change": 2.35, "pe_ratio": 28.4, "market_cap": "2.8T", "sector": "Technology", "recommendation": "Buy", "risk_level": "Medium"},
    "MSFT": {"name": "Microsoft Corp.", "price": 378.91, "change": -1.20, "pe_ratio": 35.2, "market_cap": "2.8T", "sector": "Technology", "recommendation": "Hold", "risk_level": "Low"},
    "JPM": {"name": "JPMorgan Chase", "price": 195.47, "change": 0.89, "pe_ratio": 11.8, "market_cap": "570B", "sector": "Financials", "recommendation": "Buy", "risk_level": "Low"},
    "TSLA": {"name": "Tesla Inc.", "price": 248.50, "change": -5.30, "pe_ratio": 62.1, "market_cap": "790B", "sector": "Consumer Discretionary", "recommendation": "Hold", "risk_level": "High"},
    "GS": {"name": "Goldman Sachs", "price": 458.23, "change": 3.15, "pe_ratio": 14.2, "market_cap": "155B", "sector": "Financials", "recommendation": "Buy", "risk_level": "Medium"},
}

COMPLIANCE_RULES = {
    "options_trading": {"approval_level": "Senior Advisor", "min_account_age_days": 365, "min_balance": 50000, "restrictions": ["No naked calls without $500K+ balance", "Spreads require Level 3 approval"]},
    "margin_trading": {"approval_level": "Branch Manager", "min_account_age_days": 180, "min_balance": 25000, "restrictions": ["Maximum 2x leverage for retail", "4x leverage requires institutional classification"]},
    "penny_stocks": {"approval_level": "Compliance Officer", "min_account_age_days": 730, "min_balance": 100000, "restrictions": ["Limited to 5% of portfolio", "No concentrated positions", "Mandatory risk disclosure"]},
    "international": {"approval_level": "Senior Advisor", "min_account_age_days": 90, "min_balance": 10000, "restrictions": ["Currency risk disclosure required", "Settlement may take T+3", "Some markets require local broker"]},
    "crypto_assets": {"approval_level": "Compliance Officer", "min_account_age_days": 365, "min_balance": 75000, "restrictions": ["Maximum 10% allocation", "Cold storage required for holdings >$100K", "Quarterly attestation required"]},
}


@tool
def get_stock_analysis(ticker: str) -> str:
    """Get detailed stock analysis including price, metrics, and recommendation.

    Args:
        ticker: Stock ticker symbol (e.g., AAPL, MSFT, JPM, TSLA, GS)
    """
    ticker = ticker.upper()
    if ticker not in STOCKS:
        return json.dumps({"error": f"Ticker '{ticker}' not found. Available: {', '.join(STOCKS.keys())}"})
    stock = STOCKS[ticker]
    return json.dumps({
        "ticker": ticker,
        "name": stock["name"],
        "current_price": f"${stock['price']:.2f}",
        "daily_change": f"{'+'if stock['change']>0 else ''}{stock['change']:.2f}",
        "pe_ratio": stock["pe_ratio"],
        "market_cap": stock["market_cap"],
        "sector": stock["sector"],
        "recommendation": stock["recommendation"],
        "risk_level": stock["risk_level"],
    })


@tool
def get_compliance_rules(category: str) -> str:
    """Get compliance rules and requirements for a specific trading category.

    Args:
        category: Trading category (options_trading, margin_trading, penny_stocks, international, crypto_assets)
    """
    category = category.lower().replace(" ", "_")
    if category not in COMPLIANCE_RULES:
        return json.dumps({"error": f"Category '{category}' not found. Available: {', '.join(COMPLIANCE_RULES.keys())}"})
    rules = COMPLIANCE_RULES[category]
    return json.dumps({
        "category": category,
        "approval_level": rules["approval_level"],
        "minimum_account_age": f"{rules['min_account_age_days']} days",
        "minimum_balance": f"${rules['min_balance']:,}",
        "restrictions": rules["restrictions"],
    })


# --- Gateway MCP Client (uncomment in Lab 2) ---
# from mcp_client.client import gateway_mcp_client
# mcp_tools = [gateway_mcp_client]

mcp_tools = []


def handler(event, context):
    session_id = event.get("sessionId", str(uuid.uuid4()))
    prompt = event.get("prompt", "")

    model = BedrockModel(
        model_id="us.anthropic.claude-sonnet-4-20250514-v1:0",
        region_name="us-west-2",
    )

    system_prompt = """You are a portfolio advisor for a capital markets firm. You help clients with:
- Stock analysis and market insights
- Compliance rules and requirements
- Portfolio risk assessment
- Trade execution guidance

Always provide clear, data-driven insights. Flag compliance concerns proactively.
When asked about portfolio risk, use the check_portfolio_risk tool via the Gateway.
When asked to execute trades, use the execute_trade tool via the Gateway."""

    agent = Agent(
        model=model,
        system_prompt=system_prompt,
        tools=[get_stock_analysis, get_compliance_rules] + mcp_tools,
    )

    response = agent(prompt)
    return {"response": str(response), "sessionId": session_id}
