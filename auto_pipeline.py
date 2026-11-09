import json
import requests
import sqlite3
import time

# ---------------- 1. 读取真实爬虫抓取的数据 ----------------
try:
    with open("raw_scraped_data.json", "r", encoding="utf-8") as f:
        json_data = json.load(f)
    # 提取字典里的 raw_text 字段，组装成列表
    real_scraped_data = [item["raw_text"] for item in json_data]
    print(f"📦 成功加载 {len(real_scraped_data)} 条真实爬虫数据！")
except FileNotFoundError:
    print("❌ 找不到 raw_scraped_data.json，请先运行 spider.py！")
    exit()

# ---------------- 2. 准备数据库 ----------------
conn = sqlite3.connect('jobs.db')
cursor = conn.cursor()

# 建表（加了新字段）
cursor.execute('''
    CREATE TABLE IF NOT EXISTS job_analysis (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        job_title TEXT,
        salary TEXT,
        skills TEXT,
        is_ai_related BOOLEAN,
        education TEXT,
        experience TEXT,
        company_size TEXT,
        city TEXT
    )
''')
conn.commit() # 建表后提交一下

# ---------------- 3. 开始自动化批量请求 ----------------
api_url = "http://127.0.0.1:8000/analyze"
success_count = 0

print(f"🤖 开始处理数据...\n")

for index, raw_text in enumerate(real_scraped_data):
    # 💡 先跑 50 条试试水，防止余额耗尽
    # if index >= 50:
    #     print("⚠️ 已测试 50 条数据，自动停止！")
    #     break

    # print(f"[{index + 1}/50] 正在请求 AI 分析: {raw_text[:15]}...")
    if index % 100 == 0 and index > 0:
        print(f"--- 已经处理 {index} 条，休息 5 秒防封 ---")
        time.sleep(5)

    payload = {"raw_text": raw_text}

    try:
        # proxies 显式置空：本机装了系统代理，会把 127.0.0.1 也劫持走导致连接失败
        response = requests.post(api_url, json=payload, timeout=60,
                                 proxies={"http": None, "https": None})
        response.raise_for_status()

        response_data = response.json()

        if response_data.get("status") == "success":
            ai_data = response_data.get("data")

            # 把技能列表转成字符串
            skills_str = ", ".join(ai_data.get("skills", []))

            # 🌟 注意这里：升级后的 8 字段插入语句
            cursor.execute('''
                INSERT INTO job_analysis (job_title, salary, skills, is_ai_related, education, experience, company_size, city)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                ai_data.get("job_title"),
                ai_data.get("salary"),
                skills_str,
                ai_data.get("is_ai_related"),
                ai_data.get("education"),
                ai_data.get("experience"),
                ai_data.get("company_size"),
                ai_data.get("city")
            ))
            conn.commit()
            success_count += 1
            print(f"   ✅ 入库成功: {ai_data.get('job_title')} | {ai_data.get('salary')} | {ai_data.get('education')} | {ai_data.get('city')}")
        else:
            print(f"   ❌ AI 解析失败: {response_data}")

    except Exception as e:
        print(f"   ❌ 接口请求报错: {e}")

    # 停顿一下，防止 API 请求过快
    time.sleep(1)

conn.close()
print(f"\n🎉 流水线运行完毕！成功入库 {success_count} 条新维度数据到 jobs.db")