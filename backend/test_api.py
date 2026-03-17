import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")
print(f"Testing API Key: {api_key[:10]}...")

client = OpenAI(api_key=api_key)

try:
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": "Say hello!"}]
    )
    print("API Success!")
    print(response.choices[0].message.content)
except Exception as e:
    print(f"API Error: {e}")
