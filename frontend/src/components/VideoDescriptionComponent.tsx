// VideoDescriptionComponent.tsx
import React from 'react';

interface DescriptionResponse {
  video_id: string;
  title: string;
  keywords: string[];
  category_tags: string[];
  detailed_description: string;
  summary: string;
}

interface VideoDescriptionComponentProps {
  description: DescriptionResponse | null;
  isLoading: boolean;
  error: string | null;
}

const VideoDescriptionComponent: React.FC<VideoDescriptionComponentProps> = ({ description, isLoading, error }) => {
  if (isLoading) {
    return (
      <div className="flex justify-center items-center p-8">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-gray-900"></div>
        <p className="ml-4 text-gray-700">Loading description...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-red-500 p-4 bg-red-100 rounded-lg shadow-md mt-4">
        <p>Error: {error}</p>
      </div>
    );
  }

  if (!description) {
    return (
      <div className="text-gray-600 p-4 bg-gray-100 rounded-lg shadow-md mt-4">
        <p>No description available. Please click 'Get Description' to fetch it.</p>
      </div>
    );
  }

  return (
    <div className="space-y-6 p-6 bg-white rounded-lg shadow-md mt-4">
      <h2 className="text-2xl font-bold text-gray-800 mb-4 border-b pb-3">Video Description</h2>

      <div>
        <h3 className="text-xl font-semibold mb-2 text-gray-700">Video Title</h3>
        <p className="bg-gray-50 p-4 rounded-md font-medium text-gray-900 border border-gray-200">
          {description.title || 'No title available'}
        </p>
      </div>

      <div>
        <h3 className="text-xl font-semibold mb-2 text-gray-700">Category Tags</h3>
        <p className="bg-gray-50 p-4 rounded-md italic text-gray-700 border border-gray-200">
          {description.category_tags && description.category_tags.length > 0
            ? description.category_tags.join(', ')
            : 'No category tags available'}
        </p>
      </div>

      <div>
        <h3 className="text-xl font-semibold mb-2 text-gray-700">Keywords</h3>
        <p className="bg-gray-50 p-4 rounded-md italic text-gray-700 border border-gray-200">
          {description.keywords && description.keywords.length > 0
            ? description.keywords.join(', ')
            : 'No keywords available'}
        </p>
      </div>

      <div>
        <h3 className="text-xl font-semibold mb-2 text-gray-700">Detailed Description</h3>
        <ul className="list-disc pl-5 bg-gray-50 p-4 rounded-md text-gray-800 border border-gray-200">
          {/* Added || '' to ensure detailed_description is a string before splitting */}
          {(description.detailed_description || '').split('||').map((point, index) => (
            <li key={index} className="mb-2 last:mb-0">{point || 'No details available'}</li>
          ))}
        </ul>
      </div>

      <div>
        <h3 className="text-xl font-semibold mb-2 text-gray-700">Summary</h3>
        <div className="bg-gray-50 p-4 rounded-md text-gray-800 border border-gray-200">
          {/* Added || '' to ensure summary is a string before splitting */}
          {(description.summary || '').split('||').map((paragraph, index) => (
            <p key={index} className="mb-2 last:mb-0">{paragraph || 'No summary available'}</p>
          ))}
        </div>
      </div>
    </div>
  );
};

export default VideoDescriptionComponent;
