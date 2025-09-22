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

interface IntelligentSearchResponse {
  results: SearchResult[];
  query_understanding?: {
    query_types: string[];
    geographic_region?: string;
    time_period?: string;
    measurements?: string[];
    statistics?: string[];
  };
  confidence: number;
  filters_applied: string[];
}

interface AggregatedSearchResponse {
  summary: {
    total_profiles: number;
    date_range: {
      start: string;
      end: string;
    };
    geographic_bounds: {
      latitude_range: [number, number];
      longitude_range: [number, number];
      center: [number, number];
    };
    institutions: {
      count: number;
      names: string[];
    };
  };
  measurements: {
    temperature?: {
      average: number;
      min: number;
      max: number;
      std_deviation: number;
      total_measurements: number;
      unit: string;
    };
    salinity?: {
      average: number;
      min: number;
      max: number;
      std_deviation: number;
      total_measurements: number;
      unit: string;
    };
    depth?: {
      average: number;
      min: number;
      max: number;
      std_deviation: number;
      total_measurements: number;
      unit: string;
    };
  };
  query_understanding?: {
    query_types: string[];
    geographic_region?: string;
    time_period?: string;
    measurements?: string[];
    statistics?: string[];
  };
  confidence: number;
  filters_applied: string[];
}

const Dashboard: React.FC = () => {
  const { user, logout, token } = useAuth();
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<SearchResult[]>([]);
  const [ragResponse, setRagResponse] = useState<RAGResponse | null>(null);
  const [intelligentResponse, setIntelligentResponse] = useState<IntelligentSearchResponse | null>(null);
  const [aggregatedResponse, setAggregatedResponse] = useState<AggregatedSearchResponse | null>(null);
  const [searchType, setSearchType] = useState<'text' | 'semantic' | 'intelligent'>('intelligent');

  const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';

  const handleSearch = async () => {
    if (!query.trim()) return;
    
    setLoading(true);
    setResults([]);
    setRagResponse(null);
    setAggregatedResponse(null);
    
    try {
      if (searchType === 'intelligent') {
        const response = await axios.post(
          `${API_BASE_URL}/search/intelligent`,  // ← Fixed endpoint
          { query, limit: 10, similarity_threshold: 0.3 },
          { headers: { Authorization: `Bearer ${token}` } }
        );
        setAggregatedResponse(response.data);  // ← Fixed state setter
      } else if (searchType === 'semantic') {
        const response = await axios.post(
          `${API_BASE_URL}/search/semantic`,
          { query, limit: 10, similarity_threshold: 0.3 },
          { headers: { Authorization: `Bearer ${token}` } }
        );
        setResults(response.data);
      } else {
        const response = await axios.post(
          `${API_BASE_URL}/search/text`,
          { question: query, context_limit: 5 },
          { headers: { Authorization: `Bearer ${token}` } }
        );
        setRagResponse(response.data);
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
              <h1 className="text-2xl font-bold text-blue-600">🌊 ARGO RAG</h1>
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
            {/* Search Type Selection */}
            <div className="flex space-x-6 mb-4">
              <label className="flex items-center">
                <input
                  type="radio"
                  name="searchType"
                  value="intelligent"
                  checked={searchType === 'intelligent'}
                  onChange={(e) => setSearchType(e.target.value as 'text' | 'semantic' | 'intelligent')}
                  className="mr-2 text-blue-600"
                />
                <span className="text-sm font-medium text-gray-700">🧠 Intelligent Search</span>
              </label>
              <label className="flex items-center">
                <input
                  type="radio"
                  name="searchType"
                  value="semantic"
                  checked={searchType === 'semantic'}
                  onChange={(e) => setSearchType(e.target.value as 'text' | 'semantic' | 'intelligent')}
                  className="mr-2 text-blue-600"
                />
                <span className="text-sm font-medium text-gray-700">🔍 Semantic Search</span>
              </label>
              <label className="flex items-center">
                <input
                  type="radio"
                  name="searchType"
                  value="text"
                  checked={searchType === 'text'}
                  onChange={(e) => setSearchType(e.target.value as 'text' | 'semantic' | 'intelligent')}
                  className="mr-2 text-blue-600"
                />
                <span className="text-sm font-medium text-gray-700">📝 Text Search (RAG)</span>
              </label>
            </div>

            <div className="flex space-x-4">
              <div className="flex-1 relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 h-5 w-5" />
                <input
                  type="text"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder={
                    searchType === 'intelligent' 
                      ? "Try: 'temperature of Indian Ocean in July 2004' or 'salinity data from Atlantic Ocean in 2010'"
                      : searchType === 'semantic' 
                      ? "Enter search terms for semantic similarity..."
                      : "Ask questions about oceanographic data..."
                  }
                  className="flex-1 text-black px-10 py-3 border w-200 border-gray-300 rounded-l-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
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

          {/* Search Type Description */}
          <div className="mb-4 p-3 bg-gray-50 rounded-lg">
            <p className="text-sm text-gray-600">
              {searchType === 'intelligent' && (
                <>
                  <strong>🧠 Intelligent Search:</strong> Uses NLP to understand your query and apply smart filters for geographic regions, time periods, and measurement types.
                </>
              )}
              {searchType === 'semantic' && (
                <>
                  <strong>🔍 Semantic Search:</strong> Finds profiles with similar content using vector embeddings and semantic similarity.
                </>
              )}
              {searchType === 'text' && (
                <>
                  <strong>📝 Text Search (RAG):</strong> Uses AI to answer questions by analyzing relevant oceanographic data and generating comprehensive responses.
                </>
              )}
            </p>
          </div>
        </div>

        {/* Results Section */}
        {ragResponse && (
          <div className="bg-white rounded-lg shadow-sm p-6 mb-8">
            <h2 className="text-xl font-semibold mb-4 text-gray-900">🤖 AI Analysis</h2>
            <div className="prose max-w-none">
              <div className="bg-blue-50 p-4 rounded-lg mb-4">
                <pre className="whitespace-pre-wrap text-sm text-gray-800">{ragResponse.answer}</pre>
              </div>
              <p className="text-sm text-gray-600">{ragResponse.query_summary}</p>
            </div>
          </div>
        )}

        {/* Display results for both intelligent and semantic search */}
        {((intelligentResponse && intelligentResponse.results.length > 0) || results.length > 0) && (
          <div className="bg-white rounded-lg shadow-sm p-6">
            <h2 className="text-xl font-semibold mb-4">
              🔍 Search Results ({intelligentResponse ? intelligentResponse.results.length : results.length})
              {searchType === 'intelligent' && intelligentResponse && (
                <span className="ml-2 text-sm font-normal text-blue-600">
                  (Intelligent Search - {(intelligentResponse.confidence * 100).toFixed(1)}% confidence)
                </span>
              )}
            </h2>
            <div className="space-y-4">
              {(intelligentResponse ? intelligentResponse.results : results).map((result, index) => (
                <div key={index} className="border border-gray-200 rounded-lg p-4">
                  <div className="flex justify-between items-start mb-2">
                    <h3 className="font-medium text-lg text-gray-900">Profile #{result.profile_id}</h3>
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

        {/* Query Understanding Display for Intelligent Search */}
        {aggregatedResponse && aggregatedResponse.query_understanding && (
          <div className="bg-gradient-to-r from-blue-50 to-indigo-50 rounded-lg shadow-sm p-6 mb-6 border border-blue-200">
            <h2 className="text-lg font-semibold mb-4 text-blue-800 flex items-center">
              <Search className="h-5 w-5 mr-2" />
              🧠 Query Understanding (Confidence: {(aggregatedResponse.confidence * 100).toFixed(1)}%)
            </h2>
            
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-4">
              {aggregatedResponse.query_understanding.geographic_region && (
                <div className="bg-white p-3 rounded-lg border border-blue-100">
                  <div className="text-xs font-medium text-blue-600 mb-1">📍 REGION</div>
                  <div className="text-sm font-semibold text-gray-900">{aggregatedResponse.query_understanding.geographic_region}</div>
                </div>
              )}
              
              {aggregatedResponse.query_understanding.time_period && (
                <div className="bg-white p-3 rounded-lg border border-blue-100">
                  <div className="text-xs font-medium text-blue-600 mb-1">📅 TIME PERIOD</div>
                  <div className="text-sm font-semibold text-gray-900">{aggregatedResponse.query_understanding.time_period}</div>
                </div>
              )}
              
              {aggregatedResponse.query_understanding.measurements && aggregatedResponse.query_understanding.measurements.length > 0 && (
                <div className="bg-white p-3 rounded-lg border border-blue-100">
                  <div className="text-xs font-medium text-blue-600 mb-1">🌡️ MEASUREMENTS</div>
                  <div className="text-sm font-semibold text-gray-900">{aggregatedResponse.query_understanding.measurements.join(', ')}</div>
                </div>
              )}
              
              {aggregatedResponse.query_understanding.query_types && aggregatedResponse.query_understanding.query_types.length > 0 && (
                <div className="bg-white p-3 rounded-lg border border-blue-100">
                  <div className="text-xs font-medium text-blue-600 mb-1">🔍 QUERY TYPE</div>
                  <div className="text-sm font-semibold text-gray-900">{aggregatedResponse.query_understanding.query_types.join(', ')}</div>
                </div>
              )}
            </div>
            
            {aggregatedResponse.filters_applied && aggregatedResponse.filters_applied.length > 0 && (
              <div className="bg-white p-3 rounded-lg border border-blue-100">
                <div className="text-xs font-medium text-blue-600 mb-2">🎯 FILTERS APPLIED</div>
                <div className="flex flex-wrap gap-2">
                  {aggregatedResponse.filters_applied.map((filter, index) => (
                    <span key={index} className="bg-blue-100 text-blue-800 px-2 py-1 rounded-full text-xs">
                      {filter}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Aggregated Statistics Display */}
        {aggregatedResponse && (
          <div className="bg-white rounded-lg shadow-sm p-6 mb-6">
            <h2 className="text-xl font-semibold mb-4">
              📊 <span className='text-green-600'>Oceanographic Statistics</span>
              <span className="ml-2 text-sm font-normal text-blue-600">
                ({aggregatedResponse.summary.total_profiles} profiles analyzed)
              </span>
            </h2>
            
            {/* Summary Statistics */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
              <div className="bg-blue-50 p-4 rounded-lg">
                <h3 className="font-semibold text-blue-800">📍 Geographic Coverage</h3>
                <p className="text-sm text-gray-600">
                  Lat: {aggregatedResponse.summary.geographic_bounds.latitude_range[0].toFixed(2)}° to {aggregatedResponse.summary.geographic_bounds.latitude_range[1].toFixed(2)}°
                </p>
                <p className="text-sm text-gray-600">
                  Lon: {aggregatedResponse.summary.geographic_bounds.longitude_range[0].toFixed(2)}° to {aggregatedResponse.summary.geographic_bounds.longitude_range[1].toFixed(2)}°
                </p>
              </div>
              
              <div className="bg-green-50 p-4 rounded-lg">
                <h3 className="font-semibold text-green-800">📅 Time Period</h3>
                <p className="text-sm text-gray-600">
                  {aggregatedResponse.summary.date_range.start ? new Date(aggregatedResponse.summary.date_range.start).toLocaleDateString() : 'N/A'} to {aggregatedResponse.summary.date_range.end ? new Date(aggregatedResponse.summary.date_range.end).toLocaleDateString() : 'N/A'}
                </p>
              </div>
              
              <div className="bg-purple-50 p-4 rounded-lg">
                <h3 className="font-semibold text-purple-800">🏛️ Data Sources</h3>
                <p className="text-sm text-gray-600">
                  {aggregatedResponse.summary.institutions.count} institutions
                </p>
              </div>
            </div>
            
            {/* Measurement Statistics */}
            {Object.keys(aggregatedResponse.measurements).length > 0 && (
              <div className="space-y-4">
                <h3 className="text-lg font-semibold text-gray-900">🌡️ Measurement Statistics</h3>
                
                {aggregatedResponse.measurements.temperature && (
                  <div className="bg-red-50 p-4 rounded-lg">
                    <h4 className="font-semibold text-red-800 mb-2">Temperature</h4>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                      <div>
                        <span className="font-medium text-gray-700">Average:</span> <span className="text-gray-900">{aggregatedResponse.measurements.temperature.average.toFixed(2)}°C</span>
                      </div>
                      <div>
                        <span className="font-medium text-gray-700">Range:</span> <span className="text-gray-900">{aggregatedResponse.measurements.temperature.min.toFixed(2)}°C to {aggregatedResponse.measurements.temperature.max.toFixed(2)}°C</span>
                      </div>
                      <div>
                        <span className="font-medium text-gray-700">Std Dev:</span> <span className="text-gray-900">{aggregatedResponse.measurements.temperature.std_deviation.toFixed(2)}°C</span>
                      </div>
                      <div>
                        <span className="font-medium text-gray-700">Measurements:</span> <span className="text-gray-900">{aggregatedResponse.measurements.temperature.total_measurements.toLocaleString()}</span>
                      </div>
                    </div>
                  </div>
                )}
                
                {aggregatedResponse.measurements.salinity && (
                  <div className="bg-blue-50 p-4 rounded-lg">
                    <h4 className="font-semibold text-blue-800 mb-2">Salinity</h4>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                      <div>
                        <span className="font-medium text-gray-700">Average:</span> <span className="text-gray-900">{aggregatedResponse.measurements.salinity.average.toFixed(2)} PSU</span>
                      </div>
                      <div>
                        <span className="font-medium text-gray-700">Range:</span> <span className="text-gray-900">{aggregatedResponse.measurements.salinity.min.toFixed(2)} to {aggregatedResponse.measurements.salinity.max.toFixed(2)} PSU</span>
                      </div>
                      <div>
                        <span className="font-medium text-gray-700">Std Dev:</span> <span className="text-gray-900">{aggregatedResponse.measurements.salinity.std_deviation.toFixed(2)} PSU</span>
                      </div>
                      <div>
                        <span className="font-medium text-gray-700">Measurements:</span> <span className="text-gray-900">{aggregatedResponse.measurements.salinity.total_measurements.toLocaleString()}</span>
                      </div>
                    </div>
                  </div>
                )}

                {aggregatedResponse.measurements.depth && (
                  <div className="bg-indigo-50 p-4 rounded-lg">
                    <h4 className="font-semibold text-indigo-800 mb-2">Depth/Pressure</h4>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                      <div>
                        <span className="font-medium text-gray-700">Average:</span> <span className="text-gray-900">{aggregatedResponse.measurements.depth.average.toFixed(2)} dbar</span>
                      </div>
                      <div>
                        <span className="font-medium text-gray-700">Range:</span> <span className="text-gray-900">{aggregatedResponse.measurements.depth.min.toFixed(2)} to {aggregatedResponse.measurements.depth.max.toFixed(2)} dbar</span>
                      </div>
                      <div>
                        <span className="font-medium text-gray-700">Std Dev:</span> <span className="text-gray-900">{aggregatedResponse.measurements.depth.std_deviation.toFixed(2)} dbar</span>
                      </div>
                      <div>
                        <span className="font-medium text-gray-700">Measurements:</span> <span className="text-gray-900">{aggregatedResponse.measurements.depth.total_measurements.toLocaleString()}</span>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* User Stats */}
        <div className="mt-8 bg-white rounded-lg shadow-sm p-6">
          <h2 className="text-lg font-semibold mb-4 text-gray-900">📊 Your Usage</h2>
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



