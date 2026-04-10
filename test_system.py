#!/usr/bin/env python3
"""
Test the complete system
"""

import json
import subprocess
import sys
import time

import requests


def check_rabbitmq():
    """Check if RabbitMQ is running"""
    try:
        response = requests.get("http://localhost:15672", timeout=2)
        return True
    except:
        return False


def main():
    print("=" * 60)
    print("🧪 Testing Energy MCP System")
    print("=" * 60)

    # Check RabbitMQ
    print("\n1. Checking RabbitMQ...")
    if not check_rabbitmq():
        print("❌ RabbitMQ is not running!")
        print("   Please run: docker start rabbitmq-energy")
        return False

    print("✅ RabbitMQ is running")

    # Test site mapping
    print("\n2. Testing site mapping...")
    test_sites = ["Hong Kong", "Singapore", "London", "Invalid Site"]

    print("\n3. Running queries...")
    for site in test_sites:
        print(f"\n   Query: {site}")

        # Run client with single query
        result = subprocess.run(
            [sys.executable, "mcp-client/client.py", site],
            capture_output=True,
            text=True,
            timeout=10000,
        )

        if result.returncode == 0:
            try:
                response = json.loads(result.stdout)
                if "error" in response:
                    print(f"   ❌ Error: {response['error']}")
                else:
                    print(
                        f"   ✅ Found: {response['site_id']} - {response['consumption']['consumption']} {response['consumption']['unit']}"
                    )
            except:
                print(f"   Output: {result.stdout[:100]}")
        else:
            print(f"   ❌ Failed: {result.stderr[:100]}")

    print("\n" + "=" * 60)
    print("✅ Test complete!")
    print("=" * 60)
    return True


if __name__ == "__main__":
    main()
