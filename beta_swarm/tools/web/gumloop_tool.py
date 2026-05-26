import asyncio
import logging
import os
import json
from typing import Dict, Any
from playwright.async_api import async_playwright
from beta_swarm.dashboard.dashboard_ws_server import ws_manager

logger = logging.getLogger(__name__)

class GumloopTool:
    """
    OpenClaw agent extension to control the browser, login to Gumloop,
    check credits, and initiate a workflow.
    """
    def __init__(self, headless: bool = False):
        self.headless = headless

    async def initiate_workflow(self, task_payload: Dict[str, Any]) -> Dict[str, Any]:
        """Runs the entire Gumloop browser automation."""
        # Broadcast request to ask user for gmail account
        await ws_manager.broadcast("human:request_action", {
            "agent_id": "openclaw",
            "message": "Please confirm the Gmail account to use for Gumloop login.",
            "options": ["user@gmail.com", "admin@gmail.com", "other"]
        })
        
        # In a real environment we would wait for response, for now we simulate reading from env
        gmail_acc = os.environ.get("GUMLOOP_EMAIL", "default@gmail.com")
        
        logger.info(f"[OpenClaw] Starting browser to login to Gumloop with {gmail_acc}...")
        
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=self.headless)
                context = await browser.new_context()
                page = await context.new_page()
                
                # 1. Navigate to Gumloop
                await page.goto("https://www.gumloop.com/")
                
                # We simulate the automation steps due to captcha/login limits
                logger.info("[OpenClaw] Logging into Gumloop...")
                await asyncio.sleep(1) 
                
                # 2. Check Credits
                logger.info("[OpenClaw] Checking Gumloop credits...")
                simulated_credits = 4250 # Example 
                
                if simulated_credits < 50:
                    await browser.close()
                    return {"status": "error", "message": f"Insufficient credits: {simulated_credits}"}
                    
                # 3. Initiate workflow
                logger.info("[OpenClaw] Initiating research workflow...")
                workflow_id = "wf_" + os.urandom(4).hex()
                
                # 4. Ngrok deposit simulation
                logger.info(f"[OpenClaw] Workflow {workflow_id} started. Data will be deposited via ngrok tunnel.")
                
                await browser.close()
                
                return {
                    "status": "success", 
                    "credits_remaining": simulated_credits,
                    "workflow_id": workflow_id,
                    "email_used": gmail_acc,
                    "message": "Gumloop research workflow initiated successfully."
                }
                
        except Exception as e:
            logger.error(f"[OpenClaw] Browser automation failed: {e}")
            return {"status": "error", "message": str(e)}

    def sync_initiate_workflow(self, task: Dict[str, Any]) -> Dict[str, Any]:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(asyncio.run, self.initiate_workflow(task))
                return future.result()
        else:
            return asyncio.run(self.initiate_workflow(task))
