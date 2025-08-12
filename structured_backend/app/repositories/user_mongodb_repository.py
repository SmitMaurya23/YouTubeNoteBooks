
from pymongo import MongoClient
from pymongo.collection import Collection
from bson.objectid import ObjectId
import uuid
from typing import List, Dict, Optional
from app.core.schema import UserCreate, UserLogin, UserDBEntry
from datetime import datetime
from app.core.settings import settings
from bson import ObjectId

class UserMongoDBRepository:

    def __init__(self, client: MongoClient):
        if(settings.DB_NAME is None):
            raise
        self.db=client[settings.DB_NAME]
        self.users_collection: Collection=self.db["users"]
        print(f"UserMongoDBRepository connected to database: {self.db.name}")



    def create_user(self, user_create: UserCreate) -> UserDBEntry:
        hashed_password = user_create.password

        user_db_entry = UserDBEntry(
            user_name=user_create.user_name,
            user_email=user_create.user_email,
            password=hashed_password,
            notebook_id_list=[],
            created_at=datetime.utcnow()
        )

        try:
            self.users_collection.insert_one(user_db_entry.model_dump(by_alias=True))
            created_user = self.users_collection.find_one({"user_email": user_db_entry.user_email})
            if not created_user:
                raise ValueError("User creation failed or user not found.")
            return UserDBEntry.model_validate(created_user)
        except Exception as e:
            raise e



    def authenticate_user(self, user_login: UserLogin) -> Optional[UserDBEntry]:
        try:
            user_doc = self.users_collection.find_one({"user_email": user_login.user_email})

            if not user_doc:
                return None

            stored_hashed_pw = user_doc.get("password")

            if user_login.password==stored_hashed_pw:
                return UserDBEntry.model_validate(user_doc)
            else:
                return None

        except Exception as e:
            raise e

    def find_user_by_email(self, user_email: str)->Optional[UserDBEntry]:
        try:
            user_doc = self.users_collection.find_one({"user_email": user_email})

            if not user_doc:
                return None

            return UserDBEntry.model_validate(user_doc)

        except Exception as e:
            raise e

    def find_user_by_id(self, user_id:str)->Optional[UserDBEntry]:
        try:
            user_doc = self. users_collection.find_one({"_id": ObjectId(user_id)})

            if not user_doc:
                return None

            return UserDBEntry.model_validate(user_doc)

        except Exception as e:
            raise e

    def update_notebook_id_list(self, user_id:str, notebook_id:str):

        try:
            self.users_collection.update_one({"_id": ObjectId(user_id)},{"$push": {"notebook_id_list": notebook_id}})

        except Exception as e:
            raise e




