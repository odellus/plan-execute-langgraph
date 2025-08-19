#!/usr/bin/env python3
"""
Focused test to debug DSPy streaming issues.
"""
import asyncio
import dspy
from plan_execute.config import settings

async def test_simple_streaming():
    """Test simple DSPy streaming without listeners."""
    print("🔍 Testing Simple DSPy Streaming")
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
        
        # Create streaming version WITHOUT listeners
        streaming_predict = dspy.streamify(predict, async_streaming=True)
        
        print("✅ Created simple streaming predictor")
        
        # Test streaming
        print("\n--- Simple Streaming Test ---")
        stream_gen = streaming_predict(question="Tell me a short joke")
        
        chunk_count = 0
        content_chunks = 0
        
        async for chunk in stream_gen:
            chunk_count += 1
            print(f"Chunk {chunk_count}: {type(chunk)}")
            
            if isinstance(chunk, dspy.Prediction):
                print(f"  ✅ Final prediction: {chunk.answer}")
            elif hasattr(chunk, 'choices') and chunk.choices:
                delta = chunk.choices[0].delta
                if hasattr(delta, 'content') and delta.content:
                    content = delta.content
                    content_chunks += 1
                    print(f"  📝 Content chunk {content_chunks}: {repr(content)}")
                else:
                    print(f"  ⚪ Empty content chunk")
            else:
                print(f"  ❓ Unknown chunk: {repr(chunk)}")
        
        print(f"\n📊 Total chunks: {chunk_count}, Content chunks: {content_chunks}")
        return content_chunks > 0
        
    except Exception as e:
        print(f"❌ Simple streaming test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_conversation_streaming_simple():
    """Test conversation streaming without listeners."""
    print("\n🔍 Testing Conversation Streaming (Simple)")
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
        
        # Create streaming version WITHOUT listeners first
        streaming_chat = dspy.streamify(chat_predictor, async_streaming=True)
        
        print("✅ Created conversation streaming predictor")
        
        # Test streaming
        print("\n--- Conversation Streaming Test ---")
        
        history = dspy.History(messages=[])
        
        stream_gen = streaming_chat(
            history=history,
            user_message="Tell me a fun fact about space."
        )
        
        chunk_count = 0
        content_chunks = 0
        
        async for chunk in stream_gen:
            chunk_count += 1
            print(f"Chunk {chunk_count}: {type(chunk)}")
            
            if isinstance(chunk, dspy.Prediction):
                print(f"  ✅ Final prediction: {chunk.response}")
            elif hasattr(chunk, 'choices') and chunk.choices:
                delta = chunk.choices[0].delta
                if hasattr(delta, 'content') and delta.content:
                    content = delta.content
                    content_chunks += 1
                    print(f"  📝 Content chunk {content_chunks}: {repr(content)}")
                else:
                    print(f"  ⚪ Empty content chunk")
            else:
                print(f"  ❓ Unknown chunk: {repr(chunk)}")
        
        print(f"\n📊 Total chunks: {chunk_count}, Content chunks: {content_chunks}")
        return content_chunks > 0
        
    except Exception as e:
        print(f"❌ Conversation streaming test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    async def main():
        simple_ok = await test_simple_streaming()
        conversation_ok = await test_conversation_streaming_simple()
        
        print("\n" + "=" * 50)
        print("📋 Focused Streaming Results:")
        print(f"  Simple:       {'✅ PASS' if simple_ok else '❌ FAIL'}")
        print(f"  Conversation: {'✅ PASS' if conversation_ok else '❌ FAIL'}")
        
        if simple_ok and conversation_ok:
            print("\n🎉 DSPy streaming works! Now we can fix the service.")
        else:
            print("\n💥 DSPy streaming has issues.")
    
    asyncio.run(main())