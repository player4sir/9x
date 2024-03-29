# 使用基于 Alpine Linux 的 Python 3.9 镜像
FROM python:3.9-alpine

# 设置工作目录为 /app
WORKDIR /app

# 复制Python依赖文件
COPY requirements.txt .

# 更新Alpine Linux仓库并安装依赖，然后清理缓存
RUN apk update && \
    apk add --no-cache openssl ca-certificates chromium nss freetype freetype-dev harfbuzz ttf-freefont && \
    sed -i -e 's/http:/https:/' /etc/apk/repositories && \
    rm -rf /var/cache/apk/* && \
    pip install --no-cache-dir -r requirements.txt

# 设置Pyppeteer的可执行路径环境变量
ENV PUPPETEER_EXECUTABLE_PATH=/usr/bin/chromium-browser

# 复制剩余的应用文件
COPY . .

# 创建一个非root用户并切换
RUN adduser -D nonrootuser
USER nonrootuser

# 暴露 8080 端口
EXPOSE 8080

# 启动 Python 应用
CMD ["gunicorn", "-b", "0.0.0.0:8080", "app:app"]
