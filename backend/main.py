# main.py
import os
from datetime import datetime
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl
from typing import List, Optional

from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, OperationFailure

# Import functions from other modules
from utils import extract_video_id, fetch_transcript, textify
from genai import generate_description_with_gemini # Renamed for clarity
from vector_db import embed_and_store_transcript, vector_store # Import both
from chatBot import get_chatbot_response # Import the chatbot function

from historyChatBotWithStorage import (
    create_new_chat_session,
    get_history_chatbot_response_with_storage,
    get_chat_history_from_db # For retrieving full history if needed by frontend
)

load_dotenv()

app = FastAPI()

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"], # Adjust as needed for your frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Environment Variables ---
MONGO_URI = os.getenv("MONGODB_URI")
GOOGLE_CLOUD_PROJECT = os.getenv("GOOGLE_CLOUD_PROJECT")
GOOGLE_CLOUD_LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")

if not MONGO_URI:
    raise ValueError("MONGODB_URI not set in .env file.")
if not GOOGLE_CLOUD_PROJECT:
    raise ValueError("GOOGLE_CLOUD_PROJECT not set in .env file.")

# --- MongoDB Connection ---
try:
    mongo_client = MongoClient(MONGO_URI)
    db = mongo_client["youtube_notebook"]
    videos_collection = db["videos"] # Collection to store video metadata and full transcripts
    print(f"Connected to MongoDB database: {db.name}")
except (ConnectionFailure, OperationFailure) as e:
    print(f"MongoDB connection failed: {e}")
    raise HTTPException(status_code=500, detail="Database connection failed.")


# --- Pydantic Models for Request Bodies ---
class VideoSubmission(BaseModel):
    url: HttpUrl

class ChatQuery(BaseModel):
    query: str
    video_id: Optional[str] = None # Optional: if you want to limit search to a specific video

# --- FastAPI Endpoints ---

@app.get("/")
async def read_root():
    """Root endpoint for the YouTube Notebot API."""
    return {"message": "Welcome to the YouTube Notebot API!"}

@app.post("/submit-video")
async def submit_video_endpoint(video_submission: VideoSubmission):
    """
    Submits a YouTube video URL for processing.
    Creates a placeholder in MongoDB.
    """
    try:
        video_id = extract_video_id(str(video_submission.url))
        if not video_id:
            raise HTTPException(status_code=400, detail="Invalid YouTube URL")

        if videos_collection.find_one({"video_id": video_id}):
             return {"message": f"Video with ID {video_id} was already submitted.", "video_id": video_id}

        # Generate an initial brief summary using Gemini for immediate feedback
        # This will be replaced by a more detailed description after transcript processing
        initial_description_summary_data = generate_description_with_gemini(
            "Provide a very brief, generic summary for a YouTube video. Keep it under 2 sentences."
        )

        video_data = {
            "video_id": video_id,
            "url": str(video_submission.url),
            "submitted_at": datetime.utcnow(),
            "transcript": None, # Raw transcript data
            "transcript_text": None, # Plain text transcript
            "description": { # Placeholder, will be updated with detailed description
                "title": None,
                "keywords": [],
                "category_tags": [],
                "detailed_description": None,
                "summary": initial_description_summary_data.get("summary", "No summary available yet.")
            },
            "updated_at": None,
        }
        videos_collection.insert_one(video_data)
        print(f"Video {video_id} submitted and placeholder created.")
        return {"message": f"Video {video_id} submitted. Transcript processing will begin upon request.", "video_id": video_id}
    except Exception as e:
        print(f"Error submitting video: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to submit video: {e}")

@app.get("/transcript/{video_id}")
async def get_transcript_endpoint(video_id: str):
    """
    Fetches, processes, and stores the transcript for a given video ID.
    Also triggers detailed description generation and embedding.
    """
    video_doc = videos_collection.find_one({"video_id": video_id})

    if not video_doc:
        raise HTTPException(status_code=404, detail="Video not found.")

    # If transcript_text exists, return it. Check if embeddings are also present.
    if video_doc.get("transcript_text"):
        print(f"Transcript already exists for {video_id}.")
        # Basic check to see if any chunk for this video_id exists in the embeddings collection
        # This helps re-embed if the embeddings collection was cleared or not populated previously
        if vector_store and not vector_store.collection.find_one({"video_id": video_id}):
             print(f"Re-embedding existing transcript for {video_id} as it's not in vector store.")
             embed_and_store_transcript(video_id, video_doc["transcript_text"])
        return {"video_id": video_id, "transcript_text": video_doc["transcript_text"]}

    # If transcript_text does not exist, fetch and process it
    try:
        print(f"Fetching transcript for {video_id}...")
        transcript_list = fetch_transcript(video_id)
        transcript_text = textify(transcript_list)

        # Generate richer description using the full transcript
        print(f"Generating detailed description for {video_id}...")
        generated_description_data = generate_description_with_gemini(transcript_text)

        # Update MongoDB document with full transcript and generated description
        videos_collection.update_one(
            {"video_id": video_id},
            {"$set": {
                "transcript": transcript_list, # Store full transcript object if needed
                "transcript_text": transcript_text,
                "description.title": generated_description_data.get("title"),
                "description.keywords": generated_description_data.get("keywords", []),
                "description.category_tags": generated_description_data.get("category_tags", []),
                "description.detailed_description": generated_description_data.get("detailed_description"),
                "description.summary": generated_description_data.get("summary"),
                "updated_at": datetime.utcnow()
            }}
        )
        print(f"Transcript and description updated for video {video_id}.")

        # --- Trigger Embedding and Storage in Vector DB ---
        if vector_store: # Ensure vector_store is initialized
            print(f"Embedding and storing transcript for {video_id} in vector database...")
            embed_and_store_transcript(video_id, transcript_text)
        else:
            print("Warning: Vector store not initialized. Transcript not embedded.")
            raise HTTPException(status_code=500, detail="Vector database not available for embedding.")

        return {"video_id": video_id, "transcript_text": transcript_text}
    except Exception as e:
        print(f"Error fetching or processing transcript for {video_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch or process transcript: {e}")

@app.get("/video_details/{video_id}")
async def get_video_details_endpoint(video_id: str):
    """
    Retrieves all stored details for a specific video.
    """
    video_doc = videos_collection.find_one({"video_id": video_id})
    if not video_doc:
        raise HTTPException(status_code=404, detail="Video details not found.")
    # Remove _id field for cleaner JSON response
    video_doc.pop("_id", None)
    return video_doc

@app.post("/chatOnce")
async def chat_endpoint(chat_query: ChatQuery):
    """
    Endpoint for chatbot interaction.
    Delegates to the get_chatbot_response function in chatBot.py.
    """
    try:
        response_text = get_chatbot_response(chat_query.query, chat_query.video_id)
        if "Error:" in response_text: # Simple check for errors returned by chatbot function
            raise HTTPException(status_code=500, detail=response_text)
        return {"answer": response_text}
    except HTTPException: # Re-raise FastAPI HTTPExceptions
        raise
    except Exception as e:
        print(f"Error in chat endpoint: {e}")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred during chat: {e}")



class ChatSessionCreation(BaseModel):
    video_id: Optional[str] = None # Optional: if starting a chat specific to a video
    user_id: str = "1" # Default user_id for now

class ChatQueryWithSession(BaseModel):
    query: str
    session_id: str
    video_id: Optional[str] = None # Optional: to ensure context is maintained
    user_id: str = "1" # Default user_id for now


# --- Add these FastAPI Endpoints to main.py ---

@app.post("/chat/start_session")
async def start_chat_session_endpoint(session_creation: ChatSessionCreation):
    """
    Endpoint to start a new chat session.
    Returns a new session_id.
    """
    try:
        session_id = create_new_chat_session(
            user_id=session_creation.user_id,
            video_id=session_creation.video_id
        )
        return {"session_id": session_id, "message": "New chat session started."}
    except Exception as e:
        print(f"Error starting chat session: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to start chat session: {e}")

@app.post("/chat/{session_id}")
async def chat_with_session_endpoint(session_id: str, chat_query: ChatQueryWithSession):
    """
    Endpoint for chatbot interaction with persistent history.
    Uses the provided session_id to retrieve and update chat history.
    """
    if session_id != chat_query.session_id:
        raise HTTPException(status_code=400, detail="Session ID in path does not match body.")

    try:
        response_text = get_history_chatbot_response_with_storage(
            query_text=chat_query.query,
            session_id=session_id,
            user_id=chat_query.user_id,
            target_video_id=chat_query.video_id
        )
        if "Error:" in response_text: # Simple check for errors returned by chatbot function
            raise HTTPException(status_code=500, detail=response_text)
        return {"answer": response_text}
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in chat with session endpoint: {e}")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred during chat: {e}")

@app.get("/chat/{session_id}/history")
async def get_chat_session_history_endpoint(session_id: str):
    """
    Retrieves the full chat history for a given session_id.
    """
    try:
        history = get_chat_history_from_db(session_id)
        if not history:
            raise HTTPException(status_code=404, detail="Chat session or history not found.")
        return {"session_id": session_id, "history": history}
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error retrieving chat history: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve chat history: {e}")

# This block ensures the FastAPI app runs when the script is executed directly
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="localhost", port=8000)

