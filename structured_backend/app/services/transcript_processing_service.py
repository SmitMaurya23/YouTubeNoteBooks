
from langchain.text_splitter import RecursiveCharacterTextSplitter
from app.core.schema import TranscriptEntry
from typing import List, Dict
from langchain_core.documents import Document


class TranscriptProcessingService:
    """
    Handles the business logic for converting a raw transcript into a list of LanChain Document objects with aggregates timestamps.
    """

    def __init__(self):
         self.text_splitter= RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,
            is_separator_regex=False,
        )

    def process_transcript_to_documents(self, video_id: str, transcript_list: List[Dict])->List[Document]:

        """
        Takes a raw transcript list and returns a list of context-rich documents
        with aggregated timestamps.
        """

        final_documents_for_embedding=[]
        full_transcript_text=""
        original_segments_info=[]
        current_char_index=0

        for entry in transcript_list:
            segment_text=entry.get("text","")
            segment_start=entry.get("start",0.0)
            segment_duration=entry.get("duration",0.0)
            segment_end=segment_start + segment_duration

            original_segments_info.append(
                (segment_text, segment_start, segment_end, current_char_index, current_char_index+len(segment_text))
            )
            full_transcript_text+=segment_text+" "
            current_char_index+=len(segment_text)+1

        text_chunks=self.text_splitter.split_text(full_transcript_text)



        for chunk_content in text_chunks:
            try:
                chunk_char_start=full_transcript_text.index(chunk_content)
                chunk_char_end=chunk_char_start+len(chunk_content)
            except ValueError:
                print(f"Warning: Could not find chunk content in full transcript. Skipping chunk: {chunk_content[:50]}...")
                continue

            min_start_time=float('inf')
            max_end_time=float('-inf')
            found_overlap=False

            for _, original_start, original_end, original_char_start, original_char_end in original_segments_info:
                if(max(chunk_char_start, original_char_start)<min(chunk_char_end,original_char_end)):
                    min_start_time=min(min_start_time, original_start)
                    max_end_time=max(max_end_time,original_end)
                    found_overlap=True

            if found_overlap and min_start_time !=float('inf') and max_end_time != float('-inf'):

                doc=Document(
                    page_content=chunk_content,
                    metadata={
                        "video_id": video_id,
                        "source":F"youtube_transcript_{video_id}",
                        "start": min_start_time,
                        "end":max_end_time,
                        "duration":max_end_time-min_start_time
                    }
                )
                final_documents_for_embedding.append(doc)
            else:
                print(f"Warning: No timestamp overlap found for chunk: {chunk_content[:50]}...Skipping.")


        return final_documents_for_embedding



