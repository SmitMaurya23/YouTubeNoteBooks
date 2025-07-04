# main.py
import os
from datetime import datetime
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl
from typing import List, Optional, Dict

from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, OperationFailure
from bson import ObjectId  # Add this import

# Import functions from other modules
from Functions.Helpers.utils import extract_video_id, fetch_transcript, textify
from Functions.Helpers.vector_db import embed_and_store_transcript, vector_store
from Functions.genai import generate_description_with_gemini # Renamed for clarity
from Functions.chatBot import get_chatbot_response # Import the chatbot function
from Functions.timeStampDecider import get_timestamps_for_topic

from Functions.historyChatBotWithStorage import (
    create_new_chat_session,
    get_history_chatbot_response_with_storage,
    get_chat_history_from_db,
    get_notebook_chat_sessions_summaries, # NEW Import
    get_chat_session_summary # You might not need to import this directly if get_notebook_chat_sessions_summaries uses it internally
)
# Import the new timestamp decider function


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
# main.py (inside try block where mongo_client and db are initialized)

try:
    mongo_client = MongoClient(MONGO_URI)
    db = mongo_client["youtube_notebook"]
    videos_collection = db["videos"]
    users_collection = db["users"] # New collection for users
    notebooks_collection = db["notebooks"] # New collection for notebooks
    chat_sessions_collection = db["chat_sessions"] # New collection for chat sessions
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

class ChatSessionCreation(BaseModel):
    video_id: Optional[str] = None # Optional: if starting a chat specific to a video
    user_id: str = "1" # Default user_id for now

class ChatQueryWithSession(BaseModel):
    query: str
    session_id: str
    video_id: Optional[str] = None # Optional: to ensure context is maintained
    user_id: str = "1" # Default user_id for now

class TimestampQuery(BaseModel):
    query: str
    video_id: str # Video ID is mandatory for timestamp queries

# main.py (add these to your existing Pydantic models)

class UserCreate(BaseModel):
    user_name: str
    user_email: str
    password: str

class UserLogin(BaseModel):
    user_email: str
    password: str

class NotebookCreate(BaseModel):
    user_id: str
    video_id: str
    notebook_title: str

class NotebookUpdate(BaseModel):
    notebook_title: Optional[str] = None
    # Add other fields if you want to update them later, e.g., notes_id_list

class ChatRequest(BaseModel):
    user_query: str
    video_id: str
    notebook_id: str # NEW: Required to link chat to a notebook
    session_id: Optional[str] = None # Optional for starting a new chat

# --- NEW Pydantic Model for ChatSessionSummary (for API response) ---
class ChatSessionSummary(BaseModel):
    session_id: str
    first_prompt: str
    created_at: str # Storing as ISO string

# Define the model for chat interaction, making session_id optional
class ChatInteraction(BaseModel):
    query: str
    video_id: str
    user_id: str 
    notebook_id: str # The notebook this chat session belongs to
    session_id: Optional[str] = None # THIS IS KEY: session_id is now optional

# Define the response model for chat interactions
class ChatResponse(BaseModel):
    answer: str
    session_id: str # Always return the session_id (new or existing)

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
            "transcript": None, # Raw transcript data (list of dicts with text, start, duration)
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

        print(f"Fetching transcript for {video_id}...")
        transcript_list = fetch_transcript(video_id) # This returns list of dicts with text, start, duration
        transcript_text = textify(transcript_list) # This returns just the concatenated text

        # Generate richer description using the full transcript
        print(f"Generating detailed description for {video_id}...")
        generated_description_data = generate_description_with_gemini(transcript_text)

        # Update MongoDB document with full transcript (list of dicts) and generated description
        videos_collection.update_one(
            {"video_id": video_id},
            {"$set": {
                "transcript": transcript_list, # Store full transcript object (list of dicts)
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
            # Pass the transcript_list (list of dicts) to embed_and_store_transcript
            embed_and_store_transcript(video_id, transcript_list)
        else:
            print("Warning: Vector store not initialized. Transcript not embedded.")
            raise HTTPException(status_code=500, detail="Vector database not available for embedding.")

        return {"message": f"Video {video_id} submitted. Transcript processing, Video embedding and Description Generation is done.", "video_id": video_id}
    except Exception as e:
        print(f"Error submitting video: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to submit video: {e}")

@app.get("/transcript/{video_id}")
async def get_transcript_endpoint(video_id: str):
    """
    Fetches the transcript for a given video ID.
    """
    video_doc = videos_collection.find_one({"video_id": video_id})

    if not video_doc:
        raise HTTPException(status_code=404, detail="Video not found.")

    if video_doc.get("transcript_text") and video_doc.get("transcript"):
        print(f"Transcript already exists for {video_id}.")
        return {"video_id": video_id, "transcript_text": video_doc["transcript_text"]}
    else:
        print(f"Transcript not found for {video_id}.")
        raise HTTPException(status_code=404, detail="Transcript not available for this video.")

@app.get("/video_details/{video_id}")
async def get_video_details_endpoint(video_id: str):
    """
    Retrieves all stored details for a specific video.
    """
    video_doc = videos_collection.find_one({"video_id": video_id})
    if not video_doc:
        raise HTTPException(status_code=404, detail="Video details not found.")

    # Convert ObjectId to string for JSON serialization
    video_doc["_id"] = str(video_doc["_id"])

    # Use dictionary key access and safer checks
    description_data = video_doc.get("description")
    if description_data:
        title = description_data.get("title")
        if title in ["Unknown Error", "Parsing Error", "Error: Model Not Initialized", "API Error"] or not title:
            print(f"Fetching transcript for {video_id}...")
            transcript_list = fetch_transcript(video_id) # This returns list of dicts with text, start, duration
            transcript_text = textify(transcript_list)
            print(f"Generating detailed description for {video_id}...")
            generated_description_data = generate_description_with_gemini(transcript_text)

            # Update MongoDB document with full transcript (list of dicts) and generated description
            videos_collection.update_one(
                {"video_id": video_id},
                {"$set": {
                    "transcript": transcript_list, # Store full transcript object (list of dicts)
                    "transcript_text": transcript_text,
                    "description.title": generated_description_data.get("title"),
                    "description.keywords": generated_description_data.get("keywords", []),
                    "description.category_tags": generated_description_data.get("category_tags", []),
                    "description.detailed_description": generated_description_data.get("detailed_description"),
                    "description.summary": generated_description_data.get("summary"),
                    "updated_at": datetime.utcnow()
                }}
            )
            # Re-fetch the updated document to ensure the client gets the latest data
            video_doc = videos_collection.find_one({"video_id": video_id})
            if video_doc:
                video_doc["_id"] = str(video_doc["_id"]) # Convert again after re-fetching
            else:
                raise HTTPException(status_code=404, detail="Video details not found after update.")
    else:
        pass # For now, we'll just return the existing doc without modification

    return video_doc


@app.post("/chatOnce")
async def chatOnce_endpoint(chat_query: ChatQuery):
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

@app.get("/chat/history/{session_id}")
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

@app.post("/get_timestamps")
async def get_timestamps_endpoint(timestamp_query: TimestampQuery):
    """
    Endpoint to retrieve timestamps for a specific topic in a video.
    """
    try:
        timestamps = await get_timestamps_for_topic(
            query_text=timestamp_query.query,
            video_id=timestamp_query.video_id
        )
        if not timestamps:
            return {"message": "No relevant timestamps found for your query.", "timestamps": []}
        return {"message": "Timestamps retrieved successfully.", "timestamps": timestamps}
    except Exception as e:
        print(f"Error in get_timestamps endpoint: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve timestamps: {e}")

# main.py (add these new endpoints)

@app.post("/signup")
async def signup_endpoint(user_data: UserCreate):
    """
    Registers a new user.
    """
    if users_collection.find_one({"user_email": user_data.user_email}):
        raise HTTPException(status_code=400, detail="User with this email already exists.")

    # In a real application, hash the password before storing
    hashed_password = user_data.password # Placeholder: Use bcrypt in production

    user_doc = {
        "user_name": user_data.user_name,
        "user_email": user_data.user_email,
        "password": hashed_password, # Store hashed password
        "notebook_id_list": [],
        "created_at": datetime.utcnow(),
    }
    users_collection.insert_one(user_doc)
    return {"message": "User registered successfully!", "user_id": str(user_doc["_id"])}

@app.post("/login")
async def login_endpoint(user_data: UserLogin):
    """
    Logs in a user.
    """
    user_doc = users_collection.find_one({"user_email": user_data.user_email})

    if not user_doc or user_doc["password"] != user_data.password: # Placeholder: Compare with hashed password
        raise HTTPException(status_code=401, detail="Invalid credentials.")

    return {"message": "Login successful!", "user_id": str(user_doc["_id"]), "user_name": user_doc["user_name"]}
# This block ensures the FastAPI app runs when the script is executed directly
# main.py (add these new endpoints)

@app.post("/notebooks")
async def create_notebook_endpoint(notebook_data: NotebookCreate):
    """
    Creates a new notebook for a user.
    """
    user_doc = users_collection.find_one({"_id": ObjectId(notebook_data.user_id)}) # Import ObjectId from bson
    if not user_doc:
        raise HTTPException(status_code=404, detail="User not found.")

    notebook_doc = {
        "user_id": notebook_data.user_id,
        "video_id": notebook_data.video_id,
        "notebook_title": notebook_data.notebook_title,
        "session_id_list": [],
        "latest_session_id": None,
        "notes_id_list": [],
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }
    inserted_notebook = notebooks_collection.insert_one(notebook_doc)
    notebook_id = str(inserted_notebook.inserted_id)

    # Update the user's notebook_id_list
    users_collection.update_one(
        {"_id": ObjectId(notebook_data.user_id)},
        {"$push": {"notebook_id_list": notebook_id}}
    )

    return {"message": "Notebook created successfully!", "notebook_id": notebook_id}

@app.get("/notebooks/{user_id}")
async def get_user_notebooks_endpoint(user_id: str):
    """
    Retrieves all notebooks for a given user ID.
    """
    user_doc = users_collection.find_one({"_id": ObjectId(user_id)})
    if not user_doc:
        raise HTTPException(status_code=404, detail="User not found.")

    notebooks_cursor = notebooks_collection.find({"user_id": user_id}).sort("created_at", -1)
    notebooks = []
    for notebook in notebooks_cursor:
        notebook["_id"] = str(notebook["_id"]) # Convert ObjectId to string
        notebooks.append(notebook)
    return {"message": "Notebooks retrieved successfully!", "notebooks": notebooks}

@app.get("/notebook/{notebook_id}")
async def get_single_notebook_endpoint(notebook_id: str):
    """
    Retrieves a single notebook by its ID.
    """
    notebook_doc = notebooks_collection.find_one({"_id": ObjectId(notebook_id)})
    if not notebook_doc:
        raise HTTPException(status_code=404, detail="Notebook not found.")
    notebook_doc["_id"] = str(notebook_doc["_id"])
    return {"message": "Notebook retrieved successfully!", "notebook": notebook_doc}

@app.get("/notebook/{notebook_id}/chat_sessions", response_model=List[ChatSessionSummary]) # Specify response model
async def get_notebook_chat_sessions_summaries_endpoint(notebook_id: str):
    """
    Retrieves summaries of all chat sessions associated with a specific notebook.
    """
    try:
        notebook_doc = notebooks_collection.find_one(
            {"_id": ObjectId(notebook_id)},
            {"session_id_list": 1, "latest_session_id": 1} # Fetch session_id_list and latest_session_id
        )
        if not notebook_doc:
            raise HTTPException(status_code=404, detail="Notebook not found.")

        session_ids_in_notebook = notebook_doc.get("session_id_list", [])
        
        # Call the function from historyChatBotWithStorage to get summaries for these IDs
        summaries = get_notebook_chat_sessions_summaries(session_ids_in_notebook)

        # Ensure the latest session is explicitly identified or handled by frontend
        # (The frontend will use the latest_session_id from the notebook directly)
        
        return summaries
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error getting chat session summaries for notebook {notebook_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve chat sessions: {e}")
    


@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(chat_interaction: ChatInteraction):
    try:
        current_session_id = chat_interaction.session_id

        if not current_session_id:
            # If no session_id is provided, create a new one
            print(f"Creating new chat session for notebook: {chat_interaction.notebook_id}")
            new_session_id = create_new_chat_session(
                video_id=chat_interaction.video_id,
                user_id=chat_interaction.user_id,
                notebook_id=chat_interaction.notebook_id,# Pass notebook_id to link
                first_user_prompt=chat_interaction.query
            )
            current_session_id = new_session_id
            print(f"New session created with ID: {current_session_id}")
        
        # CORRECTED LINE HERE: Unpack the tuple returned by get_history_chatbot_response_with_storage
        ai_response_text, _ = get_history_chatbot_response_with_storage(
            query_text=chat_interaction.query,
            session_id=current_session_id,
            user_id=chat_interaction.user_id,
            target_video_id=chat_interaction.video_id
        )

        # Use the unpacked ai_response_text for the 'answer' field
        return {"answer": ai_response_text, "session_id": current_session_id}

    except Exception as e:
        print(f"Error in chat_endpoint: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get chat response: {e}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="localhost", port=8000)


