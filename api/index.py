# ============================================
# api/index.py - Pure API (No HTML/Website)
# ============================================

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import yt_dlp
from typing import Dict, Any
import logging
import time

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI
app = FastAPI(
    title="Video Downloader API",
    description="API for downloading videos from social media platforms",
    version="1.0.0",
    docs_url="/docs",           # Swagger UI
    redoc_url="/redoc",         # ReDoc
    openapi_url="/openapi.json" # OpenAPI spec
)

# CORS - Allow all origins (for your main website)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # আপনার মূল ওয়েবসাইটের URL দিতে পারেন
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def extract_video_info(url: str) -> Dict[str, Any]:
    """Extract video information using yt-dlp"""
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'format': 'best',
        'no_check_certificate': True,
        'geo_bypass': True,
        'socket_timeout': 30,
        'retries': 3,
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        }
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            if not info:
                return {"success": False, "error": "No information found"}
            
            # Handle playlist
            if 'entries' in info and info['entries']:
                info = info['entries'][0]
                if not info:
                    return {"success": False, "error": "Empty playlist"}
            
            # Get direct URL
            direct_url = info.get('url')
            if not direct_url and info.get('formats'):
                formats = [f for f in info['formats'] if f.get('url')]
                if formats:
                    direct_url = formats[-1].get('url')
            
            return {
                "success": True,
                "data": {
                    "title": info.get('title', 'N/A'),
                    "thumbnail": info.get('thumbnail', 'N/A'),
                    "duration": info.get('duration', 0),
                    "uploader": info.get('uploader', 'N/A'),
                    "direct_download_url": direct_url,
                    "platform": info.get('extractor', 'N/A'),
                    "webpage_url": info.get('webpage_url', url),
                    "format": info.get('format', 'N/A'),
                    "filesize": info.get('filesize', 'N/A'),
                }
            }
            
    except Exception as e:
        logger.error(f"yt-dlp error: {str(e)}")
        return {"success": False, "error": str(e)}

@app.get("/")
async def root():
    """API Root - Returns API info"""
    return {
        "name": "Video Downloader API",
        "version": "1.0.0",
        "status": "active",
        "endpoints": {
            "/": "API Information",
            "/api/download": "Download video (GET with ?url=)",
            "/api/health": "Health check",
            "/docs": "Swagger Documentation",
            "/redoc": "ReDoc Documentation"
        },
        "usage": {
            "method": "GET or POST",
            "params": {
                "url": "Video URL (YouTube, Facebook, Instagram, TikTok, etc.)"
            },
            "example": "/api/download?url=https://www.youtube.com/watch?v=VIDEO_ID"
        },
        "supported_platforms": [
            "YouTube", "Facebook", "Instagram", "TikTok", 
            "Twitter/X", "Reddit", "Vimeo", "Dailymotion"
        ]
    }

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "service": "video-downloader-api"
    }

@app.get("/api/download")
async def download_video(url: str = Query(..., description="Video URL to download")):
    """
    Download video from any social media platform
    
    Parameters:
    - url: Video URL (YouTube, Facebook, Instagram, TikTok, etc.)
    
    Returns:
    - Video information including direct download URL
    """
    try:
        # Validate URL
        if not url or not url.startswith(('http://', 'https://')):
            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "error": "Invalid URL format",
                    "message": "URL must start with http:// or https://"
                }
            )
        
        logger.info(f"Processing URL: {url}")
        
        # Extract video info
        result = extract_video_info(url)
        
        if result.get('success'):
            return {
                "success": True,
                "message": "Video information retrieved successfully",
                "data": result.get('data')
            }
        else:
            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "error": result.get('error', 'Unknown error'),
                    "message": "Failed to fetch video details",
                    "suggestion": "Check if video is public and URL is correct"
                }
            )
            
    except Exception as e:
        logger.error(f"API error: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": "Internal server error",
                "message": str(e)
            }
        )

@app.post("/api/download")
async def download_video_post(data: Dict[str, Any]):
    """POST version of download endpoint"""
    url = data.get('url')
    if not url:
        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "error": "Missing parameter",
                "message": "url is required in request body"
            }
        )
    return await download_video(url=url)

# Vercel handler
app_handler = app
