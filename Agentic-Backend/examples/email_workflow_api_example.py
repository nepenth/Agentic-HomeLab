#!/usr/bin/env python3
"""
Email Workflow API Example

This script demonstrates how to create and use the email analyzer workflow
through the Agentic Backend API. It shows the complete workflow from
agent creation to task execution and result monitoring.
"""

import asyncio
import json
import time
from typing import Dict, Any, Optional
import aiohttp
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EmailWorkflowClient:
    """Client for interacting with the Email Analyzer Workflow API."""

    def __init__(self, base_url: str = "http://localhost:8000", api_key: str = "your-api-key"):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.session: Optional[aiohttp.ClientSession] = None
        self.agent_id: Optional[str] = None
        self.task_id: Optional[str] = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def _make_request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Dict:
        """Make an HTTP request to the API."""
        url = f"{self.base_url}{endpoint}"

        try:
            if data:
                async with self.session.request(method, url, json=data) as response:
                    response.raise_for_status()
                    return await response.json()
            else:
                async with self.session.request(method, url) as response:
                    response.raise_for_status()
                    return await response.json()
        except aiohttp.ClientError as e:
            logger.error(f"API request failed: {e}")
            raise

    async def check_system_health(self) -> Dict:
        """Check if the system is healthy."""
        logger.info("Checking system health...")
        return await self._make_request("GET", "/api/v1/health")

    async def create_email_analyzer_agent(self, agent_name: str = "My Email Analyzer") -> Dict:
        """Create an email analyzer agent instance."""
        logger.info(f"Creating email analyzer agent: {agent_name}")

        # First, we need to create the agent type (if it doesn't exist)
        # In a real scenario, you might want to check if it exists first
        agent_data = {
            "name": agent_name,
            "description": "Analyzes emails and creates follow-up tasks",
            "agent_type": "email_analyzer",
            "config": {
                "importance_threshold": 0.7,
                "max_emails": 50,
                "date_range": "7d"
            }
        }

        response = await self._make_request("POST", "/api/v1/agents/create", agent_data)
        self.agent_id = response["id"]
        logger.info(f"Created agent with ID: {self.agent_id}")
        return response

    async def run_email_analysis(self, email_credentials: Dict, options: Optional[Dict] = None) -> Dict:
        """Run email analysis task."""
        if not self.agent_id:
            raise ValueError("Agent not created yet. Call create_email_analyzer_agent() first.")

        logger.info("Starting email analysis task...")

        task_input = {
            "email_credentials": email_credentials,
            "processing_options": options or {
                "date_range": "7d",
                "max_emails": 50,
                "importance_threshold": 0.7
            }
        }

        response = await self._make_request("POST", "/api/v1/tasks/run", {
            "agent_id": self.agent_id,
            "input": task_input
        })

        self.task_id = response["id"]
        logger.info(f"Started task with ID: {self.task_id}")
        return response

    async def monitor_task_progress(self, task_id: Optional[str] = None) -> Dict:
        """Monitor task progress."""
        task_id = task_id or self.task_id
        if not task_id:
            raise ValueError("No task ID available")

        logger.info(f"Checking task status: {task_id}")
        return await self._make_request("GET", f"/api/v1/tasks/{task_id}/status")

    async def wait_for_completion(self, task_id: Optional[str] = None, timeout: int = 300) -> Dict:
        """Wait for task completion with timeout."""
        task_id = task_id or self.task_id
        if not task_id:
            raise ValueError("No task ID available")

        start_time = time.time()
        while time.time() - start_time < timeout:
            status = await self.monitor_task_progress(task_id)

            if status["status"] == "completed":
                logger.info("Task completed successfully!")
                return status
            elif status["status"] == "failed":
                logger.error(f"Task failed: {status.get('error_message', 'Unknown error')}")
                return status
            elif status["status"] == "running":
                logger.info("Task is still running...")

            await asyncio.sleep(5)  # Wait 5 seconds before checking again

        raise TimeoutError(f"Task did not complete within {timeout} seconds")

    async def get_task_logs(self, task_id: Optional[str] = None) -> list:
        """Get task execution logs."""
        task_id = task_id or self.task_id
        if not task_id:
            raise ValueError("No task ID available")

        logger.info(f"Fetching logs for task: {task_id}")
        return await self._make_request("GET", f"/api/v1/logs/{task_id}")

    async def list_created_tasks(self) -> list:
        """List tasks created by the email analyzer."""
        logger.info("Fetching created tasks...")
        return await self._make_request("GET", "/api/v1/workflow/tasks")

    async def mark_task_complete(self, task_id: str) -> Dict:
        """Mark a follow-up task as complete."""
        logger.info(f"Marking task {task_id} as complete")
        return await self._make_request("POST", f"/api/v1/workflow/tasks/{task_id}/complete")

    async def get_workflow_stats(self) -> Dict:
        """Get workflow statistics."""
        logger.info("Fetching workflow statistics...")
        return await self._make_request("GET", "/api/v1/workflow/stats")


async def main():
    """Main example workflow execution."""

    # Configuration
    API_KEY = "your-api-key-here"  # Replace with your actual API key
    EMAIL_CREDENTIALS = {
        "username": "your-email@gmail.com",
        "password": "your-app-password",
        "server": "imap.gmail.com",
        "port": 993
    }

    async with EmailWorkflowClient(api_key=API_KEY) as client:
        try:
            # Step 1: Check system health
            print("=== Step 1: System Health Check ===")
            health = await client.check_system_health()
            print(f"System status: {health.get('status', 'unknown')}")
            print()

            # Step 2: Create email analyzer agent
            print("=== Step 2: Creating Email Analyzer Agent ===")
            agent = await client.create_email_analyzer_agent("Demo Email Analyzer")
            print(f"Created agent: {agent['name']} (ID: {agent['id']})")
            print()

            # Step 3: Run email analysis
            print("=== Step 3: Running Email Analysis ===")
            task = await client.run_email_analysis(EMAIL_CREDENTIALS, {
                "date_range": "7d",
                "max_emails": 25,
                "importance_threshold": 0.6
            })
            print(f"Started analysis task: {task['id']}")
            print()

            # Step 4: Monitor progress
            print("=== Step 4: Monitoring Progress ===")
            final_status = await client.wait_for_completion(timeout=180)
            print(f"Task completed with status: {final_status['status']}")
            if final_status.get('output'):
                output = final_status['output']
                print(f"Processed {output.get('processed_emails', 0)} emails")
                print(f"Created {output.get('tasks_created', 0)} tasks")
            print()

            # Step 5: Get results
            print("=== Step 5: Getting Results ===")
            created_tasks = await client.list_created_tasks()
            print(f"Found {len(created_tasks)} created tasks")

            for task in created_tasks[:5]:  # Show first 5 tasks
                print(f"- Task: {task.get('task_description', 'N/A')[:50]}...")
                print(f"  Priority: {task.get('priority', 'N/A')}")
                print(f"  Status: {task.get('status', 'N/A')}")
            print()

            # Step 6: Get workflow stats
            print("=== Step 6: Workflow Statistics ===")
            stats = await client.get_workflow_stats()
            print(f"Total emails processed: {stats.get('emailsProcessed', 0)}")
            print(f"Total tasks created: {stats.get('tasksCreated', 0)}")
            print(f"Pending tasks: {stats.get('pendingTasks', 0)}")

        except Exception as e:
            logger.error(f"Workflow execution failed: {e}")
            print(f"Error: {e}")


async def interactive_example():
    """Interactive example showing real-time monitoring."""

    API_KEY = "your-api-key-here"
    EMAIL_CREDENTIALS = {
        "username": "your-email@gmail.com",
        "password": "your-app-password"
    }

    async with EmailWorkflowClient(api_key=API_KEY) as client:
        # Create agent
        agent = await client.create_email_analyzer_agent("Interactive Demo")

        # Start analysis
        task = await client.run_email_analysis(EMAIL_CREDENTIALS)

        # Monitor in real-time
        print("Monitoring task progress (Ctrl+C to stop)...")
        try:
            while True:
                status = await client.monitor_task_progress()
                print(f"Status: {status['status']} | Progress: {status.get('progress', 'N/A')}")

                if status['status'] in ['completed', 'failed']:
                    break

                await asyncio.sleep(10)

        except KeyboardInterrupt:
            print("\nMonitoring stopped by user")

        # Show final results
        final_status = await client.monitor_task_progress()
        print(f"\nFinal Status: {final_status['status']}")
        if final_status.get('output'):
            print(f"Results: {json.dumps(final_status['output'], indent=2)}")


if __name__ == "__main__":
    print("Email Workflow API Example")
    print("=" * 50)

    # Choose which example to run
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "interactive":
        print("Running interactive example...")
        asyncio.run(interactive_example())
    else:
        print("Running complete workflow example...")
        print("Note: Make sure to update API_KEY and EMAIL_CREDENTIALS in the script")
        asyncio.run(main())