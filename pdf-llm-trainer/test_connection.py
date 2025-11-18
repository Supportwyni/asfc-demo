"""Test script to verify OpenRouter connection."""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from backend.config import OPENROUTER_API_KEY, OPENROUTER_MODEL, OPENROUTER_BASE_URL
from backend.rag import query_openrouter

def test_connection():
    print("=" * 60)
    print("Testing OpenRouter Connection")
    print("=" * 60)
    
    # Check config
    print(f"\n[1] Configuration Check:")
    print(f"    API Key: {'[OK] Loaded' if OPENROUTER_API_KEY else '[MISSING] NOT SET'}")
    print(f"    API Key Length: {len(OPENROUTER_API_KEY) if OPENROUTER_API_KEY else 0}")
    print(f"    Model: {OPENROUTER_MODEL}")
    print(f"    Base URL: {OPENROUTER_BASE_URL}")
    
    if not OPENROUTER_API_KEY:
        print("\n[ERROR] OPENROUTER_API_KEY not set in .env file!")
        return False
    
    # Test API call
    print(f"\n[2] Testing API Call:")
    print(f"    Sending test message to {OPENROUTER_MODEL}...")
    
    messages = [
        {
            "role": "user",
            "content": "Say 'Hello, ASFC is connected!' if you can read this."
        }
    ]
    
    response = query_openrouter(messages)
    
    if response:
        print(f"\n[SUCCESS] Connection successful!")
        print(f"    Response: {response[:100]}...")
        return True
    else:
        print(f"\n[ERROR] Connection failed!")
        return False

if __name__ == '__main__':
    success = test_connection()
    sys.exit(0 if success else 1)

