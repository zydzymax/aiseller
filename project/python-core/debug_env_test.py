import os
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.expanduser("~/ai_seller/project/.env"))

key = os.getenv("OPENAI_API_KEY")

if key:
    print("✅ Ключ найден:", key[:8] + "...")
else:
    print("❌ Ключ не найден")

