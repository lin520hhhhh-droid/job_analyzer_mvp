import requests
import json

# 你的本地接口地址
url = "http://127.0.0.1:8000/analyze"

# 模拟你爬虫抓下来的 3 条招聘文案
job_texts = [
    "急招资深Python开发，要求精通FastAPI和大模型RAG，月薪25k-35k。",
    "招数据分析实习生，熟悉Pandas，包吃包住，日薪200。",
    "招聘前端Vue工程师，要求3年经验，不用懂AI，月薪15k。"
]

results = []

for text in job_texts:
    # 构造发送给 FastAPI 的数据
    payload = {"raw_text": text}

    # 发送 POST 请求
    response = requests.post(url, json=payload)

    # 提取返回的 JSON 数据
    if response.status_code == 200:
        data = response.json().get("data")
        results.append(data)
        print(f"成功解析：{data}")
    else:
        print(f"报错啦：{response.text}")

# 最后，把结果存成一个文件（这就叫“落库”的平替）
with open("results.json", "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=4)
print("所有数据已保存到 results.json")