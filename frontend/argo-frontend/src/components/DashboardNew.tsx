"use client";

import React, { useState } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { Search, User, LogOut, Waves, Compass, Anchor, Ship, Fish, Navigation, Activity, MapPin, Calendar, Thermometer } from 'lucide-react';
import Link from 'next/link';





interface SearchResponse {
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
    [key: string]: {
      average: number;
      min: number;
      max: number;
      std_deviation: number;
      total_measurements: number;
      unit: string;
    };
  };
  query_understanding: {
    query_types: string[];
    geographic_region?: string;
    time_period?: string;
    measurements: string[];
    statistics: unknown;
  };
  confidence: number;
  filters_applied: string[];
}

const DashboardNew: React.FC = () => {
  const { user, logout, token } = useAuth();
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [searchResponse, setSearchResponse] = useState<SearchResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleSearch = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!query.trim()) return;
    
    // Check if user is authenticated
    if (!user || !token) {
      setError('Please log in to perform searches');
      return;
    }
    
    setLoading(true);
    setError(null);
    setSearchResponse(null);
    
    try {
      const response = await fetch('http://localhost:8000/search/intelligent', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({ query: query.trim() }),
      });
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'Search failed' }));
        throw new Error(errorData.detail || `Search failed: ${response.statusText}`);
      }
      
      const data = await response.json();
      console.log('Search response:', data); // Debug log to see actual structure
      setSearchResponse(data);
    } catch (err) {
      console.error('Search error:', err);
      setError(err instanceof Error ? err.message : 'Search failed');
    } finally {
      setLoading(false);
    }
  };

  // If user is not authenticated, show login prompt
  if (!user) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 via-cyan-50 to-teal-50 flex items-center justify-center">
        <div className="text-center p-8 bg-white/80 backdrop-blur-sm rounded-xl shadow-lg border border-blue-200">
          <Waves className="h-16 w-16 text-blue-500 mx-auto mb-4" />
          <h2 className="text-2xl font-bold text-blue-800 mb-4">Welcome to Ocean Explorer</h2>
          <p className="text-blue-600 mb-6">Please log in to explore oceanographic data</p>
          <Link 
            href="/login"
            className="px-6 py-3 bg-blue-500 hover:bg-blue-600 text-white rounded-full transition-colors duration-200"
          >
            Go to Login
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-cyan-50 to-teal-50 relative overflow-hidden">
      {/* Animated Ocean Background Elements */}
      <div className="absolute inset-0 opacity-20">
        <div className="absolute top-20 left-10 text-blue-400 animate-pulse">
          <Waves size={24} />
        </div>
        <div className="absolute top-40 right-20 text-cyan-400 animate-bounce">
          <Fish size={20} />
        </div>
        <div className="absolute bottom-40 left-20 text-teal-400 animate-pulse">
          <Anchor size={28} />
        </div>
        <div className="absolute bottom-20 right-10 text-blue-500 animate-bounce">
          <Ship size={22} />
        </div>
        <div className="absolute top-1/2 left-1/3 text-cyan-300 animate-pulse">
          <Navigation size={18} />
        </div>
        <div className="absolute top-1/4 right-1/3 text-teal-300 animate-bounce">
          <Compass size={26} />
        </div>
      </div>

      {/* Header */}
      <header className="relative z-10 p-4 flex justify-between items-center">
        <div className="flex items-center space-x-4">
          <div className="flex items-center space-x-2 text-blue-700">
            <Waves className="h-8 w-8" />
            <h1 className="text-2xl font-bold bg-gradient-to-r from-blue-600 to-cyan-600 bg-clip-text text-transparent">
              ARGO Ocean Explorer
            </h1>
          </div>
        </div>
        <div className="flex items-center space-x-4">
          <Link 
            href="/dashboard"
            className="px-4 py-2 bg-blue-100 hover:bg-blue-200 text-blue-700 rounded-full transition-colors duration-200 flex items-center space-x-2"
          >
            <Activity size={16} />
            <span>Classic Dashboard</span>
          </Link>
          {user && (
            <div className="flex items-center space-x-2 px-4 py-2 bg-white/70 backdrop-blur-sm rounded-full border border-blue-200">
              <User className="h-5 w-5 text-blue-600" />
              <span className="text-blue-800 font-medium">{user.username}</span>
            </div>
          )}
          <button
            onClick={logout}
            className="p-2 hover:bg-red-100 text-red-600 rounded-full transition-colors duration-200"
          >
            <LogOut size={20} />
          </button>
        </div>
      </header>

      {/* Main Content - Google-style centered search */}
      <main className="flex-1 flex flex-col items-center justify-center px-4 pt-20">
        <div className="text-center mb-12">
          <div className="flex items-center justify-center mb-6">
            <div className="p-4 bg-white/80 backdrop-blur-sm rounded-full shadow-lg border border-blue-200">
              <Waves className="h-16 w-16 text-blue-500" />
            </div>
          </div>
          <h1 className="text-6xl font-light text-blue-800 mb-2">
            Ocean
          </h1>
          <p className="text-xl text-blue-600 mb-8">
            Explore the depths of oceanographic data
          </p>
        </div>

        {/* Search Box - Google style */}
        <div className="w-full max-w-2xl mb-8">
          <form onSubmit={handleSearch} className="relative">
            <div className="relative bg-white/80 backdrop-blur-sm rounded-full shadow-lg border border-blue-200 hover:shadow-xl transition-shadow duration-300">
              <div className="absolute left-4 top-1/2 transform -translate-y-1/2">
                <Search className="h-5 w-5 text-blue-400" />
              </div>
              <input
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder={user ? "Search ocean data: temperature, salinity, depth profiles..." : "Please log in to search"}
                disabled={!user || !token}
                className="w-full pl-12 pr-16 py-4 bg-transparent rounded-full focus:outline-none focus:ring-2 focus:ring-blue-300 text-gray-800 placeholder-blue-400 disabled:opacity-50 disabled:cursor-not-allowed"
              />
              <button
                type="submit"
                disabled={loading || !query.trim() || !user || !token}
                className="absolute right-2 top-1/2 transform -translate-y-1/2 px-6 py-2 bg-blue-500 hover:bg-blue-600 disabled:bg-blue-300 text-white rounded-full transition-colors duration-200 disabled:cursor-not-allowed"
              >
                {loading ? (
                  <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                ) : (
                  'Search'
                )}
              </button>
            </div>
          </form>
        </div>

        {/* Quick Search Suggestions - Google style */}
        {!searchResponse && !loading && (
          <div className="flex flex-wrap justify-center gap-3 mb-12">
            {[
              "Temperature in Pacific Ocean",
              "Salinity profiles 2023",
              "Deep water currents",
              "Arctic Ocean data",
              "Tropical temperature anomalies"
            ].map((suggestion, index) => (
              <button
                key={index}
                onClick={() => {
                  setQuery(suggestion);
                  handleSearch();
                }}
                className="px-4 py-2 bg-white/60 hover:bg-white/80 text-blue-700 rounded-full border border-blue-200 transition-colors duration-200 text-sm"
              >
                {suggestion}
              </button>
            ))}
          </div>
        )}

        {/* Error Display */}
        {error && (
          <div className="w-full max-w-4xl mb-6">
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg">
              <p>Error: {error}</p>
            </div>
          </div>
        )}

        {/* Search Results */}
        {searchResponse && (
          <div className="w-full max-w-6xl mt-8">
            {/* Query Understanding */}
            <div className="bg-white/80 backdrop-blur-sm rounded-lg shadow-lg border border-blue-200 p-6 mb-6">
              <h3 className="text-lg font-semibold text-blue-800 mb-4 flex items-center">
                <Activity className="h-5 w-5 mr-2" />
                Query Understanding
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                <div className="bg-blue-50 p-4 rounded-lg border border-blue-200">
                  <div className="text-sm text-blue-600 mb-1">Confidence</div>
                  <div className="text-lg font-semibold text-blue-800">
                    {(searchResponse.confidence * 100).toFixed(1)}%
                  </div>
                </div>
                
                {searchResponse.query_understanding.geographic_region && (
                  <div className="bg-green-50 p-4 rounded-lg border border-green-200">
                    <div className="text-sm text-green-600 mb-1 flex items-center">
                      <MapPin className="h-4 w-4 mr-1" />
                      Geographic Region
                    </div>
                    <div className="text-lg font-semibold text-green-800">
                      {searchResponse.query_understanding.geographic_region}
                    </div>
                  </div>
                )}
                
                {searchResponse.query_understanding.time_period && (
                  <div className="bg-purple-50 p-4 rounded-lg border border-purple-200">
                    <div className="text-sm text-purple-600 mb-1 flex items-center">
                      <Calendar className="h-4 w-4 mr-1" />
                      Time Period
                    </div>
                    <div className="text-lg font-semibold text-purple-800">
                      {searchResponse.query_understanding.time_period}
                    </div>
                  </div>
                )}
                
                {searchResponse.query_understanding.measurements && searchResponse.query_understanding.measurements.length > 0 && (
                  <div className="bg-orange-50 p-4 rounded-lg border border-orange-200">
                    <div className="text-sm text-orange-600 mb-1 flex items-center">
                      <Thermometer className="h-4 w-4 mr-1" />
                      Measurements
                    </div>
                    <div className="text-lg font-semibold text-orange-800">
                      {searchResponse.query_understanding.measurements.join(', ')}
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* Results */}
            <div className="bg-white/80 backdrop-blur-sm rounded-lg shadow-lg border border-blue-200 p-6">
              <h3 className="text-lg font-semibold text-blue-800 mb-4">
                Search Results ({searchResponse.summary?.total_profiles || 0} profiles found)
              </h3>
              
              {searchResponse.summary?.total_profiles > 0 ? (
                <div className="space-y-6">
                  {/* Summary Cards */}
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {/* Data Summary */}
                    <div className="bg-gradient-to-br from-blue-50 to-cyan-50 p-6 rounded-lg border border-blue-200">
                      <h4 className="font-semibold text-blue-800 mb-3 flex items-center">
                        <Activity className="h-5 w-5 mr-2" />
                        Data Overview
                      </h4>
                      <div className="space-y-2 text-sm">
                        <p><span className="text-blue-600">Total Profiles:</span> <span className="font-semibold text-blue-800">{searchResponse.summary.total_profiles.toLocaleString()}</span></p>
                        <p><span className="text-blue-600">Date Range:</span> <span className="font-semibold text-blue-800">{searchResponse.summary.date_range.start}</span></p>
                        <p><span className="text-blue-600">to:</span> <span className="font-semibold text-blue-800">{searchResponse.summary.date_range.end}</span></p>
                        <p><span className="text-blue-600">Institution:</span> <span className="font-semibold text-blue-800">{searchResponse.summary.institutions.names.join(', ')}</span></p>
                      </div>
                    </div>
                    
                    {/* Geographic Coverage */}
                    <div className="bg-gradient-to-br from-green-50 to-emerald-50 p-6 rounded-lg border border-green-200">
                      <h4 className="font-semibold text-green-800 mb-3 flex items-center">
                        <MapPin className="h-5 w-5 mr-2" />
                        Geographic Coverage
                      </h4>
                      <div className="space-y-2 text-sm">
                        <p><span className="text-green-600">Latitude:</span> <span className="font-semibold text-green-800">{searchResponse.summary.geographic_bounds.latitude_range[0].toFixed(2)}° to {searchResponse.summary.geographic_bounds.latitude_range[1].toFixed(2)}°</span></p>
                        <p><span className="text-green-600">Longitude:</span> <span className="font-semibold text-green-800">{searchResponse.summary.geographic_bounds.longitude_range[0].toFixed(2)}° to {searchResponse.summary.geographic_bounds.longitude_range[1].toFixed(2)}°</span></p>
                        <p><span className="text-green-600">Center:</span> <span className="font-semibold text-green-800">[{searchResponse.summary.geographic_bounds.center[0].toFixed(2)}°, {searchResponse.summary.geographic_bounds.center[1].toFixed(2)}°]</span></p>
                      </div>
                    </div>
                    
                    {/* Applied Filters */}
                    <div className="bg-gradient-to-br from-purple-50 to-indigo-50 p-6 rounded-lg border border-purple-200">
                      <h4 className="font-semibold text-purple-800 mb-3 flex items-center">
                        <Calendar className="h-5 w-5 mr-2" />
                        Applied Filters
                      </h4>
                      <div className="space-y-1 text-sm">
                        {searchResponse.filters_applied.map((filter, index) => (
                          <p key={index} className="text-purple-600">• {filter}</p>
                        ))}
                      </div>
                    </div>
                  </div>
                  
                  {/* Measurement Statistics */}
                  {Object.keys(searchResponse.measurements).length > 0 && (
                    <div>
                      <h4 className="text-lg font-semibold text-blue-800 mb-4 flex items-center">
                        <Thermometer className="h-5 w-5 mr-2" />
                        Measurement Statistics
                      </h4>
                      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                        {Object.entries(searchResponse.measurements).map(([measurementType, data]) => (
                          <div key={measurementType} className="bg-gradient-to-br from-orange-50 to-yellow-50 p-6 rounded-lg border border-orange-200">
                            <h5 className="font-semibold text-orange-800 mb-3 capitalize flex items-center">
                              <Thermometer className="h-4 w-4 mr-2" />
                              {measurementType}
                            </h5>
                            <div className="space-y-2 text-sm">
                              <p><span className="text-orange-600">Average:</span> <span className="font-semibold text-orange-800">{data.average.toFixed(2)} {data.unit}</span></p>
                              <p><span className="text-orange-600">Range:</span> <span className="font-semibold text-orange-800">{data.min} - {data.max} {data.unit}</span></p>
                              <p><span className="text-orange-600">Std Dev:</span> <span className="font-semibold text-orange-800">{data.std_deviation.toFixed(2)} {data.unit}</span></p>
                              <p><span className="text-orange-600">Total Points:</span> <span className="font-semibold text-orange-800">{data.total_measurements.toLocaleString()}</span></p>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              ) : (
                <div className="text-center py-8">
                  <div className="text-blue-400 mb-2">
                    <Fish size={48} className="mx-auto opacity-50" />
                  </div>
                  <p className="text-blue-600">No ocean profiles found matching your search criteria.</p>
                </div>
              )}
            </div>
          </div>
        )}
      </main>

      {/* Footer - Ocean Stats */}
      {user && (
        <div className="relative z-10 mt-auto p-6">
          <div className="bg-white/60 backdrop-blur-sm rounded-xl border border-blue-200 p-6">
            <h2 className="text-lg font-semibold text-blue-800 mb-4 flex items-center">
              <User className="h-5 w-5 mr-2 text-cyan-400" />
              🌊 Your Ocean Research Activity
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div className="text-center p-4 bg-gradient-to-br from-cyan-100 to-blue-100 rounded-xl border border-cyan-200">
                <div className="text-2xl font-bold text-cyan-700 mb-1">{user?.daily_query_count || 0}</div>
                <div className="text-sm text-cyan-600">Searches Today</div>
              </div>
              <div className="text-center p-4 bg-gradient-to-br from-emerald-100 to-green-100 rounded-xl border border-emerald-200">
                <div className="text-2xl font-bold text-emerald-700 mb-1">{user?.total_queries || 0}</div>
                <div className="text-sm text-emerald-600">Total Ocean Queries</div>
              </div>
              <div className="text-center p-4 bg-gradient-to-br from-purple-100 to-indigo-100 rounded-xl border border-purple-200">
                <div className="text-2xl font-bold text-purple-700 mb-1">{user?.user_tier}</div>
                <div className="text-sm text-purple-600">Research Tier</div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default DashboardNew;