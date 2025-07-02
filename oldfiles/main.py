from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl
from pymongo import MongoClient
from dotenv import load_dotenv
from datetime import datetime
from genai import generate_description
from utils import extract_video_id, fetch_transcript, textify
import os
import uvicorn

load_dotenv()

app = FastAPI()

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# MongoDB connection
MONGO_URI = os.getenv("LocalMongoDBURI")
client = MongoClient(MONGO_URI)
db = client["youtube_notebook"]
videos_collection = db["videos"]

# Pydantic model for request body
class VideoSubmission(BaseModel):
    url: HttpUrl

@app.get("/")
async def root():
    return {"message": "YouTube Notebook API"}

@app.post("/submit-video")
async def submit_video(video: VideoSubmission):
    video_id = extract_video_id(str(video.url))
    if not video_id:
        raise HTTPException(status_code=400, detail="Invalid YouTube URL")
    
    if videos_collection.find_one({"video_id": video_id}):
         return {"message": "Video was already submitted !!", "video_id": video_id}
    
    video_data = {
        "video_id": video_id,
        "url": str(video.url),
        "submitted_at": datetime.utcnow(),
        "transcript": None,
        "transcript_text":None,
        "description": None,
        "updated_at": None,
    }
    videos_collection.insert_one(video_data)
    
    return {"message": "Video submitted successfully", "video_id": video_id}

@app.get("/transcript/{video_id}")
async def get_transcript(video_id: str):
    video = videos_collection.find_one({"video_id": video_id})
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    
    if video.get("transcript"):
        return {"video_id": video_id, "transcript": video["transcript"]}
    
    formatted_transcript = fetch_transcript(video_id)
    videos_collection.update_one(
        {"video_id": video_id},
        {"$set": {"transcript": formatted_transcript, "updated_at": datetime.utcnow(), "transcript_text": textify(formatted_transcript)}}
    )
    
    return {"video_id": video_id, "transcript": formatted_transcript}

@app.get("/description/{video_id}")

async def get_description(video_id: str):
    video = videos_collection.find_one({"video_id": video_id})
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    
    if video.get("description"):
        return {
            "video_id": video_id,
            "title": video["description"].get("title"),
            "keywords": video["description"].get("keywords", []),  # Ensure keywords is a list
            "category_tags": video["description"].get("category_tags", []),  # Added for consistency
            "detailed_description": video["description"].get("detailed_description"),
            "summary": video["description"].get("summary")
        }
    
    if not video.get("transcript"):
        raise HTTPException(status_code=400, detail="Transcript not available for this video")
    
    description = generate_description(video["transcript"])
    videos_collection.update_one(
        {"video_id": video_id},
        {"$set": {"description": description, "updated_at": datetime.utcnow()}}
    )
    return {
        "video_id": video_id,
        "title": description.get("title"),
        "keywords": description.get("keywords", []),  # Ensure keywords is a list
        "category_tags": description.get("category_tags", []),  # Added for consistency
        "detailed_description": description.get("detailed_description"),
        "summary": description.get("summary")
    }

if __name__ == "__main__":
    uvicorn.run(app, host="localhost", port=8000)