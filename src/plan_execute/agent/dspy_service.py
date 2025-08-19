"""
DSPy-based agent service that replaces the LangGraph implementation.
Provides streaming chat with conversation history and persistence.
"""
import logging
import json
import time
from typing import Dict, Any, AsyncGenerator
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
    """A conversational AI assistant that maintains context and history."""
    history: dspy.History = dspy.InputField(desc="Previous conversation history")
    user_message: str = dspy.InputField(desc="Current user message")
    response: str = dspy.OutputField(desc="Helpful assistant response")


class DSPyAgentService:
    """
    DSPy-based agent service with streaming and conversation persistence.
    This replaces the LangGraph SimpleAgentService with equivalent functionality.
    """

    def __init__(self, pool: AsyncConnectionPool) -> None:
        self.checkpointer = DSPyConversationCheckpointer(pool)
        self.pool = pool
        
        # Configure DSPy with the same LLM settings as the original service
        self.lm = self._configure_dspy_lm()
        dspy.configure(lm=self.lm)
        
        # Create the conversation predictor
        self.chat_predictor = dspy.Predict(ConversationSignature)
        
        # Create streaming version (simple approach without listeners)
        self.streaming_chat = dspy.streamify(
            self.chat_predictor,
            async_streaming=True,
            include_final_prediction_in_output_stream=True
        )

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

    async def initialize(self) -> None:
        """One-time DB setup; call once at start-up."""
        try:
            await self.checkpointer.setup()
        except Exception as e:
            logger.error(f"Error initializing DSPy checkpointer: {e}")
            raise e

    async def chat_stream(self, req: ChatRequest) -> AsyncGenerator[str, None]:
        """
        Stream chat responses back to the client with proper state persistence.
        
        :param req: validated request model
        :yields: chunks of the response as they're generated
        """
        logger.info("Processing DSPy streaming chat for thread_id=%s message=%r", req.thread_id, req.message)
        
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
            
            # Call the streaming predictor
            stream_generator = self.streaming_chat(
                history=history,
                user_message=req.message
            )
            
            async for chunk in stream_generator:
                if isinstance(chunk, dspy.Prediction):
                    # This is the final prediction - extract the response
                    final_prediction = chunk
                    full_response = chunk.response
                    logger.debug(f"Final DSPy prediction: {chunk.response}")
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
            
            # Generate response using DSPy
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