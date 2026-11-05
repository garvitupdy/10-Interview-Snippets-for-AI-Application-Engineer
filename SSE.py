"""
Snippet: Asynchronous Server-Sent Events (SSE) Stream Processor for LLMs
Difficulty: Advanced

Interview Context:
Real-time streaming is essential for lowering perceived latency (Time To First Token) in chat interfaces. Interviewers evaluate your knowledge of asynchronous I/O (`asyncio`), HTTP chunked transfer encoding, and how to robustly parse line-delimited Server-Sent Events (SSE) while handling malformed payloads and stream termination signals like '[DONE]'.
"""

import asyncio
import json
from typing import AsyncGenerator, Dict, Any

async def parse_sse_stream(response_line_iterator: AsyncGenerator[str, None]) -> AsyncGenerator[str, None]:
    """
    Parses a raw Server-Sent Events (SSE) byte/line stream from an LLM endpoint 
    and yields individual text tokens as they arrive.
    
    SSE Protocol Format:
    - Lines starting with 'data: ' contain the payload.
    - The stream ends with a special 'data: [DONE]' marker.
    - Empty lines or comments (starting with ':') are ignored.
    """
    async for line in response_line_iterator:
        # Strip trailing/leading whitespace and carriage returns
        line = line.strip()
        
        # Skip empty lines or SSE comment lines (e.g., keep-alive pings)
        if not line or line.startswith(":"):
            continue
            
        # SSE payloads are prefixed with 'data: '
        if line.startswith("data: "):
            data_content = line[6:].strip()
            
            # Check for the standard stream termination signal used by OpenAI & compatible APIs
            if data_content == "[DONE]":
                break
                
            try:
                # Parse the JSON payload chunk
                chunk = json.loads(data_content)
                
                # Extract the text delta from the standard OpenAI-compatible schema
                # Path: choices -> [0] -> delta -> content
                choices = chunk.get("choices", [])
                if choices:
                    delta = choices[0].get("delta", {})
                    content_token = delta.get("content")
                    
                    if content_token:
                        yield content_token
                        
            except json.JSONDecodeError as e:
                # Production guard: Log malformed chunks but don't crash the entire stream 
                # if a single packet is corrupted or truncated.
                print(f"[Warning] Failed to decode JSON chunk: {data_content}. Error: {e}")
                continue

# Mock Network Stream for Execution Testing 
async def mock_sse_network_stream() -> AsyncGenerator[str, None]:
    """Simulates an asynchronous HTTP response stream using SSE protocol format."""
    mock_chunks = [
        "data: {\"choices\": [{\"delta\": {\"role\": \"assistant\"}}]}\n",
        "\n", # Keep-alive empty line
        "data: {\"choices\": [{\"delta\": {\"content\": \"Hello\"}}]}\n",
        "data: {\"choices\": [{\"delta\": {\"content\": \" world\"}}]}\n",
        "data: {\"choices\": [{\"delta\": {\"content\": \"!\"}}]}\n",
        "data: [DONE]\n"
    ]
    
    for chunk in mock_chunks:
        # Simulate network latency between token packets
        await asyncio.sleep(0.05)
        # Yield line by line (mimicking httpx's aiter_lines())
        yield chunk.strip()

async def main():
    print(" Simulating Real-Time Asynchronous LLM Stream")
    
    # In a production environment using 'httpx', you would do:
    # async with httpx.AsyncClient() as client:
    #     async with client.stream("POST", url, json=payload, headers=headers) as response:
    #         async for token in parse_sse_stream(response.aiter_lines()):
    #             print(token, end="", flush=True)

    full_response = []
    
    # Consume our mock async stream using our SSE parser
    async for token in parse_sse_stream(mock_sse_network_stream()):
        print(token, end="", flush=True) # flush=True ensures instant terminal output
        full_response.append(token)
        
    print(f"\n\n--- Stream Completed. Total tokens received: {len(full_response)} ---")

if __name__ == "__main__":
    # Run the async event loop
    asyncio.run(main())

"""
Architectural Trade-offs & Performance Notes:
1. Buffering vs. Streaming: Processing line-by-line via async generators ensures 
   O(1) memory overhead. We never buffer the entire response body into RAM, 
   making it scalable to handle extremely long context generations (e.g., 100k+ tokens).
   
2. Backpressure: Async generators naturally respect backpressure. If the client 
   consuming the tokens is slow, the upstream HTTP read buffer pauses, preventing 
   unbounded memory growth on the server side.
"""
