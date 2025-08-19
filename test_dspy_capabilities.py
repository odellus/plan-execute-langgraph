#!/usr/bin/env python3
"""
Test DSPy capabilities for streaming, history, and persistence.
"""
import dspy
import asyncio
from dotenv import load_dotenv
import os

load_dotenv()

def test_dspy_basic():
    """Test basic DSPy setup and configuration."""
    print("=== Testing DSPy Basic Setup ===")
    
    # Configure DSPy using helper function
    lm = get_dspy_lm()
    dspy.configure(lm=lm)
    
    # Simple prediction
    predict = dspy.Predict("question -> answer")
    response = predict(question="What is 2+2?")
    print(f"Basic response: {response.answer}")
    return True

def test_dspy_streaming():
    """Test DSPy streaming capabilities."""
    print("\n=== Testing DSPy Streaming ===")
    
    try:
        # Configure DSPy - reuse configuration function
        lm = get_dspy_lm()
        dspy.configure(lm=lm)
        
        # Test streaming
        predict = dspy.Predict("question -> answer")
        
        # Check if we can use streaming
        print("Checking streaming capabilities...")
        print(f"streamify function: {dspy.streamify}")
        print(f"streaming module: {dspy.streaming}")
        
        # Try to create a streaming version
        streaming_predict = dspy.streamify(predict)
        
        print("Streaming predict created successfully!")
        return True
        
    except Exception as e:
        print(f"Streaming test failed: {e}")
        return False

def test_dspy_history():
    """Test DSPy history and conversation capabilities."""
    print("\n=== Testing DSPy History ===")
    
    try:
        # Configure DSPy - reuse configuration function
        lm = get_dspy_lm()
        dspy.configure(lm=lm)
        
        # Test history tracking
        print("Testing history capabilities...")
        
        # Create a conversation signature
        class ConversationSignature(dspy.Signature):
            """A conversation with context and history."""
            history: str = dspy.InputField(desc="Previous conversation history")
            user_message: str = dspy.InputField(desc="Current user message")
            response: str = dspy.OutputField(desc="Assistant response")
        
        # Create predictor
        chat = dspy.Predict(ConversationSignature)
        
        # Test with history
        response1 = chat(
            history="", 
            user_message="My name is Alice. What's 2+2?"
        )
        print(f"Response 1: {response1.response}")
        
        # Continue conversation with history
        history_text = f"User: My name is Alice. What's 2+2?\nAssistant: {response1.response}"
        response2 = chat(
            history=history_text,
            user_message="What's my name?"
        )
        print(f"Response 2: {response2.response}")
        
        return True
        
    except Exception as e:
        print(f"History test failed: {e}")
        return False

def get_dspy_lm():
    """Get a configured DSPy LM instance."""
    # Try different model configurations
    try:
        # Try with openai/ prefix for OpenAI-compatible endpoints
        return dspy.LM(
            model="openai/claude4_sonnet",
            api_base="http://host.docker.internal:11434/v1",
            api_key=os.getenv("OPENAI_API_KEY", "dummy"),
        )
    except Exception as e1:
        print(f"OpenAI-compatible attempt failed: {e1}")
        try:
            # Try with ollama/ prefix
            return dspy.LM(
                model="ollama/claude4_sonnet",
                api_base="http://host.docker.internal:11434",
                api_key=os.getenv("OPENAI_API_KEY", "dummy"),
            )
        except Exception as e2:
            print(f"Ollama attempt failed: {e2}")
            # Fallback to a simple configuration
            print("Using fallback configuration for testing...")
            return dspy.LM(
                model="gpt-3.5-turbo",
                api_key=os.getenv("OPENAI_API_KEY", "test-key"),
            )

def test_dspy_context():
    """Test DSPy context management."""
    print("\n=== Testing DSPy Context ===")
    
    try:
        # Test context capabilities
        print(f"Context module: {dspy.context}")
        print(f"Settings: {dspy.settings}")
        
        # Check if we can access conversation history
        if hasattr(dspy, 'inspect_history'):
            print("inspect_history available")
            
        if hasattr(dspy, 'History'):
            print("History class available")
            
        return True
        
    except Exception as e:
        print(f"Context test failed: {e}")
        return False

if __name__ == "__main__":
    print("🧪 Testing DSPy Capabilities")
    print("=" * 50)
    
    try:
        basic_ok = test_dspy_basic()
        streaming_ok = test_dspy_streaming()
        history_ok = test_dspy_history()
        context_ok = test_dspy_context()
        
        print("\n" + "=" * 50)
        print("📋 Test Results:")
        print(f"  Basic:     {'✅ PASS' if basic_ok else '❌ FAIL'}")
        print(f"  Streaming: {'✅ PASS' if streaming_ok else '❌ FAIL'}")
        print(f"  History:   {'✅ PASS' if history_ok else '❌ FAIL'}")
        print(f"  Context:   {'✅ PASS' if context_ok else '❌ FAIL'}")
        
    except Exception as e:
        print(f"❌ Test suite failed: {e}")