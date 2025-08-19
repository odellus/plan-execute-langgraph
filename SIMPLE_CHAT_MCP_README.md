# Simple Chat with MCP Integration

The existing `/simple-chat-stream` and `/simple-chat` endpoints have been enhanced with MCP (Model Context Protocol) airline booking tools while maintaining full backward compatibility.

## What Changed

### Enhanced DSPy Service
- The `DSPyAgentService` now automatically attempts to load MCP tools during initialization
- If MCP tools are available, it uses `dspy.ReAct` for tool-enabled conversations
- If MCP tools are unavailable, it gracefully falls back to basic `dspy.Predict` for regular chat
- No breaking changes - existing functionality is preserved

### Graceful Degradation
- **With MCP**: Full airline booking capabilities + general conversation
- **Without MCP**: Standard conversational AI (original functionality)
- The service automatically detects and adapts to the available capabilities

## Usage

### Same Endpoints, Enhanced Capabilities

#### Streaming Endpoint
```bash
POST /simple-chat-stream
{
    "thread_id": "user-123",
    "message": "Book a flight from SFO to JFK on September 1st for Adam"
}
```

#### Non-Streaming Endpoint  
```bash
POST /simple-chat
{
    "thread_id": "user-123", 
    "message": "What flights are available from LAX to JFK tomorrow?"
}
```

### Example Conversations

#### General Chat (works with or without MCP)
```
User: "Hello! How are you today?"
Assistant: "Hello! I'm doing well, thank you for asking. How can I help you today?"
```

#### Airline Booking (requires MCP tools)
```
User: "I need to book a flight from SFO to JFK on September 1st, 2025 for Adam"
Assistant: "I found several flights from SFO to JFK on September 1st, 2025. Let me book the most economical option for Adam...

✅ Flight booked successfully!
- Confirmation: abc123de
- Flight: DA123 (SFO → JFK)
- Date: September 1st, 2025 at 1:00 AM  
- Duration: 3 hours
- Price: $200
- Passenger: Adam (adam@gmail.com)"
```

#### Mixed Conversation
```
User: "Hi! I'm planning a trip and wondering what the weather is like, also can you check flights from LAX to JFK?"
Assistant: "Hello! I'd be happy to help with your trip planning. While I can't check current weather conditions, I can definitely help you with flights.

Let me search for flights from LAX to JFK... I found flight DA135 departing LAX at 10:00 AM on September 1st, 2025, arriving at JFK after 5 hours for $275. Would you like me to book this flight for you?"
```

## Available MCP Tools

When MCP is available, the assistant can:

1. **fetch_flight_info** - Search flights by date, origin, destination
2. **book_itinerary** - Book flights for users  
3. **fetch_itinerary** - Check booking details with confirmation numbers
4. **modify_itinerary** - Change or cancel existing bookings
5. **get_user_info** - Look up user profiles
6. **file_ticket** - Create support tickets for complex requests

## Testing

### Quick Test
```bash
python test_simple_chat_mcp.py
```

### Manual Testing
1. Start your server: `python -m src.plan_execute.app`
2. Test with curl:
```bash
# General conversation
curl -X POST http://localhost:8000/simple-chat \
  -H "Content-Type: application/json" \
  -d '{"thread_id": "test", "message": "Hello!"}'

# Flight booking  
curl -X POST http://localhost:8000/simple-chat \
  -H "Content-Type: application/json" \
  -d '{"thread_id": "test", "message": "Book a flight from SFO to JFK on September 1st for Adam"}'
```

## Architecture

```
Client Request
    ↓
/simple-chat-stream or /simple-chat
    ↓  
DSPyAgentService.__init__()
    ↓
Attempts MCP Tool Loading
    ↓
┌─ MCP Available ─────────────┐  ┌─ MCP Unavailable ──────────┐
│ • Uses dspy.ReAct           │  │ • Uses dspy.Predict        │
│ • Tool-enabled conversations│  │ • Standard chat only       │
│ • Airline booking + chat    │  │ • Backward compatible      │
└─────────────────────────────┘  └────────────────────────────┘
    ↓                               ↓
Streaming/Non-streaming Response
```

## Key Benefits

1. **No Breaking Changes** - Existing clients continue to work unchanged
2. **Automatic Enhancement** - Clients get airline booking capabilities without modification
3. **Graceful Fallback** - Service works even if MCP server is unavailable
4. **Single Endpoint** - No need for separate airline-specific endpoints
5. **Context Preservation** - All conversations maintain thread history
6. **Tool Integration** - MCP tools feel natural in conversation flow

## Implementation Details

### Service Initialization
```python
# During service startup
async def initialize(self):
    # Try to load MCP tools
    self.mcp_tools = await self._initialize_mcp_tools()
    
    if self.mcp_tools:
        # Enhanced mode with tools
        self.chat_predictor = dspy.ReAct(ConversationSignature, tools=self.mcp_tools)
    else:
        # Fallback mode without tools  
        self.chat_predictor = dspy.Predict(ConversationSignature)
```

### Runtime Adaptation
```python
# During chat processing
if self.mcp_tools:
    # Use async ReAct for tool execution
    prediction = await self.chat_predictor.acall(history=history, user_message=message)
    response = prediction.process_result
else:
    # Use sync Predict for basic chat
    prediction = self.chat_predictor(history=history, user_message=message)  
    response = prediction.response
```

This approach ensures that your existing simple-chat functionality is preserved while seamlessly adding powerful MCP tool capabilities when available.
