
from pymongo import MongoClient
from pymongo.collection import Collection
from bson.objectid import ObjectId
import uuid
from typing import List, Dict, Optional
from app.core.schema import NotebookDBEntry, NotebookCreate, ChatSessionSummary
from datetime import datetime
from app.core.settings import settings
from app.repositories.user_mongodb_repository import UserMongoDBRepository
from app.repositories.notebook_mongodb_repository import NotebookMongoDBRepository
from app.repositories.chat_mongodb_repository import ChatMongoDBRepository

class NotebookService:

    def __init__(self, user_mongodb_repository: UserMongoDBRepository, notebook_mongodb_repository: NotebookMongoDBRepository,chat_mongodb_repository:ChatMongoDBRepository):
        self.user_mongodb_repository=user_mongodb_repository
        self.notebook_mongodb_repository=notebook_mongodb_repository
        self.chat_mongodb_repository= chat_mongodb_repository

    def create_notebook_service(self,notebook_data: NotebookCreate)->Optional[NotebookDBEntry]:
        try:
            user=self.user_mongodb_repository.find_user_by_id
            (notebook_data.user_id)

            if user is None:
                return None

            notebook=NotebookDBEntry(
                user_id=str(notebook_data.user_id),
                video_id=notebook_data.video_id,
                notebook_title=notebook_data.notebook_title,
                session_id_list=[],
                latest_session_id=None,
                notes_id_list=[],
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )

            created_notebook = self.notebook_mongodb_repository.create_notebook(notebook)

            if created_notebook is None:
                raise RuntimeError("Failed to create notebook in the database.")

            self.user_mongodb_repository.update_notebook_id_list(notebook_data.user_id, str(created_notebook.id))

            return created_notebook
        except Exception as e:
            raise RuntimeError(f"Error occured while creating notebook: {e}")


    def get_user_notebooks(self,user_id:str)->Optional[List[NotebookDBEntry]]:
        user = self.user_mongodb_repository.find_user_by_id(user_id)
        if not user:
            raise RuntimeError("Failed to fetch user details!!!")

        notebook_id_list=user.notebook_id_list
        notebooks = []
        for notebook_id in notebook_id_list:
            notebook_dict=self.notebook_mongodb_repository.find_notebook_by_id(notebook_id)
            notebook=NotebookDBEntry.model_validate(notebook_dict)
            notebooks.append(notebook)

        return notebooks

    def get_single_notebook(self,notebook_id:str):
        notebook=self.notebook_mongodb_repository.find_notebook_by_id(notebook_id)
        if notebook is None:
            return None
        return NotebookDBEntry.model_validate(notebook)

    def get_notebook_chat_sessions_summaries(self,notebook_id:str)->List[ChatSessionSummary]:
        """
    Retrieves summaries of all chat sessions associated with a specific notebook.
    """
        try:
            notebook_dict = self.notebook_mongodb_repository.find_notebook_by_id(
                {"_id": ObjectId(notebook_id)},
            )
            if not notebook_dict:
                raise ValueError(f"cant find notebook with notebooki_id:{notebook_id}")

            session_ids = notebook_dict.session_id_list

            # Call the function from historyChatBotWithStorage to get summaries for these IDs
            summaries = []
            for s_id in session_ids:
                summary = self.chat_mongodb_repository.get_session_summary(s_id)
                if summary:
                    summaries.append(summary)
            # Sort by created_at, most recent first
            summaries.sort(key=lambda x: x["created_at"], reverse=True)

            # Ensure the latest session is explicitly identified or handled by frontend
            # (The frontend will use the latest_session_id from the notebook directly)

            return summaries
        except Exception as e:
            raise


