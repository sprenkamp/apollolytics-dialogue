# Apollolytics Dialogue - Development Guide

## Build & Run Commands
- **Frontend Dev**: `cd frontend && npm run dev`
- **Frontend Build**: `cd frontend && npm run build`
- **Frontend Lint**: `cd frontend && npm run lint`
- **Backend Run**: `uvicorn backend.app:app --host 0.0.0.0 --port 8080`
- **Speech Backend**: `uvicorn backend.ws_speech_real-time:app --host 0.0.0.0 --port 8080`
- **Docker Build**: `docker build -t apollolytics_dialogue_bot .`

## Code Style Guidelines
- **Frontend**: React/Next.js with functional components, Tailwind CSS
- **Backend**: Python 3.9+ with FastAPI and asyncio
- **Naming**: PascalCase for components, camelCase for JS variables, snake_case for Python
- **Imports**: Group by standard library → third-party → local imports
- **Types**: Use TypeScript for frontend, Python type hints for backend
- **Error Handling**: Try/catch with user feedback, detailed logging for backend
- **Documentation**: JSDoc for JS functions, docstrings for Python functions/classes
- **State Management**: React hooks for frontend, environment variables for configuration