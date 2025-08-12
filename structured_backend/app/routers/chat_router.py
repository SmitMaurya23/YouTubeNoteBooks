# app/routers/chat_router.py
from fastapi import APIRouter, HTTPException, Depends
from typing import Optional
from app.core.dependencies import get_basic_rag_service, get_persistant_chat_rag_service,get_timestamp_service, get_chat_mongodb_repository
from app.services.rag_service import BasicRAGService
from app.services.persistant_chat_rag_service import PersistentChatRAGService
from app.services.timestamp_service import TimestampService
from app.repositories.chat_mongodb_repository import ChatMongoDBRepository
from app.core.schema import ChatQuery, ChatInteraction, ChatResponse, TimestampQuery

router = APIRouter(
    prefix="/chat",
    tags=["Chat"]
)

@router.post("/once")
async def chat_once_endpoint(
    chat_query: ChatQuery,
    rag_service: BasicRAGService = Depends(get_basic_rag_service)
):
    try:
        response_text = await rag_service.get_response(
            query_text=chat_query.query,
            video_id=chat_query.video_id
        )
        return {"answer": response_text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {e}")

@router.post("/")
async def chat_endpoint(
    chat_interaction: ChatInteraction,
    persistent_chat_service: PersistentChatRAGService = Depends(get_persistant_chat_rag_service)
):
    try:
        response, session_id = await persistent_chat_service.get_response_with_storage(
            query_text=chat_interaction.query,
            session_id=chat_interaction.session_id,
            user_id=chat_interaction.user_id,
           # notebook_id=chat_interaction.notebook_id,
            video_id=chat_interaction.video_id
        )
        return {"answer": response, "session_id": session_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get chat response: {e}")

@router.get("/history/{session_id}")
async def get_chat_session_history_endpoint(
    session_id: str,
    chat_mongo_repo: ChatMongoDBRepository = Depends(get_chat_mongodb_repository)
):
    try:
        history = await chat_mongo_repo.get_chat_history(session_id)
        if not history:
            raise HTTPException(status_code=404, detail="Chat session or history not found.")
        return {"session_id": session_id, "history": history}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve chat history: {e}")

@router.post("/get_timestamps")
async def get_timestamps_endpoint(
    timestamp_query: TimestampQuery,
    timestamp_service: TimestampService = Depends(get_timestamp_service)
):
    try:
        timestamps = await timestamp_service.get_timestamps_for_query(
            query_text=timestamp_query.query,
            video_id=timestamp_query.video_id
        )
        return {"message": "Timestamps retrieved successfully.", "timestamps": timestamps}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve timestamps: {e}")