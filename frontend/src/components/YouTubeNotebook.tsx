import React, { useState, useEffect, useRef } from 'react';
import axios, { AxiosError } from 'axios';
import VideoDescriptionComponent from './VideoDescriptionComponent';
import ChatBotComponent from './ChatBotComponent';
import ChatHistoryPanel from './ChatHistoryPanel'; 

// Declare YouTube global object
declare global {
  interface Window {
    onYouTubeIframeAPIReady: () => void;
    YT: any;
  }
}


interface DescriptionResponse {
  video_id: string;
  title: string;
  keywords: string[];
  category_tags: string[];
  detailed_description: string;
  summary: string;
}

interface TimestampEntry {
  timestamp: string; // MM:SS format
  text: string;
}

interface TimestampResponse {
  message: string;
  timestamps: TimestampEntry[];
}

interface TranscriptEntry {
  time: string; // MM:SS or similar
  text: string;
}

interface VideoDetailsResponse {
  video_id: string;
  url: string;
  submitted_at: string;
  transcript: TranscriptEntry[];
  transcript_text: string;
  description: DescriptionResponse;
  updated_at: string;
}

interface YouTubeNoteBookProps {
  videoId: string;
  notebookId: string; 
  userId: string; 
  onBack: () => void;
}

// NEW Interface for Chat Session Summary
interface ChatSessionSummary {
  session_id: string;
  first_prompt: string;
  created_at: string; // Will be a string from backend (ISO format)
}

const YouTubeNoteBook: React.FC<YouTubeNoteBookProps> = ({ videoId, notebookId, onBack,userId }) => { 
  const [activePanel, setActivePanel] = useState<'description' | 'chat' | null>(null);
  const [description, setDescription] = useState<DescriptionResponse | null>(null);
  const [descriptionLoading, setDescriptionLoading] = useState<boolean>(false);
  const [descriptionError, setDescriptionError] = useState<string | null>(null);
  const [timestampQuery, setTimestampQuery] = useState<string>('');
  const [timestamps, setTimestamps] = useState<TimestampEntry[]>([]);
  const [timestampLoading, setTimestampLoading] = useState<boolean>(false);
  const [timestampError, setTimestampError] = useState<string | null>(null);
  const [videoTitle, setVideoTitle] = useState<string>('Loading Video Title...');
  const [playerReady, setPlayerReady] = useState<boolean>(false);

  const playerRef = useRef<any>(null);

  // NEW STATES for chat session management
  const [currentChatSessionId, setCurrentChatSessionId] = useState<string | null>(null);
  const [chatSessionHistorySummaries, setChatSessionHistorySummaries] = useState<ChatSessionSummary[]>([]);
  const [chatHistoryLoading, setChatHistoryLoading] = useState<boolean>(false);
  const [chatHistoryError, setChatHistoryError] = useState<string | null>(null);

  // Load YouTube IFrame Player API
   useEffect(() => {
    const tag = document.createElement('script');
    tag.src = 'https://www.youtube.com/iframe_api';
    const firstScriptTag = document.getElementsByTagName('script')[0];
    firstScriptTag?.parentNode?.insertBefore(tag, firstScriptTag) || document.body.appendChild(tag);

    window.onYouTubeIframeAPIReady = () => {
      if (videoId) {
        playerRef.current = new window.YT.Player('youtube-player', {
          videoId: videoId,
          playerVars: {
            autoplay: 0,
            controls: 1,
            enablejsapi: 1,
            rel: 0,
          },
          events: {
            onReady: (event: any) => {
              console.log('YouTube Player Ready:', event.target);
              setPlayerReady(true);
            },
            onError: (event: any) => {
              console.error('YouTube Player Error:', event.data);
            },
          },
        });
      }
    };

    return () => {
      if (playerRef.current && typeof playerRef.current.destroy === 'function') {
        playerRef.current.destroy();
        playerRef.current = null;
      }
    };
  }, [videoId]);


  // Fetch video details
  useEffect(() => {
    const fetchVideoDetails = async () => {
      try {
        const response = await axios.get<VideoDetailsResponse>(`http://localhost:8000/video_details/${videoId}`);
        setVideoTitle(response.data.description.title || 'Video Unavailable');
      } catch (err) {
        setVideoTitle('Video Unavailable');
        setDescriptionError('Failed to fetch video details');
        console.error('Error fetching video details:', err);
      }
    };
    fetchVideoDetails();
  }, [videoId]);

  const fetchDescription = async () => {
    setActivePanel('description');
    setDescriptionLoading(true);
    setDescriptionError(null);
    try {
      const response = await axios.get<VideoDetailsResponse>(`http://localhost:8000/video_details/${videoId}`);
      setDescription(response.data.description);
    } catch (err) {
      setDescriptionError('Failed to fetch description');
    } finally {
      setDescriptionLoading(false);
    }
  };

  const handleTimestampSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!timestampQuery.trim()) return;

    setTimestampLoading(true);
    setTimestampError(null);
    setTimestamps([]);

    try {
      const response = await axios.post<TimestampResponse>(
        'http://localhost:8000/get_timestamps',
        { query: timestampQuery, video_id: videoId }
      );
      setTimestamps(response.data.timestamps);
      if (response.data.timestamps.length === 0) {
        setTimestampError('No relevant timestamps found.');
      }
    } catch (err) {
      setTimestampError('Failed to fetch timestamps.');
    } finally {
      setTimestampLoading(false);
    }
  };

  const handleTimestampClick = (timestamp: string) => {
    const parts = timestamp.split(':');
    if (parts.length !== 2) {
      console.error('Invalid timestamp format (expected MM:SS):', timestamp);
      return;
    }
    const minutes = parseInt(parts[0], 10);
    const seconds = parseFloat(parts[1]);
    if (isNaN(minutes) || isNaN(seconds)) {
      console.error('Invalid timestamp values:', timestamp);
      return;
    }
    const totalSeconds = minutes * 60 + seconds;

    if (playerReady && playerRef.current?.seekTo) {
      playerRef.current.seekTo(totalSeconds, true);
      playerRef.current.playVideo();
    } else {
      setTimestampError('Player not ready. Try again shortly.');
    }
  };

  const getYoutubeEmbedUrl = (id: string) => {
    return `https://www.youtube.com/embed/${id}?enablejsapi=1&version=3&playerapiid=ytplayer`;
  };

  // NEW: useEffect to fetch chat session summaries and determine initial session
useEffect(() => {
  const fetchChatSessionSummaries = async () => {
    setChatHistoryLoading(true);
    setChatHistoryError(null);
    try {
      // Fetch summaries for all sessions linked to this notebook
      const summariesResponse = await axios.get<ChatSessionSummary[]>(
        `http://localhost:8000/notebook/${notebookId}/chat_sessions`
      );
      setChatSessionHistorySummaries(summariesResponse.data);

      // Fetch notebook details to get the actual latest_session_id
      const notebookResponse = await axios.get<{ notebook: { latest_session_id: string | null } }>(
          `http://localhost:8000/notebook/${notebookId}`
      );
      const latestId = notebookResponse.data.notebook.latest_session_id;

      if (latestId) {
            setCurrentChatSessionId(latestId);
            console.log("Loaded latest session ID:", latestId);
      } else if (summariesResponse.data.length > 0) {
          // Fallback: If no latest_session_id in notebook, but sessions exist, pick the most recent one (first in sorted list)
          setCurrentChatSessionId(summariesResponse.data[0].session_id);
          console.log("No latest session ID in notebook, defaulting to most recent existing session.");
      } else {
          // THIS IS THE "ELSE WHAT" SCENARIO: No existing sessions found.
          // currentChatSessionId will remain null, signaling a new chat.
          setCurrentChatSessionId(null); // Explicitly set to null for clarity, though it's likely already null
          console.log("No chat sessions found for this notebook. Starting a new chat.");
      }

    } catch (err: any) {
      setChatHistoryError(err.response?.data?.detail || 'Failed to fetch chat session history.');
      console.error('Error fetching chat session summaries:', err);
    } finally {
      setChatHistoryLoading(false);
    }
  };

  if (notebookId) { // Only fetch if notebookId is available
    fetchChatSessionSummaries();
  }
}, [notebookId]); // Re-run when notebookId changes

// NEW: Function to start a new chat session
const startNewChatSession = () => {
  setCurrentChatSessionId(null); // Setting to null tells ChatBotComponent to create a new session
  setActivePanel('chat'); // Ensure chat panel is active
};

// NEW: Handler for when a chat session from history is clicked
const handleSelectChatSession = (sessionId: string) => {
  setCurrentChatSessionId(sessionId); // This will cause ChatBotComponent to load this session's history
  setActivePanel('chat'); // Switch to chat panel
};

// NEW: Callback from ChatBotComponent after a chat response
const handleChatResponse = (response: string, newSessionId: string) => {
  // Update the current active session ID (important if a new session was just created)
  setCurrentChatSessionId(newSessionId);

  // Re-fetch chat session summaries to ensure the list is up-to-date
  // This is crucial if a new session was just created and its 'first_prompt' needs to appear.
  const reFetchChatSessionSummaries = async () => {
    try {
      const response = await axios.get<ChatSessionSummary[]>(
        `http://localhost:8000/notebook/${notebookId}/chat_sessions`
      );
      setChatSessionHistorySummaries(response.data);
    } catch (err) {
      console.error('Error re-fetching chat session summaries after chat response:', err);
    }
  };
  reFetchChatSessionSummaries();
};


/////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
  return (
    <div className="container mx-auto p-4 max-w-4xl bg-white rounded-lg shadow-xl mt-8">
      <button
        onClick={onBack}
        className="mb-4 bg-gray-200 hover:bg-gray-300 text-gray-800 font-semibold py-2 px-4 rounded-lg transition duration-200 flex items-center"
      >
        <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 mr-2" viewBox="0 0 20 20" fill="currentColor">
          <path fillRule="evenodd" d="M12.707 5.293a1 1 0 010 1.414L9.414 10l3.293 3.293a1 1 0 01-1.414 1.414l-4-4a1 1 0 010-1.414l4-4a1 1 0 011.414 0z" clipRule="evenodd" />
        </svg>
        Back to Home
      </button>

      <h2 className="text-3xl font-bold text-center text-gray-900 mb-6">{videoTitle}</h2>

      <div className="relative w-full overflow-hidden rounded-lg shadow-md mb-6" style={{ paddingTop: '56.25%' }}>
        <iframe
          id="youtube-player"
          className="absolute top-0 left-0 w-full h-full"
          src={getYoutubeEmbedUrl(videoId)}
          frameBorder="0"
          allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
          allowFullScreen
          title="YouTube video player"
        ></iframe>
      </div>

      <form onSubmit={handleTimestampSearch} className="mb-6 flex items-center space-x-3">
        <input
          type="text"
          value={timestampQuery}
          onChange={(e) => setTimestampQuery(e.target.value)}
          placeholder="Search for timestamps (e.g., 'introduction', 'conclusion')"
          className="flex-grow border border-gray-300 p-3 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500 transition duration-200"
          disabled={timestampLoading}
        />
        <button
          type="submit"
          className={`p-3 rounded-lg text-white font-semibold transition-colors duration-200 ${
            timestampLoading ? 'bg-purple-400 cursor-not-allowed' : 'bg-purple-600 hover:bg-purple-700'
          }`}
          disabled={timestampLoading}
        >
          {timestampLoading ? 'Searching...' : 'Get Timestamps'}
        </button>
      </form>

      {timestampError && (
        <p className="text-red-500 mb-4 p-3 bg-red-100 rounded-lg">{timestampError}</p>
      )}

      {timestamps.length > 0 && (
        <div className="mb-6 p-4 bg-gray-50 rounded-lg shadow-inner max-h-60 overflow-y-auto custom-scrollbar">
          <h3 className="text-xl font-semibold mb-3 text-gray-800">Relevant Timestamps</h3>
          <ul className="list-none space-y-2">
            {timestamps.map((ts, index) => (
              <li key={index} className="flex items-center p-2 bg-white rounded-md shadow-sm border border-gray-200">
                <button
                  onClick={() => handleTimestampClick(ts.timestamp)}
                  className="text-blue-600 hover:underline font-medium mr-3 text-left bg-transparent border-none cursor-pointer p-0"
                  disabled={!playerReady}
                  title={`Click to jump to ${ts.timestamp}`}
                >
                  [{ts.timestamp}]
                </button>
                <span className="text-gray-800 text-sm">{ts.text}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="flex justify-center space-x-4 mb-6">
        <button
          onClick={fetchDescription}
          className={`flex-1 p-4 rounded-lg font-semibold transition-colors duration-200 shadow-md ${
            activePanel === 'description' ? 'bg-blue-700 text-white' : 'bg-blue-500 hover:bg-blue-600 text-white'
          }`}
        >
          Get Description
        </button>
        <button
          onClick={() => setActivePanel('chat')}
          className={`flex-1 p-4 rounded-lg font-semibold transition-colors duration-200 shadow-md ${
            activePanel === 'chat' ? 'bg-green-700 text-white' : 'bg-green-500 hover:bg-green-600 text-white'
          }`}
        >
          Chat with Video
        </button>
      </div>

      {activePanel === 'description' && (
        <VideoDescriptionComponent
          description={description}
          isLoading={descriptionLoading}
          error={descriptionError}
        />
      )}
      {activePanel === 'chat' && (
      <ChatHistoryPanel
        chatSessionHistorySummaries={chatSessionHistorySummaries}
        currentChatSessionId={currentChatSessionId}
        chatHistoryLoading={chatHistoryLoading}
        chatHistoryError={chatHistoryError}
        onStartNewChatSession={startNewChatSession}
        onSelectChatSession={handleSelectChatSession}
      />
    )}
      {activePanel === 'chat' && <ChatBotComponent
          videoId={videoId}
          notebookId={notebookId}
          currentSessionId={currentChatSessionId}
          onChatResponse={handleChatResponse} 
          userId={userId}
        />}
    </div>
  );
};

export default YouTubeNoteBook;