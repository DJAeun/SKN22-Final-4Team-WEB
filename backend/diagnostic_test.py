import os
import sys
from pathlib import Path
from dotenv import load_dotenv

def diagnostic():
    BASE_DIR = Path(__file__).resolve().parent
    print(f"Base Directory: {BASE_DIR}")
    
    # Load .env
    env_path = BASE_DIR / '.env'
    if env_path.exists():
        load_dotenv(env_path)
        print(f"✅ Loaded .env from {env_path}")
    else:
        print(f"⚠️ .env not found at {env_path}")

    api_key = os.getenv("OPENAI_API_KEY")
    
    if not api_key:
        print("❌ Error: OPENAI_API_KEY not found in environment")
        return
    else:
        print(f"✅ Success: OPENAI_API_KEY found (starts with: {api_key[:10]}...)")
        
    try:
        print("--- Testing Real API Call ---")
        from langchain_openai import ChatOpenAI
        from langchain_core.messages import HumanMessage
        
        llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
        print("Sending message: 'Hello, are you there?'")
        response = llm.invoke([HumanMessage(content="Hello, are you there?")])
        print(f"✅ Real API response: {response.content}")
        
    except Exception as e:
        print(f"❌ Real API call failed: {e}")
        import traceback
        traceback.print_exc()

    try:
        print("\n--- Testing HariAIEngine Initialization ---")
        # Ensure imports work
        sys.path.append(str(BASE_DIR))
        from chat.engine import HariAIEngine
        
        engine = HariAIEngine()
        if engine.chain:
            print("✅ HariAIEngine initialized successfully!")
            print("Testing engine.get_response()...")
            resp = engine.get_response("안녕?")
            print(f"✅ Engine response: {resp}")
        else:
            print("❌ HariAIEngine chain initialization failed (see logs).")
    except Exception as e:
        print(f"❌ HariAIEngine test failed: {e}")

if __name__ == "__main__":
    diagnostic()
