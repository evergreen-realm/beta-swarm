import os
import re
import sys
import json
import time
import pickle
import logging
import hashlib
from datetime import datetime
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

# Predefined common technologies for extraction
TECH_KEYWORDS = [
    "React", "Vue", "Angular", "Svelte", "FastAPI", "Flask", "Django", "Node.js", 
    "Express", "Python", "JavaScript", "TypeScript", "HTML5", "CSS3", "Tailwind", 
    "Bootstrap", "SQL", "PostgreSQL", "MySQL", "SQLite", "MongoDB", "Redis", 
    "Docker", "Kubernetes", "AWS", "Google Cloud", "Azure", "Selenium", 
    "Playwright", "Next.js", "Nuxt.js", "GraphQL", "REST", "Aider", "Goose"
]

class GumloopWebManager:
    def __init__(self, project_path: str = "C:/Users/Admin/Documents/Beta Swarnv2"):
        self.project_path = project_path
        self.email = os.getenv("GUMLOOP_EMAIL")
        self.password = os.getenv("GUMLOOP_PASSWORD")
        self.cookie_path = os.path.join(self.project_path, "gumloop_cookies.pkl")
        self.results_dir = os.path.join(self.project_path, "gumloop_results")
        os.makedirs(self.results_dir, exist_ok=True)
        
        self.ngrok_tunnel = None
        self.webhook_url = None
        self.webhook_log_file = os.path.join(self.project_path, "gumloop_webhook_url.txt")

    def _ensure_browser(self):
        """Set up and return Chrome or Edge Selenium WebDriver."""
        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
            from webdriver_manager.chrome import ChromeDriverManager
            from selenium.webdriver.chrome.service import Service
            
            options = Options()
            options.add_argument("--headless=new")
            options.add_argument("--disable-gpu")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
            
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=options)
            return driver
        except Exception as e_chrome:
            logger.warning(f"Failed to initialize Chrome, trying Edge: {e_chrome}")
            try:
                from selenium import webdriver
                from selenium.webdriver.edge.options import Options
                from webdriver_manager.microsoft import EdgeChromiumDriverManager
                from selenium.webdriver.edge.service import Service
                
                options = Options()
                options.add_argument("--headless")
                options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
                
                service = Service(EdgeChromiumDriverManager().install())
                driver = webdriver.Edge(service=service, options=options)
                return driver
            except Exception as e_edge:
                logger.error(f"Failed to initialize browser: {e_edge}")
                raise RuntimeError(f"No usable browser driver found (Chrome/Edge): {e_edge}")

    def login(self, driver) -> bool:
        """Logs into Gumloop using email and password and saves cookies."""
        if not self.email or not self.password:
            logger.warning("Gumloop credentials missing from environment.")
            return False
            
        try:
            logger.info("Navigating to Gumloop login...")
            driver.get("https://www.gumloop.com/login")
            time.sleep(3)
            
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            
            # Find email and password input fields defensively
            email_field = WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.XPATH, "//input[@type='email' or contains(@placeholder, 'email') or contains(@placeholder, 'Email')]"))
            )
            email_field.clear()
            email_field.send_keys(self.email)
            
            pass_field = driver.find_element(By.XPATH, "//input[@type='password' or contains(@placeholder, 'password') or contains(@placeholder, 'Password')]")
            pass_field.clear()
            pass_field.send_keys(self.password)
            
            # Find and click login/submit button
            submit_btn = driver.find_element(By.XPATH, "//button[contains(text(), 'Sign In') or contains(text(), 'Log In') or contains(text(), 'Login') or @type='submit']")
            submit_btn.click()
            
            # Wait for dashboard redirects
            WebDriverWait(driver, 30).until(
                lambda d: "/dashboard" in d.current_url or "/home" in d.current_url or "/chat" in d.current_url or "/pipeline" in d.current_url
            )
            
            # Save cookies
            cookies = driver.get_cookies()
            with open(self.cookie_path, "wb") as f:
                pickle.dump(cookies, f)
            logger.info("Successfully logged in and saved cookies.")
            return True
        except Exception as e:
            logger.error(f"Gumloop login failed: {e}")
            return False

    def load_cookies(self, driver) -> bool:
        """Tries to load cached cookies and verifies logged in state."""
        if not os.path.exists(self.cookie_path):
            return False
            
        try:
            logger.info("Loading cookies for Gumloop...")
            driver.get("https://www.gumloop.com/")
            time.sleep(2)
            
            with open(self.cookie_path, "rb") as f:
                cookies = pickle.load(f)
                for cookie in cookies:
                    driver.add_cookie(cookie)
            
            driver.get("https://www.gumloop.com/dashboard")
            time.sleep(3)
            
            if "/login" not in driver.current_url:
                logger.info("Successfully restored login session via cookies.")
                return True
        except Exception as e:
            logger.warning(f"Failed to load cookies: {e}")
        return False

    def trigger_research_chat(self, query: str, depth: str = "standard") -> str:
        """Triggers Gumloop research chat and returns raw scraped response text."""
        driver = self._ensure_browser()
        try:
            # Check login
            logged_in = self.load_cookies(driver)
            if not logged_in:
                logged_in = self.login(driver)
                
            if not logged_in:
                raise RuntimeError("Could not authenticate to Gumloop.")
                
            # Navigate to chat page
            driver.get("https://www.gumloop.com/chat")
            time.sleep(4)
            
            from selenium.webdriver.common.by import By
            from selenium.webdriver.common.keys import Keys
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            
            # Construct structured prompt
            if depth == "quick":
                prompt = f"Research: {query}. Quick overview only."
            elif depth == "deep":
                prompt = f"Deep research: {query}. Comprehensive analysis with multiple sources, expert opinions, comparative analysis, and implementation recommendations."
            else:
                prompt = f"Research: {query}. Full web research with sources. Extract key findings, technologies mentioned, and best practices."
                
            # Find input box
            input_box = WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.XPATH, "//textarea[contains(@placeholder, 'message') or contains(@placeholder, 'Ask')] | //input[@type='text']"))
            )
            input_box.send_keys(prompt)
            input_box.send_keys(Keys.ENTER)
            logger.info(f"Submitted Gumloop prompt: {prompt}")
            
            # Wait for response completion (polling text stability)
            timeout = 300
            start_time = time.time()
            last_text = ""
            stable_time = 0
            
            # Find bot message container xpath - defensive check
            bot_msg_xpath = "//div[contains(@class, 'bot-message') or contains(@class, 'assistant') or contains(@class, 'response')]"
            
            while time.time() - start_time < timeout:
                time.sleep(5)
                try:
                    elements = driver.find_elements(By.XPATH, bot_msg_xpath)
                    if elements:
                        current_text = elements[-1].text
                        # If text stops changing for 10 seconds, assume completed
                        if current_text and current_text == last_text:
                            stable_time += 5
                            if stable_time >= 10:
                                logger.info("Response stable, scraping completed.")
                                break
                        else:
                            last_text = current_text
                            stable_time = 0
                    else:
                        # Fallback: get all visible text on the page
                        body_text = driver.find_element(By.TAG_NAME, "body").text
                        # Match something containing "Research:" response
                        last_text = body_text
                except Exception:
                    pass
            
            if not last_text:
                raise TimeoutError("Timeout waiting for Gumloop response.")
                
            # Save raw response
            query_hash = hashlib.md5(query.encode('utf-8')).hexdigest()[:8]
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            raw_path = os.path.join(self.results_dir, f"{timestamp}_{query_hash}.txt")
            with open(raw_path, "w", encoding="utf-8") as f:
                f.write(last_text)
                
            return last_text
        finally:
            driver.quit()

    def extract_structured_findings(self, raw_text: str) -> Dict[str, Any]:
        """Parses the raw text response into structured findings, sources, and tech."""
        # Extracts URLs
        url_pattern = re.compile(r'https?://[^\s\)\]]+')
        sources = list(set(url_pattern.findall(raw_text)))
        
        # Extracts Technologies
        technologies = []
        for tech in TECH_KEYWORDS:
            if re.search(r'\b' + re.escape(tech) + r'\b', raw_text, re.IGNORECASE):
                technologies.append(tech)
                
        # Confidence Score based on number of references/sources
        confidence = min(1.0, 0.5 + 0.1 * len(sources))
        
        return {
            "findings": raw_text[:2000],
            "sources": sources,
            "technologies": technologies,
            "confidence": confidence,
            "raw": raw_text
        }

    def start_ngrok_webhook(self, port: int = 8765) -> str:
        """Starts a local ngrok tunnel to receive webhook data from Gumloop."""
        try:
            from pyngrok import ngrok
            authtoken = os.getenv("NGROK_AUTHTOKEN")
            if authtoken:
                ngrok.set_auth_token(authtoken)
            
            self.ngrok_tunnel = ngrok.connect(port)
            self.webhook_url = self.ngrok_tunnel.public_url + "/webhook/gumloop"
            
            with open(self.webhook_log_file, "w", encoding="utf-8") as f:
                f.write(self.webhook_url)
                
            logger.info(f"ngrok webhook URL configured: {self.webhook_url}")
            return self.webhook_url
        except Exception as e:
            logger.error(f"Failed to start ngrok: {e}")
            return ""

    def receive_webhook_result(self, timeout: int = 300) -> Optional[Dict]:
        """Polls results dir for newly generated webhook JSON results."""
        start_time = time.time()
        while time.time() - start_time < timeout:
            time.sleep(2)
            try:
                files = [os.path.join(self.results_dir, f) for f in os.listdir(self.results_dir) if f.startswith("webhook_") and f.endswith(".json")]
                if files:
                    # Return latest file content
                    latest_file = max(files, key=os.path.getmtime)
                    with open(latest_file, "r", encoding="utf-8") as f:
                        return json.load(f)
            except Exception as e:
                logger.warning(f"Error checking webhook files: {e}")
        return None

    def _local_search_fallback(self, query: str, depth: str) -> Dict[str, Any]:
        """Local DuckDuckGo research fallback when Gumloop is unavailable."""
        logger.info(f"Running local DuckDuckGo fallback research for: {query}")
        results = []
        try:
            from duckduckgo_search import DDGS
            with DDGS() as ddgs:
                ddgs_res = list(ddgs.text(query, max_results=5))
                for r in ddgs_res:
                    results.append({
                        "title": r.get("title", ""),
                        "url": r.get("href", ""),
                        "snippet": r.get("body", "")
                    })
        except Exception as e:
            logger.warning(f"DuckDuckGo search failed: {e}")
            
        findings = f"Local Research fallback for query: '{query}'.\n\n"
        sources = []
        techs = []
        
        if results:
            for idx, r in enumerate(results, 1):
                findings += f"[{idx}] {r['title']}\nSnippet: {r['snippet']}\nSource: {r['url']}\n\n"
                sources.append(r["url"])
                # Extract technologies from snippets
                for tech in TECH_KEYWORDS:
                    if tech.lower() in r['snippet'].lower() or tech.lower() in r['title'].lower():
                        if tech not in techs:
                            techs.append(tech)
        else:
            findings += "No research results retrieved. Proceeding with standard project defaults."
            
        return {
            "findings": findings[:2000],
            "sources": list(set(sources)),
            "technologies": techs,
            "confidence": 0.5,
            "raw": findings
        }

    def run_research(self, query: str, depth: str = "standard") -> Dict[str, Any]:
        """Executes full research pipeline using webhook -> browser -> local search fallback."""
        # 1. Webhook Approach
        if os.path.exists(self.webhook_log_file):
            try:
                with open(self.webhook_log_file, "r", encoding="utf-8") as f:
                    url = f.read().strip()
                if url:
                    logger.info("Webhook active. Waiting for webhook callback...")
                    result = self.receive_webhook_result(timeout=60) # Wait 60 seconds for quick check
                    if result:
                        logger.info("Webhook payload successfully received.")
                        raw_content = json.dumps(result, indent=2)
                        return self.extract_structured_findings(raw_content)
            except Exception as e:
                logger.warning(f"Webhook retrieval failed: {e}")

        # 2. Browser Automation Approach
        if self.email and self.password:
            try:
                logger.info("Running browser automation to trigger Gumloop research...")
                raw_text = self.trigger_research_chat(query, depth)
                if raw_text:
                    return self.extract_structured_findings(raw_text)
            except Exception as e:
                logger.warning(f"Browser automation failed: {e}. Falling back to local search.")

        # 3. Fallback to DuckDuckGo search
        return self._local_search_fallback(query, depth)
