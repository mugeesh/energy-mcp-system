# health_check.py
import subprocess
import sys


MCP_SERVER =  "server.py"

def check_mcp_server():
    """Health check for MCP server"""
    try:
        # Check if process is running
        result = subprocess.run(
            ["pgrep", "-f", MCP_SERVER],
            capture_output=True
        )

        if result.returncode == 0:
            print("✅ MCP Server is running")
            return 0
        else:
            print("❌ MCP Server is not running")
            return 1
    except Exception as e:
        print(f"Error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(check_mcp_server())
