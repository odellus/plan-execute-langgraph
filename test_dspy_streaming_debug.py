#!/usr/bin/env python3
"""
Debug DSPy streaming to understand how it works.
"""
import asyncio
import dspy
from plan_execute.config import settings

async def test_dspy_streaming_simple():
    """Test DSPy streaming with a simple example."""
    print("🔍 Testing DSPy Streaming (Simple)")
    print("=" * 50)
    
    try:
        # Configure DSPy
        lm = dspy.LM(
            model="openai/claude4_sonnet",
            api_base=settings.openai_base_url,
            api_key=settings.openai_api_key.get_secret_value(),
        )
        dspy.configure(lm=lm)
        
        # Create a simple predictor
        predict = dspy.Predict("question -> answer")
        
        # Create streaming version
        streaming_predict = dspy.streamify(predict, async_streaming=True)
        
        print("✅ Created streaming predictor")
        
        # Test streaming
        print("\n--- Streaming Test ---")
        stream_gen = streaming_predict(question="What is 2+2? Explain step by step.")
        
        chunk_count = 0
        response_text = ""
        
        async for chunk in stream_gen:
            chunk_count += 1
            print(f"Chunk {chunk_count}: {type(chunk)} - {repr(chunk)}")
            
            if isinstance(chunk, dspy.Prediction):
                print(f"  Final prediction: {chunk.answer}")
                response_text = chunk.answer
            elif hasattr(chunk, 'content'):
                print(f"  Content: {chunk.content}")
                response_text += chunk.content
            elif hasattr(chunk, 'text'):
                print(f"  Text: {chunk.text}")
                response_text += chunk.text
            else:
                print(f"  Raw chunk: {str(chunk)}")
        
        print(f"\n📊 Total chunks: {chunk_count}")
        print(f"📝 Final response: {response_text}")
        
        return True
        
    except Exception as e:
        print(f"❌ Simple streaming test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_dspy_streaming_with_listeners():
    """Test DSPy streaming with stream listeners."""
    print("\n🔍 Testing DSPy Streaming (With Listeners)")
    print("=" * 50)
    
    try:
        # Configure DSPy
        lm = dspy.LM(
            model="openai/claude4_sonnet",
            api_base=settings.openai_base_url,
            api_key=settings.openai_api_key.get_secret_value(),
        )
        dspy.configure(lm=lm)
        
        # Create a predictor
        predict = dspy.Predict("question -> answer")
        
        # Create stream listeners
        stream_listeners = [
            dspy.streaming.StreamListener(signature_field_name="answer"),
        ]
        
        # Create streaming version with listeners
        streaming_predict = dspy.streamify(
            predict, 
            stream_listeners=stream_listeners,
            async_streaming=True,
            include_final_prediction_in_output_stream=True
        )
        
        print("✅ Created streaming predictor with listeners")
        
        # Test streaming
        print("\n--- Streaming Test with Listeners ---")
        stream_gen = streaming_predict(question="Tell me a short joke.")
        
        chunk_count = 0
        response_text = ""
        
        async for chunk in stream_gen:
            chunk_count += 1
            print(f"Chunk {chunk_count}: {type(chunk)} - {repr(chunk)}")
            
            if isinstance(chunk, dspy.Prediction):
                print(f"  Final prediction: {chunk.answer}")
                response_text = chunk.answer
            elif isinstance(chunk, dspy.streaming.StreamResponse):
                print(f"  Stream response - field: {chunk.field_name}, content: {chunk.content}")
                response_text += chunk.content
            elif hasattr(chunk, 'content'):
                print(f"  Content: {chunk.content}")
                response_text += chunk.content
            else:
                print(f"  Raw chunk: {str(chunk)}")
        
        print(f"\n📊 Total chunks: {chunk_count}")
        print(f"📝 Final response: {response_text}")
        
        return True
        
    except Exception as e:
        print(f"❌ Listener streaming test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_conversation_streaming():
    """Test streaming with conversation signature."""
    print("\n🔍 Testing Conversation Streaming")
    print("=" * 50)
    
    try:
        # Configure DSPy
        lm = dspy.LM(
            model="openai/claude4_sonnet",
            api_base=settings.openai_base_url,
            api_key=settings.openai_api_key.get_secret_value(),
        )
        dspy.configure(lm=lm)
        
        # Create conversation signature
        class ConversationSignature(dspy.Signature):
            """A conversational AI assistant."""
            history: dspy.History = dspy.InputField(desc="Previous conversation history")
            user_message: str = dspy.InputField(desc="Current user message")
            response: str = dspy.OutputField(desc="Assistant response")
        
        # Create predictor
        chat_predictor = dspy.Predict(ConversationSignature)
        
        # Create stream listeners for the response field
        stream_listeners = [
            dspy.streaming.StreamListener(signature_field_name="response"),
        ]
        
        # Create streaming version
        streaming_chat = dspy.streamify(
            chat_predictor,
            stream_listeners=stream_listeners,
            async_streaming=True,
            include_final_prediction_in_output_stream=True
        )
        
        print("✅ Created conversation streaming predictor")
        
        # Test streaming
        print("\n--- Conversation Streaming Test ---")
        
        history = dspy.History(messages=[])
        
        stream_gen = streaming_chat(
            history=history,
            user_message="Tell me a fun fact about space."
        )
        
        chunk_count = 0
        response_text = ""
        
        async for chunk in stream_gen:
            chunk_count += 1
            print(f"Chunk {chunk_count}: {type(chunk)} - {repr(chunk)}")
            
            if isinstance(chunk, dspy.Prediction):
                print(f"  Final prediction: {chunk.response}")
                response_text = chunk.response
            elif isinstance(chunk, dspy.streaming.StreamResponse):
                print(f"  Stream response - field: {chunk.field_name}, content: {chunk.content}")
                if chunk.field_name == "response":
                    response_text += chunk.content
            elif hasattr(chunk, 'content'):
                print(f"  Content: {chunk.content}")
                response_text += chunk.content
            else:
                print(f"  Raw chunk: {str(chunk)}")
        
        print(f"\n📊 Total chunks: {chunk_count}")
        print(f"📝 Final response: {response_text}")
        
        return True
        
    except Exception as e:
        print(f"❌ Conversation streaming test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    async def main():
        simple_ok = await test_dspy_streaming_simple()
        listeners_ok = await test_dspy_streaming_with_listeners()
        conversation_ok = await test_conversation_streaming()
        
        print("\n" + "=" * 50)
        print("📋 Streaming Debug Results:")
        print(f"  Simple:       {'✅ PASS' if simple_ok else '❌ FAIL'}")
        print(f"  Listeners:    {'✅ PASS' if listeners_ok else '❌ FAIL'}")
        print(f"  Conversation: {'✅ PASS' if conversation_ok else '❌ FAIL'}")
    
    asyncio.run(main())