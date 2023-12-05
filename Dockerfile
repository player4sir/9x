# 使用基于 Alpine Linux 的 Python 3.9 镜像
FROM python:3.9-alpine

# 设置工作目录为 /app
WORKDIR /app

# 复制当前目录下的所有文件到容器中
COPY . .

ENV PUPPETEER_SKIP_CHROMIUM_DOWNLOAD=true

# 更新Alpine Linux仓库
RUN apk update && apk upgrade
RUN sed -i -e 's/http:/https:/' /etc/apk/repositories
# 安装 Python 依赖包
RUN pip install --no-cache-dir -r requirements.txt
# 安装 Pyppeteer 的依赖，包括 Chromium 浏览器
RUN apk add --no-cache openssl ca-certificates chromium nss freetype freetype-dev harfbuzz ttf-freefont

ENV PUPPETEER_EXECUTABLE_PATH=/usr/bin/chromium-browser

# 暴露 5000 端口
EXPOSE 8080

# 启动 Python 应用
CMD ["python", "app.py"]