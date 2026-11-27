import sqlite3
import pymysql

# --- 配置区 ---
SQLITE_DB = 'jobs.db'
MYSQL_CONFIG = {
    'host': '127.0.0.1',
    'port': 3306,
    'user': 'root',
    'password': 'root',  # 确保这是你的 MySQL 密码
    'database': 'jobs_db',
    'charset': 'utf8mb4'
}

def migrate():
    print("1. 正在连接数据库...")
    sqlite_conn = sqlite3.connect(SQLITE_DB)
    sqlite_cursor = sqlite_conn.cursor()

    mysql_conn = pymysql.connect(**MYSQL_CONFIG)
    mysql_cursor = mysql_conn.cursor()

    print("2. 正在读取SQLite数据(表名P: job_analysis)...")
    # 注意: 我们把id也查出来了，这样数据迁移过去ID不会乱
    sqlite_cursor.execute("""
        SELECT id, job_title, salary, skills, is_ai_related, 
               education, experience, company_size, city 
        FROM job_analysis
    """)
    rows = sqlite_cursor.fetchall()
    print(f'   -> 成功读取{len(rows)}条数据')

    print("3. 正在写入 MySQL...")
    # 字段名必须和刚才新建的 MySQL 表一模一样
    insert_sql = """
        INSERT INTO job_analysis 
        (id, job_title, salary, skills, is_ai_related, education, experience, company_size, city) 
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    """

    try:
        # 批量插入
        mysql_cursor.executemany(insert_sql, rows)
        mysql_conn.commit()
        print(f"   -> 🎉 成功迁移 {mysql_cursor.rowcount} 条数据！")
    except Exception as e:
        mysql_conn.rollback()
        print(f"   ❌ 迁移失败，已回滚。错误原因: {e}")

    # 4. 关闭连接
    sqlite_cursor.close()
    sqlite_conn.close()
    mysql_cursor.close()
    mysql_conn.close()

if __name__ == "__main__":
    migrate()