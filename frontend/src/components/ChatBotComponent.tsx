// ChatBotComponent.tsx
import React, { useState, useEffect, useRef } from 'react';
import axios, { AxiosError } from 'axios';
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL; 

interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
}

interface ChatBotComponentProps {
  videoId: string;
  notebookId: string;
  currentSessionId: string | null;
  onChatResponse: (newSessionId: string) => void;
  userId: string;
}

const ChatBotComponent: React.FC<ChatBotComponentProps> = ({
  videoId,
  notebookId,
  currentSessionId, // This prop now correctly dictates if we're in an existing session
  onChatResponse,
  userId,
}) => {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState<string>('');
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Scroll to bottom of chat messages
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  // NEW: Load chat history when currentSessionId changes
  useEffect(() => {
    const fetchChatHistory = async () => {
      if (currentSessionId) { // Only fetch if a session ID is provided
        setIsLoading(true);
        setError(null);
        try {
          const response = await axios.get<{ session_id: string, history: ChatMessage[] }>(
            `${API_BASE_URL}/chat/history/${currentSessionId}`
          );
          setMessages(response.data.history);
          console.log(`Loaded history for session: ${currentSessionId}`);
        } catch (err) {
          const errorMessage = (err as AxiosError<{ detail: string }>).response?.data?.detail || 'Failed to load chat history.';
          setError(errorMessage);
          setMessages([{ role: 'assistant', content: `Error loading history: ${errorMessage}` }]);
          console.error("Error loading chat history:", err);
        } finally {
          setIsLoading(false);
        }
      } else {
        // If currentSessionId is null, it's a new chat, so clear messages and set initial greeting
        setMessages([{ role: 'assistant', content: "Hello! How can I help you with this video?" }]);
        setError(null);
      }
    };

    fetchChatHistory();
  }, [currentSessionId, videoId]); // Depend on currentSessionId and videoId

  // Scroll to bottom whenever messages update
  useEffect(() => {
    scrollToBottom();
  }, [messages]);

   const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return; // Removed !sessionId check

    const newUserMessage: ChatMessage = { role: 'user', content: input.trim() };
    setMessages((prevMessages) => [...prevMessages, newUserMessage]);
    setInput('');
    setIsLoading(true);
    setError(null);

    try {
      // Build the payload for the single /chat endpoint
      const payload: {
        query: string;
        video_id: string;
        user_id: string;
        notebook_id: string;
        session_id?: string; // Optional session_id for new/existing chat
      } = {
        query: newUserMessage.content,
        video_id: videoId,
        user_id: userId,
        notebook_id: notebookId,
      };

      // Only include session_id in the payload if it's an existing session
      if (currentSessionId) {
        payload.session_id = currentSessionId;
      }

      const response = await axios.post<{ answer: string; session_id: string }>(
        `${API_BASE_URL}/chat`, // ALWAYS use this single endpoint
        payload
      );

      const modelResponse: ChatMessage = { role: 'assistant', content: response.data.answer };
      setMessages((prevMessages) => [...prevMessages, modelResponse]);

      // The backend will always return the session_id (either the existing one, or a new one)
      // Call the parent callback to update its state with the correct session ID
      onChatResponse(response.data.session_id);

    } catch (err) {
      const errorMessage = (err as AxiosError<{ detail: string }>).response?.data?.detail || 'Failed to get response from chatbot.';
      setError(errorMessage);
      setMessages((prevMessages) => [...prevMessages, { role: 'assistant', content: `Error: ${errorMessage}` }]);
      console.error("Error sending message:", err);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="bg-white rounded-lg shadow-lg p-6 flex flex-col h-full mt-4 text-xs">
      {error && (
        <div className="text-red-500 p-3 bg-red-100 rounded-md mb-4">
          <p>{error}</p>
        </div>
      )}

      {isLoading && !messages.length && ( // Show initial loading if no messages yet (implies history fetch or initial greeting)
        <div className="flex justify-center items-center flex-grow">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-gray-900"></div>
          <p className="ml-4 text-gray-700">Loading chat...</p>
        </div>
      )}

      {/* Always render chat interface once currentSessionId is set or if it's a new chat (messages will be initialized) */}
      {!isLoading || messages.length > 0 ? (
        <>
          <div className="flex-grow overflow-y-auto pr-4 custom-scrollbar">
            {messages.map((msg, index) => (
              <div
                key={index}
                className={`flex mb-4 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                <div
                  className={`max-w-[75%] p-3 rounded-lg shadow-md ${
                    msg.role === 'user'
                      ? 'bg-blue-500 text-white rounded-br-none'
                      : 'bg-gray-200 text-gray-800 rounded-bl-none'
                  }`}
                >
                  {msg.content}
                </div>
              </div>
            ))}
            {isLoading && messages.length > 0 && ( // Show loading indicator after first message
              <div className="flex justify-start mb-4">
                <div className="max-w-[75%] p-3 rounded-lg shadow-md bg-gray-200 text-gray-800 rounded-bl-none">
                  <div className="flex items-center">
                    <div className="animate-pulse flex space-x-1">
                      <div className="w-2 h-2 bg-gray-500 rounded-full"></div>
                      <div className="w-2 h-2 bg-gray-500 rounded-full"></div>
                      <div className="w-2 h-2 bg-gray-500 rounded-full"></div>
                    </div>
                    <span className="ml-2">Typing...</span>
                  </div>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          <form onSubmit={handleSendMessage} className="mt-4 flex items-center">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Type your message..."
              className="flex-grow border border-gray-300 p-3 rounded-l-lg focus:outline-none focus:ring-2 focus:ring-blue-500 transition duration-200"
              disabled={isLoading}
            />
            <button
              type="submit"
              className={`p-3 rounded-r-lg text-white font-semibold transition-colors duration-200 flex items-center justify-center ${
                isLoading ? 'bg-blue-400 cursor-not-allowed' : 'bg-blue-600 hover:bg-blue-700'
              }`}
              disabled={isLoading}
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                className="h-6 w-6"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M14 5l7 7m0 0l-7 7m7-7H3"
                />
              </svg>
            </button>
          </form>
        </>
      ) : null}
    </div>
  );
};

export default ChatBotComponent;