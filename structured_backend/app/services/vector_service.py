
from app.repositories.vector_repository import VectorRepository
from app.services.transcript_processing_service import TranscriptProcessingService
from typing import List,Dict
from langchain_core.documents import Document



class VectorService:
    """
    Contains the business logic for processing transcripts and interacting with the vector database.
    This class orchestrates the chunking, timestamp aggregation, and storage process.
    """

    def __init__(self, vector_repository: VectorRepository, transcript_processing_service: TranscriptProcessingService):
        self.vector_repository=vector_repository
        self.transcript_processing_service=transcript_processing_service


    async def embed_and_store_transcript(self, video_id: str,transcript_list: List[Dict])->bool:
        """
        Chunks the transcript, aggregates timestamps, and stores the documents via the repository.
        """
        if not transcript_list:
            print(f"No transcipt list provided for video ID:{video_id}.Skipping embedding.")
            return False

        print(f"Preparing chunks for video_id:{video_id}. ")

        final_documents_for_embedding=self.transcript_processing_service.process_transcript_to_documents(video_id=video_id,transcript_list=transcript_list)

        if final_documents_for_embedding:
            try:
                self.vector_repository.add_documents_list(documents=final_documents_for_embedding)
                return True
            except Exception:
                return False

        return False

