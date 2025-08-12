# Simple Chat Agent with Streaming

This project provides a simple chat agent built with LangGraph and FastAPI, featuring real-time streaming responses and a React frontend powered by Assistant UI.

## Features

- **Simple Agent**: A minimal LangGraph agent that streams responses back to clients
- **FastAPI Backend**: RESTful API with streaming endpoints using Server-Sent Events (SSE)
- **React Frontend**: Modern chat interface built with Assistant UI, similar to Perplexity
- **Streaming Support**: Real-time response streaming for better user experience
- **Thread Management**: Maintains conversation context across multiple messages

## Quick Start

### Backend Setup

1. **Install dependencies with uv**:
   ```bash
   uv sync
   ```

2. **Set up environment variables**:
   Create a `.env` file in `src/plan_execute/`:
   ```env
   # Database
   postgres_password=your_password
   
   # OpenAI (for local models via Ollama)
   openai_base_url=http://localhost:11434/v1
   openai_api_key=ollama
   
   # Phoenix (optional, for tracing)
   phoenix_api_key=your_phoenix_api_key
   
   # SearXNG (optional, for search functionality)
   searxng_host=http://localhost
   searxng_port=8082
   ```

3. **Start the backend**:
   ```bash
   # Using uv
   uv run python -m plan_execute.app
   
   # Or using uvicorn directly
   uvicorn plan_execute.app:app --host 0.0.0.0 --port 8094 --reload
   ```

### Frontend Setup

1. **Navigate to the frontend directory**:
   ```bash
   cd frontend
   ```

2. **Install dependencies**:
   ```bash
   npm install
   ```

3. **Start the development server**:
   ```bash
   npm run dev
   ```

4. **Open your browser**:
   Navigate to `http://localhost:3000`

## API Endpoints

### Simple Agent Endpoints

#### Streaming Chat (Recommended)
```
POST /simple-chat-stream
Content-Type: application/json

{
  "message": "Hello, how are you?",
  "thread_id": "optional-thread-id"
}
```

Returns a Server-Sent Events (SSE) stream with response chunks.

#### Non-Streaming Chat
```
POST /simple-chat
Content-Type: application/json

{
  "message": "Hello, how are you?",
  "thread_id": "optional-thread-id"
}
```

Returns a JSON response:
```json
{
  "response": "Hello! I'm doing well, thank you for asking. How can I help you today?"
}
```

### Original Plan-Execute Agent

The original complex agent is still available at:
```
POST /chat
```

## Frontend Features

The React frontend provides:

- **Real-time Streaming**: See responses as they're being generated
- **Modern UI**: Clean, responsive interface similar to Perplexity
- **Message History**: Maintains conversation context
- **Markdown Support**: Rendered markdown in responses
- **Dark Theme**: Easy on the eyes for extended use

## Architecture

### Backend

```
src/plan_execute/
├── app.py                    # FastAPI application with endpoints
├── config.py                 # Configuration management
└── agent/
    ├── simple_service.py     # New simple agent service
    ├── service.py            # Original plan-execute service
    ├── models.py             # Pydantic models
    └── nodes.py              # LangGraph nodes
```

### Frontend

```
frontend/
├── src/
│   ├── App.tsx              # Main React component
│   ├── main.tsx             # Application entry point
│   └── index.css            # Global styles
├── package.json             # Dependencies
├── vite.config.ts           # Vite configuration
└── tsconfig.json            # TypeScript configuration
```

## Development

### Running Tests

Test the simple agent functionality:
```bash
python test_simple_agent.py
```

### Adding New Features

1. **Backend**: Modify the simple agent in `simple_service.py`
2. **Frontend**: Update the React components in `frontend/src/`
3. **API**: Add new endpoints in `app.py`

## Configuration

### Backend Configuration

Key configuration options in `src/plan_execute/config.py`:

- `host`: Server host (default: 0.0.0.0)
- `port`: Server port (default: 8094)
- `openai_base_url`: LLM API endpoint
- `openai_api_key`: API key for the LLM

### Frontend Configuration

Frontend configuration in `frontend/vite.config.ts`:

- Development server port: 3000
- API proxy to backend: `http://localhost:8094`

## Troubleshooting

### Common Issues

1. **Backend won't start**:
   - Check that PostgreSQL is running
   - Verify environment variables in `.env` file
   - Ensure all dependencies are installed with `uv sync`

2. **Frontend won't connect**:
   - Ensure backend is running on port 8094
   - Check CORS headers in the backend response
   - Verify proxy configuration in `vite.config.ts`

3. **Streaming not working**:
   - Check that the browser supports Server-Sent Events
   - Verify the backend endpoint is returning correct SSE format
   - Check network tab in browser dev tools for connection errors

### Logs

- Backend logs: Console output with detailed logging
- Frontend logs: Browser developer tools console

## Docker Support

The project includes Docker configuration for easy deployment:

```bash
# Build and run with Docker Compose
docker-compose up --build
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This project is open source and available under the MIT License.