from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import yt_dlp

app = FastAPI()

# আপনার মেইন ওয়েবসাইট (Netlify) যেন এই এপিআই ব্যবহার করতে পারে, তাই CORS ইনেবল করা হয়েছে
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ১. ভিডিওর ইনফো (থাম্বনেইল ও টাইটেল) আনার জন্য রুট (যা আপনার ফ্রন্টএন্ডে দরকার)
@app.get("/api/info")
def get_video_info(url: str):
    if not url:
        raise HTTPException(status_code=400, detail="URL is required")
        
    ydl_opts = {
        'format': 'best',
        'quiet': True,
        'no_warnings': True,
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return {
                "success": True,
                "title": info.get('title'),
                "thumbnail": info.get('thumbnail')
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ২. মূল ভিডিও/অডিও ডাউনলোড লিংক জেনারেট করার জন্য রুট
@app.get("/api/download")
def download_video(url: str, type: str = "video", quality: str = "high"):
    if not url:
        raise HTTPException(status_code=400, detail="URL is required")
        
    # ইউজার অডিও চেয়েছে নাকি ভিডিও, তার ওপর ভিত্তি করে ফরম্যাট সিলেক্ট হবে
    if type == "audio":
        format_opt = 'bestaudio/best'
    else:
        format_opt = 'bestvideo+bestaudio/best' if quality == 'high' else 'worst/worst'
        
    ydl_opts = {
        'format': format_opt,
        'quiet': True,
        'no_warnings': True,
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            # সরাসরি ডাউনলোড ফাইলের রিলিজ ইউআরএল
            download_url = info.get('url')
            
            if not download_url:
                raise HTTPException(status_code=404, detail="Download URL not found")
                
            return {
                "success": True,
                "title": info.get('title'),
                "thumbnail": info.get('thumbnail'),
                "download_url": download_url
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
