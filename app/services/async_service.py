"""
ASYNC SERVICE - Asynchronous operations for better performance

This service provides async versions of operations that can benefit from
non-blocking execution, particularly LLM API calls and database operations.
"""

import asyncio
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from app.services.llm import judge_prompt, optimize_prompt
from app.utils import get_logger

logger = get_logger(__name__)

class AsyncService:
    """Service class for asynchronous operations."""
    
    @staticmethod
    async def async_judge_prompt(prompt: str, response: Optional[str] = None) -> Dict[str, Any]:
        """
        Asynchronous version of judge_prompt for non-blocking LLM calls.
        
        This runs the LLM evaluation in a thread pool to avoid blocking
        the main event loop.
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, judge_prompt, prompt, response)
    
    @staticmethod
    async def async_optimize_prompt(original: str, notes: Optional[str] = "") -> str:
        """
        Asynchronous version of optimize_prompt for non-blocking LLM calls.
        
        This runs the LLM optimization in a thread pool to avoid blocking
        the main event loop.
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, optimize_prompt, original, notes)
    
    @staticmethod
    async def batch_evaluate_prompts(prompts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Evaluate multiple prompts concurrently for better performance.
        
        Args:
            prompts: List of dicts with 'prompt' and optional 'response' keys
            
        Returns:
            List of evaluation results in the same order
        """
        tasks = []
        for prompt_data in prompts:
            task = AsyncService.async_judge_prompt(
                prompt_data.get('prompt', ''),
                prompt_data.get('response')
            )
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle any exceptions
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Error evaluating prompt {i}: {result}")
                processed_results.append({
                    "error": str(result),
                    "prompt_index": i
                })
            else:
                processed_results.append(result)
        
        return processed_results
    
    @staticmethod
    async def async_database_operation(operation_func, *args, **kwargs):
        """
        Run database operations in a thread pool to avoid blocking.
        
        This is useful for heavy database operations that might block
        the event loop.
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, operation_func, *args, **kwargs)
