# Website Cloner Backend

This is the backend service for the website cloning application. It provides APIs for website scraping and cloning using FastAPI and LLM.

## Setup

1. Install dependencies:
```bash
uv sync
```

2. Set up environment variables:
Create a `.env` file with:
```
ANTHROPIC_API_KEY=your_api_key_here
```

3. Run the development server:
```bash
uvicorn app.main:app --reload
```

## API Endpoints

- `POST /api/clone`: Clone a website from a given URL
- `GET /`: Health check endpoint 