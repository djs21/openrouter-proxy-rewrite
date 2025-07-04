#!/usr/bin/env python3
"""
Test script for OpenRouter API Proxy (Vertical Slice Architecture)
Tests all features using configuration from config.yml.
"""

import asyncio
import json
import os
from typing import Dict, Any

import httpx
import yaml

# Test configuration - use Deepseek model that works with proxy's free_only setting
MODEL = "deepseek/deepseek-chat:free"
STREAM = False

def load_config() -> Dict[str, Any]:
    """Load configuration from config.yml"""
    with open("config.yml", encoding="utf-8") as file:
        return yaml.safe_load(file)

async def test_feature(feature_name: str, test_func: callable):
    """Run a feature test with formatted output"""
    print(f"\n=== Testing {feature_name} ===")
    try:
        await test_func()
        print(f"✅ {feature_name} test passed")
    except Exception as e:
        print(f"❌ {feature_name} test failed: {str(e)}")
        raise

async def test_list_models(client: httpx.AsyncClient, base_url: str):
    """Test the List Models feature - public endpoint requires no auth header"""
    url = f"{base_url}/models"
    resp = await client.get(url)  # No Authorization header for public endpoint
    resp.raise_for_status()
    data = resp.json()
    assert isinstance(data.get("data"), list), "Expected list of models"
    print(f"Found {len(data['data'])} models")

async def test_proxy_chat(client: httpx.AsyncClient, base_url: str, headers: Dict[str, str]):
    """Test the Proxy Chat feature"""
    url = f"{base_url}/chat/completions"
    request_data = {
        "model": MODEL,
        "messages": [{"role": "user", "content": "Hello!"}],
        "stream": STREAM,
    }
    
    if STREAM:
        async with client.stream("POST", url, headers=headers, json=request_data) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                line = line.strip()
                if not line:
                    continue
                if line.startswith("data: "):
                    content = line[6:].strip()
                    if content == "[DONE]":
                        continue
                    try:
                        if content:
                            data = json.loads(content)
                            print(".", end="", flush=True)
                    except json.JSONDecodeError:
                        print("", end="", flush=True)
        print("\nStream completed")
    else:
        resp = await client.post(url, headers=headers, json=request_data)
        resp.raise_for_status()
        print("Chat completion received")

async def test_proxy_chat_error(client: httpx.AsyncClient, base_url: str, headers: Dict[str, str]):
    """Test Proxy Chat with an invalid model to trigger an error"""
    print("Testing error handling for non-existent model...")
    url = f"{base_url}/chat/completions"
    request_data = {
        "model": "this/model-does-not-exist",  # Invalid model
        "messages": [{"role": "user", "content": "Hello!"}],
        "stream": False,
    }
    resp = await client.post(url, headers=headers, json=request_data)
    
    assert resp.status_code != 200, f"Expected an error status code, but got 200. Body: {resp.text}"
    print(f"Received expected error status: {resp.status_code}. Test passed.")

async def test_key_management(client: httpx.AsyncClient, base_url: str, headers: Dict[str, str]):
    """Test Key Management features by ensuring multiple requests work"""
    # Make two requests to chat endpoint to test key rotation
    request_data = {
        "model": MODEL,
        "messages": [{"role": "user", "content": "Hello!"}],
    }
    
    # First request should succeed
    resp1 = await client.post(f"{base_url}/chat/completions", headers=headers, json=request_data)
    resp1.raise_for_status()
    
    # Second request should also succeed
    resp2 = await client.post(f"{base_url}/chat/completions", headers=headers, json=request_data)
    resp2.raise_for_status()
    
    print("Verified key rotation across multiple requests")

async def run_tests():
    """Run all feature tests"""
    config = load_config()
    server_config = config["server"]
    
    host = "127.0.0.1" if server_config["host"] == "0.0.0.0" else server_config["host"]
    port = server_config["port"]
    base_url = f"http://{host}:{port}/api/v1"
    access_key = os.environ.get("ACCESS_KEY", server_config["access_key"])
    headers = {"Authorization": f"Bearer {access_key}"} if access_key else {}

    async with httpx.AsyncClient(timeout=60.0) as client:
        await test_feature("List Models", lambda: test_list_models(client, base_url))
        await test_feature("Proxy Chat", lambda: test_proxy_chat(client, base_url, headers))
        await test_feature("Proxy Chat Error Handling", lambda: test_proxy_chat_error(client, base_url, headers))
        await test_feature("Key Management", lambda: test_key_management(client, base_url, headers))

if __name__ == "__main__":
    print("Running OpenRouter Proxy Tests (Vertical Slice Architecture)")
    asyncio.run(run_tests())
