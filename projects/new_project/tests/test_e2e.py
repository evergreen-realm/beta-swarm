import os
import pytest
from playwright.sync_api import sync_playwright

def test_frontend_basic():
    # Use real Playwright E2E testing to verify the generated HTML frontend
    index_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend", "index.html"))
    if not os.path.exists(index_path):
        # If running React, check the build public index
        index_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend", "public", "index.html"))
        
    assert os.path.exists(index_path), "index.html frontend file does not exist"
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            page.goto("file://" + index_path)
            # Verify DOM element and visual page title
            assert "Test App" in page.title()
            
            # Click button if it exists
            btn = page.locator("#fetch-btn")
            if btn.count() > 0:
                btn.click()
        finally:
            browser.close()
