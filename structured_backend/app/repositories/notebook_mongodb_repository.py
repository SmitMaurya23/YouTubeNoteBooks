
from pymongo import MongoClient
from pymongo.collection import Collection
from bson.objectid import ObjectId
import uuid
from typing import List, Dict, Optional
from app.core.schema import ChatMessage, ChatSessionSummary, VideoDescription, VideoDBEntry, NotebookDBEntry, NotebookCreate
from datetime import datetime
from app.core.settings import settings


class NotebookMongoDBRepository:

    def __init__(self, client: MongoClient):
        if(settings.DB_NAME is None):
            raise
        self.db=client[settings.DB_NAME]
        self.notebooks_collection: Collection=self.db["notebooks"]
        print(f"NotebookMongoDBRepository connected to database: {self.db.name}")

    def create_notebook(self,notebook:NotebookDBEntry)->Optional[NotebookDBEntry]:
        try:
            self.notebooks_collection.insert_one(notebook.model_dump(by_alias=True))
            created_notebook = self.notebooks_collection.find_one({"user_id": notebook.user_id}, {"video_id":notebook.video_id})
            if not created_notebook:
                return None
            return NotebookDBEntry.model_validate(created_notebook)
        except Exception as e:
            raise e

    def find_notebook_by_id(self,notebook_id)->NotebookDBEntry:
        notebook_dict = self.notebooks_collection.find_one({"_id": ObjectId(notebook_id)})
        if not notebook_dict:
            raise ValueError(f"Cant find notebook with notebook_id: {notebook_id}")

        notebook=NotebookDBEntry.model_validate(notebook_dict)
        return notebook


