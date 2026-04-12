import asyncio
import json
import subprocess

async def test_mcp_server():
    # Start the server process
    process = await asyncio.create_subprocess_exec(
        "/usr/local/bin/uv",
        "--directory", "/mcp_server",
        "run", "server.py",
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    # Initialize connection first (required by MCP)
    init_request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "0.1.0",
            "capabilities": {}
        }
    }

    print("Sending initialize request...")
    process.stdin.write((json.dumps(init_request) + "\n").encode())
    await process.stdin.drain()

    # Read initialize response
    response_line = await process.stdout.readline()
    print("Initialize response:", response_line.decode())

    # Send initialized notification
    initialized_notification = {
        "jsonrpc": "2.0",
        "method": "notifications/initialized"
    }

    process.stdin.write((json.dumps(initialized_notification) + "\n").encode())
    await process.stdin.drain()

    # Now list tools
    tools_request = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/list",
        "params": {}
    }

    print("\nSending tools/list request...")
    process.stdin.write((json.dumps(tools_request) + "\n").encode())
    await process.stdin.drain()

    # Read tools response
    response_line = await process.stdout.readline()
    print("Tools response:", response_line.decode())

    # Call list_all_sites tool
    tool_call = {
        "jsonrpc": "2.0",
        "id": 3,
        "method": "tools/call",
        "params": {
            "name": "list_all_sites",
            "arguments": {}
        }
    }

    print("\nSending list_all_sites call...")
    process.stdin.write((json.dumps(tool_call) + "\n").encode())
    await process.stdin.drain()

    # Read tool response (might need multiple reads)
    for _ in range(3):  # Read up to 3 responses
        response_line = await process.stdout.readline()
        if response_line:
            print("Tool result:", response_line.decode())
        else:
            break

    # Try get_energy_consumption
    energy_call = {
        "jsonrpc": "2.0",
        "id": 4,
        "method": "tools/call",
        "params": {
            "name": "get_energy_consumption",
            "arguments": {
                "site_name": "Daniel Hub",
                "days": 7
            }
        }
    }

    print("\nSending get_energy_consumption call...")
    process.stdin.write((json.dumps(energy_call) + "\n").encode())
    await process.stdin.drain()

    # Read response
    response_line = await process.stdout.readline()
    print("Energy result:", response_line.decode())

    # Give it a moment to process and output all responses
    await asyncio.sleep(1)

    # Read any remaining output
    remaining = []
    while True:
        try:
            line = await asyncio.wait_for(process.stdout.readline(), timeout=0.5)
            if line:
                remaining.append(line.decode())
            else:
                break
        except asyncio.TimeoutError:
            break

    if remaining:
        print("\nAdditional output:")
        for line in remaining:
            print(line)

    # Clean up
    process.terminate()
    await process.wait()
    print("\nTest completed")

if __name__ == "__main__":
    asyncio.run(test_mcp_server())
