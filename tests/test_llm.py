import asyncio
import sys
from google import genai
from src.config import settings

async def test_connection():
    print("Testing connection to Gemini API...")
    
    if settings.GOOGLE_API_KEY == "placeholder" or not settings.GOOGLE_API_KEY:
        print("[WARNING] GOOGLE_API_KEY is not set. Please configure it in your .env file.")
        print("Skipping actual API call to prevent authentication error.")
        return False
        
    try:
        # The new google-genai SDK uses client.aio for async calls
        client = genai.Client(api_key=settings.GOOGLE_API_KEY)
        response = await client.aio.models.generate_content(
            model=settings.GEMINI_MODEL,
            contents="Hello! Confirm connection."
        )
        print("Success! Response from Gemini:")
        print(response.text)
        return True
    except Exception as e:
        print(f"Error connecting to Gemini: {e}", file=sys.stderr)
        return False

if __name__ == "__main__":
    asyncio.run(test_connection())
