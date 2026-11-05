"""
Snippet: Streaming Token & Tool Buffer Orchestrator
Difficulty: Advanced
Interview Context:
This is a high-frequency question for "AI Platform" or "Inference Optimization" roles. It tests your ability to manage asynchronous state, minimize Time To First Token (TTFT) for users, and correctly handle the "Parallel Tool Calling" mechanic where an LLM might stream text and multiple JSON tool arguments simultaneously.
"""
import json
import asyncio
from typing import AsyncGenerator, Dict, Any, List, Optional
async def process_llm_stream(stream_iterator: AsyncGenerator[Dict[str, Any], None]):
"""
Processes a raw LLM stream, yielding text tokens to the client immediately
while buffering tool call arguments for backend execution.
Code
Why this pattern? 
1. UX: Users see text immediately (low latency).
2. Correctness: Tool arguments are partial JSON strings until the stream ends; 
   attempting to parse them mid-stream will cause JSONDecodeErrors.
"""

# Track partial content for logging or internal state
full_content = []

# Tool calls are often sent as a list of 'deltas'. 
# We use a dict keyed by 'index' to support Parallel Tool Calling.
# Structure: { index: {"name": str, "arguments": [str, str, ...]} }
tool_buffers: Dict[int, Dict[str, Any]] = {}

print("--- Starting Stream Processing ---")

async for chunk in stream_iterator:
    # OpenAI/Anthropic style chunks usually have a 'choices' or 'delta' key
    delta = chunk.get("choices", [{}])[0].get("delta", {})

    # 1. Handle Partial Text Tokens
    # We yield these immediately to the frontend.
    if "content" in delta and delta["content"]:
        token = delta["content"]
        full_content.append(token)
        # In a real API, you'd yield this to the HTTP response
        yield {"type": "token", "data": token}

    # 2. Handle Tool Call Deltas
    # Tool calls stream in fragments: first the 'name', then chunks of 'arguments'.
    if "tool_calls" in delta:
        for tool_delta in delta["tool_calls"]:
            idx = tool_delta.get("index", 0)
            
            # Initialize buffer for this specific tool index if not present
            if idx not in tool_buffers:
                tool_buffers[idx] = {"name": "", "arguments": []}
            
            # The 'name' is usually only sent in the first chunk for that index
            if "function" in tool_delta:
                fn_delta = tool_delta["function"]
                if "name" in fn_delta:
                    tool_buffers[idx]["name"] = fn_delta["name"]
                
                # Append the partial JSON string fragment to our list
                if "arguments" in fn_delta:
                    tool_buffers[idx]["arguments"].append(fn_delta["arguments"])

# 3. Post-Stream: Finalize and Parse Tool Calls
# Once the stream is exhausted, we join the fragments and parse the JSON.
final_tool_calls = []
for idx, data in tool_buffers.items():
    full_args_str = "".join(data["arguments"])
    try:
        # Numerical Safety: Ensure we handle empty or malformed JSON
        parsed_args = json.loads(full_args_str) if full_args_str else {}
        
        final_tool_calls.append({
            "index": idx,
            "name": data["name"],
            "args": parsed_args
        })
    except json.JSONDecodeError as e:
        # Production Tip: If the LLM cuts off due to max_tokens, 
        # the JSON will be truncated. You need a strategy (retry or fail).
        yield {"type": "error", "data": f"Failed to parse tool {idx}: {str(e)}"}

if final_tool_calls:
    yield {"type": "tool_calls", "data": final_tool_calls}
--- Mock Stream Generator for Verification ---
async def mock_openai_stream():

# Simulates a stream where the model says "Hello!" and then calls a 'get_weather' tool.
                         
chunks = [
{"choices": [{"delta": {"content": "Hello"}}]},
{"choices": [{"delta": {"content": "! "}}]},
{"choices": [{"delta": {"tool_calls": [{"index": 0, "function": {"name": "get_weather"}}]}}]},
{"choices": [{"delta": {"tool_calls": [{"index": 0, "function": {"arguments": '{"locat'}}]}}]},
{"choices": [{"delta": {"tool_calls": [{"index": 0, "function": {"arguments": 'ion": "NYC"'}}]}}]},
{"choices": [{"delta": {"tool_calls": [{"index": 0, "function": {"arguments": '}'}}]}}]},
]
for chunk in chunks:
await asyncio.sleep(0.05) # Simulate network latency
yield chunk
async def main():
# Consume the processed stream
async for message in process_llm_stream(mock_openai_stream()):
if message["type"] == "token":
# Real-time output
print(f"Token received: {message['data']}")
elif message["type"] == "tool_calls":
# Final buffered output
print(f"\nAll Tool Calls Buffered & Parsed: {message['data']}")
if name == "main":
asyncio.run(main())


