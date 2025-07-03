// LinkSubmission.tsx
import React, { useState } from 'react';

interface LinkSubmissionProps {
  onSubmit: (url: string) => void;
  isLoading: boolean;
  error: string | null;
}

const LinkSubmission: React.FC<LinkSubmissionProps> = ({ onSubmit, isLoading, error }) => {
  const [url, setUrl] = useState<string>('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit(url);
  };

  return (
    <div className="bg-white p-8 rounded-lg shadow-lg w-full max-w-md mx-auto mt-8">
      <h2 className="text-2xl font-bold mb-6 text-center text-gray-800">Submit YouTube Video URL</h2>
      <form onSubmit={handleSubmit} className="space-y-4">
        <input
          type="text"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder="Enter YouTube URL"
          className="border border-gray-300 p-3 rounded-md w-full focus:outline-none focus:ring-2 focus:ring-blue-500 transition duration-200"
          disabled={isLoading}
        />
        <button
          type="submit"
          className={`w-full p-3 rounded-md text-white font-semibold transition-colors duration-200 ${
            isLoading ? 'bg-blue-400 cursor-not-allowed' : 'bg-blue-600 hover:bg-blue-700'
          }`}
          disabled={isLoading}
        >
          {isLoading ? 'Submitting...' : 'Submit Video'}
        </button>
      </form>
      {error && (
        <p className="text-red-500 text-sm mt-4 text-center p-2 bg-red-100 rounded-md">{error}</p>
      )}
    </div>
  );
};

export default LinkSubmission;
