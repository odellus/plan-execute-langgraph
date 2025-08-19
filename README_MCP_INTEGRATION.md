# DSPy MCP Integration - Airline Booking System

This project demonstrates the integration of Model Context Protocol (MCP) tools with DSPy streaming services, implementing a complete airline booking system.

## Overview

The integration provides:
- **MCP Server**: Airline booking tools with flight search, booking, and management capabilities
- **DSPy MCP Service**: Streaming chat service that uses MCP tools through DSPy's ReAct agent
- **API Endpoints**: RESTful endpoints for both streaming and non-streaming interactions
- **Conversation Persistence**: Full conversation history stored in PostgreSQL

## Architecture

```
Frontend/Client
    ↓
FastAPI Endpoints (/airline-chat-stream, /airline-chat)
    ↓
DSPyMCPAgentService (streaming DSPy ReAct agent)
    ↓
MCP Tools (via stdio client)
    ↓
MCP Server (airline booking database and tools)
```

## Files Created/Modified

### New Files
- `mcp_server.py` - MCP server with airline booking tools
- `src/plan_execute/agent/dspy_mcp_service.py` - DSPy service with MCP integration
- `test_dspy_mcp_integration.py` - Comprehensive test suite
- `demo_mcp_airline.py` - Interactive demo script

### Modified Files
- `src/plan_execute/app.py` - Added new airline booking endpoints
- `pyproject.toml` - Added MCP dependencies

## MCP Tools Available

The MCP server provides the following tools:

1. **fetch_flight_info** - Search for flights by date, origin, and destination
2. **book_itinerary** - Book a flight for a user
3. **fetch_itinerary** - Retrieve booking details using confirmation number
4. **modify_itinerary** - Change or cancel existing bookings
5. **get_user_info** - Look up user profile information
6. **file_ticket** - Create support tickets for complex requests

## Sample Database

The system includes sample data:
- **Users**: Adam, Bob, Chelsie, David
- **Flights**: SFO↔JFK, LAX↔JFK routes on Sept 1-2, 2025
- **Bookings**: Stored dynamically as users make reservations

## API Endpoints

### Streaming Endpoint
```
POST /airline-chat-stream
Content-Type: application/json

{
    "thread_id": "user-session-123",
    "message": "Book a flight from SFO to JFK on September 1st, 2025 for Adam"
}
```

Returns Server-Sent Events (SSE) stream compatible with OpenAI's streaming format.

### Non-Streaming Endpoint
```
POST /airline-chat
Content-Type: application/json

{
    "thread_id": "user-session-123", 
    "message": "Show me flights from SFO to JFK on September 1st, 2025"
}
```

Returns complete JSON response.

## Installation

1. Install dependencies:
```bash
pip install -U dspy-ai[mcp] mcp aiohttp
```

Or update using the project dependencies:
```bash
pip install -e .
```

2. Ensure PostgreSQL is running and configured in your `.env` file.

## Usage

### Running the Full System

1. Start the FastAPI server:
```bash
python -m src.plan_execute.app
```

2. The MCP server will be started automatically by the DSPy MCP service.

3. Access the airline booking endpoints:
   - Streaming: `POST http://localhost:8000/airline-chat-stream`
   - Non-streaming: `POST http://localhost:8000/airline-chat`

### Running the Demo

```bash
python demo_mcp_airline.py
```

This will demonstrate various booking scenarios including:
- Flight searches
- Booking flights
- Checking itineraries
- User lookups
- Complex multi-step requests

### Running Tests

```bash
python test_dspy_mcp_integration.py
```

Tests include:
- MCP server standalone functionality
- DSPy MCP service integration
- API endpoint testing
- Streaming functionality

## Example Interactions

### Flight Search
```
User: "Show me flights from SFO to JFK on September 1st, 2025"
Assistant: "I found 3 available flights from SFO to JFK on September 1st, 2025:
1. DA123 - Departure: 1:00 AM, Duration: 3 hours, Price: $200
2. DA125 - Departure: 7:00 AM, Duration: 9 hours, Price: $500  
3. DA127 - Departure: 7:00 PM, Duration: 5 hours, Price: $300"
```

### Flight Booking
```
User: "Book the cheapest flight from SFO to JFK on September 1st for Adam"
Assistant: "I've successfully booked flight DA123 from SFO to JFK on September 1st, 2025 for Adam. 
Confirmation number: abc123de
Flight details: Departure 1:00 AM, Duration: 3 hours, Price: $200"
```

### Itinerary Check
```
User: "Check my booking with confirmation number abc123de"
Assistant: "Here are your booking details:
- Confirmation: abc123de
- Passenger: Adam (adam@gmail.com)
- Flight: DA123 from SFO to JFK
- Date: September 1st, 2025 at 1:00 AM
- Duration: 3 hours
- Price: $200"
```

## Key Features

### Streaming Support
- Real-time response streaming using DSPy's `streamify`
- OpenAI-compatible streaming format
- Proper conversation persistence during streaming

### Tool Integration
- Seamless MCP tool integration through DSPy's `Tool.from_mcp_tool`
- Automatic tool discovery and conversion
- Async tool execution support

### Conversation Memory
- Full conversation history stored in PostgreSQL
- Thread-based conversation management
- Persistent state across requests

### Error Handling
- Graceful error handling for MCP server issues
- Fallback responses for tool failures
- Comprehensive logging and debugging

## Development Notes

### MCP Server Communication
- Uses stdio client for MCP server communication
- Server process managed automatically by the service
- Tools are initialized once during service startup

### DSPy ReAct Integration
- Uses DSPy's ReAct module for reasoning and tool execution
- Custom signature for airline service context
- Streaming support through `streamify` wrapper

### Database Integration
- Reuses existing PostgreSQL checkpointer
- Compatible with existing conversation storage
- Thread-based isolation for multiple users

## Troubleshooting

### Common Issues

1. **MCP server fails to start**
   - Check that `mcp` package is installed
   - Verify Python path in server parameters
   - Check for port conflicts

2. **Tools not found**
   - Ensure MCP server is running
   - Check server initialization in logs
   - Verify tool registration with `@mcp.tool()`

3. **Streaming issues**
   - Verify async/await usage
   - Check for proper chunk formatting
   - Ensure proper connection handling

### Debug Logging

Enable debug logging to see detailed MCP communication:
```python
import logging
logging.getLogger("dspy_mcp_service").setLevel(logging.DEBUG)
logging.getLogger("mcp").setLevel(logging.DEBUG)
```

## Future Enhancements

Potential improvements:
- Real database integration (replace in-memory storage)
- Additional airline tools (seat selection, meal preferences)
- Multi-airline support
- Payment processing integration
- Email confirmation system
- Advanced search filters (price range, preferred times)

## References

- [DSPy Documentation](https://dspy.ai/)
- [MCP Tutorial](https://dspy.ai/tutorials/mcp/)
- [Model Context Protocol](https://github.com/modelcontextprotocol/python-sdk)
