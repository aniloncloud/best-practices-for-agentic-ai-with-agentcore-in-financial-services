# Gateway MCP Client
# This client connects to the AgentCore Gateway to access centralized tools
# (portfolio risk check, trade execution) via the MCP protocol.
#
# Uncomment this file's usage in main.py during Lab 2.

import os
from strands.tools.mcp import MCPClient
from mcp import StdioServerParameters

GATEWAY_URL = os.environ.get("AGENTCORE_GATEWAY_MY_GATEWAY_URL", "")

gateway_mcp_client = MCPClient(
    lambda: StdioServerParameters(
        command="uvx",
        args=["awslabs.agentcore-mcp-gateway@latest", "--gateway-url", GATEWAY_URL],
    )
)
