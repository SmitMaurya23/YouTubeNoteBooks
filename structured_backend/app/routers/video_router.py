# app/routers/video_router.py
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, HttpUrl
from app.core.dependencies import get_youtube_service, get_vector_service, get_genai_service, get_mongodb_repository
from app.services.youtube_service import YouTubeService
from app.services.vector_service import VectorService
from app.services.genai_service import GenAIService
from app.repositories.mongodb_repository import MongoDBRepository

router = APIRouter(
    prefix="/videos",
    tags=["Videos"]
)

# Pydantic models specific to this router can be defined here or in a schemas file
class VideoSubmission(BaseModel):
    url: HttpUrl

@router.post("/submit-video")
async def submit_video_endpoint(
    video_submission: VideoSubmission,
    youtube_service: YouTubeService = Depends(get_youtube_service),
    vector_service: VectorService = Depends(get_vector_service),
    genai_service: GenAIService = Depends(get_genai_service),
    mongo_repo: MongoDBRepository = Depends(get_mongodb_repository)
):
    try:
        video_id = await youtube_service.extract_video_id(str(video_submission.url))
        if not video_id:
            raise HTTPException(status_code=400, detail="Invalid YouTube URL")

        if await mongo_repo.get_video(video_id):
            return {"message": f"Video with ID {video_id} was already submitted.", "video_id": video_id}

        initial_description = await genai_service.generate_video_description(
            "Provide a very brief, generic summary for a YouTube video. Keep it under 2 sentences."
        )
        await mongo_repo.create_video_placeholder(video_id, str(video_submission.url), initial_description)

        transcript_list = await youtube_service.fetch_transcript(video_id)
        transcript_text = youtube_service.textify(transcript_list)
        generated_description = await genai_service.generate_video_description(transcript_text)
        await mongo_repo.update_video_details(
            video_id, transcript_list, transcript_text, generated_description
        )

        await vector_service.embed_and_store_transcript(video_id, transcript_list)

        return {"message": f"Video {video_id} submitted and processed successfully.", "video_id": video_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to submit video: {e}")

@router.get("/transcript/{video_id}")
async def get_transcript_endpoint(
    video_id: str,
    mongo_repo: MongoDBRepository = Depends(get_mongodb_repository)
):
    transcript_text = await mongo_repo.get_video_transcript(video_id)
    if not transcript_text:
        raise HTTPException(status_code=404, detail="Transcript not available for this video.")
    return {"video_id": video_id, "transcript_text": transcript_text}

@router.get("/video_details/{video_id}")
async def get_video_details_endpoint(
    video_id: str,
    mongo_repo: MongoDBRepository = Depends(get_mongodb_repository),
    youtube_service: YouTubeService = Depends(get_youtube_service),
    genai_service: GenAIService = Depends(get_genai_service),
    vector_service: VectorService = Depends(get_vector_service)
):
    video_doc = await mongo_repo.get_video(video_id)
    if not video_doc:
        raise HTTPException(status_code=404, detail="Video details not found.")

    title = video_doc.get("description", {}).get("title")
    if not title or title in ["Unknown Error", "Parsing Error", "Error: Model Not Initialized", "API Error"]:
        transcript_list = await youtube_service.fetch_transcript(video_id)
        transcript_text = youtube_service.textify(transcript_list)
        generated_description = await genai_service.generate_video_description(transcript_text)
        await mongo_repo.update_video_details(
            video_id, transcript_list, transcript_text, generated_description
        )
        video_doc = await mongo_repo.get_video(video_id)
        if not video_doc:
            raise HTTPException(status_code=404, detail="Video details not found after update.")

    video_doc["_id"] = str(video_doc["_id"])
    return video_doc