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

@app.get("/api/download")
def download_video(url: str):
    if not url:
        raise HTTPException(status_code=400, detail="URL is required")
        
    # yt-dlp এর সেটিংস (ভিডিওর বেস্ট কোয়ালিটি লিংক স্ক্র্যাপ করবে)
    ydl_opts = {
        'format': 'best',
        'quiet': True,
        'no_warnings': True,
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # ভিডিওর ডেটা এক্সট্র্যাক্ট করা হচ্ছে
            info = ydl.extract_info(url, download=False)
            
            return {
                "success": True,
                "title": info.get('title'),
                "thumbnail": info.get('thumbnail'),
                "download_url": info.get('url')
            }
    except Exception as e:
        return {"success": False, "error": str(e)}
