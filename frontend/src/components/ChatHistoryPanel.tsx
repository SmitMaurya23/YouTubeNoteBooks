// src/components/ChatHistoryPanel.tsx

import React from 'react';

// Re-declare the interface here or import it from a common types file if you create one
interface ChatSessionSummary {
  session_id: string;
  first_prompt: string;
  created_at: string; // Will be ISO string from backend
}

interface ChatHistoryPanelProps {
  chatSessionHistorySummaries: ChatSessionSummary[];
  currentChatSessionId: string | null;
  chatHistoryLoading: boolean;
  chatHistoryError: string | null;
  onStartNewChatSession: () => void;
  onSelectChatSession: (sessionId: string) => void;
}

const ChatHistoryPanel: React.FC<ChatHistoryPanelProps> = ({
  chatSessionHistorySummaries,
  currentChatSessionId,
  chatHistoryLoading,
  chatHistoryError,
  onStartNewChatSession,
  onSelectChatSession,
}) => {
  return (
    <div className="bg-white p-4 rounded-lg shadow-lg h-[600px] overflow-y-auto custom-scrollbar">

      <h3 className="text-xl font-bold text-gray-800 mb-4">Chat History</h3>
      <button
        onClick={onStartNewChatSession}
        className="w-full bg-indigo-600 hover:bg-indigo-700 text-white font-semibold py-2 px-4 rounded-lg mb-4 transition duration-200"
      >
        + Start New Chat
      </button>
      {chatHistoryLoading && <p className="text-gray-600 text-center">Loading chat history...</p>}
      {chatHistoryError && <p className="text-red-500 text-center">{chatHistoryError}</p>}
      {!chatHistoryLoading && !chatSessionHistorySummaries.length && !chatHistoryError && (
        <p className="text-gray-600 text-sm text-center">No chat sessions yet.</p>
      )}
      <ul className="space-y-2">
        {chatSessionHistorySummaries.map((session) => (
          <li key={session.session_id}>
            <button
              onClick={() => onSelectChatSession(session.session_id)}
              className={`w-full text-left p-3 rounded-md transition-colors duration-200 ${
                currentChatSessionId === session.session_id
                  ? 'bg-blue-100 text-blue-800 font-semibold'
                  : 'bg-gray-50 hover:bg-gray-100 text-gray-700'
              }`}
            >
              <p className="text-xs truncate">{session.first_prompt}</p>
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
};

export default ChatHistoryPanel;