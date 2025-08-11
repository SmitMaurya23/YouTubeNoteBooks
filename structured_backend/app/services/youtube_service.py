from fastapi import HTTPException
from youtube_transcript_api._api import YouTubeTranscriptApi
from urllib.parse import urlparse, parse_qs


class YouTubeService:
    async def extract_video_id(self,url: str) -> str:
        """Extract YouTube video ID from URL."""
        parsed_url = urlparse(url)
        if parsed_url.hostname in ("www.youtube.com", "youtube.com"):
            query = parse_qs(parsed_url.query)
            video_id = query.get("v", [None])[0]
            return video_id if video_id is not None else ""
        elif parsed_url.hostname == "youtu.be":
            return parsed_url.path.lstrip("/")
        return ""

    async def fetch_transcript(self,video_id: str) -> list:
        """Fetch and format transcript from YouTube."""
        try:
            transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=["en-GB", "en-IN", "en-CA", "en-AU", "en"])
            return [{"text": entry["text"], "start": entry["start"], "duration": entry["duration"]} for entry in transcript]
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error fetching transcript: {str(e)}")

    def textify(self, transcript: list) -> str:
        """Convert transcript list to a single text string."""
        return " ".join(entry["text"] for entry in transcript if "text" in entry)