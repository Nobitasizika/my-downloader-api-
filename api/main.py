# ============================================
# main.py (আপডেটেড ভার্সন - সমস্যা সমাধান সহ)
# ============================================

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import yt_dlp
import json
import os
import re
from typing import Optional, Dict, Any
import logging
import time

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
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Custom exception class
class VideoDownloadError(Exception):
    pass

def validate_url(url: str) -> bool:
    """Validate if URL is properly formatted"""
    url_pattern = re.compile(
        r'^https?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
        r'localhost|'  # localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    return re.match(url_pattern, url) is not None

def get_video_info(url: str) -> Dict[str, Any]:
    """
    Extract video information using yt-dlp with enhanced error handling
    """
    # yt-dlp options with better error handling
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': False,
        'format': 'best[height<=720]',  # Simplified format selection
        'force_generic_extractor': False,
        'ignoreerrors': True,
        'no_check_certificate': True,  # Bypass SSL issues
        'prefer_insecure': False,
        'geo_bypass': True,
        'socket_timeout': 60,  # Increased timeout
        'retries': 5,  # More retries
        'fragment_retries': 5,
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-us,en;q=0.5',
            'Sec-Fetch-Mode': 'navigate',
        },
        'extractor_args': {
            'youtube': {
                'skip': ['hls', 'dash'],  # Skip problematic formats
                'player_client': ['android', 'web'],  # Try different clients
            }
        }
    }

    try:
        # Validate URL first
        if not validate_url(url):
            raise VideoDownloadError("Invalid URL format. Please provide a valid URL.")

        logger.info(f"Fetching video info for URL: {url}")
        
        # Try with yt-dlp
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                info = ydl.extract_info(url, download=False)
            except Exception as e:
                # Try with different options if first attempt fails
                logger.warning(f"First attempt failed: {str(e)}. Trying with different options...")
                ydl_opts['extractor_args']['youtube']['player_client'] = ['web']
                with yt_dlp.YoutubeDL(ydl_opts) as ydl2:
                    info = ydl2.extract_info(url, download=False)
            
            if not info:
                raise VideoDownloadError("No video information found. The URL might be invalid or the video is private.")
            
            # Handle playlist or single video
            if 'entries' in info and info['entries']:
                info = info['entries'][0]
                if not info:
                    raise VideoDownloadError("No video found in the playlist.")
            
            # Check if video is available
            if info.get('_type') == 'url' or not info.get('title'):
                raise VideoDownloadError("Could not extract video details. The URL might be unsupported.")
            
            # Get direct download URL with fallback
            direct_url = None
            
            # Method 1: Check for direct URL
            if info.get('url'):
                direct_url = info['url']
            
            # Method 2: Check formats
            if not direct_url and info.get('formats'):
                # Sort formats by quality
                formats = [f for f in info['formats'] if f.get('url')]
                if formats:
                    # Try to get best format with both video and audio
                    for f in reversed(formats):
                        if f.get('vcodec') != 'none' and f.get('acodec') != 'none':
                            direct_url = f['url']
                            break
                    # If no combined format, get best video
                    if not direct_url:
                        for f in reversed(formats):
                            if f.get('vcodec') != 'none':
                                direct_url = f['url']
                                break
            
            # Method 3: Check request formats
            if not direct_url and info.get('requested_formats'):
                for f in info['requested_formats']:
                    if f.get('url'):
                        direct_url = f['url']
                        break
            
            # Method 4: Use yt-dlp to get URL
            if not direct_url:
                try:
                    # Try to extract URL using different method
                    ydl_opts['format'] = 'best[ext=mp4]/best'
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl_temp:
                        temp_info = ydl_temp.extract_info(url, download=False)
                        if temp_info and temp_info.get('url'):
                            direct_url = temp_info['url']
                except:
                    pass

            # Get thumbnail with fallback
            thumbnail = info.get('thumbnail')
            if not thumbnail and info.get('thumbnails'):
                thumbnails = info['thumbnails']
                if thumbnails:
                    # Get highest quality thumbnail
                    thumbnail = thumbnails[-1].get('url', thumbnails[0].get('url'))

            # Prepare formats list (limited for response size)
            formats_list = []
            if info.get('formats'):
                for f in info['formats'][:3]:  # Only top 3 formats
                    formats_list.append({
                        'format_id': f.get('format_id', 'N/A'),
                        'ext': f.get('ext', 'N/A'),
                        'resolution': f.get('resolution', 'N/A'),
                        'filesize': f.get('filesize', 'N/A'),
                        'vcodec': f.get('vcodec', 'N/A'),
                        'acodec': f.get('acodec', 'N/A'),
                    })

            # Build response
            response = {
                'title': info.get('title', 'Untitled'),
                'thumbnail': thumbnail or 'N/A',
                'description': (info.get('description', '') or '')[:300],
                'duration': info.get('duration', 0),
                'view_count': info.get('view_count', 0),
                'like_count': info.get('like_count', 0),
                'uploader': info.get('uploader') or info.get('channel') or info.get('creator') or 'Unknown',
                'upload_date': info.get('upload_date', 'N/A'),
                'extractor': info.get('extractor', 'N/A'),
                'webpage_url': info.get('webpage_url', url),
                'direct_download_url': direct_url,
                'formats': formats_list,
                'format': info.get('format', 'N/A'),
                'resolution': info.get('resolution', 'N/A'),
                'filesize': info.get('filesize', 'N/A'),
                'ext': info.get('ext', 'N/A'),
                'is_live': info.get('is_live', False),
            }

            # Clean None values
            response = {k: v for k, v in response.items() if v is not None}
            
            # Check if we have a direct URL
            if not response.get('direct_download_url'):
                logger.warning("No direct download URL found for this video")
                response['message'] = 'No direct download URL available. Video may require additional authentication.'

            return response
            
    except yt_dlp.utils.DownloadError as e:
        error_msg = str(e).lower()
        if 'unavailable' in error_msg or 'private' in error_msg:
            raise VideoDownloadError("Video is private or unavailable")
        elif 'georestricted' in error_msg:
            raise VideoDownloadError("Video is geo-restricted and cannot be accessed from this location")
        elif 'login' in error_msg or 'authentication' in error_msg:
            raise VideoDownloadError("Video requires authentication or is age-restricted")
        else:
            raise VideoDownloadError(f"Download error: {str(e)}")
    except yt_dlp.utils.ExtractorError as e:
        raise VideoDownloadError(f"Extractor error: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        raise VideoDownloadError(f"An unexpected error occurred: {str(e)}")

@app.get("/")
async def home():
    """Home endpoint with API documentation"""
    return {
        "message": "Welcome to All Video Downloader API",
        "status": "active",
        "endpoints": {
            "/": "This documentation",
            "/api/download": "Download video from social media (GET or POST)",
            "/api/health": "Health check endpoint",
            "/docs": "Swagger API documentation"
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
        ],
        "note": "Some videos may not be downloadable due to privacy settings or platform restrictions"
    }

@app.get("/api/download")
async def download_video_get(
    url: str = Query(..., description="Social media video URL to download")
):
    """Download video information using GET method"""
    return await process_download(url)

@app.post("/api/download")
async def download_video_post(data: Dict[str, Any]):
    """Download video information using POST method"""
    url = data.get('url')
    if not url:
        raise HTTPException(status_code=400, detail="URL parameter is required")
    return await process_download(url)

async def process_download(url: str):
    """Process video download request with improved error handling"""
    start_time = time.time()
    
    try:
        # Validate URL
        if not url or not url.strip():
            raise HTTPException(status_code=400, detail="Invalid URL provided")
        
        # URL validation
        if not validate_url(url):
            raise HTTPException(status_code=400, detail="Invalid URL format. Please provide a valid URL starting with http:// or https://")
        
        logger.info(f"Processing request for URL: {url}")
        
        # Get video information
        video_info = get_video_info(url)
        
        # Log processing time
        processing_time = time.time() - start_time
        logger.info(f"Video processed in {processing_time:.2f} seconds")
        
        # Prepare response
        response_data = {
            "success": True,
            "message": "Video information retrieved successfully",
            "processing_time": f"{processing_time:.2f}s",
            "data": video_info
        }
        
        # If no direct URL, add warning
        if not video_info.get('direct_download_url'):
            response_data["warning"] = "No direct download URL found. The video might be restricted or require additional access."
        
        return response_data
        
    except VideoDownloadError as e:
        logger.error(f"Video download error: {str(e)}")
        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "message": str(e),
                "error_type": "VideoDownloadError",
                "suggestion": "Try a different URL or check if the video is publicly accessible"
            }
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Unhandled exception: {str(e)}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": "Internal server error. Please try again later.",
                "error": str(e) if os.getenv("DEBUG") else "Contact support"
            }
        )

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "video-downloader-api", "timestamp": time.time()}

# For Vercel serverless deployment
app_handler = app
