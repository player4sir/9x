import os
import logging
from typing import List, Optional
from contextlib import asynccontextmanager
from asyncio import Queue

from fastapi import FastAPI, Query, HTTPException, Depends
from fastapi.responses import JSONResponse
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.middleware.cors import CORSMiddleware
from crawl4ai.extraction_strategy import JsonCssExtractionStrategy
from playwright.async_api import async_playwright, Browser, Page
from pydantic import BaseModel

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 使用环境变量获取配置
WEB_SITE = os.getenv('WEB_SITE', 'https://9xbuddy.xyz/en-1cd')
CHROME_PATH = os.getenv('PUPPETEER_EXECUTABLE_PATH', '/usr/bin/chromium-browser')

class LinkItem(BaseModel):
    format: str
    res: str
    link: str

class ExtractionSchema(BaseModel):
    name: str
    baseSelector: str
    fields: List[dict]

schema = ExtractionSchema(
    name="Video Download Links",
    baseSelector="div.lg\\:flex.lg\\:justify-center.items-center.text-gray-600.dark\\:text-gray-200.capitalize.sm\\:uppercase.text-sm.tracking-wide.px-3.py-3.pb-5.mb-2.border-b-2.border-gray-200.dark\\:border-night-500",
    fields=[
        {
            "name": "format",
            "selector": "div.w-24.sm\\:w-1\\/3.lg\\:w-24.text-blue-500.uppercase",
            "type": "text",
        },
        {
            "name": "res",
            "selector": "div.w-1\\/2.sm\\:w-1\\/3.lg\\:w-1\\/2.truncate",
            "type": "text",
        },
        {
            "name": "link",
            "selector": "a",
            "type": "attribute",
            "attribute": "href",
        },
    ],
)

class BrowserPool:
    def __init__(self, max_browsers=3):
        self.max_browsers = max_browsers
        self.browsers = Queue()
        self.playwright = None

    async def setup(self):
        self.playwright = await async_playwright().start()
        for _ in range(self.max_browsers):
            browser = await self.playwright.chromium.launch(
                executable_path=CHROME_PATH,
                headless=True,
                chromium_sandbox=False
            )
            await self.browsers.put(browser)

    async def get_browser(self) -> Browser:
        return await self.browsers.get()

    async def release_browser(self, browser: Browser):
        await self.browsers.put(browser)

    async def close(self):
        while not self.browsers.empty():
            browser = await self.browsers.get()
            await browser.close()
        await self.playwright.stop()

browser_pool: Optional[BrowserPool] = None

async def scrape_website(url: str, browser: Browser) -> List[LinkItem]:
    extraction_strategy = JsonCssExtractionStrategy(schema.dict(), verbose=True)
    
    try:
        context = await browser.new_context()
        page: Page = await context.new_page()

        try:
            logger.info(f"Navigating to {WEB_SITE}")
            await page.goto(WEB_SITE, wait_until='domcontentloaded')
            
            logger.info(f"Inputting URL: {url}")
            await page.fill('div.relative input[name="text"]', url)
            await page.click('button.bg-blue-500.text-md.text-white.uppercase')
            
            logger.info("Waiting for results")
            await page.wait_for_selector('section.px-4.sm\\:px-0.container.mx-auto.mb-4.mt-10', timeout=30000)
            
            logger.info("Extracting data")
            content = await page.content()
            current_url = page.url
            result = extraction_strategy.extract(html=content, url=current_url)
            
            if result:
                processed_data = [
                    LinkItem(**item) for item in result
                    if item.get('format') == 'mp4' and 'backup' not in item.get('res', '').lower()
                ]
                logger.info(f"Extracted {len(processed_data)} items")
                return processed_data
            else:
                logger.warning("No data extracted")
                return []
        finally:
            await page.close()
            await context.close()
    except Exception as e:
        logger.error(f"Error during scraping: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@asynccontextmanager
async def lifespan(app: FastAPI):
    global browser_pool
    logger.info("Setting up browser pool")
    browser_pool = BrowserPool(max_browsers=3)  # 调整数量以适应您的需求
    await browser_pool.setup()
    yield
    if browser_pool:
        logger.info("Closing browser pool")
        await browser_pool.close()

app = FastAPI(title="52解析", lifespan=lifespan)

# 添加中间件
app.add_middleware(TrustedHostMiddleware, allowed_hosts=["*"])  # 在生产环境中应该限制允许的主机
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 在生产环境中应该限制允许的源
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api", response_class=JSONResponse)
async def scrape(url: str = Query(..., description="URL of the video to scrape")):
    """
    Scrape download links for a given video URL.
    """
    logger.info(f"Received request to scrape URL: {url}")
    try:
        if not browser_pool:
            raise HTTPException(status_code=500, detail="Browser pool not available.")
        
        browser = await browser_pool.get_browser()
        try:
            results = await scrape_website(url, browser)
        finally:
            await browser_pool.release_browser(browser)
        return results
    except Exception as e:
        logger.error(f"Error occurred while scraping: {str(e)}")
        raise HTTPException(status_code=500, detail="An error occurred during scraping.")