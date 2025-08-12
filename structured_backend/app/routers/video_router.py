# app/routers/video_router.py
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, HttpUrl
from app.core.dependencies import get_youtube_service, get_vector_service, get_genai_service, get_video_mongodb_repository
from app.services.youtube_service import YouTubeService
from app.services.vector_service import VectorService
from app.services.genai_service import GenAIService
from app.repositories.video_mongodb_repository import VideoMongoDBRepository
from app.core.schema import VideoDBEntry, VideoSubmission
from datetime import datetime

router = APIRouter(
    prefix="/videos",
    tags=["Videos"]
)


@router.post("/submit-video")
async def submit_video_endpoint(
    video_submission: VideoSubmission,
    youtube_service: YouTubeService = Depends(get_youtube_service),
    vector_service: VectorService = Depends(get_vector_service),
    genai_service: GenAIService = Depends(get_genai_service),
    video_mongo_repo: VideoMongoDBRepository = Depends(get_video_mongodb_repository)
):
    url=(str(video_submission.url))
    try:
        video_id = youtube_service.extract_video_id(url)
        if not video_id:
            raise HTTPException(status_code=400, detail="Invalid YouTube URL")

        if video_mongo_repo.get_video(video_id):
            return {"message": f"Video with ID {video_id} was already submitted.", "video_id": video_id}

        transcript_list = youtube_service.fetch_transcript(video_id)
        transcript_text = youtube_service.textify(transcript_list)
        generated_description = await genai_service.generate_video_description(transcript_text)

        video_db_entry=VideoDBEntry(
            video_id= video_id,
            url=url,
            submitted_at=datetime.utcnow(),
            transcript= transcript_list,
            transcript_text=transcript_text,
            description= generated_description,
            updated_at= datetime.utcnow()
        )

        video_mongo_repo.add_video_details(video_db_entry)

        vector_service.embed_and_store_transcript(video_id, transcript_list)

        return {"message": f"Video {video_id} submitted. Transcript processing, Video embedding and Description Generation is done.", "video_id": video_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to submit video: {e}")



@router.get("/video_details/{video_id}")
async def get_video_details_endpoint(
    video_id: str,
    video_mongo_repo: VideoMongoDBRepository = Depends(get_video_mongodb_repository),
    youtube_service: YouTubeService = Depends(get_youtube_service),
    genai_service: GenAIService = Depends(get_genai_service),
    vector_service: VectorService = Depends(get_vector_service)
):
    video_db_entry= video_mongo_repo.get_video(video_id)
    if not video_db_entry:
        raise HTTPException(status_code=404, detail="Video details not found.")
    # Convert ObjectId to string else error will occur
    return video_db_entry