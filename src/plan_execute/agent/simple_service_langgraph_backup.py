import logging
import json
import time
from typing import Dict, Any, AsyncGenerator
from typing_extensions import TypedDict

from psycopg_pool import AsyncConnectionPool
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from pydantic import BaseModel, Field
from langgraph.graph import StateGraph, START, END
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage, AIMessage

from plan_execute.agent.models import ChatRequest
from plan_execute.config import settings

from langfuse.langchain import CallbackHandler
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("simple_service")
langfuse_handler = CallbackHandler()

class SimpleChatState(TypedDict):
    messages: list
    response: str


class SimpleChatResponse(BaseModel):
    response: str


class SimpleAgentService:
    """
    A simple agent service that streams responses back to the client.
    This is a much simpler alternative to the complex plan-execute agent.
    """

    def __init__(self, pool: AsyncConnectionPool) -> None:
        self.checkpointer = AsyncPostgresSaver(pool)
        self.graph = self._build_graph()
        self.llm = ChatOpenAI(
            model="claude4_sonnet",
            base_url=settings.openai_base_url,
            api_key=settings.openai_api_key.get_secret_value(),
            streaming=True,
        )

    def _build_graph(self):
        """Build a simple graph that just processes messages and responds."""
        workflow = StateGraph(SimpleChatState)
        
        # Add a single node that processes the message and generates a response
        workflow.add_node("respond", self._respond_node)
        
        # Connect START to the respond node
        workflow.add_edge(START, "respond")
        
        # Connect respond node to END
        workflow.add_edge("respond", END)
        
        return workflow.compile(checkpointer=self.checkpointer)

    async def _respond_node(self, state: SimpleChatState) -> Dict[str, Any]:
        """Simple node that generates a response to the user's message with full conversation context."""
        try:
            messages = state.get("messages", [])
            
            if not messages:
                return {"response": "I didn't receive any message."}
            
            # Convert messages to raw format - no templates!
            llm_messages = [
                {"role": "system", "content": "You are a helpful assistant. Respond directly and helpfully to the user's message."}
            ]
            
            for msg in messages:
                if isinstance(msg, HumanMessage):
                    content = msg.content if isinstance(msg.content, str) else str(msg.content)
                    if content.strip():
                        llm_messages.append({"role": "user", "content": content})
                elif isinstance(msg, AIMessage):
                    content = msg.content if isinstance(msg.content, str) else str(msg.content)
                    if content.strip():
                        llm_messages.append({"role": "assistant", "content": content})
            
            # Generate response directly from LLM
            full_response = ""
            async for chunk in self.llm.astream(llm_messages): #, config=dict(callbacks=[langfuse_handler])):
                if chunk.content:
                    full_response += chunk.content
            
            # Add the assistant's response to the message history
            updated_messages = messages + [AIMessage(content=full_response)]
            
            return {
                "messages": updated_messages,
                "response": full_response
            }
            
        except Exception as e:
            logger.error(f"Error in respond node: {e}")
            error_response = f"I'm sorry, I encountered an error: {str(e)}"
            # Still update messages even on error
            updated_messages = state.get("messages", []) + [AIMessage(content=error_response)]
            return {
                "messages": updated_messages, 
                "response": error_response
            }

    async def initialize(self) -> None:
        """One-time DB setup; call once at start-up."""
        try:
            await self.checkpointer.setup()
        except Exception as e:
            logger.error(f"Error initializing checkpointer: {e}")
            raise e

    async def chat_stream(self, req: ChatRequest) -> AsyncGenerator[str, None]:
        """
        Stream chat responses back to the client with proper state persistence.
        
        :param req: validated request model
        :yields: chunks of the response as they're generated
        """
        logger.info("Processing streaming chat for thread_id=%s message=%r", req.thread_id, req.message)
        
        # Validate message
        if not req.message or not req.message.strip():
            logger.warning("Empty message received, providing default response")
            error_response = "I didn't receive a message. Please type something and try again."
            
            # Return a simple error response in streaming format
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
                    "delta": {"content": error_response},
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
            return
        
        try:
            # Configuration for LangGraph with thread persistence
            config = {
                "recursion_limit": 10, 
                "configurable": {"thread_id": req.thread_id}
            }
            
            # Get current state to retrieve existing messages
            try:
                current_state = await self.graph.aget_state(config)
                existing_messages = current_state.values.get("messages", []) if current_state.values else []
            except Exception:
                # If no previous state, start with empty messages
                existing_messages = []
            
            # Add the new user message
            new_user_message = HumanMessage(content=req.message)
            all_messages = existing_messages + [new_user_message]
            
            logger.info(f"Thread ID: {req.thread_id}")
            logger.info(f"Retrieved {len(existing_messages)} existing messages from state")
            logger.info(f"Total messages in conversation: {len(all_messages)}")
            for i, msg in enumerate(all_messages):
                logger.info(f"Message {i}: {type(msg).__name__} - {repr(msg.content)}")
            
            # LangGraph doesn't stream well from nodes, so let's use direct LLM streaming
            # but still maintain state persistence
            logger.info("Using direct LLM streaming with state persistence")
            
            # Skip ChatPromptTemplate entirely - just use raw messages
            # Add system message at the beginning
            llm_messages = [
                {"role": "system", "content": "You are a helpful assistant. Respond directly and helpfully to the user's message."}
            ]
            
            for msg in all_messages:
                if isinstance(msg, HumanMessage):
                    content = msg.content if isinstance(msg.content, str) else str(msg.content)
                    if content.strip():
                        llm_messages.append({"role": "user", "content": content})
                elif isinstance(msg, AIMessage):
                    content = msg.content if isinstance(msg.content, str) else str(msg.content)
                    if content.strip():
                        llm_messages.append({"role": "assistant", "content": content})
            
            logger.debug(f"Raw messages for LLM: {llm_messages}")
            
            # Stream directly from LLM in OpenAI-compatible format
            response_content = ""
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
            
            # Stream content chunks
            async for chunk in self.llm.astream(llm_messages): #, config=dict(callbacks=[langfuse_handler])):
                if chunk.content:
                    response_content += chunk.content
                    logger.debug(f"Streaming chunk: {repr(chunk.content)}")
                    
                    # OpenAI-compatible streaming chunk
                    streaming_chunk = {
                        "id": chunk_id,
                        "object": "chat.completion.chunk",
                        "created": int(time.time()),
                        "model": "claude4_sonnet",
                        "choices": [{
                            "index": 0,
                            "delta": {"content": chunk.content},
                            "finish_reason": None
                        }]
                    }
                    yield f"data: {json.dumps(streaming_chunk)}\n\n"
            
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
            
            # Save the conversation to state after streaming - use the graph to maintain state
            final_messages = all_messages + [AIMessage(content=response_content)]
            final_inputs = {
                "messages": final_messages,
                "response": response_content
            }
            
            # Use the graph's state management to persist the conversation
            try:
                logger.info(f"Attempting to save conversation state with {len(final_messages)} messages")
                # Update the state using the graph's internal state management
                # Specify the "respond" node to avoid ambiguity
                await self.graph.aupdate_state(config, final_inputs, as_node="respond")
                logger.info("Successfully saved conversation state to PostgreSQL")
                
                # Verify the state was actually saved
                verification_state = await self.graph.aget_state(config)
                saved_messages = verification_state.values.get("messages", []) if verification_state.values else []
                logger.info(f"Verification: PostgreSQL now has {len(saved_messages)} messages")
                
            except Exception as e:
                logger.error(f"Failed to save conversation state: {e}", exc_info=True)
                # Continue anyway - the conversation still worked for this turn
            
            # Signal completion
            yield "data: [DONE]\n\n"
                    
        except Exception as exc:
            logger.exception("Streaming chat execution failed")
            yield f"data: Error: {str(exc)}\n\n"
            yield "data: [DONE]\n\n"

    async def chat(self, req: ChatRequest) -> SimpleChatResponse:
        """
        Non-streaming chat method for compatibility.
        
        :param req: validated request model
        :returns: complete response
        """
        logger.info("Processing chat for thread_id=%s message=%r", req.thread_id, req.message)
        
        config = {"recursion_limit": 10, "configurable": {"thread_id": req.thread_id}}
        inputs: Dict[str, Any] = {
            "messages": [HumanMessage(content=req.message)],
            "response": ""
        }
        
        try:
            # Run the graph and get the final result
            result = await self.graph.ainvoke(inputs, config=config)
            response_text = result.get("response", "No response generated")
            
            return SimpleChatResponse(response=response_text)
            
        except Exception as exc:
            logger.exception("Graph execution failed")
            raise Exception("Chat execution failed") from exc

