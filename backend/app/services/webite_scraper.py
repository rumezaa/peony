from typing import Dict, Any, List
import asyncio
from urllib.parse import urljoin, urlparse
from playwright.async_api import async_playwright
from .llm_cloner import LLMCloner
from bs4 import BeautifulSoup
import aiohttp
import os
import logging
from browserbase import Browserbase

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WebsiteScraper:
    def __init__(self):
        self.browser = None
        self.context = None
        self.playwright = None
        self.session_id = None
        
        # Browserbase configuration
        self.api_key = os.getenv('BROWSERBASE_API_KEY')
        self.project_id = os.getenv('BROWSERBASE_PROJECT_ID')
        self.browserbase = Browserbase(api_key=self.api_key)
        
        # Debug logging
        logger.info("Initializing WebsiteScraper with credentials:")
        logger.info(f"Project ID: {self.project_id}")
        logger.info(f"API Key exists: {bool(self.api_key)}")
        if self.api_key:
            logger.info(f"API Key length: {len(self.api_key)}")
            logger.info(f"API Key first 4 chars: {self.api_key[:4]}...")

    async def initialize(self):
        """Initialize the browser instance"""
        try:
            if self.api_key and self.project_id:
                await self._initialize_browserbase()
                logger.info("Successfully initialized Browserbase browser")
            else:
                logger.warning("Browserbase credentials not found, using local browser")
                await self._initialize_local()
        except Exception as e:
            logger.error(f"Failed to initialize Browserbase: {e}")
            logger.info("Falling back to local browser")
            await self._initialize_local()

    async def _initialize_browserbase(self):
        """Initialize Browserbase cloud browser"""
        # Create new browser session
        session = self.browserbase.sessions.create(project_id=self.project_id)
        self.session_id = session.id
        
        # Connect to browser using Playwright
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.connect_over_cdp(session.connect_url)
        self.context = self.browser.contexts[0]

    async def _initialize_local(self):
        """Initialize local browser instance"""
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=True)
        self.context = await self.browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        )

    async def extract_design_context(self, url: str) -> Dict[str, Any]:
        """Extract design context from the given URL"""
        page = await self.context.new_page()
        try:
            await page.goto(url, wait_until="networkidle")
            screenshot = await page.screenshot()
            
            # Get the page content
            content = await page.content()
            
            # Parse with BeautifulSoup
            soup = BeautifulSoup(content, 'html.parser')
            
            # Extract styles
            styles = []
            for style in soup.find_all('style'):
                styles.append(style.string)
            
            # Extract CSS links
            css_links = []
            for link in soup.find_all('link', rel='stylesheet'):
                css_links.append(link.get('href'))
            
            # Extract images
            images = []
            for img in soup.find_all('img'):
                images.append({
                    'src': img.get('src'),
                    'alt': img.get('alt', ''),
                    'width': img.get('width'),
                    'height': img.get('height')
                })
            
            # Get computed styles for key elements
            computed_styles = await page.evaluate('''() => {
                const elements = document.querySelectorAll('*');
                const styles = {};
                elements.forEach(el => {
                    const computed = window.getComputedStyle(el);
                    styles[el.tagName] = {
                        color: computed.color,
                        backgroundColor: computed.backgroundColor,
                        fontSize: computed.fontSize,
                        fontFamily: computed.fontFamily,
                        margin: computed.margin,
                        padding: computed.padding
                    };
                });
                return styles;
            }''')
            
            return {
                'html': content,
                'screenshot': screenshot,
                'styles': styles,
                'css_links': css_links,
                'images': images,
                'computed_styles': computed_styles
            }
            
        finally:
            await page.close()

    async def discover_site_pages(self, base_url: str, max_pages: int = 10) -> List[str]:
        """Discover all pages on the website"""
        discovered_pages = set([base_url])
        to_visit = [base_url]
        visited = set()
        
        page = await self.context.new_page()
        
        try:
            while to_visit and len(discovered_pages) < max_pages:
                current_url = to_visit.pop(0)
                if current_url in visited:
                    continue
                
                visited.add(current_url)
                
                try:
                    await page.goto(current_url, wait_until="networkidle", timeout=15000)
                    
                    # Extract all links
                    links = await page.evaluate('''() => {
                        return Array.from(document.querySelectorAll('a[href]'))
                            .map(link => link.href)
                            .filter(href => href);
                    }''')
                    
                    # Filter internal links
                    base_domain = urlparse(base_url).netloc
                    for link in links:
                        parsed_link = urlparse(link)
                        if (parsed_link.netloc == base_domain or not parsed_link.netloc):
                            full_link = urljoin(base_url, link)
                            if full_link not in discovered_pages:
                                discovered_pages.add(full_link)
                                to_visit.append(full_link)
                
                except Exception as e:
                    print(f"Error visiting {current_url}: {e}")
                    continue
        
        finally:
            await page.close()
        
        return list(discovered_pages)

    async def clone_multipage_website(self, base_url: str, max_pages: int = 10) -> Dict[str, str]:
        """Clone entire multi-page website"""
        try:
            await self.initialize()
            
            # Discover all pages
            pages = await self.discover_site_pages(base_url, max_pages)
            print(f"Discovered {len(pages)} pages to clone")
            
            cloned_pages = {}
            llm_cloner = LLMCloner()
            
            for i, page_url in enumerate(pages):
                print(f"Cloning page {i+1}/{len(pages)}: {page_url}")
                
                try:
                    # Extract design context
                    design_context = await self.extract_design_context(page_url)
                    
                    # Generate clone
                    cloned_html = await llm_cloner.generate_complete_clone(design_context)
                    
                    # Store with path as key
                    path = urlparse(page_url).path or "index"
                    cloned_pages[path] = cloned_html
                    
                    await asyncio.sleep(1)
                    
                except Exception as e:
                    print(f"Error cloning {page_url}: {e}")
                    continue
            
            return cloned_pages
            
        finally:
            await self.close()

    async def close(self):
        """Close browser resources"""

        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()