from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import yt_dlp
from typing import Dict, Any
import logging
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# CORS - সম্পূর্ণ ওপেন
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

def extract_video_info(url: str) -> Dict[str, Any]:
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
            
            if 'entries' in info and info['entries']:
                info = info['entries'][0]
                if not info:
                    return {"success": False, "error": "Empty playlist"}
            
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
                }
            }
            
    except Exception as e:
        logger.error(f"yt-dlp error: {str(e)}")
        return {"success": False, "error": str(e)}

@app.get("/")
async def root():
    return {
        "status": "active",
        "message": "Video Downloader API is running",
        "version": "1.0.0",
        "endpoints": {
            "/": "This page",
            "/api/download": "GET with ?url=VIDEO_URL",
            "/api/health": "Health check"
        }
    }

@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "service": "video-downloader-api"
    }

@app.get("/api/download")
async def download_video(url: str = Query(..., description="Video URL")):
    try:
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
                    "message": "Failed to fetch video details"
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

app_handler = app
