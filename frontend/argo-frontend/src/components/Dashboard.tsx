"use client";

import React, { useState } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { Search, MapPin, Calendar, Thermometer, LogOut, User } from 'lucide-react';
import axios from 'axios';

interface SearchResult {
  profile_id: number;
  latitude: number;
  longitude: number;
  date: string;
  institution: string;
  platform_number: string;
  ocean_data: any;
  similarity_score: number;
  content_summary: string;
}

interface RAGResponse {
  answer: string;
  context_profiles: SearchResult[];
  query_summary: string;
}

const Dashboard: React.FC = () => {
  const { user, logout, token } = useAuth();
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<SearchResult[]>([]);
  const [ragResponse, setRagResponse] = useState<RAGResponse | null>(null);
  const [searchType, setSearchType] = useState<'text' | 'semantic' | 'intelligent'>('intelligent');

  const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';

  const handleSearch = async () => {
    if (!query.trim()) return;
    
    setLoading(true);
    try {
      if (searchType === 'semantic') {
        const response = await axios.post(
          `${API_BASE_URL}/search/intelligent`,
          { query, limit: 10, similarity_threshold: 0.3 },
          { headers: { Authorization: `Bearer ${token}` } }
        );
        setResults(response.data);
        setRagResponse(null);
      } else {
        const response = await axios.post(
          `${API_BASE_URL}/search/text`,
          { question: query, context_limit: 5 },
          { headers: { Authorization: `Bearer ${token}` } }
        );
        setRagResponse(response.data);
        setResults([]);
      }
    } catch (error) {
      console.error('Search failed:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center">
              <h1 className="text-2xl font-bold text-blue-600"> ARGO RAG</h1>
              <span className="ml-4 text-sm text-gray-500">Oceanographic Intelligence</span>
            </div>
            <div className="flex items-center space-x-4">
              <div className="flex items-center space-x-2 text-sm text-gray-600">
                <User className="h-4 w-4" />
                <span>{user?.email}</span>
                <span className="bg-blue-100 text-blue-800 px-2 py-1 rounded-full text-xs">
                  {user?.user_tier}
                </span>
              </div>
              <button
                onClick={logout}
                className="flex items-center space-x-1 text-gray-600 hover:text-gray-900"
              >
                <LogOut className="h-4 w-4" />
                <span>Logout</span>
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Search Section */}
        <div className="bg-white rounded-lg shadow-sm p-6 mb-8">
          <div className="mb-4">
            <div className="flex space-x-4 mb-4">
              <button
                onClick={() => setSearchType('text')}
                className={`px-4 py-2 rounded-lg ${
                  searchType === 'text' 
                    ? 'bg-blue-600 text-black' 
                    : 'bg-gray-200 text-gray-700'
                }`}
              >
                RAG Query
              </button>
              <button
                onClick={() => setSearchType('semantic')}
                className={`px-4 py-2 rounded-lg ${
                  searchType === 'semantic'
                    ? 'bg-blue-600 text-black'
                    : 'bg-gray-200 text-gray-700'
                }`}
              >
                Semantic Search
              </button>
            </div>
            
            <div className="flex space-x-4">
              <div className="flex-1 relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 h-5 w-5" />
                <input
                  type="text"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
                  className="w-full  text-black pl-10 pr-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  placeholder={
                    searchType === 'intelligent'
                      ? "Ask naturally: 'temperature of Indian Ocean in July 2004', 'Atlantic salinity trends'..."
                      : searchType === 'text' 
                      ? "Ask about ocean temperature, salinity, or specific regions..."
                      : "Search for oceanographic profiles..."
                  }
                />
              </div>
              <button
                onClick={handleSearch}
                disabled={loading || !query.trim()}
                className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {loading ? 'Searching...' : 'Search'}
              </button>
            </div>
          </div>
        </div>

        {/* Results Section */}
        {ragResponse && (
          <div className="bg-white rounded-lg shadow-sm p-6 mb-8">
            <h2 className="text-xl font-semibold mb-4"> AI Analysis</h2>
            <div className="prose max-w-none">
              <div className="bg-blue-50 p-4 rounded-lg mb-4">
                <pre className="whitespace-pre-wrap text-sm">{ragResponse.answer}</pre>
              </div>
              <p className="text-sm text-gray-600">{ragResponse.query_summary}</p>
            </div>
          </div>
        )}

        {results.length > 0 && (
          <div className="bg-white rounded-lg shadow-sm p-6">
            <h2 className="text-xl font-semibold mb-4"> Search Results ({results.length})</h2>
            <div className="space-y-4">
              {results.map((result, index) => (
                <div key={index} className="border border-gray-200 rounded-lg p-4">
                  <div className="flex justify-between items-start mb-2">
                    <h3 className="font-medium text-lg">Profile #{result.profile_id}</h3>
                    <span className="bg-green-100 text-green-800 px-2 py-1 rounded-full text-xs">
                      {(result.similarity_score * 100).toFixed(1)}% match
                    </span>
                  </div>
                  
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-3">
                    <div className="flex items-center space-x-2 text-sm text-gray-600">
                      <MapPin className="h-4 w-4" />
                      <span>{result.latitude.toFixed(2)}N, {result.longitude.toFixed(2)}E</span>
                    </div>
                    <div className="flex items-center space-x-2 text-sm text-gray-600">
                      <Calendar className="h-4 w-4" />
                      <span>{new Date(result.date).toLocaleDateString()}</span>
                    </div>
                    <div className="flex items-center space-x-2 text-sm text-gray-600">
                      <Thermometer className="h-4 w-4" />
                      <span>{result.institution}</span>
                    </div>
                  </div>
                  
                  <p className="text-sm text-gray-700">{result.content_summary}</p>
                  
                  {result.ocean_data && Object.keys(result.ocean_data).length > 0 && (
                    <div className="mt-3 p-3 bg-gray-50 rounded">
                      <span className="text-xs font-medium text-gray-500">OCEAN DATA PREVIEW</span>
                      <div className="text-xs text-gray-600 mt-1">
                        {Object.entries(result.ocean_data).slice(0, 3).map(([key, value]) => (
                          <span key={key} className="mr-4">
                            {key}: {Array.isArray(value) ? `${value.length} measurements` : String(value)}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* User Stats */}
        <div className="mt-8 bg-white rounded-lg shadow-sm p-6">
          <h2 className="text-lg font-semibold mb-4"> Your Usage</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="text-center p-4 bg-blue-50 rounded-lg">
              <div className="text-2xl font-bold text-blue-600">{user?.daily_query_count || 0}</div>
              <div className="text-sm text-gray-600">Queries Today</div>
            </div>
            <div className="text-center p-4 bg-green-50 rounded-lg">
              <div className="text-2xl font-bold text-green-600">{user?.total_queries || 0}</div>
              <div className="text-sm text-gray-600">Total Queries</div>
            </div>
            <div className="text-center p-4 bg-purple-50 rounded-lg">
              <div className="text-2xl font-bold text-purple-600">{user?.user_tier}</div>
              <div className="text-sm text-gray-600">Account Type</div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
};

export default Dashboard;



