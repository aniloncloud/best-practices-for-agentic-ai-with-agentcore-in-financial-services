import os
import logging
from mcp.client.streamable_http import streamablehttp_client
from strands.tools.mcp.mcp_client import MCPClient

logger = logging.getLogger(__name__)

# ExaAI provides information about code through web searches, crawling and code context searches through their platform. Requires no authentication
EXAMPLE_MCP_ENDPOINT = "https://mcp.exa.ai/mcp"

def get_streamable_http_mcp_client() -> MCPClient:
    """Returns an MCP Client compatible with Strands"""
    # to use an MCP server that supports bearer authentication, add headers={"Authorization": f"Bearer {access_token}"}
    return MCPClient(lambda: streamablehttp_client(EXAMPLE_MCP_ENDPOINT))


def get_gateway_mcp_client(auth_header: str = "") -> MCPClient | None:
    """Returns an MCP Client for AgentCore Gateway, forwarding the caller's JWT"""
    url = os.environ.get("AGENTCORE_GATEWAY_MY_GATEWAY_SECURE_URL") or os.environ.get("AGENTCORE_GATEWAY_MY_GATEWAY_URL")
    if not url:
        logger.warning("Gateway URL not set — gateway tools unavailable")
        return None
    if not url.endswith("/mcp"):
        url = url.rstrip("/") + "/mcp"
    headers = {"Authorization": auth_header} if auth_header else {}
    return MCPClient(lambda: streamablehttp_client(url=url, headers=headers))
