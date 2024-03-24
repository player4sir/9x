# 导入所需的库
import os
from flask import Flask, request, jsonify
import pyppeteer
from bs4 import BeautifulSoup
import json
import asyncio
import logging
from fake_useragent import UserAgent

# 创建一个Flask对象
app = Flask(__name__)
web_site = 'https://9xbuddy.xyz/en-1cd'
# 定义一个异步函数，用于导航到网站
async def navigate_to_website(page):
    await page.goto(web_site)

# 定义一个异步函数，用于输入目标链接并提交
async def input_url_and_submit(page, url):
    # 等待输入框出现
    input_element = await page.waitForSelector('div.relative input[name="text"]')
    # 输入目标链接
    await input_element.type(url)
    # 点击提交按钮
    button_element = await page.querySelector('button.bg-blue-500.text-md.text-white.uppercase')
    await button_element.click()
    # 等待导航完成
    # await page.waitForNavigation()

# 定义一个异步函数，用于等待结果出现
async def wait_for_results(page):
    # 等待结果区域出现
    await page.waitForSelector('section.px-4.sm\\:px-0.container.mx-auto.mb-4.mt-10')

# 定义一个异步函数，用于从结果中提取数据
async def extract_data_from_results(page):
    # 获取网页的html内容
    html = await page.content()
    # 用BeautifulSoup解析html
    soup = BeautifulSoup(html, 'html.parser')
    # 找到所有的结果元素
    result_elements = soup.find_all('div', {'class': 'lg:flex lg:justify-center items-center text-gray-600 dark:text-gray-200 capitalize sm:uppercase text-sm tracking-wide px-3 py-3 pb-5 mb-2 border-b-2 border-gray-200 dark:border-night-500'})
    # 创建一个空列表，用于存储结果数据
    results = []
    # 遍历每个结果元素
    for e in result_elements:
        # 创建一个空字典，用于存储单个结果数据
        data = {}
        # 找到格式元素
        format_element = e.find('div', {'class': 'w-24 sm:w-1/3 lg:w-24 text-blue-500 uppercase'})
        # 获取格式文本，如果不存在则为None
        data['format'] = format_element.text if format_element else None
        # 找到分辨率元素
        resolution_element = e.find('div', {'class': 'w-1/2 sm:w-1/3 lg:w-1/2 truncate'})
        # 获取分辨率文本，如果不存在则为None
        resolution_text = resolution_element.text if resolution_element else None
        # 如果分辨率文本包含"备份"，则跳过该结果
        if "backup" in resolution_text:
            continue
        # 将分辨率文本赋值给字典
        data['res'] = resolution_text
        # 找到下载链接元素
        download_link_element = e.find('a')
        # 获取下载链接，如果不存在则为None
        data['link'] = download_link_element['href'] if download_link_element and 'href' in download_link_element.attrs else None
        # 如果格式是mp4，则将字典添加到列表中
        results.append(data)
    # 返回结果列表
    return results

# 定义一个异步函数，用于爬取网站
async def scrape_website(url, page):
    try:
        # 设置随机的用户代理
        await page.setUserAgent(UserAgent().random)
        # 调用导航函数
        await navigate_to_website(page)
        # 调用输入函数
        await input_url_and_submit(page, url)
        # 调用等待函数
        await wait_for_results(page)
        # 调用提取函数
        results = await extract_data_from_results(page)
        # 将结果转换成json格式，并打印到日志中
        json_results = json.dumps(results, indent=4, ensure_ascii=False)
        logging.info(json_results)
        # 返回结果
        return results
    # 捕获元素处理错误，并打印到日志中
    except pyppeteer.errors.ElementHandleError as e:
        logging.error(f"Element handling error: {e}")
        # 返回空列表
        return []
    # 捕获其他错误，并打印到日志中
    except Exception as e:
        logging.error(f"Error processing {url}: {e}")
        # 返回空列表
        return []

# 定义一个异步函数，用于创建浏览器和页面，并调用爬取函数
async def main(url):
    # 创建一个无头浏览器
    browser = await pyppeteer.launch(headless=True,executablePath=os.environ.get('PUPPETEER_EXECUTABLE_PATH'),
            args=['--no-sandbox', '--disable-setuid-sandbox'])
    # 创建一个新页面
    page = await browser.newPage()
    # 定义一个空列表，用于存储结果
    results = []
    try:
        # 调用爬取函数，并将结果赋值给列表
        results = await scrape_website(url, page)
    # 无论是否有错误，都关闭浏览器
    finally:
        await browser.close()
    # 返回结果
    return results

# 定义一个路由，用于处理/scrape的GET请求
@app.route('/api', methods=['GET'])
def scrape():
    # 获取请求参数中的url
    url = request.args.get('url')
    # 调用main函数，并将结果赋值给变量
    results = asyncio.run(main(url))
    # 将结果转换成json格式，并返回给客户端
    return jsonify(results)

# 如果是主模块，运行应用
# if __name__ == "__main__":
#     app.run(host='0.0.0.0',port=8080,debug=False,threaded=False)

