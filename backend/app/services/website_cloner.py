from typing import Dict, Any
from .llm_cloner import LLMCloner
from .webite_scraper import WebsiteScraper

class WebsiteCloner:
    def __init__(self):
        self.scraper = WebsiteScraper()
        self.llm_cloner = LLMCloner()

    async def clone_single_page(self, url: str) -> str:
        """Clone a single page"""
        try:
            await self.scraper.initialize()
            design_context = await self.scraper.extract_design_context(url)
            cloned_html = await self.llm_cloner.generate_complete_clone(design_context)
            return cloned_html
        finally:
            await self.scraper.close()

    async def clone_multipage_site(self, url: str, max_pages: int = 10) -> Dict[str, str]:
        """Clone entire multi-page website"""
        return await self.scraper.clone_multipage_website(url, max_pages)

    async def extract_design_context(self, url: str) -> Dict[str, Any]:
        """Extract design context only (for analysis)"""
        try:
            await self.scraper.initialize()
            return await self.scraper.extract_design_context(url)
        finally:
            await self.scraper.close()