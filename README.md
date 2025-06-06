# Peony 🌸

Peony is a powerful website cloning service that uses AI to create pixel-perfect replicas of websites. Built with FastAPI, Playwrite, BrowserBase and the Anthropic API, it can handle both single-page and multi-page website cloning with high accuracy.

## Features

- 🎯 Pixel-perfect website cloning
- 🌐 Multi-page website support
- 🤖 AI-powered design analysis
- 🎨 CSS and style preservation
- 📱 Responsive design handling
- 🔄 Real-time cloning progress
- 🛡️ Browserbase integration for reliable scraping

## Tech Stack

- **Backend**: FastAPI, Python 3.8+
- **Browser Automation**: Playwright
- **AI/ML**: Custom LLM integration
- **Cloud Browser**: Browserbase
- **Frontend**: Next js

## Getting Started

### Prerequisites

- Python 3.8 or higher
- Node.js 16+ (for frontend)
- Browserbase account and API key

### Installation

1. Clone the repository:
```bash
git clone https://github.com/rumezaa/peony.git
cd peony
```

2. Install backend dependencies:
```bash
cd backend
uv pip install -r requirements.txt
```

3. Create a .env in the backend folder and add the following variables with api keys:
```bash
ANTHROPIC_API_KEY="your key"
BROWSERBASE_API_KEY="your key"
BROWSERBASE_PROJECT_ID="your key"
```

4. Install Playwright browsers:
```bash
playwright install chromium
```

### Running the Application

1. Start the backend server:
```bash
cd backend
uv run fastapi dev
```

2. The API will be available at `http://localhost:8000`

## API Endpoints

### Clone Single Page
```http
POST /api/clone
Content-Type: application/json

{
    "url": "https://example.com"
}
```

### Clone Multi-page Website
```http
POST /api/clone/multipage
Content-Type: application/json

{
    "url": "https://example.com",
    "max_pages": 5
}
```

### Stream Clone Progress
```http
GET /api/clone/stream?url=https://example.com
```

## Development

### Project Structure
```
peony/
├── backend/
│   ├── app/
│   │   ├── services/
│   │   │   ├── website_cloner.py
│   │   │   ├── website_scraper.py
│   │   │   └── llm_cloner.py
|   |   |── .env 
│   │   └── main.py
│   └── requirements.txt
└── frontend/ (coming soon)
```
# peony
