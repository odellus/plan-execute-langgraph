# TRAE.md

This is a markdown file intended for trae agent. It contains the instructions for trae-agent to follow.

# INSTRUCTIONS
We want to use DSPy instead of langgraph. Search dspy.ai for solutions to 
- streaming
- chat history
- memory/persistence
- write your own conversation persistence checkpointer for DSPy
- do for a single endpoint first
- try to replace the simple_service.py with DSPy 
- Should not require modifications to frontend
- Do not modify frontend I will test after we have a complete DSPy based endpoint that functions in a similar way to simple service

# RULES
- Test often
- we use uv for running python so do uv run instead of python
- Search the internet for how to do things in DSPy
- Look to see how we do things with langgraph and base approach in DSPy on that

# LINKS
- https://dspy.ai/tutorials/conversation_history/
- https://dspy.ai/tutorials/streaming/
- https://dspy.ai/tutorials/deployment/