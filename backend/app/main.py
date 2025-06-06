from fastapi import FastAPI, HTTPException, Request, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel, HttpUrl, Field
from typing import Dict, Any, List, AsyncGenerator, Optional
import asyncio
import json
import logging
from datetime import datetime

# Import your enhanced cloners
from .services.website_cloner import WebsiteCloner

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Peony API",
    description="Clone websites with pixel-perfect accuracy using AI",
    version="1.0.0"
)
# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request Models
class CloneRequest(BaseModel):
    url: HttpUrl
    options: Optional[Dict[str, Any]] = Field(default_factory=dict)

class MultiPageCloneRequest(BaseModel):
    url: HttpUrl
    max_pages: Optional[int] = Field(default=5, le=20)  # Limit to 20 pages max, it gets yucky after that
    options: Optional[Dict[str, Any]] = Field(default_factory=dict)

class AnalyzeRequest(BaseModel):
    url: HttpUrl

# Response Models
class CloneResponse(BaseModel):
    success: bool
    html: Optional[str] = None
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class MultiPageCloneResponse(BaseModel):
    success: bool
    pages: Optional[Dict[str, str]] = None
    total_pages: Optional[int] = None
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class AnalyzeResponse(BaseModel):
    success: bool
    design_context: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

@app.post("/api/clone")
async def clone_website(request: Request):
    try:
        body = await request.json()
        url = body["url"]
        website_cloner = WebsiteCloner()
        html = await website_cloner.clone_single_page(str(url))
        return {"html": html}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/clone/multipage", response_model=MultiPageCloneResponse)
async def clone_multipage_website(request: MultiPageCloneRequest):
    """Clone an entire multi-page website"""
    start_time = datetime.now()
    
    try:
        logger.info(f"Starting multi-page clone for URL: {request.url}, max_pages: {request.max_pages}")
        
        # Initialize the enhanced cloner
        cloner = WebsiteCloner()
        
        # Clone the entire website
        pages = await cloner.clone_multipage_site(str(request.url), request.max_pages)
        
        if not pages:
            raise HTTPException(status_code=500, detail="No pages were successfully cloned")
        
        processing_time = (datetime.now() - start_time).total_seconds()
        total_html_length = sum(len(html) for html in pages.values())
        
        metadata = {
            "processing_time_seconds": processing_time,
            "total_pages_cloned": len(pages),
            "total_html_length": total_html_length,
            "timestamp": datetime.now().isoformat(),
            "source_url": str(request.url),
            "pages_list": list(pages.keys())
        }
        
        logger.info(f"Multi-page clone completed: {len(pages)} pages in {processing_time:.2f}s")
        
        return MultiPageCloneResponse(
            success=True,
            pages=pages,
            total_pages=len(pages),
            metadata=metadata
        )
        
    except Exception as e:
        logger.error(f"Error cloning multi-page website {request.url}: {str(e)}")
        return MultiPageCloneResponse(
            success=False,
            error=str(e)
        )


@app.get("/api/clone/stream")
async def clone_website_stream(url: str = Query(...)):
    """Stream the cloning process with real-time updates (SSE)"""
    async def generate_clone_stream():
        try:
            yield f"data: {json.dumps({'status': 'starting', 'message': 'Initializing cloner...'})}\n\n"
            cloner = WebsiteCloner()
            yield f"data: {json.dumps({'status': 'extracting', 'message': 'Extracting design context...'})}\n\n"
            html = await cloner.clone_single_page(str(url))
            yield f"data: {json.dumps({'status': 'generating', 'message': 'Generating complete HTML...'})}\n\n"
            if html:
                yield f"data: {json.dumps({'status': 'complete', 'html': html, 'message': 'Clone completed successfully!'})}\n\n"
            else:
                yield f"data: {json.dumps({'status': 'error', 'message': 'Failed to generate HTML'})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'status': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        generate_clone_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": exc.detail,
            "timestamp": datetime.now().isoformat()
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "Internal server error",
            "timestamp": datetime.now().isoformat()
        }
    )

@app.on_event("startup")
async def startup_event():
    logger.info("Peony API starting up...")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Peony API shutting down...")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=8000,
        log_level="info"
    )