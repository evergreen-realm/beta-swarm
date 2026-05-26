import logging
from typing import Dict, Optional
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

logger = logging.getLogger(__name__)

class SeleniumTool:
    """
    A tool for autonomous agents to interact with the web using Selenium.
    Useful for specific legacy compatibility or scenarios where Selenium is preferred.
    """
    
    def __init__(self, headless: bool = True):
        self.options = Options()
        if headless:
            self.options.add_argument("--headless")
        self.options.add_argument("--no-sandbox")
        self.options.add_argument("--disable-dev-shm-usage")

    def fetch_page_content(self, url: str) -> Dict[str, str]:
        """Fetch the text content and title using Selenium."""
        driver = webdriver.Chrome(options=self.options)
        try:
            driver.get(url)
            # Wait for body to be present
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            text = driver.find_element(By.TAG_NAME, "body").text
            title = driver.title
            return {
                "url": url,
                "title": title,
                "text": text[:10000],
                "source": "selenium"
            }
        except Exception as e:
            logger.error(f"Selenium error fetching {url}: {e}")
            return {"error": str(e), "url": url}
        finally:
            driver.quit()

if __name__ == "__main__":
    # Quick test
    tool = SeleniumTool()
    result = tool.fetch_page_content("https://example.com")
    print(f"Title: {result.get('title')}")
