import json
from fastapi import FastAPI
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from openai import OpenAI
import sqlite3
import pandas as pd
from collections import Counter
import time
from config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL
# ================= 1. 初始化大模型客户端 =================
# ⚠️ 注意：把你自己的 API Key 填在下面！
client = OpenAI(
    api_key=DEEPSEEK_API_KEY,
    base_url=DEEPSEEK_BASE_URL
)

# 全局只实例化一次 app，所有的接口都挂在它上面
app = FastAPI()

# ================= 2. 静态资源与图表接口 =================
# 挂载 assets 文件夹，让 ECharts 的 js 文件能通过网络访问
app.mount("/assets", StaticFiles(directory="assets"), name="assets")


@app.get("/chart", response_class=FileResponse)
def show_chart():
    # 返回我们本地生成的 HTML 图表文件
    return "skills_chart.html"


# ================= 3. 数据模型定义 =================
class JobRequest(BaseModel):
    raw_text: str


# ================= 4. 核心业务接口 =================
@app.get("/")
def read_root():
    return {"status": "success", "message": "我的AI系统跑起来了！"}


@app.post("/analyze")
def analyze_job(request: JobRequest):
    text = request.raw_text

    prompt = f"""
    你是一个资深的招聘数据分析师。下面是一段招聘网站抓取的文本，其中的字体混淆已在前端解密还原，数字与汉字均为原文。
    请直接抽取关键信息，不要推测、不要补全文本里没有的内容；某项确实缺失时填"未知"。严格按以下 JSON 格式输出，不要包含任何其他废话：
    {{
        "job_title": "推测出的完整职位名称（如：Java后端开发、Python爬虫实习生）",
        "salary": "薪资范围（如'面议'或'150-200/天'）",
        "skills": ["请从以下标准技能中挑选并输出：Python, Java, C++, SQL, 机器学习, 深度学习, NLP, 爬虫, 数据分析, 前端开发, 后端开发, 算法, 测试, 运维。不要自创词汇"],
        "is_ai_related": true 或 false,
        "education": "学历要求（如：本科、大专、不限）",
        "experience": "经验要求（如：1-3年、应届生、不限）",
        "company_size": "公司规模（如'大厂'、'中型企业'、'创业公司'）",
        "city": "城市名称（如：北京、大连）",
        "job_category": "请将岗位归类为：后端开发、前端开发、算法工程师、数据分析、测试工程师、运维工程师、其他"
    }}

    招聘文本如下：
    {text}
    """

    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        temperature=0.1
    )

    ai_result = response.choices[0].message.content

    try:
        parsed_data = json.loads(ai_result)
        parsed_data.pop("type", None)

        return {
            "status": "success",
            "data": parsed_data
        }
    except Exception as e:
        return {"status": "error", "message": "AI 返回格式有误", "raw": ai_result}


# ================= 5. 测试用前端页面 =================
@app.get("/web", response_class=HTMLResponse)
def read_web():
    return """
    <html>
        <body>
            <h2>招聘数据智能分析系统</h2>
            <p>以后这里放一个上传按钮，选了 Excel 文件后，后台自动清洗并调用 AI。</p>
            <p>然后页面上直接显示 Echarts 的柱状图。</p>
        </body>
    </html>
    """



@app.get("/dashboard", response_class=FileResponse)
def show_dashboard():
    # 直接返回我们刚写的炫酷大屏文件
    return "index.html"


@app.get("/api/dashboard_data")
def get_dashboard_data():
    conn = sqlite3.connect('jobs.db')
    df = pd.read_sql_query("SELECT * FROM job_analysis", conn)
    conn.close()

    # 1. 算 AI 占比
    ai_counts = df['is_ai_related'].value_counts()
    ai_data = [{"name": "非AI岗位", "value": int(ai_counts.get(0, 0))},
               {"name": "AI岗位", "value": int(ai_counts.get(1, 0))}]

    # 2. 算技能 Top 8
    all_skills = []
    for skills_str in df['skills'].dropna():
        if skills_str.strip():
            all_skills.extend([s.strip() for s in skills_str.split(',') if s.strip()])
    top_skills = Counter(all_skills).most_common(8)

    # 3. 算岗位类型 Top 5
    title_counts = df['job_title'].value_counts().head(5)

    # 4. 算薪资结算方式 (新增)
    def analyze_salary_type(salary_str):
        if pd.isna(salary_str): return "未知"
        if '/天' in str(salary_str): return "按天结算"
        if '/月' in str(salary_str): return "按月结算"
        if '面议' in str(salary_str): return "面议"
        return "其他"

    df['salary_type'] = df['salary'].apply(analyze_salary_type)
    salary_counts = df['salary_type'].value_counts()
    salary_data = [{"name": k, "value": int(v)} for k, v in salary_counts.items()]

    # 5. 🌟 直接读取数据库里大模型提取好的 city 字段
    # 过滤掉空值和'未知'，直接统计前 20 个城市
    valid_cities = df[df['city'].notna() & (df['city'] != '未知')]['city']
    city_counts = valid_cities.value_counts().head(20)
    city_data = [{"name": k, "value": int(v)} for k, v in city_counts.items()]
 # 👇👇👇 必须补上这个 return，把数据打包发给前端 👇👇👇
    return {
        "total": len(df),
        "ai_count": int(ai_counts.get(1, 0)),
        "ai_pie": ai_data,
        "skills_name": [x[0] for x in top_skills],
        "skills_value": [x[1] for x in top_skills],
        "titles_name": title_counts.index.tolist(),
        "titles_value": title_counts.values.tolist(),
        "salary_data": salary_data,
        "city_data": city_data
    }


@app.get("/api/generate_insight")
def generate_insight():
    try:
        # 1. 读取数据
        conn = sqlite3.connect('jobs.db')
        df = pd.read_sql_query("SELECT * FROM job_analysis", conn)
        conn.close()

        if len(df) == 0:
            return {"insight": "暂无数据，请先运行爬虫和数据处理流水线。"}

        # 2. 提取数据摘要（全部强制转换为原生 Python 类型，防止 JSON 报错）
        total = int(len(df))
        ai_count = int(df['is_ai_related'].sum())

        valid_cities = df[df['city'].notna() & (df['city'] != '未知')]
        top_cities = {str(k): int(v) for k, v in valid_cities['city'].value_counts().head(3).items()}

        all_skills_str = " ".join(df['skills'].dropna().tolist())

        summary_data = {
            "总样本数": total,
            "AI相关岗位数": ai_count,
            "热门城市前3名": top_cities,
            "热门技能原始文本": all_skills_str[:500]
        }

        # 3. 组装 Prompt（面向求职者）
        prompt = f"""
        你是一位资深的人力资源数据分析专家。
        我为你提供了一份近期实习招聘市场的真实数据摘要，如下：
        {json.dumps(summary_data, ensure_ascii=False, indent=2)}

        请你利用你的商业洞察力，针对【大学生求职者】，写一段高度概括的数据分析报告（200字以内）。
        要求：
        1. 语气要专业、犀利，给出实用的求职建议。
        2. 必须结合上面的数据（指出哪个城市实习需求最旺盛，AI相关岗位占比如何，哪些技能最吃香）。
        3. 不要废话，直接输出报告正文，不要包含任何 markdown 格式。
        """

        # 4. 请求大模型（加入重试机制和超时设置）
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = client.chat.completions.create(
                    model="deepseek-chat",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.7,
                    timeout=30.0  # 增加超时时间到 30 秒
                )
                ai_text = response.choices[0].message.content
                return {"insight": ai_text}  # 成功拿到结果，直接返回结束函数

            except Exception as e:
                print(f"⚠️ 第 {attempt + 1} 次请求失败: {e}")
                if attempt == max_retries - 1:
                    raise e  # 如果最后一次重试还失败，抛出异常给外层
                time.sleep(2)  # 失败后等 2 秒再试

    except Exception as e:
        # 如果大模型接口欠费、超时，或者代码报错，这里会接住，并给前端返回合法的 JSON
        print(f"❌ 报告生成报错: {e}")
        return {"insight": f"⚠️ 报告生成失败。原因：{str(e)}"}