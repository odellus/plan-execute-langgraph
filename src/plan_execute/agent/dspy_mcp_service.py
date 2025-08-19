"""
Enhanced DSPy service with MCP (Model Context Protocol) tool integration.
Extends the base DSPy service with airline booking and management capabilities.
"""
import logging
import json
import time
import asyncio
from typing import Dict, Any, AsyncGenerator, List
from pydantic import BaseModel

from psycopg_pool import AsyncConnectionPool
import dspy
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from plan_execute.agent.models import ChatRequest
from plan_execute.agent.dspy_checkpointer import DSPyConversationCheckpointer
from plan_execute.config import settings

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("dspy_mcp_service")


class DSPyMCPChatResponse(BaseModel):
    response: str


class AirlineServiceSignature(dspy.Signature):
    """An airline customer service agent with access to booking tools. You can help users with flight searches, bookings, modifications, and cancellations."""
    history: dspy.History = dspy.InputField(desc="Previous conversation history")
    user_request: str = dspy.InputField(desc="User's request for airline services")
    process_result: str = dspy.OutputField(
        desc="Message that summarizes the process result and provides information users need, such as confirmation numbers for bookings"
    )


class DSPyMCPAgentService:
    """
    Enhanced DSPy service with MCP tool integration for airline booking capabilities.
    Provides streaming chat with tool execution and conversation persistence.
    """

    def __init__(self, pool: AsyncConnectionPool, mcp_server_path: str = None) -> None:
        self.checkpointer = DSPyConversationCheckpointer(pool)
        self.pool = pool
        
        # MCP server configuration
        self.mcp_server_path = mcp_server_path or "/Users/thomas.wood/src/plan-execute-langgraph/mcp_server.py"
        self.mcp_tools = []
        
        # Configure DSPy with the same LLM settings as the original service
        self.lm = self._configure_dspy_lm()
        dspy.configure(lm=self.lm)
        
        # This will be initialized with MCP tools in initialize()
        self.react_agent = None

    def _configure_dspy_lm(self):
        """Configure DSPy LM with the same settings as the original service."""
        try:
            # Try OpenAI-compatible configuration first
            return dspy.LM(
                model="openai/claude4_sonnet",
                api_base=settings.openai_base_url,
                api_key=settings.openai_api_key.get_secret_value(),
            )
        except Exception as e:
            logger.warning(f"Failed to configure OpenAI-compatible LM: {e}")
            try:
                # Fallback to direct model name
                return dspy.LM(
                    model="claude4_sonnet",
                    api_base=settings.openai_base_url,
                    api_key=settings.openai_api_key.get_secret_value(),
                )
            except Exception as e2:
                logger.error(f"Failed to configure DSPy LM: {e2}")
                raise Exception(f"Could not configure DSPy LM: {e2}")

    async def _initialize_mcp_tools(self) -> List[dspy.Tool]:
        """Initialize MCP tools by connecting to the MCP server."""
        server_params = StdioServerParameters(
            command="python",
            args=[self.mcp_server_path],
            env=None,
        )
        
        try:
            async with stdio_client(server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    # Initialize the connection
                    await session.initialize()
                    
                    # List available tools
                    tools = await session.list_tools()
                    
                    # Convert MCP tools to DSPy tools
                    dspy_tools = []
                    for tool in tools.tools:
                        dspy_tool = dspy.Tool.from_mcp_tool(session, tool)
                        dspy_tools.append(dspy_tool)
                    
                    logger.info(f"Successfully initialized {len(dspy_tools)} MCP tools")
                    return dspy_tools
                    
        except Exception as e:
            logger.error(f"Failed to initialize MCP tools: {e}")
            raise Exception(f"Could not initialize MCP tools: {e}")

    async def initialize(self) -> None:
        """One-time setup; call once at start-up."""
        try:
            # Initialize the checkpointer
            await self.checkpointer.setup()
            
            # Initialize MCP tools
            self.mcp_tools = await self._initialize_mcp_tools()
            
            # Create the ReAct agent with tools
            self.react_agent = dspy.ReAct(AirlineServiceSignature, tools=self.mcp_tools)
            
            # Create streaming version
            self.streaming_react = dspy.streamify(
                self.react_agent,
                async_streaming=True,
                include_final_prediction_in_output_stream=True
            )
            
            logger.info("DSPy MCP service initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing DSPy MCP service: {e}")
            raise e

    async def chat_stream(self, req: ChatRequest) -> AsyncGenerator[str, None]:
        """
        Stream chat responses with MCP tool execution and proper state persistence.
        
        :param req: validated request model
        :yields: chunks of the response as they're generated
        """
        logger.info("Processing DSPy MCP streaming chat for thread_id=%s message=%r", req.thread_id, req.message)
        
        # Validate message
        if not req.message or not req.message.strip():
            logger.warning("Empty message received, providing default response")
            error_response = "I didn't receive a message. Please type something and try again."
            
            # Return error response in OpenAI-compatible streaming format
            async for chunk in self._stream_error_response(error_response):
                yield chunk
            return
        
        try:
            # Load conversation history from PostgreSQL
            history = await self.checkpointer.load_conversation(req.thread_id)
            
            logger.info(f"Thread ID: {req.thread_id}")
            logger.info(f"Retrieved {len(history.messages) if history.messages else 0} existing messages from DSPy checkpointer")
            
            # Use DSPy ReAct streaming to generate response with tool execution
            chunk_id = f"chatcmpl-{int(time.time())}"
            
            # Send initial chunk
            initial_chunk = {
                "id": chunk_id,
                "object": "chat.completion.chunk",
                "created": int(time.time()),
                "model": "claude4_sonnet",
                "choices": [{
                    "index": 0,
                    "delta": {"role": "assistant", "content": ""},
                    "finish_reason": None
                }]
            }
            yield f"data: {json.dumps(initial_chunk)}\n\n"
            
            # Stream the DSPy ReAct response
            full_response = ""
            
            # Call the streaming ReAct agent
            stream_generator = self.streaming_react(
                history=history,
                user_request=req.message
            )
            
            async for chunk in stream_generator:
                if isinstance(chunk, dspy.Prediction):
                    # This is the final prediction - extract the response
                    final_prediction = chunk
                    full_response = chunk.process_result
                    logger.debug(f"Final DSPy ReAct prediction: {chunk.process_result}")
                elif hasattr(chunk, 'choices') and chunk.choices:
                    # This is a ModelResponseStream from LiteLLM - extract content
                    delta = chunk.choices[0].delta
                    if hasattr(delta, 'content') and delta.content:
                        content = delta.content
                        logger.debug(f"DSPy streaming chunk: {repr(content)}")
                        
                        # Convert to OpenAI-compatible streaming format
                        streaming_chunk = {
                            "id": chunk_id,
                            "object": "chat.completion.chunk",
                            "created": int(time.time()),
                            "model": "claude4_sonnet",
                            "choices": [{
                                "index": 0,
                                "delta": {"content": content},
                                "finish_reason": None
                            }]
                        }
                        yield f"data: {json.dumps(streaming_chunk)}\n\n"
                elif isinstance(chunk, dspy.streaming.StreamResponse):
                    # This is a DSPy StreamResponse from listeners
                    if hasattr(chunk, 'content') and chunk.content:
                        content = chunk.content
                        logger.debug(f"DSPy stream response: {repr(content)}")
                        
                        # Convert to OpenAI-compatible streaming format
                        streaming_chunk = {
                            "id": chunk_id,
                            "object": "chat.completion.chunk",
                            "created": int(time.time()),
                            "model": "claude4_sonnet",
                            "choices": [{
                                "index": 0,
                                "delta": {"content": content},
                                "finish_reason": None
                            }]
                        }
                        yield f"data: {json.dumps(streaming_chunk)}\n\n"
                else:
                    # Handle other chunk types (status messages, etc.)
                    logger.debug(f"Other DSPy chunk type: {type(chunk)} - {repr(chunk)}")
                    # Skip status messages to match original behavior
            
            # Send final chunk
            final_chunk = {
                "id": chunk_id,
                "object": "chat.completion.chunk",
                "created": int(time.time()),
                "model": "claude4_sonnet",
                "choices": [{
                    "index": 0,
                    "delta": {},
                    "finish_reason": "stop"
                }]
            }
            yield f"data: {json.dumps(final_chunk)}\n\n"
            
            # Update conversation history with the new exchange
            try:
                # Add the new user message and assistant response to history
                updated_messages = history.messages.copy() if history.messages else []
                updated_messages.append({
                    "user_message": req.message,
                    "response": full_response
                })
                
                # Create updated history and save to PostgreSQL
                updated_history = dspy.History(messages=updated_messages)
                await self.checkpointer.save_conversation(req.thread_id, updated_history)
                
                logger.info(f"Successfully saved conversation state with {len(updated_messages)} messages")
                
            except Exception as e:
                logger.error(f"Failed to save conversation state: {e}", exc_info=True)
                # Continue anyway - the conversation still worked for this turn
            
            # Signal completion
            yield "data: [DONE]\n\n"
                    
        except Exception as exc:
            logger.exception("DSPy MCP streaming chat execution failed")
            async for chunk in self._stream_error_response(f"Error: {str(exc)}"):
                yield chunk

    async def _stream_error_response(self, error_message: str) -> AsyncGenerator[str, None]:
        """Stream an error response in OpenAI-compatible format."""
        chunk_id = f"chatcmpl-{int(time.time())}"
        
        initial_chunk = {
            "id": chunk_id,
            "object": "chat.completion.chunk",
            "created": int(time.time()),
            "model": "claude4_sonnet",
            "choices": [{
                "index": 0,
                "delta": {"role": "assistant", "content": ""},
                "finish_reason": None
            }]
        }
        yield f"data: {json.dumps(initial_chunk)}\n\n"
        
        content_chunk = {
            "id": chunk_id,
            "object": "chat.completion.chunk",
            "created": int(time.time()),
            "model": "claude4_sonnet",
            "choices": [{
                "index": 0,
                "delta": {"content": error_message},
                "finish_reason": None
            }]
        }
        yield f"data: {json.dumps(content_chunk)}\n\n"
        
        final_chunk = {
            "id": chunk_id,
            "object": "chat.completion.chunk",
            "created": int(time.time()),
            "model": "claude4_sonnet",
            "choices": [{
                "index": 0,
                "delta": {},
                "finish_reason": "stop"
            }]
        }
        yield f"data: {json.dumps(final_chunk)}\n\n"
        yield "data: [DONE]\n\n"

    async def chat(self, req: ChatRequest) -> DSPyMCPChatResponse:
        """
        Non-streaming chat method with MCP tool execution.
        
        :param req: validated request model
        :returns: complete response
        """
        logger.info("Processing DSPy MCP chat for thread_id=%s message=%r", req.thread_id, req.message)
        
        # Validate message
        if not req.message or not req.message.strip():
            logger.warning("Empty message received, providing default response")
            return DSPyMCPChatResponse(response="I didn't receive a message. Please type something and try again.")
        
        try:
            # Load conversation history
            history = await self.checkpointer.load_conversation(req.thread_id)
            
            # Generate response using DSPy ReAct with tools
            prediction = await self.react_agent.acall(
                history=history,
                user_request=req.message
            )
            
            response_text = prediction.process_result
            
            # Update conversation history
            updated_messages = history.messages.copy() if history.messages else []
            updated_messages.append({
                "user_message": req.message,
                "response": response_text
            })
            
            updated_history = dspy.History(messages=updated_messages)
            await self.checkpointer.save_conversation(req.thread_id, updated_history)
            
            return DSPyMCPChatResponse(response=response_text)
            
        except Exception as exc:
            logger.exception("DSPy MCP chat execution failed")
            raise Exception("Chat execution failed") from exc
