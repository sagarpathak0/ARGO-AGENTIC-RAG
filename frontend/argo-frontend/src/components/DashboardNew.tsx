"use client";

import React, { useState } from "react";
import { useAuth } from "@/contexts/AuthContext";
import {
  Search,
  User,
  LogOut,
  Waves,
  Compass,
  Anchor,
  Ship,
  Fish,
  Navigation,
  Activity,
  MapPin,
  Calendar,
  Thermometer,
} from "lucide-react";
import Link from "next/link";

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
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [searchResponse, setSearchResponse] = useState<SearchResponse | null>(
    null
  );
  const [error, setError] = useState<string | null>(null);

  const handleSearch = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!query.trim()) return;

    // Check if user is authenticated
    if (!user || !token) {
      setError("Please log in to perform searches");
      return;
    }

    setLoading(true);
    setError(null);
    setSearchResponse(null);

    try {
      const response = await fetch("http://localhost:8000/search/intelligent", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ query: query.trim() }),
      });

      if (!response.ok) {
        const errorData = await response
          .json()
          .catch(() => ({ detail: "Search failed" }));
        throw new Error(
          errorData.detail || `Search failed: ${response.statusText}`
        );
      }

      const data = await response.json();
      console.log("Search response:", data); // Debug log to see actual structure
      setSearchResponse(data);
    } catch (err) {
      console.error("Search error:", err);
      setError(err instanceof Error ? err.message : "Search failed");
    } finally {
      setLoading(false);
    }
  };

  // If user is not authenticated, show login prompt
  if (!user) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-900 via-blue-900 to-teal-800 flex items-center justify-center">
        <div className="text-center p-8 bg-white/90 backdrop-blur-sm rounded-xl shadow-2xl border border-blue-300">
          <Waves className="h-16 w-16 text-blue-500 mx-auto mb-4" />
          <h2 className="text-2xl font-bold text-blue-800 mb-4">
            Welcome to Ocean Explorer
          </h2>
          <p className="text-blue-600 mb-6">
            Please log in to explore oceanographic data
          </p>
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
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-blue-900 to-teal-800 relative overflow-hidden">
      {/* Animated Ocean Background Elements */}
      <div className="absolute inset-0 opacity-30">
        {/* Floating bubbles */}
        <div className="absolute top-10 left-10 text-cyan-300 animate-bounce">
          <div className="w-3 h-3 bg-cyan-300 rounded-full opacity-60"></div>
        </div>
        <div className="absolute top-32 left-20 text-cyan-400 animate-pulse">
          <div className="w-2 h-2 bg-cyan-400 rounded-full opacity-40"></div>
        </div>
        <div className="absolute top-20 left-96 text-blue-300 animate-bounce">
          <div className="w-4 h-4 bg-blue-300 rounded-full opacity-50"></div>
        </div>
        
        {/* Seaweed */}
        <div className="absolute bottom-0 left-10 text-green-400 animate-pulse">
          <div className="w-2 h-32 bg-gradient-to-t from-green-600 to-green-400 rounded-t-full transform rotate-12"></div>
        </div>
        <div className="absolute bottom-0 left-24 text-green-500 animate-pulse">
          <div className="w-3 h-28 bg-gradient-to-t from-green-700 to-green-500 rounded-t-full transform -rotate-6"></div>
        </div>
        <div className="absolute bottom-0 right-16 text-emerald-400 animate-pulse">
          <div className="w-2 h-36 bg-gradient-to-t from-emerald-600 to-emerald-400 rounded-t-full transform rotate-8"></div>
        </div>
        <div className="absolute bottom-0 right-32 text-emerald-500 animate-pulse">
          <div className="w-3 h-24 bg-gradient-to-t from-emerald-700 to-emerald-500 rounded-t-full transform -rotate-12"></div>
        </div>
        
        {/* Coral formations */}
        <div className="absolute bottom-4 left-40 text-pink-400 animate-pulse">
          <div className="w-8 h-12 bg-gradient-to-t from-pink-600 to-pink-400 rounded-full opacity-70"></div>
        </div>
        <div className="absolute bottom-2 right-48 text-orange-400 animate-pulse">
          <div className="w-6 h-8 bg-gradient-to-t from-orange-600 to-orange-400 rounded-full opacity-60"></div>
        </div>
        
        {/* Original ocean elements */}
        <div className="absolute top-20 left-10 text-cyan-300 animate-pulse">
          <Waves size={24} />
        </div>
        <div className="absolute top-40 right-20 text-cyan-400 animate-bounce">
          <Fish size={20} />
        </div>
        <div className="absolute top-60 left-1/4 text-blue-300 animate-bounce">
          <Fish size={16} className="transform -scale-x-100" />
        </div>
        <div className="absolute top-80 right-1/3 text-teal-300 animate-bounce">
          <Fish size={18} />
        </div>
        <div className="absolute bottom-40 left-20 text-teal-400 animate-pulse">
          <Anchor size={28} />
        </div>
        <div className="absolute bottom-20 right-10 text-blue-400 animate-bounce">
          <Ship size={22} />
        </div>
        <div className="absolute top-1/2 left-1/3 text-cyan-300 animate-pulse">
          <Navigation size={18} />
        </div>
        <div className="absolute top-1/4 right-1/3 text-teal-300 animate-bounce">
          <Compass size={26} />
        </div>
        
        {/* Additional scattered fish */}
        <div className="absolute top-96 left-1/2 text-blue-300 animate-bounce">
          <Fish size={14} className="transform rotate-45" />
        </div>
        <div className="absolute bottom-32 right-1/4 text-cyan-300 animate-bounce">
          <Fish size={22} className="transform -scale-x-100 rotate-12" />
        </div>
      </div>

      {/* Header */}
      <header className="relative z-10 p-4 flex flex-col sm:flex-row justify-between items-center gap-4">
        <div className="flex items-center space-x-4">
          <div className="flex items-center space-x-2 text-cyan-200">
            <Waves className="h-6 w-6 sm:h-8 sm:w-8" />
            <h1 className="text-xl sm:text-2xl font-bold bg-gradient-to-r from-cyan-300 to-blue-300 bg-clip-text text-transparent">
              ARGO Ocean Explorer
            </h1>
          </div>
        </div>
        <div className="flex items-center space-x-2 sm:space-x-4">
          <Link
            href="/dashboard"
            className="px-3 py-2 sm:px-4 sm:py-2 bg-blue-800/60 hover:bg-blue-700/60 text-cyan-200 rounded-full transition-colors duration-200 flex items-center space-x-2 border border-cyan-400/30 text-sm"
          >
            <Activity size={14} />
            <span className="hidden sm:inline">Classic Dashboard</span>
            <span className="sm:hidden">Dashboard</span>
          </Link>
          {user && (
            <div className="flex items-center space-x-2 px-3 py-2 sm:px-4 sm:py-2 bg-slate-800/70 backdrop-blur-sm rounded-full border border-cyan-400/30">
              <User className="h-4 w-4 sm:h-5 sm:w-5 text-cyan-400" />
              <span className="text-cyan-200 font-medium text-sm sm:text-base">{user.username}</span>
            </div>
          )}
          <button
            onClick={logout}
            aria-label="Logout"
            className="p-2 hover:bg-red-800/60 text-red-400 rounded-full transition-colors duration-200"
          >
            <LogOut size={18} />
          </button>
        </div>
      </header>

      {/* Main Content - Google-style centered search */}
      <main className="flex-1 flex flex-col items-center justify-center px-4 pt-8 sm:pt-20">
        <div className="text-center mb-8 sm:mb-12">
          <div className="flex items-center justify-center mb-4 sm:mb-6">
            <div className="p-3 sm:p-4 bg-slate-800/80 backdrop-blur-sm rounded-full shadow-2xl border border-cyan-400/30">
              <Waves className="h-12 w-12 sm:h-16 sm:w-16 text-cyan-400" />
            </div>
          </div>
          <h1 className="text-4xl sm:text-6xl font-light text-cyan-100 mb-2">Ocean</h1>
          <p className="text-lg sm:text-xl text-cyan-200 mb-6 sm:mb-8 px-4">
            Explore the depths of oceanographic data
          </p>
        </div>

        {/* Search Box - Google style */}
        <div className="w-full max-w-2xl mb-6 sm:mb-8">
          <form onSubmit={handleSearch} className="relative">
            <div className="relative bg-slate-800/80 backdrop-blur-sm rounded-full shadow-2xl border border-cyan-400/30 hover:shadow-cyan-400/20 hover:shadow-2xl transition-all duration-300">
              <div className="absolute left-3 sm:left-4 top-1/2 transform -translate-y-1/2">
                <Search className="h-4 w-4 sm:h-5 sm:w-5 text-cyan-400" />
              </div>
              <input
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder={
                  user
                    ? "Search ocean data: temperature, salinity, depth profiles..."
                    : "Please log in to search"
                }
                disabled={!user || !token}
                className="w-full pl-10 sm:pl-12 pr-20 sm:pr-16 py-3 sm:py-4 bg-transparent rounded-full focus:outline-none focus:ring-2 focus:ring-cyan-400/50 text-cyan-100 placeholder-cyan-400 disabled:opacity-50 disabled:cursor-not-allowed text-sm sm:text-base"
              />
              <button
                type="submit"
                disabled={loading || !query.trim() || !user || !token}
                className="absolute right-1 sm:right-2 top-1/2 transform -translate-y-1/2 px-4 sm:px-6 py-2 bg-cyan-600 hover:bg-cyan-500 disabled:bg-cyan-800 text-white rounded-full transition-colors duration-200 disabled:cursor-not-allowed text-sm sm:text-base"
              >
                {loading ? (
                  <div className="w-4 h-4 sm:w-5 sm:h-5 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                ) : (
                  "Search"
                )}
              </button>
            </div>
          </form>
        </div>

        {/* Quick Search Suggestions - Google style */}
        {!searchResponse && !loading && (
          <div className="w-full max-w-4xl mb-12">
            <div className="text-center mb-6">
              <h3 className="text-lg font-medium text-cyan-200 mb-2">🔍 Explore Indian Ocean Data (1999-2012)</h3>
              <p className="text-sm text-cyan-300">Temperature • Depth • Pressure • Salinity measurements available</p>
            </div>
            
            {/* Category-based suggestions */}
            <div className="space-y-4">
              {/* Temperature Analysis */}
              <div className="text-center">
                <h4 className="text-sm font-medium text-cyan-300 mb-3">🌡️ Temperature Analysis</h4>
                <div className="flex flex-wrap justify-center gap-2">
                  {[
                    "Indian Ocean temperature trends 2000-2010",
                    "Surface temperature variations 1999-2012",
                    "Deep water temperature profiles",
                    "Seasonal temperature changes Indian Ocean",
                    "Temperature anomalies 2004 tsunami period"
                  ].map((suggestion, index) => (
                    <button
                      key={`temp-${index}`}
                      onClick={() => {
                        setQuery(suggestion);
                        handleSearch();
                      }}
                      className="px-3 py-2 bg-slate-800/60 hover:bg-slate-700/80 text-cyan-200 rounded-full border border-cyan-400/30 transition-all duration-200 text-sm backdrop-blur-sm hover:border-cyan-300/50 hover:shadow-lg hover:shadow-cyan-400/20"
                    >
                      {suggestion}
                    </button>
                  ))}
                </div>
              </div>

              {/* Salinity Studies */}
              <div className="text-center">
                <h4 className="text-sm font-medium text-emerald-300 mb-3">🧪 Salinity Studies</h4>
                <div className="flex flex-wrap justify-center gap-2">
                  {[
                    "Indian Ocean salinity profiles 1999-2012",
                    "Bay of Bengal fresh water influence",
                    "Arabian Sea salinity patterns",
                    "Monsoon impact on salinity levels",
                    "Deep water salinity variations"
                  ].map((suggestion, index) => (
                    <button
                      key={`salinity-${index}`}
                      onClick={() => {
                        setQuery(suggestion);
                        handleSearch();
                      }}
                      className="px-3 py-2 bg-slate-800/60 hover:bg-slate-700/80 text-emerald-200 rounded-full border border-emerald-400/30 transition-all duration-200 text-sm backdrop-blur-sm hover:border-emerald-300/50 hover:shadow-lg hover:shadow-emerald-400/20"
                    >
                      {suggestion}
                    </button>
                  ))}
                </div>
              </div>

              {/* Depth & Pressure Analysis */}
              <div className="text-center">
                <h4 className="text-sm font-medium text-blue-300 mb-3">📊 Depth & Pressure Analysis</h4>
                <div className="flex flex-wrap justify-center gap-2">
                  {[
                    "Deep ocean pressure measurements",
                    "Depth profiles Indian Ocean basins",
                    "Pressure variations with depth",
                    "Abyssal plain characteristics",
                    "Mid-water pressure patterns 2000s"
                  ].map((suggestion, index) => (
                    <button
                      key={`depth-${index}`}
                      onClick={() => {
                        setQuery(suggestion);
                        handleSearch();
                      }}
                      className="px-3 py-2 bg-slate-800/60 hover:bg-slate-700/80 text-blue-200 rounded-full border border-blue-400/30 transition-all duration-200 text-sm backdrop-blur-sm hover:border-blue-300/50 hover:shadow-lg hover:shadow-blue-400/20"
                    >
                      {suggestion}
                    </button>
                  ))}
                </div>
              </div>

              {/* Time Period & Regional Focus */}
              <div className="text-center">
                <h4 className="text-sm font-medium text-purple-300 mb-3">�️ Time Periods & Regions</h4>
                <div className="flex flex-wrap justify-center gap-2">
                  {[
                    "Early 2000s oceanographic conditions",
                    "2004 Indian Ocean changes",
                    "Decade comparison 1999-2009",
                    "Western Indian Ocean data",
                    "Southern Indian Ocean patterns 2010-2012"
                  ].map((suggestion, index) => (
                    <button
                      key={`period-${index}`}
                      onClick={() => {
                        setQuery(suggestion);
                        handleSearch();
                      }}
                      className="px-3 py-2 bg-slate-800/60 hover:bg-slate-700/80 text-purple-200 rounded-full border border-purple-400/30 transition-all duration-200 text-sm backdrop-blur-sm hover:border-purple-300/50 hover:shadow-lg hover:shadow-purple-400/20"
                    >
                      {suggestion}
                    </button>
                  ))}
                </div>
              </div>

              {/* Multi-parameter Queries */}
              <div className="text-center">
                <h4 className="text-sm font-medium text-orange-300 mb-3">🔗 Multi-parameter Analysis</h4>
                <div className="flex flex-wrap justify-center gap-2">
                  {[
                    "Temperature and salinity correlation",
                    "Pressure depth relationship analysis",
                    "All parameters 2005-2008 period",
                    "Vertical profile complete data",
                    "Compare temperature salinity trends"
                  ].map((suggestion, index) => (
                    <button
                      key={`multi-${index}`}
                      onClick={() => {
                        setQuery(suggestion);
                        handleSearch();
                      }}
                      className="px-3 py-2 bg-slate-800/60 hover:bg-slate-700/80 text-orange-200 rounded-full border border-orange-400/30 transition-all duration-200 text-sm backdrop-blur-sm hover:border-orange-300/50 hover:shadow-lg hover:shadow-orange-400/20"
                    >
                      {suggestion}
                    </button>
                  ))}
                </div>
              </div>
            </div>
            
            {/* Data availability notice */}
            <div className="mt-6 text-center">
              <p className="text-xs text-cyan-400/70 bg-slate-800/40 rounded-lg px-4 py-2 inline-block">
                💡 Currently featuring Indian Ocean ARGO float data from 1999-2012
              </p>
            </div>
          </div>
        )}

        {/* Error Display */}
        {error && (
          <div className="w-full max-w-4xl mb-6">
            <div className="bg-red-900/60 border border-red-400/30 text-red-200 px-4 py-3 rounded-lg backdrop-blur-sm">
              <p>Error: {error}</p>
            </div>
          </div>
        )}

        {/* Query Understanding */}
        {searchResponse && (
          <div className="w-full max-w-6xl mt-8">
            {/* Query Understanding */}
            <div className="bg-gradient-to-br from-slate-800/80 to-blue-800/80 backdrop-blur-sm rounded-xl shadow-2xl border border-cyan-400/30 p-8 mb-8">
              <h3 className="text-xl font-bold text-cyan-100 mb-6 flex items-center">
                <Activity className="h-6 w-6 mr-3 text-cyan-400" />
                🧠 Query Understanding
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                <div className="bg-gradient-to-br from-cyan-900/60 to-blue-900/60 p-6 rounded-xl border border-cyan-400/20 backdrop-blur-sm">
                  <div className="text-sm text-cyan-300 mb-2 font-medium">AI Confidence</div>
                  <div className="text-2xl font-bold text-cyan-100 mb-1">
                    {(searchResponse.confidence * 100).toFixed(1)}%
                  </div>
                  <div className="w-full bg-slate-700 rounded-full h-2">
                    <div className="bg-gradient-to-r from-cyan-500 to-blue-500 h-2 rounded-full transition-all duration-1000 w-full"></div>
                  </div>
                </div>

                {searchResponse.query_understanding.geographic_region && (
                  <div className="bg-gradient-to-br from-emerald-900/60 to-teal-900/60 p-6 rounded-xl border border-emerald-400/20 backdrop-blur-sm">
                    <div className="text-sm text-emerald-300 mb-2 font-medium flex items-center">
                      <MapPin className="h-4 w-4 mr-2" />
                      Geographic Region
                    </div>
                    <div className="text-lg font-bold text-emerald-100">
                      {searchResponse.query_understanding.geographic_region}
                    </div>
                  </div>
                )}

                {searchResponse.query_understanding.time_period && (
                  <div className="bg-gradient-to-br from-purple-900/60 to-indigo-900/60 p-6 rounded-xl border border-purple-400/20 backdrop-blur-sm">
                    <div className="text-sm text-purple-300 mb-2 font-medium flex items-center">
                      <Calendar className="h-4 w-4 mr-2" />
                      Time Period
                    </div>
                    <div className="text-lg font-bold text-purple-100">
                      {searchResponse.query_understanding.time_period}
                    </div>
                  </div>
                )}

                {searchResponse.query_understanding.measurements &&
                  searchResponse.query_understanding.measurements.length > 0 && (
                    <div className="bg-gradient-to-br from-orange-900/60 to-red-900/60 p-6 rounded-xl border border-orange-400/20 backdrop-blur-sm">
                      <div className="text-sm text-orange-300 mb-2 font-medium flex items-center">
                        <Thermometer className="h-4 w-4 mr-2" />
                        Measurements
                      </div>
                      <div className="text-lg font-bold text-orange-100">
                        {searchResponse.query_understanding.measurements.join(", ")}
                      </div>
                    </div>
                  )}
              </div>
            </div>

            {/* Results */}
            <div className="bg-gradient-to-br from-slate-800/80 to-blue-800/80 backdrop-blur-sm rounded-xl shadow-2xl border border-cyan-400/30 p-8">
              <h3 className="text-xl font-bold text-cyan-100 mb-6 flex items-center">
                <Compass className="h-6 w-6 mr-3 text-cyan-400" />
                🔍 Search Results ({searchResponse.summary?.total_profiles || 0} profiles found)
              </h3>

              {searchResponse.summary?.total_profiles > 0 ? (
                <div className="space-y-8">
                  {/* Summary Cards */}
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {/* Data Summary */}
                    <div className="bg-gradient-to-br from-blue-900/60 to-cyan-900/60 p-6 rounded-xl border border-blue-400/20 backdrop-blur-sm">
                      <h4 className="font-bold text-blue-100 mb-4 flex items-center">
                        <Activity className="h-5 w-5 mr-2 text-cyan-400" />
                        📊 Data Overview
                      </h4>
                      <div className="space-y-3 text-sm">
                        <p>
                          <span className="text-cyan-300">Total Profiles:</span>{" "}
                          <span className="font-bold text-cyan-100">
                            {searchResponse.summary.total_profiles.toLocaleString()}
                          </span>
                        </p>
                        <p>
                          <span className="text-cyan-300">Date Range:</span>{" "}
                          <span className="font-bold text-cyan-100">
                            {searchResponse.summary.date_range.start}
                          </span>
                        </p>
                        <p>
                          <span className="text-cyan-300">to:</span>{" "}
                          <span className="font-bold text-cyan-100">
                            {searchResponse.summary.date_range.end}
                          </span>
                        </p>
                        <p>
                          <span className="text-cyan-300">Institution:</span>{" "}
                          <span className="font-bold text-cyan-100">
                            {searchResponse.summary.institutions.names.join(", ")}
                          </span>
                        </p>
                      </div>
                    </div>

                    {/* Geographic Coverage */}
                    <div className="bg-gradient-to-br from-emerald-900/60 to-teal-900/60 p-6 rounded-xl border border-emerald-400/20 backdrop-blur-sm">
                      <h4 className="font-bold text-emerald-100 mb-4 flex items-center">
                        <MapPin className="h-5 w-5 mr-2 text-emerald-400" />
                        🗺️ Geographic Coverage
                      </h4>
                      <div className="space-y-3 text-sm">
                        <p>
                          <span className="text-emerald-300">Latitude:</span>{" "}
                          <span className="font-bold text-emerald-100">
                            {searchResponse.summary.geographic_bounds.latitude_range[0].toFixed(2)}° to{" "}
                            {searchResponse.summary.geographic_bounds.latitude_range[1].toFixed(2)}°
                          </span>
                        </p>
                        <p>
                          <span className="text-emerald-300">Longitude:</span>{" "}
                          <span className="font-bold text-emerald-100">
                            {searchResponse.summary.geographic_bounds.longitude_range[0].toFixed(2)}° to{" "}
                            {searchResponse.summary.geographic_bounds.longitude_range[1].toFixed(2)}°
                          </span>
                        </p>
                        <p>
                          <span className="text-emerald-300">Center:</span>{" "}
                          <span className="font-bold text-emerald-100">
                            [{searchResponse.summary.geographic_bounds.center[0].toFixed(2)}°,{" "}
                            {searchResponse.summary.geographic_bounds.center[1].toFixed(2)}°]
                          </span>
                        </p>
                      </div>
                    </div>

                    {/* Applied Filters */}
                    <div className="bg-gradient-to-br from-purple-900/60 to-indigo-900/60 p-6 rounded-xl border border-purple-400/20 backdrop-blur-sm">
                      <h4 className="font-bold text-purple-100 mb-4 flex items-center">
                        <Calendar className="h-5 w-5 mr-2 text-purple-400" />
                        🔍 Applied Filters
                      </h4>
                      <div className="space-y-2 text-sm">
                        {searchResponse.filters_applied.map((filter, index) => (
                          <p key={index} className="text-purple-300">
                            • {filter}
                          </p>
                        ))}
                      </div>
                    </div>
                  </div>

                  {/* Measurement Statistics */}
                  {Object.keys(searchResponse.measurements).length > 0 && (
                    <div>
                      <h4 className="text-xl font-bold text-cyan-100 mb-6 flex items-center">
                        <Thermometer className="h-6 w-6 mr-3 text-orange-400" />
                        🌡️ Measurement Statistics
                      </h4>
                      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                        {Object.entries(searchResponse.measurements).map(
                          ([measurementType, data]) => (
                            <div
                              key={measurementType}
                              className="bg-gradient-to-br from-orange-900/60 to-red-900/60 p-6 rounded-xl border border-orange-400/20 backdrop-blur-sm"
                            >
                              <h5 className="font-bold text-orange-100 mb-4 capitalize flex items-center">
                                <Thermometer className="h-5 w-5 mr-2 text-orange-400" />
                                {measurementType}
                              </h5>
                              <div className="space-y-3 text-sm">
                                <p>
                                  <span className="text-orange-300">Average:</span>{" "}
                                  <span className="font-bold text-orange-100">
                                    {data.average.toFixed(2)} {data.unit}
                                  </span>
                                </p>
                                <p>
                                  <span className="text-orange-300">Range:</span>{" "}
                                  <span className="font-bold text-orange-100">
                                    {data.min} - {data.max} {data.unit}
                                  </span>
                                </p>
                                <p>
                                  <span className="text-orange-300">Std Dev:</span>{" "}
                                  <span className="font-bold text-orange-100">
                                    {data.std_deviation.toFixed(2)} {data.unit}
                                  </span>
                                </p>
                                <p>
                                  <span className="text-orange-300">Total Points:</span>{" "}
                                  <span className="font-bold text-orange-100">
                                    {data.total_measurements.toLocaleString()}
                                  </span>
                                </p>
                              </div>
                            </div>
                          )
                        )}
                      </div>
                    </div>
                  )}
                </div>
              ) : (
                <div className="text-center py-12">
                  <div className="text-cyan-400 mb-4">
                    <Fish size={64} className="mx-auto opacity-60" />
                  </div>
                  <p className="text-cyan-200 text-lg">
                    🌊 No ocean profiles found matching your search criteria.
                  </p>
                  <p className="text-cyan-300 text-sm mt-2">
                    Try adjusting your search terms or exploring different regions.
                  </p>
                </div>
              )}
            </div>
          </div>
        )}
      </main>

      {/* Footer - Ocean Stats */}
      {user && (
        <div className="relative z-10 mt-auto p-6">
          <div className="bg-gradient-to-br from-slate-800/80 to-blue-800/80 backdrop-blur-sm rounded-xl border border-cyan-400/30 p-6">
            <h2 className="text-lg font-bold text-cyan-100 mb-4 flex items-center">
              <User className="h-5 w-5 mr-2 text-cyan-400" />
              🌊 Your Ocean Research Activity
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div className="text-center p-4 bg-gradient-to-br from-cyan-900/60 to-blue-900/60 rounded-xl border border-cyan-400/20">
                <div className="text-2xl font-bold text-cyan-100 mb-1">
                  {user?.daily_query_count || 0}
                </div>
                <div className="text-sm text-cyan-300">Searches Today</div>
              </div>
              <div className="text-center p-4 bg-gradient-to-br from-emerald-900/60 to-teal-900/60 rounded-xl border border-emerald-400/20">
                <div className="text-2xl font-bold text-emerald-100 mb-1">
                  {user?.total_queries || 0}
                </div>
                <div className="text-sm text-emerald-300">
                  Total Ocean Queries
                </div>
              </div>
              <div className="text-center p-4 bg-gradient-to-br from-purple-900/60 to-indigo-900/60 rounded-xl border border-purple-400/20">
                <div className="text-2xl font-bold text-purple-100 mb-1">
                  {user?.user_tier}
                </div>
                <div className="text-sm text-purple-300">Research Tier</div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default DashboardNew;
