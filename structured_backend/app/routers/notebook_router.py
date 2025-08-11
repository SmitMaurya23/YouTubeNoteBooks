# app/routers/notebook_router.py
from typing import List
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from app.core.dependencies import get_mongodb_repository
from app.repositories.mongodb_repository import MongoDBRepository
from app.core.schema import NotebookCreate, ChatSessionSummary
from app.core.schema import NotebookModel

router = APIRouter(
    prefix="/notebooks",
    tags=["Notebooks"]
)

@router.post("/")
async def create_notebook_endpoint(
    notebook_data: NotebookCreate,
    mongo_repo: MongoDBRepository = Depends(get_mongodb_repository)
):
    try:
        notebook_id = await mongo_repo.create_notebook(notebook_data)
        return {"message": "Notebook created successfully!", "notebook_id": str(notebook_id)}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create notebook: {e}")

@router.get("/{user_id}", response_model=List[NotebookModel]) # response model added for clarity
async def get_user_notebooks_endpoint(
    user_id: str,
    mongo_repo: MongoDBRepository = Depends(get_mongodb_repository)
):
    try:
        notebooks = await mongo_repo.get_user_notebooks(user_id)
        return {"message": "Notebooks retrieved successfully!", "notebooks": notebooks}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve notebooks: {e}")

@router.get("/{notebook_id}", response_model=NotebookModel)
async def get_single_notebook_endpoint(
    notebook_id: str,
    mongo_repo: MongoDBRepository = Depends(get_mongodb_repository)
):
    try:
        notebook = await mongo_repo.get_single_notebook(notebook_id)
        return {"message": "Notebook retrieved successfully!", "notebook": notebook}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve notebook: {e}")

@router.get("/{notebook_id}/chat_sessions", response_model=List[ChatSessionSummary])
async def get_notebook_chat_sessions_summaries_endpoint(
    notebook_id: str,
    mongo_repo: MongoDBRepository = Depends(get_mongodb_repository)
):
    try:
        summaries = await mongo_repo.get_notebook_chat_sessions_summaries(notebook_id)
        return summaries
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve chat sessions: {e}")