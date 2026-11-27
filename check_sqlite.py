import sqlite3
from distutils.util import execute

#  1. 连接SQLite(因为脚本和db文件在同级目录，直接用文件名)
conn = sqlite3.connect('jobs.db')
cursor = conn.cursor()

# 2. 查看数据库里有那些表
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cursor.fetchall()
print("===发现数据表===")
for table in tables:
    print(f"- {table[0]}")

# 3. 看看 'job_analysis' 表的具体结构
print("\n=== 'job_analysis' 表的字段结构 ===")
cursor.execute("PRAGMA table_info(job_analysis);")
columns = cursor.fetchall()
for col in columns:
    print(f"字段名：{col[1]:<15} | 类型：{col[2]}")

# 4. 看一眼前三条数据什么样
print("\n=== 前3条数据样例 ===")
cursor.execute("SELECT * FROM job_analysis LIMIT 3")
rows = cursor.fetchall()
for row in rows:
    print(row)

conn.close()