
import os
from dotenv import load_dotenv

# 获取当前 config.py 所在目录，并拼上 .env
env_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(env_path)

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")

if not DEEPSEEK_API_KEY:
    raise ValueError("❌ 缺少 DEEPSEEK_API_KEY，请检查 .env 文件！")