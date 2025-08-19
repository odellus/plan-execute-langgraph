"""
DSPy-based agent service that replaces the LangGraph implementation.
Provides streaming chat with conversation history and persistence.
Enhanced with MCP (Model Context Protocol) tools for airline booking.
"""
import logging
import json
import time
from typing import Dict, Any, AsyncGenerator, List
from pydantic import BaseModel

from psycopg_pool import AsyncConnectionPool
import dspy

from plan_execute.agent.models import ChatRequest
from plan_execute.agent.dspy_checkpointer import DSPyConversationCheckpointer
from plan_execute.config import settings

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("dspy_service")


class DSPyChatResponse(BaseModel):
    response: str


class ConversationSignature(dspy.Signature):
    """A conversational AI assistant with airline booking tools. Can help with flight searches, bookings, modifications, and general conversation."""
    history: dspy.History = dspy.InputField(desc="Previous conversation history")
    user_message: str = dspy.InputField(desc="Current user message")
    response: str = dspy.OutputField(desc="Helpful assistant response with tool usage when needed")


class DSPyAgentService:
    """
    DSPy-based agent service with streaming and conversation persistence.
    Enhanced with MCP tools for airline booking capabilities.
    This replaces the LangGraph SimpleAgentService with equivalent functionality.
    """

    def __init__(self, pool: AsyncConnectionPool, mcp_server_path: str = None) -> None:
        self.checkpointer = DSPyConversationCheckpointer(pool)
        self.pool = pool
        
        # MCP server configuration - co-locate with this service
        import os
        current_dir = os.path.dirname(os.path.abspath(__file__))
        self.mcp_server_path = mcp_server_path or os.path.join(current_dir, "mcp_server.py")
        self.mcp_tools = []
        self.mcp_session = None  # Keep session alive for tool calls
        
        # Configure DSPy with the same LLM settings as the original service
        self.lm = self._configure_dspy_lm()
        dspy.configure(lm=self.lm)
        
        # These will be initialized with MCP tools in initialize()
        self.chat_predictor = None
        self.streaming_chat = None

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

    async def _create_mcp_tool_wrapper(self, tool_name: str, tool_description: str, tool_func):
        """Create a DSPy tool wrapper for MCP tools."""
        
        class MCPToolWrapper(dspy.Tool):
            def __init__(self, name: str, description: str, func):
                self.name = name
                self.description = description
                self.func = func
                
            async def acall(self, **kwargs):
                """Async call to MCP tool."""
                logger.info(f"🛠️ Calling MCP tool: {self.name} with args: {kwargs}")
                try:
                    result = await self.func(**kwargs)
                    logger.info(f"✅ MCP tool {self.name} completed successfully")
                    logger.debug(f"Tool result: {result}")
                    return result
                except Exception as e:
                    logger.error(f"❌ MCP tool {self.name} failed: {e}")
                    raise
                    
            def __call__(self, **kwargs):
                """Sync call - not supported for MCP tools."""
                raise NotImplementedError("MCP tools only support async calls. Use acall() instead.")
        
        return MCPToolWrapper(tool_name, tool_description, tool_func)

    async def _initialize_mcp_tools(self) -> List[dspy.Tool]:
        """Initialize MCP tools by connecting to the MCP server."""
        logger.info(f"🔧 Initializing MCP tools from server: {self.mcp_server_path}")
        
        try:
            from mcp import ClientSession, StdioServerParameters
            from mcp.client.stdio import stdio_client
            
            # Check if MCP server file exists
            import os
            if not os.path.exists(self.mcp_server_path):
                logger.warning(f"⚠️ MCP server file not found: {self.mcp_server_path}")
                return []
            
            # Create persistent connection parameters
            self.mcp_server_params = StdioServerParameters(
                command="python",
                args=[self.mcp_server_path],
                env=None,
            )
            
            logger.info("🚀 Testing MCP server connection...")
            async with stdio_client(self.mcp_server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    # Initialize the connection
                    logger.info("🤝 Initializing MCP session...")
                    await session.initialize()
                    
                    # List available tools
                    logger.info("📋 Listing available MCP tools...")
                    tools = await session.list_tools()
                    
                    # Create tool wrappers that can create their own sessions
                    dspy_tools = []
                    for tool in tools.tools:
                        logger.info(f"🛠️ Creating wrapper for MCP tool: {tool.name} - {tool.description}")
                        
                        # Create a closure that captures the tool info
                        async def create_tool_func(tool_name=tool.name):
                            async def tool_func(**kwargs):
                                # Create a new session for each tool call
                                async with stdio_client(self.mcp_server_params) as (read, write):
                                    async with ClientSession(read, write) as session:
                                        await session.initialize()
                                        result = await session.call_tool(tool_name, kwargs)
                                        return result.content
                            return tool_func
                        
                        tool_func = await create_tool_func(tool.name)
                        tool_wrapper = await self._create_mcp_tool_wrapper(tool.name, tool.description, tool_func)
                        dspy_tools.append(tool_wrapper)
                    
                    logger.info(f"✅ Successfully initialized {len(dspy_tools)} MCP tools")
                    for tool in dspy_tools:
                        logger.info(f"  • {tool.name}: {tool.description}")
                    
                    return dspy_tools
                    
        except ImportError as e:
            logger.warning(f"📦 MCP packages not available: {e} - continuing without tools")
            return []
        except Exception as e:
            logger.error(f"❌ Failed to initialize MCP tools: {e} - continuing without tools")
            logger.debug("Full MCP initialization error:", exc_info=True)
            return []

    async def initialize(self) -> None:
        """One-time setup; call once at start-up."""
        try:
            # Initialize the checkpointer
            await self.checkpointer.setup()
            
            # Initialize MCP tools
            self.mcp_tools = await self._initialize_mcp_tools()
            
            # Create the chat predictor (with or without tools)
            if self.mcp_tools:
                logger.info(f"🤖 Creating ReAct agent with {len(self.mcp_tools)} MCP tools")
                tool_names = [tool.name for tool in self.mcp_tools]
                logger.info(f"🛠️ Available tools: {', '.join(tool_names)}")
                self.chat_predictor = dspy.ReAct(ConversationSignature, tools=self.mcp_tools)
            else:
                logger.info("💬 Creating basic Predict agent (no MCP tools available)")
                self.chat_predictor = dspy.Predict(ConversationSignature)
            
            # Create streaming version
            self.streaming_chat = dspy.streamify(
                self.chat_predictor,
                async_streaming=True,
                include_final_prediction_in_output_stream=True
            )
            
            logger.info("DSPy service initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing DSPy service: {e}")
            raise e

    async def chat_stream(self, req: ChatRequest) -> AsyncGenerator[str, None]:
        """
        Stream chat responses back to the client with proper state persistence.
        
        :param req: validated request model
        :yields: chunks of the response as they're generated
        """
        logger.info("🚀 Processing DSPy streaming chat for thread_id=%s message=%r", req.thread_id, req.message)
        
        # Log tool availability
        if self.mcp_tools:
            logger.info(f"🛠️ Tools available for this request: {len(self.mcp_tools)} MCP tools")
        else:
            logger.info("💬 No tools available - using basic conversation mode")
        
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
            
            # Use DSPy streaming to generate response
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
            
            # Stream the DSPy response
            full_response = ""
            
            # Call the streaming predictor (ReAct or Predict depending on tools)
            if self.mcp_tools:
                logger.info("🤖 Using ReAct agent with MCP tools for streaming response")
                # Use ReAct with tools - need to use acall for async tools
                stream_generator = self.streaming_chat(
                    history=history,
                    user_message=req.message
                )
            else:
                logger.info("💬 Using basic Predict for streaming response")
                # Use basic Predict
                stream_generator = self.streaming_chat(
                    history=history,
                    user_message=req.message
                )
            
            async for chunk in stream_generator:
                if isinstance(chunk, dspy.Prediction):
                    # This is the final prediction - extract the response
                    final_prediction = chunk
                    # Handle both ReAct (with process_result) and Predict (with response) outputs
                    if hasattr(chunk, 'process_result'):
                        full_response = chunk.process_result
                        logger.info(f"✅ Final DSPy ReAct prediction completed")
                        logger.debug(f"ReAct response: {chunk.process_result}")
                        
                        # Log tool usage if available in trajectory
                        if hasattr(chunk, 'trajectory') and chunk.trajectory:
                            tool_calls = [k for k in chunk.trajectory.keys() if k.startswith('tool_name_')]
                            if tool_calls:
                                used_tools = [chunk.trajectory[k] for k in tool_calls]
                                logger.info(f"🛠️ Tools used in this conversation: {', '.join(used_tools)}")
                    else:
                        full_response = chunk.response
                        logger.info(f"✅ Final DSPy Predict response completed")
                        logger.debug(f"Predict response: {chunk.response}")
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
            logger.exception("DSPy streaming chat execution failed")
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

    async def chat(self, req: ChatRequest) -> DSPyChatResponse:
        """
        Non-streaming chat method for compatibility.
        
        :param req: validated request model
        :returns: complete response
        """
        logger.info("Processing DSPy chat for thread_id=%s message=%r", req.thread_id, req.message)
        
        # Validate message
        if not req.message or not req.message.strip():
            logger.warning("Empty message received, providing default response")
            return DSPyChatResponse(response="I didn't receive a message. Please type something and try again.")
        
        try:
            # Load conversation history
            history = await self.checkpointer.load_conversation(req.thread_id)
            
            # Generate response using DSPy (ReAct or Predict depending on tools)
            if self.mcp_tools:
                # Use ReAct with tools - need async call for tools
                prediction = await self.chat_predictor.acall(
                    history=history,
                    user_message=req.message
                )
                # ReAct uses process_result
                response_text = prediction.process_result if hasattr(prediction, 'process_result') else prediction.response
            else:
                # Use basic Predict
                prediction = self.chat_predictor(
                    history=history,
                    user_message=req.message
                )
                response_text = prediction.response
            
            # Update conversation history
            updated_messages = history.messages.copy() if history.messages else []
            updated_messages.append({
                "user_message": req.message,
                "response": response_text
            })
            
            updated_history = dspy.History(messages=updated_messages)
            await self.checkpointer.save_conversation(req.thread_id, updated_history)
            
            return DSPyChatResponse(response=response_text)
            
        except Exception as exc:
            logger.exception("DSPy chat execution failed")
            raise Exception("Chat execution failed") from exc