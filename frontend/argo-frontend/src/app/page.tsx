"use client";

import { useAuth } from "@/contexts/AuthContext";
import LoginForm from "@/components/LoginForm";
import Dashboard from "@/components/Dashboard";

export default function Home() {
  const { user, isLoading } = useAuth();

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-900 via-blue-800 to-cyan-900">
        <div className="text-white text-center">
          <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-white mx-auto mb-4"></div>
          <h2 className="text-2xl font-semibold">Loading ARGO RAG...</h2>
          <p className="text-blue-200 mt-2">Initializing oceanographic intelligence platform</p>
        </div>
      </div>
    );
  }

  return user ? <Dashboard /> : <LoginForm />;
}
