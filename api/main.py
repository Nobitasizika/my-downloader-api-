# main.py
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import yt_dlp
import json
import os
from typing import Optional, Dict, Any
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="All Video Downloader API",
    description="API to download videos from various social media platforms",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Custom exception handler for yt-dlp errors
class VideoDownloadError(Exception):
    pass

def get_video_info(url: str) -> Dict[str, Any]:
    """
    Extract video information using yt-dlp
    """
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': False,
        'format': 'bestvideo[height<=720]+bestaudio/best[height<=720]',
        'force_generic_extractor': False,
        'ignoreerrors': True,
        'no_check_certificate': True,
        'prefer_insecure': False,
        'geo_bypass': True,
        'socket_timeout': 30,
        'retries': 3,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            logger.info(f"Fetching video info for URL: {url}")
            info = ydl.extract_info(url, download=False)
            
            if not info:
                raise VideoDownloadError("Failed to extract video information")
            
            # Handle playlist or single video
            if 'entries' in info:
                # If playlist, take first video
                info = info['entries'][0]
                if not info:
                    raise VideoDownloadError("Empty playlist or no video found")
            
            # Extract available formats
            formats = []
            if 'formats' in info:
                for f in info['formats'][:5]:  # Limit to top 5 formats for clarity
                    formats.append({
                        'format_id': f.get('format_id', 'N/A'),
                        'ext': f.get('ext', 'N/A'),
                        'resolution': f.get('resolution', 'N/A'),
                        'filesize': f.get('filesize', 'N/A'),
                        'filesize_approx': f.get('filesize_approx', 'N/A'),
                        'vcodec': f.get('vcodec', 'N/A'),
                        'acodec': f.get('acodec', 'N/A'),
                    })

            # Get direct download URL if available
            # Prefer the best format URL
            direct_url = None
            if 'url' in info:
                direct_url = info['url']
            elif 'requested_formats' in info:
                # If merged format
                for f in info['requested_formats']:
                    if 'url' in f:
                        direct_url = f['url']
                        break
            elif 'formats' in info and info['formats']:
                # Get the last format (usually the best quality)
                for f in reversed(info['formats']):
                    if f.get('url') and f.get('vcodec') != 'none':
                        direct_url = f['url']
                        break
                if not direct_url and info['formats']:
                    direct_url = info['formats'][-1].get('url')

            # Build response
            response = {
                'title': info.get('title', 'N/A'),
                'thumbnail': info.get('thumbnail', info.get('thumbnails', [{}])[-1].get('url', 'N/A') if info.get('thumbnails') else 'N/A'),
                'description': info.get('description', 'N/A')[:500],  # Limit description length
                'duration': info.get('duration', 0),
                'view_count': info.get('view_count', 0),
                'like_count': info.get('like_count', 0),
                'uploader': info.get('uploader', info.get('channel', 'N/A')),
                'upload_date': info.get('upload_date', 'N/A'),
                'extractor': info.get('extractor', 'N/A'),
                'webpage_url': info.get('webpage_url', url),
                'direct_download_url': direct_url,
                'formats': formats,
                'format': info.get('format', 'N/A'),
                'resolution': info.get('resolution', 'N/A'),
                'filesize': info.get('filesize', info.get('filesize_approx', 'N/A')),
                'ext': info.get('ext', 'N/A'),
            }

            # Clean None values
            response = {k: v for k, v in response.items() if v is not None}
            
            return response
            
    except yt_dlp.utils.DownloadError as e:
        logger.error(f"yt-dlp download error: {str(e)}")
        raise VideoDownloadError(f"Failed to download video: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise VideoDownloadError(f"An error occurred: {str(e)}")

@app.get("/")
async def home():
    """Home endpoint with API documentation"""
    return {
        "message": "Welcome to All Video Downloader API",
        "endpoints": {
            "/": "This documentation",
            "/api/download": "Download video from social media (GET or POST)",
            "/docs": "Swagger API documentation",
            "/redoc": "ReDoc API documentation"
        },
        "usage": {
            "method": "GET or POST",
            "parameters": {
                "url": "Social media video URL (e.g., YouTube, Facebook, Instagram, TikTok)"
            },
            "example": "/api/download?url=https://www.youtube.com/watch?v=VIDEO_ID"
        },
        "supported_platforms": [
            "YouTube",
            "Facebook",
            "Instagram",
            "TikTok",
            "Twitter/X",
            "Reddit",
            "Vimeo",
            "Dailymotion",
            "And many more..."
        ]
    }

@app.get("/api/download")
async def download_video_get(
    url: str = Query(..., description="Social media video URL to download")
):
    """Download video information using GET method"""
    return await process_download(url)

@app.post("/api/download")
async def download_video_post(
    data: Dict[str, Any]
):
    """Download video information using POST method"""
    url = data.get('url')
    if not url:
        raise HTTPException(status_code=400, detail="URL parameter is required")
    return await process_download(url)

async def process_download(url: str):
    """Process video download request"""
    try:
        # Validate URL
        if not url or not url.strip():
            raise HTTPException(status_code=400, detail="Invalid URL provided")
        
        # Get video information
        video_info = get_video_info(url)
        
        # Check if direct download URL exists
        if not video_info.get('direct_download_url'):
            return JSONResponse(
                status_code=200,
                content={
                    "success": False,
                    "message": "No direct download URL available. The video might be protected or require authentication.",
                    "data": video_info
                }
            )
        
        return {
            "success": True,
            "message": "Video information retrieved successfully",
            "data": video_info
        }
        
    except VideoDownloadError as e:
        logger.error(f"Video download error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unhandled exception: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

# Health check endpoint for Vercel
@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "video-downloader-api"}

# For Vercel serverless deployment
app_handler = app
