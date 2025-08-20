import json
import logging
import os
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import openai
from playwright.sync_api import Page, Playwright, sync_playwright


@dataclass
class TaskResult:
    success: bool
    message: str
    details: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class LLMInterface(ABC):
    """Abstract interface for LLM reasoning."""
    
    @abstractmethod
    def interpret_instruction(self, instruction: str) -> Dict[str, Any]:
        """Convert natural language instruction to structured task."""
        pass
    
    @abstractmethod
    def generate_ui_steps(self, task: Dict[str, Any], page_content: str) -> List[Dict[str, Any]]:
        """Generate UI interaction steps based on page content."""
        pass


class MockLLM(LLMInterface):
    """Mock LLM for testing without API calls."""
    
    def interpret_instruction(self, instruction: str) -> Dict[str, Any]:
        """Parse common email/scheduling patterns."""
        instruction_lower = instruction.lower()
        
        if "email" in instruction_lower and "send" in instruction_lower:
            # Extract email details
            to_match = re.search(r'to\s+([^\s]+@[^\s]+)', instruction_lower)
            subject_match = re.search(r'about\s+([^.]+)', instruction_lower)
            
            return {
                "action": "send_email",
                "to": to_match.group(1) if to_match else "recipient@example.com",
                "subject": subject_match.group(1).strip() if subject_match else "Message",
                "body": "Automated message from AI agent"
            }
        
        elif "schedule" in instruction_lower and "meeting" in instruction_lower:
            return {
                "action": "schedule_meeting",
                "title": "AI Scheduled Meeting",
                "duration": "30",
                "description": "Meeting scheduled by AI agent"
            }
        
        else:
            return {
                "action": "unknown",
                "message": f"Could not interpret: {instruction}"
            }
    
    def generate_ui_steps(self, task: Dict[str, Any], page_content: str) -> List[Dict[str, Any]]:
        """Generate mock UI steps based on task type."""
        if task["action"] == "send_email":
            return [
                {"action": "click", "selector": "button[aria-label='Compose']", "description": "Click Compose button"},
                {"action": "fill", "selector": "input[name='to']", "value": task["to"], "description": "Fill recipient field"},
                {"action": "fill", "selector": "input[name='subject']", "value": task["subject"], "description": "Fill subject field"},
                {"action": "fill", "selector": "textarea[name='body']", "value": task["body"], "description": "Fill message body"},
                {"action": "click", "selector": "button[type='submit']", "description": "Click Send button"}
            ]
        
        elif task["action"] == "schedule_meeting":
            return [
                {"action": "click", "selector": "button[aria-label='Create']", "description": "Click Create button"},
                {"action": "fill", "selector": "input[name='title']", "value": task["title"], "description": "Fill meeting title"},
                {"action": "fill", "selector": "input[name='duration']", "value": task["duration"], "description": "Fill duration"},
                {"action": "click", "selector": "button[type='submit']", "description": "Click Save button"}
            ]
        
        return []


class OpenAILLM(LLMInterface):
    """OpenAI GPT integration for real LLM reasoning."""
    
    def __init__(self, api_key: str):
        self.client = openai.OpenAI(api_key=api_key)
    
    def interpret_instruction(self, instruction: str) -> Dict[str, Any]:
        """Use OpenAI to interpret natural language instruction."""
        try:
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are an AI assistant that converts natural language instructions into structured task objects. Return only valid JSON."},
                    {"role": "user", "content": f"Convert this instruction to a task object: {instruction}"}
                ],
                temperature=0.1
            )
            
            content = response.choices[0].message.content
            return json.loads(content)
        
        except Exception as e:
            logging.error(f"OpenAI API error: {e}")
            return {"action": "error", "message": str(e)}
    
    def generate_ui_steps(self, task: Dict[str, Any], page_content: str) -> List[Dict[str, Any]]:
        """Use OpenAI to generate UI interaction steps."""
        try:
            prompt = f"""
            Task: {json.dumps(task)}
            Page content: {page_content[:1000]}...
            
            Generate a list of UI interaction steps as JSON array. Each step should have:
            - action: "click", "fill", "wait", or "navigate"
            - selector: CSS selector or text to find element
            - value: value to fill (for fill actions)
            - description: human-readable description
            
            Return only valid JSON array.
            """
            
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are an AI assistant that generates UI automation steps. Return only valid JSON arrays."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1
            )
            
            content = response.choices[0].message.content
            return json.loads(content)
        
        except Exception as e:
            logging.error(f"OpenAI API error: {e}")
            return []


class WebServiceProvider(ABC):
    """Abstract base for different web service providers."""
    
    def __init__(self, name: str, base_url: str):
        self.name = name
        self.base_url = base_url
    
    @abstractmethod
    def authenticate(self, page: Page, credentials: Dict[str, str]) -> bool:
        """Authenticate with the service."""
        pass
    
    @abstractmethod
    def execute_task(self, page: Page, task: Dict[str, Any], ui_steps: List[Dict[str, Any]]) -> TaskResult:
        """Execute the given task using the provided UI steps."""
        pass


class GmailProvider(WebServiceProvider):
    """Gmail web interface automation."""
    
    def __init__(self):
        super().__init__("Gmail", "https://mail.google.com")
    
    def authenticate(self, page: Page, credentials: Dict[str, str]) -> bool:
        """Authenticate with Gmail."""
        try:
            page.goto(f"{self.base_url}/mail")
            
            # Check if already logged in
            if page.locator("button[aria-label='Compose']").count() > 0:
                logging.info("Already authenticated with Gmail")
                return True
            
            # Fill email
            page.fill("input[type='email']", credentials["email"])
            page.click("button:has-text('Next')")
            
            # Wait for password field and fill
            page.wait_for_selector("input[type='password']")
            page.fill("input[type='password']", credentials["password"])
            page.click("button:has-text('Next')")
            
            # Wait for Gmail to load
            page.wait_for_selector("button[aria-label='Compose']", timeout=30000)
            logging.info("Successfully authenticated with Gmail")
            return True
            
        except Exception as e:
            logging.error(f"Gmail authentication failed: {e}")
            return False
    
    def execute_task(self, page: Page, task: Dict[str, Any], ui_steps: List[Dict[str, Any]]) -> TaskResult:
        """Execute email task in Gmail."""
        try:
            for step in ui_steps:
                logging.info(f"Executing step: {step['description']}")
                
                if step["action"] == "click":
                    page.click(step["selector"])
                elif step["action"] == "fill":
                    page.fill(step["selector"], step["value"])
                elif step["action"] == "wait":
                    page.wait_for_timeout(int(step.get("value", 1000)))
                
                page.wait_for_timeout(500)  # Small delay between steps
            
            # Wait for success indication
            page.wait_for_timeout(2000)
            
            return TaskResult(
                success=True,
                message=f"Successfully executed {task['action']} in Gmail",
                details={"provider": "Gmail", "task": task}
            )
            
        except Exception as e:
            return TaskResult(
                success=False,
                message=f"Failed to execute task in Gmail",
                error=str(e)
            )


class OutlookProvider(WebServiceProvider):
    """Outlook web interface automation."""
    
    def __init__(self):
        super().__init__("Outlook", "https://outlook.live.com")
    
    def authenticate(self, page: Page, credentials: Dict[str, str]) -> bool:
        """Authenticate with Outlook."""
        try:
            page.goto(f"{self.base_url}/mail")
            
            # Check if already logged in
            if page.locator("button[aria-label='New message']").count() > 0:
                logging.info("Already authenticated with Outlook")
                return True
            
            # Fill email
            page.fill("input[type='email']", credentials["email"])
            page.click("button:has-text('Next')")
            
            # Wait for password field and fill
            page.wait_for_selector("input[type='password']")
            page.fill("input[type='password']", credentials["password"])
            page.click("button:has-text('Sign in')")
            
            # Wait for Outlook to load
            page.wait_for_selector("button[aria-label='New message']", timeout=30000)
            logging.info("Successfully authenticated with Outlook")
            return True
            
        except Exception as e:
            logging.error(f"Outlook authentication failed: {e}")
            return False
    
    def execute_task(self, page: Page, task: Dict[str, Any], ui_steps: List[Dict[str, Any]]) -> TaskResult:
        """Execute email task in Outlook."""
        try:
            for step in ui_steps:
                logging.info(f"Executing step: {step['description']}")
                
                if step["action"] == "click":
                    page.click(step["selector"])
                elif step["action"] == "fill":
                    page.fill(step["selector"], step["value"])
                elif step["action"] == "wait":
                    page.wait_for_timeout(int(step.get("value", 1000)))
                
                page.wait_for_timeout(500)  # Small delay between steps
            
            # Wait for success indication
            page.wait_for_timeout(2000)
            
            return TaskResult(
                success=True,
                message=f"Successfully executed {task['action']} in Outlook",
                details={"provider": "Outlook", "task": task}
            )
            
        except Exception as e:
            return TaskResult(
                success=False,
                message=f"Failed to execute task in Outlook",
                error=str(e)
            )


class GenericUIAgent:
    """Main agent class that orchestrates cross-platform automation."""
    
    def __init__(self, llm: LLMInterface, headless: bool = True):
        self.llm = llm
        self.headless = headless
        self.playwright: Optional[Playwright] = None
        self.browser = None
        self.page: Optional[Page] = None
        
        # Register available providers
        self.providers: Dict[str, WebServiceProvider] = {
            "gmail": GmailProvider(),
            "outlook": OutlookProvider(),
        }
    
    def start(self):
        """Start the browser automation environment."""
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(headless=self.headless)
        self.page = self.browser.new_page()
        logging.info("Browser automation environment started")
    
    def stop(self):
        """Stop the browser automation environment."""
        if self.page:
            self.page.close()
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()
        logging.info("Browser automation environment stopped")
    
    def execute_across_providers(self, instruction: str, provider_names: List[str], credentials: Dict[str, Dict[str, str]]) -> List[TaskResult]:
        """Execute a task across multiple providers."""
        if not self.page:
            raise RuntimeError("Agent not started. Call start() first.")
        
        # Interpret the instruction
        task = self.llm.interpret_instruction(instruction)
        logging.info(f"Interpreted task: {task}")
        
        results = []
        
        for provider_name in provider_names:
            if provider_name not in self.providers:
                logging.warning(f"Unknown provider: {provider_name}")
                continue
            
            provider = self.providers[provider_name]
            provider_creds = credentials.get(provider_name, {})
            
            logging.info(f"Executing task on {provider.name}")
            
            try:
                # Authenticate
                if not provider.authenticate(self.page, provider_creds):
                    results.append(TaskResult(
                        success=False,
                        message=f"Authentication failed for {provider.name}",
                        error="Authentication failed"
                    ))
                    continue
                
                # Get page content for UI step generation
                page_content = self.page.content()
                
                # Generate UI steps
                ui_steps = self.llm.generate_ui_steps(task, page_content)
                logging.info(f"Generated {len(ui_steps)} UI steps for {provider.name}")
                
                # Execute task
                result = provider.execute_task(self.page, task, ui_steps)
                results.append(result)
                
            except Exception as e:
                results.append(TaskResult(
                    success=False,
                    message=f"Execution failed for {provider.name}",
                    error=str(e)
                ))
        
        return results


def main():
    """CLI interface for the agent."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Cross-Platform Action Agent")
    parser.add_argument("instruction", help="Natural language instruction (e.g., 'Send email to joe@example.com about meeting')")
    parser.add_argument("--providers", nargs="+", default=["gmail", "outlook"], help="Providers to use")
    parser.add_argument("--headless", action="store_true", default=True, help="Run browser in headless mode")
    parser.add_argument("--mock-llm", action="store_true", help="Use mock LLM instead of OpenAI")
    
    args = parser.parse_args()
    
    # Configure logging
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    
    # Initialize LLM
    if args.mock_llm:
        llm = MockLLM()
        logging.info("Using mock LLM")
    else:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logging.error("OPENAI_API_KEY environment variable not set. Using mock LLM instead.")
            llm = MockLLM()
        else:
            llm = OpenAILLM(api_key)
            logging.info("Using OpenAI LLM")
    
    # Initialize agent
    agent = GenericUIAgent(llm, headless=args.headless)
    
    try:
        agent.start()
        
        # Mock credentials for demo
        credentials = {
            "gmail": {"email": "demo@gmail.com", "password": "demo"},
            "outlook": {"email": "demo@outlook.com", "password": "demo"}
        }
        
        # Execute task
        results = agent.execute_across_providers(args.instruction, args.providers, credentials)
        
        # Print results
        for i, result in enumerate(results):
            print(f"\nProvider {i+1} ({args.providers[i]}):")
            print(f"  Success: {result.success}")
            print(f"  Message: {result.message}")
            if result.error:
                print(f"  Error: {result.error}")
            if result.details:
                print(f"  Details: {result.details}")
    
    finally:
        agent.stop()


if __name__ == "__main__":
    main()
