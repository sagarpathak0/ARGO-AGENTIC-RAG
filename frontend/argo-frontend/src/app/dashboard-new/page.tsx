"use client";

import { useAuth } from '@/contexts/AuthContext';
import DashboardNew from '@/components/DashboardNew';
import { useEffect } from 'react';
import { useRouter } from 'next/navigation';

export default function DashboardNewPage() {
  const { user, isLoading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!isLoading && !user) {
      router.push('/');
    }
  }, [user, isLoading, router]);

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-900 via-blue-800 to-indigo-900 flex items-center justify-center">
        <div className="text-white text-lg">Loading Ocean Dashboard...</div>
      </div>
    );
  }

  if (!user) {
    return null;
  }

  return <DashboardNew />;
}