
from pymongo import MongoClient
from pymongo.collection import Collection
from bson.objectid import ObjectId
import uuid
from typing import List, Dict, Optional
from app.core.schema import ChatMessage, ChatSessionSummary, VideoDescription, VideoDBEntry
from datetime import datetime
from app.core.settings import settings

class VideoMongoDBRepository:

    def __init__(self, client: MongoClient):
        if(settings.DB_NAME is None):
            raise
        self.db=client[settings.DB_NAME]
        self.videos_collection: Collection=self.db["videos"]
        print(f"VideoMongoDBRepository connected to database: {self.db.name}")

    def get_video(self,video_id:str)->VideoDBEntry:

        try:
            video=self.videos_collection.find_one({"video_id":video_id})
            if not video:
                raise ValueError("Video not found!!!")
            return VideoDBEntry.model_validate(video)
        except Exception as e:
            raise


    def add_video_details(self,video_db_entry: VideoDBEntry):
        try:
            self.videos_collection.insert_one(video_db_entry.model_dump(by_alias=True))
        except Exception as e:
            raise


