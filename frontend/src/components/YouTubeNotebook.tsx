// YouTubeNotebook.tsx
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
}

// NEW Interface for Chat Session Summary
interface ChatSessionSummary {
  session_id: string;
  first_prompt: string;
  created_at: string; // Will be a string from backend (ISO format)
}

const YouTubeNoteBook: React.FC<YouTubeNoteBookProps> = ({ videoId, notebookId, userId }) => {
  // State to manage content in the LEFT column: 'timestamps' (default view) or 'description'
  // State to manage content in the RIGHT column: 'chat' (default view) or 'chatHistory'
  const [activeRightContent, setActiveRightContent] = useState<'chat' | 'chatHistory' | 'description'>('chat'); 
  const [description, setDescription] = useState<DescriptionResponse | null>(null);
  const [descriptionLoading, setDescriptionLoading] = useState<boolean>(false);
  const [descriptionError, setDescriptionError] = useState<string | null>(null);
  const [timestampQuery, setTimestampQuery] = useState<string>('');
  const [timestamps, setTimestamps] = useState<TimestampEntry[]>([]);
  const [timestampLoading, setTimestampLoading] = useState<boolean>(false);
  const [timestampError, setTimestampError] = useState<string | null>(null);
  const [videoTitle, setVideoTitle] = useState<string>('Loading Video Title...');
  const [playerReady, setPlayerReady] = useState<boolean>(false);
  const [showTimestamps, setShowTimestamps] = useState(true);


  const playerRef = useRef<any>(null);

  // States for chat session management (used by ChatBotComponent and ChatHistoryPanel)
  const [currentChatSessionId, setCurrentChatSessionId] = useState<string | null>(null);
  const [chatSessionHistorySummaries, setChatSessionHistorySummaries] = useState<ChatSessionSummary[]>([]);
  const [chatHistoryLoading, setChatHistoryLoading] = useState<boolean>(false);
  const [chatHistoryError, setChatHistoryError] = useState<string | null>(null);


  // Load YouTube IFrame Player API
  useEffect(() => {
    const tag = document.createElement('script');
    tag.src = 'https://www.youtube.com/iframe_api'; // Correct YouTube API URL
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
        // Pre-fetch description so it's ready when user switches
        setDescription(response.data.description);
      } catch (err) {
        setVideoTitle('Video Unavailable');
        console.error('Error fetching video details:', err);
      }
    };
    fetchVideoDetails();
  }, [videoId]);

  // Function to fetch and display video description
  const fetchDescription = async () => {
    setActiveRightContent('description'); // Switch right panel to description
    setDescriptionLoading(true);
    setDescriptionError(null);
    try {
      const response = await axios.get<VideoDetailsResponse>(`http://localhost:8000/video_details/${videoId}`);
      setDescription(response.data.description);
    } catch (err) {
      setDescriptionError('Failed to fetch description');
      console.error('Error fetching description:', err);
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
      const axiosError = err as AxiosError<{ detail: string }>;
      setTimestampError(axiosError.response?.data?.detail || 'Failed to fetch timestamps.');
      console.error('Error fetching timestamps:', err);
    } finally {
      setTimestampLoading(false);
    }
  };

function getYoutubeEmbedUrl(videoId: string, timestamp?: string): string {
  const timeParam = timestamp ? `&start=${convertTimestampToSeconds(timestamp)}` : '';
  return `https://www.youtube.com/embed/${videoId}?autoplay=1${timeParam}`;
}

function convertTimestampToSeconds(timestamp: string): number {
  const parts = timestamp.split(':').map(Number);
  if (parts.length === 3) return parts[0] * 3600 + parts[1] * 60 + parts[2];
  if (parts.length === 2) return parts[0] * 60 + parts[1];
  return parts[0];
}

function handleTimestampClick(timestamp: string) {
  const iframe = document.getElementById('youtube-player') as HTMLIFrameElement;
  if (iframe) {
    iframe.src = getYoutubeEmbedUrl(videoId, timestamp);
  }
}


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
        // Sort by created_at in descending order to get most recent first, then reverse for display
        // Assuming 'created_at' is an ISO string and can be compared directly or converted to Date objects
        const sortedSummaries = summariesResponse.data.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
        setChatSessionHistorySummaries(sortedSummaries);

        // Fetch notebook details to get the actual latest_session_id
        const notebookResponse = await axios.get<{ notebook: { latest_session_id: string | null } }>(
            `http://localhost:8000/notebook/${notebookId}`
        );
        const latestId = notebookResponse.data.notebook.latest_session_id;

        if (latestId) {
          setCurrentChatSessionId(latestId);
          console.log("Loaded latest session ID:", latestId);
        } else if (sortedSummaries.length > 0) {
          // Fallback: If no latest_session_id in notebook, but sessions exist, pick the most recent one
          setCurrentChatSessionId(sortedSummaries[0].session_id);
          console.log("No latest session ID in notebook, defaulting to most recent existing session.");
        } else {
          // No existing sessions found. currentChatSessionId will remain null, signaling a new chat.
          setCurrentChatSessionId(null);
          console.log("No chat sessions found for this notebook. Starting a new chat.");
        }

      } catch (err: any) {
        setChatHistoryError((err as AxiosError<{ detail: string }>).response?.data?.detail || 'Failed to fetch chat session history.');
        console.error('Error fetching chat session summaries:', err);
      } finally {
        setChatHistoryLoading(false);
      }
    };

    if (notebookId) { // Only fetch if notebookId is available
      fetchChatSessionSummaries();
    }
  }, [notebookId]); // Re-run when notebookId changes

  // NEW: Function to start a new chat session (called from ChatHistoryPanel)
  const startNewChatSession = () => {
    setCurrentChatSessionId(null); // Setting to null tells ChatBotComponent to create a new session
    setActiveRightContent('chat'); // Switch back to chat view
  };

  // NEW: Handler for when a chat session from history is clicked (from ChatHistoryPanel)
  const handleSelectChatSession = (sessionId: string) => {
    setCurrentChatSessionId(sessionId); // This will cause ChatBotComponent to load this session's history
    setActiveRightContent('chat'); // Switch back to chat view
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
        // Sort again after re-fetching
        const sortedSummaries = response.data.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
        setChatSessionHistorySummaries(sortedSummaries);
      } catch (err) {
        console.error('Error re-fetching chat session summaries after chat response:', err);
      }
    };
    reFetchChatSessionSummaries();
  };


  return (
    <div className="container mx-auto p-2 bg-white rounded-lg shadow-xl mt-8">

      {/* Main content area: Two columns */}
      <div className="flex flex-col lg:flex-row gap-8">
        {/* Left Column: Video Player, Timestamps */}
<div className="lg:w-1/2 w-full flex flex-col py-6">
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

  <span className="text-lg font-bold text-center text-gray-900 mb-6">{videoTitle}</span>

  {/* Buttons to switch between Description and Chat/Chat History */}
          <div className="flex space-x-4 mb-6 text-xs">
            <button
              onClick={() => { setActiveRightContent('description'); fetchDescription(); }}
              className={`flex-1 p-4 rounded-lg font-semibold transition-colors duration-200 shadow-md ${
                activeRightContent === 'description' ? 'bg-blue-700 text-white' : 'bg-blue-500 hover:bg-blue-600 text-white'
              }`}
            >
              Show Description
            </button>
            <button
              onClick={() => setActiveRightContent('chat')}
              className={`flex-1 p-4 rounded-lg font-semibold transition-colors duration-200 shadow-md ${
                activeRightContent === 'chat' || activeRightContent === 'chatHistory' ? 'bg-purple-700 text-white' : 'bg-purple-500 hover:bg-purple-600 text-white'
              }`}
            >
              Chat with Video
            </button>
          </div>

          <form onSubmit={handleTimestampSearch} className="mb-6 flex items-center space-x-3 text-xs">
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
              className={`p-3 rounded-lg text-xs text-white font-semibold transition-colors duration-200 ${
                timestampLoading ? 'bg-purple-400 cursor-not-allowed' : 'bg-purple-600 hover:bg-purple-700'
              }`}
              disabled={timestampLoading}
            >
              {timestampLoading ? 'Searching...' : 'Get Timestamps'}
            </button>
          </form>

  {timestamps.length > 0 && (
    <div className="mb-6 p-4 bg-gray-50 rounded-lg shadow-inner  h-auto overflow-y-auto custom-scrollbar">
      <span className="text-xl font-semibold mb-3 text-gray-800">Relevant Timestamps</span>

      <ul className="list-none space-y-2">
        {timestamps.map((ts, index) => (
          <li key={index} className="flex items-center p-2 bg-white rounded-md shadow-sm border border-gray-200">
            <button
              onClick={() => handleTimestampClick(ts.timestamp)}
              className="text-blue-600 hover:underline font-medium mr-3 text-left bg-transparent border-none cursor-pointer p-0"
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
  <p className="px-4 text-md font-semibold mb-3 text-gray-800">  You can click on a timsetamp to start player from there 😊</p>
</div>


        {/* Right Column: Dynamic Content (Description or Chat) */}
        <div className="lg:w-1/2 w-full flex flex-col text-l">
          {/* Conditional rendering for right column content */}
          {activeRightContent === 'description' && (
            <VideoDescriptionComponent
              description={description}
              isLoading={descriptionLoading}
              error={descriptionError}
            />
          )}

          {activeRightContent === 'chat' && (
            <div className="flex flex-col h-full">
              <div className="flex justify-between items-center mb-4">
                <h3 className="text-xl font-bold text-gray-800">Chat with Video</h3>
                <button
                  onClick={() => setActiveRightContent('chatHistory')}
                  className="bg-gray-200 hover:bg-gray-300 text-gray-800 font-semibold py-2 px-4 rounded-lg transition duration-200"
                >
                  See Chat History
                </button>
              </div>
              <ChatBotComponent
                videoId={videoId}
                notebookId={notebookId}
                currentSessionId={currentChatSessionId}
                onChatResponse={handleChatResponse}
                userId={userId}
              />
            </div>
          )}

          {activeRightContent === 'chatHistory' && (
            <ChatHistoryPanel
              chatSessionHistorySummaries={chatSessionHistorySummaries}
              currentChatSessionId={currentChatSessionId}
              chatHistoryLoading={chatHistoryLoading}
              chatHistoryError={chatHistoryError}
              onStartNewChatSession={startNewChatSession}
              onSelectChatSession={handleSelectChatSession}
            />
          )}
        </div>
      </div>
    </div>
  );
};

export default YouTubeNoteBook;