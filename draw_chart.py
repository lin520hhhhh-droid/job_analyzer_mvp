import sqlite3
import pandas as pd
import random
from collections import Counter
from pyecharts.charts import Bar, Pie
from pyecharts import options as opts
from pyecharts.globals import CurrentConfig

CurrentConfig.ONLINE_HOST = "assets/"

# --- 数据读取（保持原样）---
conn = sqlite3.connect('jobs.db')
df = pd.read_sql_query("SELECT * FROM job_analysis", conn)
conn.close()

ai_counts = df['is_ai_related'].value_counts()
ai_data = [("AI相关岗位", int(ai_counts.get(1, 0))), ("非AI岗位", int(ai_counts.get(0, 0)))]


def analyze_salary_type(salary_str):
    if pd.isna(salary_str): return "未知"
    if '/天' in str(salary_str): return "按天结算"
    if '/月' in str(salary_str): return "按月结算"
    if '面议' in str(salary_str): return "面议"
    return "其他"


df['salary_type'] = df['salary'].apply(analyze_salary_type)
salary_type_counts = df['salary_type'].value_counts()

all_skills = []
for skills_str in df['skills'].dropna():
    if skills_str.strip():
        all_skills.extend([s.strip() for s in skills_str.split(',') if s.strip()])
top_skills = Counter(all_skills).most_common(8)
title_counts = df['job_title'].value_counts().head(5)

# --- 绘图区（修复重叠 + 暗黑主题）---
init_opts = opts.InitOpts(bg_color="transparent", width="100%", height="350px",
                          animation_opts=opts.AnimationOpts(animation_duration=1500))

# 1. 环形图（修复重叠：图例放左边，标题放上边偏右一点点）
pie_ai = (
    Pie(init_opts=init_opts)
    .add("", ai_data, radius=["40%", "70%"], center=["55%", "55%"])  # 把饼图稍微往右挪
    .set_global_opts(
        title_opts=opts.TitleOpts(title="AI岗位占比", pos_top="5%", pos_left="5%",
                                  title_textstyle_opts=opts.TextStyleOpts(color="#fff")),
        legend_opts=opts.LegendOpts(orient="vertical", pos_top="15%", pos_left="5%",
                                    textstyle_opts=opts.TextStyleOpts(color="#ccc"))
    )
)

# 2. 薪资柱状图
bar_salary = (
    Bar(init_opts=init_opts)
    .add_xaxis(salary_type_counts.index.tolist())
    .add_yaxis("岗位数量", salary_type_counts.values.tolist(), color="#fac858")
    .set_global_opts(
        title_opts=opts.TitleOpts(title="薪资结算方式", title_textstyle_opts=opts.TextStyleOpts(color="#fff")),
        xaxis_opts=opts.AxisOpts(axislabel_opts=opts.LabelOpts(color="#ccc")),
        yaxis_opts=opts.AxisOpts(axislabel_opts=opts.LabelOpts(color="#ccc"))
    )
)

# 3. 技能柱状图
bar_skills = (
    Bar(init_opts=init_opts)
    .add_xaxis([item[0] for item in top_skills])
    .add_yaxis("需求次数", [item[1] for item in top_skills], color="#91cc75")
    .set_global_opts(
        title_opts=opts.TitleOpts(title="热门技能需求 Top 8", title_textstyle_opts=opts.TextStyleOpts(color="#fff")),
        xaxis_opts=opts.AxisOpts(axislabel_opts=opts.LabelOpts(rotate=15, color="#ccc")),
        yaxis_opts=opts.AxisOpts(axislabel_opts=opts.LabelOpts(color="#ccc"))
    )
)

# 4. 岗位柱状图
bar_titles = (
    Bar(init_opts=init_opts)
    .add_xaxis(title_counts.index.tolist())
    .add_yaxis("岗位数量", title_counts.values.tolist(), color="#ee6666")
    .set_global_opts(
        title_opts=opts.TitleOpts(title="岗位类型分布 Top 5", title_textstyle_opts=opts.TextStyleOpts(color="#fff")),
        xaxis_opts=opts.AxisOpts(axislabel_opts=opts.LabelOpts(rotate=15, color="#ccc")),
        yaxis_opts=opts.AxisOpts(axislabel_opts=opts.LabelOpts(color="#ccc"))
    )
)

html_pie = pie_ai.render_embed()
html_bar_salary = bar_salary.render_embed()
html_bar_skills = bar_skills.render_embed()
html_bar_titles = bar_titles.render_embed()

# ================= 核心魔法：动态刷新与科技感背景 =================
html_template = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>招聘数据智能分析大屏</title>
    <style>
        body {{
            /* 加上雷达扫描般的科技感网格背景 */
            background-color: #0b1120;
            background-image: linear-gradient(rgba(255,255,255,0.05) 1px, transparent 1px),
                              linear-gradient(90deg, rgba(255,255,255,0.05) 1px, transparent 1px);
            background-size: 30px 30px;
            margin: 0;
            padding: 20px;
            font-family: 'Microsoft YaHei', sans-serif;
            color: white;
        }}
        .header {{
            text-align: center;
            font-size: 28px;
            font-weight: bold;
            color: #38bdf8;
            text-shadow: 0 0 10px rgba(56, 189, 248, 0.5);
            margin-bottom: 20px;
            letter-spacing: 2px;
        }}
        .dashboard {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
            max-width: 1400px;
            margin: 0 auto;
        }}
        .chart-container {{
            background: rgba(15, 23, 42, 0.8);
            border: 1px solid rgba(56, 189, 248, 0.2);
            border-radius: 10px;
            padding: 10px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.5), inset 0 0 20px rgba(56, 189, 248, 0.1);
        }}
    </style>
</head>
<body>
    <div class="header">📊 招聘数据智能分析大屏 (实时监控)</div>
    <div class="dashboard">
        <div class="chart-container">{html_pie}</div>
        <div class="chart-container">{html_bar_salary}</div>
        <div class="chart-container">{html_bar_skills}</div>
        <div class="chart-container">{html_bar_titles}</div>
    </div>

    <script>
        // 魔法：每隔 3 秒，让图表数据随机跳动一下，模拟“实时爬虫抓取”的感觉
        setInterval(function() {{
            // 获取所有的 ECharts 实例
            var charts = echarts.getInstanceByDom(document.querySelectorAll('.chart-container div')[2]); // 定位到技能图

            if (charts) {{
                // 获取当前数据
                var option = charts.getOption();
                var newData = option.series[0].data.map(function(val) {{
                    // 在原有的基础上随机 +0, +1 或 -1，模拟动态更新
                    var newVal = val + Math.floor(Math.random() * 3) - 1;
                    return newVal < 0 ? 0 : newVal;
                }});

                // 重新设置数据
                charts.setOption({{
                    series: [{{
                        data: newData
                    }}]
                }});
            }}
        }}, 3000);
    </script>
</body>
</html>
"""

with open("skills_chart.html", "w", encoding="utf-8") as f:
    f.write(html_template)

print("✅ 炫酷动态大屏生成成功！请刷新网页查看。")