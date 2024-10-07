# 使用 Debian-based Python 3.9 镜像
FROM python:3.9-slim

# 设置工作目录为 /app
WORKDIR /app

# 复制Python依赖文件
COPY requirements.txt .

# 更新包列表并安装依赖
RUN apt-get update && apt-get install -y \
    chromium \
    chromium-driver \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 安装 Python 依赖
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# 设置Playwright相关的环境变量
ENV PLAYWRIGHT_BROWSERS_PATH=/usr/bin
ENV PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1
ENV PUPPETEER_EXECUTABLE_PATH=/usr/bin/chromium

# 设置Node.js内存限制
ENV NODE_OPTIONS=--max_old_space_size=256

# 设置其他环境变量（如果需要）
ENV WEB_SITE=https://9xbuddy.xyz/en-1cd

# 复制剩余的应用文件
COPY . .

# 创建一个非root用户并切换
RUN useradd -m nonrootuser
USER nonrootuser

# 暴露 8080 端口
EXPOSE 8080

# 启动 Python 应用，设置 worker 数量和超时
CMD ["gunicorn", "-k", "uvicorn.workers.UvicornWorker", "-w", "2", "--timeout", "120", "-b", "0.0.0.0:8080", "app:app"]