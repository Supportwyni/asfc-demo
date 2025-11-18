"""Test OpenRouter model connection."""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import requests

# Load environment variables
project_root = Path(__file__).parent
env_path = project_root / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=str(env_path), override=True)

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "qwen/qwen-2.5-72b-instruct:free")

print("=" * 60)
print("Testing OpenRouter Model Connection")
print("=" * 60)
print(f"\nAPI Key: {'[SET]' if OPENROUTER_API_KEY else '[NOT SET]'}")
print(f"Base URL: {OPENROUTER_BASE_URL}")
print(f"Model: {OPENROUTER_MODEL}")
print()

if not OPENROUTER_API_KEY:
    print("[ERROR] OPENROUTER_API_KEY not set in .env")
    sys.exit(1)

# Test API connection
url = f"{OPENROUTER_BASE_URL}/chat/completions"
headers = {
    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
    "Content-Type": "application/json",
    "HTTP-Referer": "https://github.com/asfc",
    "X-Title": "ASFC Test"
}

payload = {
    "model": OPENROUTER_MODEL,
    "messages": [
        {"role": "user", "content": "Say 'Hello' if you can read this."}
    ],
    "max_tokens": 50
}

print(f"Sending test request to {OPENROUTER_MODEL}...")
try:
    response = requests.post(url, json=payload, headers=headers, timeout=30)
    
    print(f"\nStatus Code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        if 'choices' in data and len(data['choices']) > 0:
            content = data['choices'][0]['message']['content']
            print(f"\n[SUCCESS] Model is working!")
            print(f"Response: {content}")
        else:
            print(f"\n[ERROR] No choices in response")
            print(f"Response: {data}")
    elif response.status_code == 404:
        print(f"\n[ERROR] Model not found (404)")
        print(f"The model '{OPENROUTER_MODEL}' doesn't exist or isn't available.")
        print(f"\nResponse: {response.text[:500]}")
        print(f"\nTry checking available models at: https://openrouter.ai/models")
    elif response.status_code == 401:
        print(f"\n[ERROR] Authentication failed (401)")
        print(f"Check your API key in .env file")
        print(f"\nResponse: {response.text[:500]}")
    elif response.status_code == 429:
        print(f"\n[ERROR] Rate limited (429)")
        print(f"Too many requests. Please wait and try again.")
    else:
        print(f"\n[ERROR] API returned status {response.status_code}")
        print(f"Response: {response.text[:500]}")
        
except requests.exceptions.RequestException as e:
    print(f"\n[ERROR] Request failed: {type(e).__name__}: {str(e)}")
    sys.exit(1)

