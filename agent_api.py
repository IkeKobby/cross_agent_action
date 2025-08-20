import json
import logging
import os
from typing import Dict, List, Optional

import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from agent import GenericUIAgent, MockLLM, OpenAILLM


class InstructionRequest(BaseModel):
    instruction: str
    providers: List[str] = ["gmail", "outlook"]
    headless: bool = True
    use_mock_llm: bool = True


class TaskResult(BaseModel):
    success: bool
    message: str
    details: Optional[Dict] = None
    error: Optional[str] = None


class InstructionResponse(BaseModel):
    task_interpretation: Dict
    results: List[TaskResult]


app = FastAPI(
    title="Cross-Platform Action Agent API",
    description="Execute natural language instructions across multiple web services",
    version="1.0.0",
)


@app.get("/")
async def root():
    return {
        "message": "Cross-Platform Action Agent API",
        "version": "1.0.0",
        "available_providers": ["gmail", "outlook"]
    }


@app.post("/execute", response_model=InstructionResponse)
async def execute_instruction(request: InstructionRequest):
    """Execute a natural language instruction across multiple providers."""
    
    # Configure logging
    logging.basicConfig(level=logging.INFO)
    
    try:
        # Initialize LLM
        if request.use_mock_llm:
            llm = MockLLM()
            logging.info("Using mock LLM")
        else:
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise HTTPException(
                    status_code=400,
                    detail="OPENAI_API_KEY environment variable not set. Use use_mock_llm=true for testing."
                )
            llm = OpenAILLM(api_key)
            logging.info("Using OpenAI LLM")
        
        # Initialize agent
        agent = GenericUIAgent(llm, headless=request.headless)
        
        try:
            agent.start()
            
            # Mock credentials for demo (in production, these would come from secure storage)
            credentials = {
                "gmail": {"email": "demo@gmail.com", "password": "demo"},
                "outlook": {"email": "demo@outlook.com", "password": "demo"}
            }
            
            # Execute task
            results = agent.execute_across_providers(
                request.instruction,
                request.providers,
                credentials
            )
            
            # Convert results to response format
            response_results = []
            for result in results:
                response_results.append(TaskResult(
                    success=result.success,
                    message=result.message,
                    details=result.details,
                    error=result.error
                ))
            
            # Get task interpretation from LLM
            task_interpretation = llm.interpret_instruction(request.instruction)
            
            return InstructionResponse(
                task_interpretation=task_interpretation,
                results=response_results
            )
            
        finally:
            agent.stop()
            
    except Exception as e:
        logging.error(f"Execution failed: {e}")
        raise HTTPException(status_code=500, detail=f"Execution failed: {str(e)}")


@app.get("/providers")
async def get_providers():
    """Get available service providers."""
    return {
        "providers": [
            {
                "name": "gmail",
                "description": "Gmail web interface",
                "base_url": "https://mail.google.com"
            },
            {
                "name": "outlook",
                "description": "Outlook web interface", 
                "base_url": "https://outlook.live.com"
            }
        ]
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": "2025-08-20T11:00:00Z"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)
