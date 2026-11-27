# 1. 使用官方 Python 3.9 镜像（和你本地环境一致）
FROM python:3.9-slim

# 2. 设置工作目录
WORKDIR /app

# 3. 复制依赖文件并安装 (利用缓存机制，加快速度)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 4. 复制所有项目代码
COPY ../.. .

# 5. 暴露端口 (Render/Railway 会动态分配，但写个默认的比较好)
EXPOSE 8000

# 6. 启动命令
# ⚠️ 重点：host 必须是 0.0.0.0，不能是 127.0.0.1，否则外网访问不到！
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]