# app/routers/notebook_router.py
from typing import List
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from app.core.dependencies import get_notebook_mongodb_repository, get_notebook_service
from app.repositories.notebook_mongodb_repository import NotebookMongoDBRepository
from app.core.schema import NotebookCreate, ChatSessionSummary, NotebookDBEntry
from app.services.notebook_service import NotebookService

router = APIRouter(
    prefix="/notebooks",
    tags=["Notebooks"]
)

@router.post("/")
async def create_notebook_endpoint(
    notebook_create: NotebookCreate,
    notebook_servce: NotebookService = Depends(get_notebook_service)
):
    try:
        notebook_db_entry= notebook_servce.create_notebook_service(notebook_create)
        if not notebook_db_entry:
            raise HTTPException(status_code=404, detail=f"Failed to create notebook")
        return {"message": "Notebook created successfully!", "notebook_id": str(notebook_db_entry.id)}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create notebook: {e}")




@router.get("/{user_id}")
async def get_user_notebooks_endpoint(
    user_id: str,
    notebook_service: NotebookService = Depends(get_notebook_service)
):
    try:
        notebooks = notebook_service.get_user_notebooks(user_id)
        return {"message": "Notebooks retrieved successfully!", "notebooks": notebooks}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve notebooks: {e}")


@router.get("/{notebook_id}")
async def get_single_notebook_endpoint(
    notebook_id: str,
    notebook_mongo_repo: NotebookMongoDBRepository = Depends(get_notebook_mongodb_repository)
):
    try:
        notebook = notebook_mongo_repo.find_notebook_by_id(notebook_id)
        return {"message": "Notebook retrieved successfully!", "notebook": notebook}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve notebook: {e}")

@router.get("/{notebook_id}/chat_sessions")
async def get_notebook_chat_sessions_summaries_endpoint(
    notebook_id: str,
    notebook_servce: NotebookService = Depends(get_notebook_service)
):
    try:
        summaries = notebook_servce.get_notebook_chat_sessions_summaries(notebook_id)
        return summaries
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve chat sessions: {e}")