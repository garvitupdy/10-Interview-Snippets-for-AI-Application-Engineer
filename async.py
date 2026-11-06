
"""
Snippet: Concurrent Multi-Tool Execution Orchestrator
Difficulty: Advanced
Interview Context:
This snippet evaluates your ability to optimize Agentic workflows for latency. In production, an LLM might trigger multiple independent tools (e.g., fetching data from three different APIs); executing these sequentially is a major bottleneck. 
Interviewers look for proficiency with asyncio primitives and robust error isolation—ensuring one failing tool doesn't crash the entire batch.
"""
import asyncio
import json
import time
from typing import Any, Dict, List, Callable
# Mock Tool Definitions 
# We use 'async' here because most production tools are I/O bound (API calls, DB queries).
async def get_stock_price(symbol: str) -> str:
"""Simulates a network-bound API call to fetch stock data."""
    await asyncio.sleep(1.0) # Simulate 1 second of network latency
    prices = {"AAPL": "150.00", "GOOG": "2800.00"}
    return f"Price of {symbol}: ${prices.get(symbol.upper(), 'N/A')}"

async def get_company_news(symbol: str) -> str:
"""Simulates a network-bound API call to fetch news headlines."""
    await asyncio.sleep(1.2) # Simulate 1.2 seconds of network latency
    return f"Latest news for {symbol}: 'Record earnings reported!'"

async def get_weather(location: str) -> str:
"""Simulates a tool that might fail."""
    await asyncio.sleep(0.5)
    if location.lower() == "error":
    raise ValueError("Weather service is currently offline.")
    return f"Weather in {location}: Sunny, 25°C"
# The Orchestrator
class ConcurrentToolRunner:
    def init(self, registry: Dict[str, Callable]):
    self.registry = registry
    
    async def _execute_single_tool(self, tool_call: Dict[str, Any]) -> Dict[str, Any]:
        """
        Wraps a single tool execution with error handling.
         Why? If we run 5 tools and one throws an exception, we don't want 
        asyncio.gather to fail the entire batch. We want to capture the 
        error and return it as an 'Observation' for the LLM to see.
        """
        call_id = tool_call.get("id", "unknown")
        function_info = tool_call.get("function", {})
        name = function_info.get("name")
        # Arguments from LLMs are usually strings; we must parse them.
        args = json.loads(function_info.get("arguments", "{}"))
    
        if name not in self.registry:
            return {
                "id": call_id,
                "output": f"Error: Tool '{name}' not found in registry."
            }
    
        try:
            # Execute the tool from the registry
            # We await it because our tools are defined as async functions.
            result = await self.registry[name](**args)
            return {"id": call_id, "output": result}
        except Exception as e:
            # Capture the stack trace or error message to feed back to the LLM
            return {"id": call_id, "output": f"Error executing {name}: {str(e)}"}
    
    async def run_parallel(self, llm_response: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Parses the LLM response and runs all tool calls concurrently.
        
        Latency Logic:
        If Tool A takes 1s and Tool B takes 1.2s:
        - Sequential: 2.2 seconds
        - Concurrent: 1.2 seconds (Max of the batch)
        """
        tool_calls = llm_response.get("tool_calls", [])
        if not tool_calls:
            return []
    
        # 1. Create a list of 'Tasks' (Futures)
        # We don't await them yet; we just prepare the coroutines.
        tasks = [self._execute_single_tool(tc) for tc in tool_calls]
    
        # 2. Execute concurrently using asyncio.gather
        # This is the core primitive for running multiple I/O operations at once.
        # It returns a list of results in the same order as the tasks.
        print(f"Dispatching {len(tasks)} tools concurrently")
        start_time = time.perf_counter()
        
        results = await asyncio.gather(*tasks)
        
        end_time = time.perf_counter()
        print(f"All tools finished in {end_time - start_time:.2f}s")
        
        return results


if name == "main":
# 1. Setup Registry
tool_map = {
"get_stock_price": get_stock_price,
"get_company_news": get_company_news,
"get_weather": get_weather
}
runner = ConcurrentToolRunner(tool_map)

# 2. Mock LLM Output (Simulating a Parallel Tool Call response)
# This follows the OpenAI 'tool_calls' schema.
mock_llm_output = {
    "tool_calls": [
        {
            "id": "call_001",
            "function": {"name": "get_stock_price", "arguments": '{"symbol": "AAPL"}'}
        },
        {
            "id": "call_002",
            "function": {"name": "get_company_news", "arguments": '{"symbol": "AAPL"}'}
        },
        {
            "id": "call_003",
            "function": {"name": "get_weather", "arguments": '{"location": "error"}'}
        }
    ]
}

# 3. Run the Event Loop
async def test():
    results = await runner.run_parallel(mock_llm_output)
    
    for res in results:
        print(f"ID: {res['id']} | Result: {res['output']}")

    # Sanity Check: Total time should be ~1.2s, not ~2.7s (1.0 + 1.2 + 0.5)
    # Sanity Check: The 'error' location should have returned a string error, not crashed the script.
    assert len(results) == 3
    assert any("ValueError" in r["output"] for r in results), "Error isolation failed!"

asyncio.run(test())
"""
Performance & Design Notes:
Threading vs Asyncio: We use asyncio here because these tools simulate network I/O.
If the tools were CPU-bound (e.g., heavy data processing), we would use
'loop.run_in_executor' with a ProcessPoolExecutor to bypass the GIL.
JSON Safety: In a real-world scenario, LLMs occasionally output malformed JSON
in arguments. The 'json.loads' should be wrapped in a try-except block
inside the execution wrapper.
Scalability: For massive batches (e.g., 100+ calls), you might want to use
an 'asyncio.Semaphore' to throttle concurrency and avoid hitting rate limits
on external APIs.
"""
