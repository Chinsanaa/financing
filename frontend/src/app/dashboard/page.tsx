'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { createClient } from '@/utils/supabase';
import { api } from '@/utils/api';
import UploadTab from '@/components/tabs/UploadTab';
import LabelTab from '@/components/tabs/LabelTab';
import StatsTab from '@/components/tabs/StatsTab';
import CategoriesTab from '@/components/tabs/CategoriesTab';
import TrainingTab from '@/components/tabs/TrainingTab';
import ReviewTab from '@/components/tabs/ReviewTab';

type TabType = 'upload' | 'label' | 'stats' | 'categories' | 'training' | 'review';

export default function DashboardPage() {
  const router = useRouter();
  const supabase = createClient();

  const [user, setUser] = useState<any>(null);
  const [token, setToken] = useState<string>('');
  const [activeTab, setActiveTab] = useState<TabType>('stats');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const checkAuth = async () => {
      const {
        data: { session },
      } = await supabase.auth.getSession();

      if (!session) {
        router.push('/auth');
        return;
      }

      setUser(session.user);
      setToken(session.access_token);
      setLoading(false);
    };

    checkAuth();
  }, [supabase, router]);

  const handleLogout = async () => {
    await supabase.auth.signOut();
    router.push('/auth');
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <p className="text-gray-600">Loading...</p>
      </div>
    );
  }

  const tabs: { id: TabType; label: string; icon: string }[] = [
    { id: 'stats', label: 'Dashboard', icon: '📊' },
    { id: 'upload', label: 'Upload', icon: '📁' },
    { id: 'label', label: 'Label', icon: '🏷️' },
    { id: 'review', label: 'Review', icon: '✅' },
    { id: 'categories', label: 'Categories', icon: '📂' },
    { id: 'training', label: 'Training', icon: '🔄' },
  ];

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4 flex justify-between items-center">
          <h1 className="text-2xl font-bold text-gray-900">Financing</h1>
          <div className="flex items-center gap-4">
            <p className="text-sm text-gray-600">{user?.email}</p>
            <button
              onClick={handleLogout}
              className="px-3 py-2 bg-red-50 text-red-700 rounded-lg hover:bg-red-100 transition text-sm font-medium"
            >
              Logout
            </button>
          </div>
        </div>
      </header>

      {/* Tabs Navigation */}
      <div className="bg-white border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex gap-1 overflow-x-auto">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`px-4 py-3 border-b-2 whitespace-nowrap transition ${
                  activeTab === tab.id
                    ? 'border-blue-600 text-blue-600 font-medium'
                    : 'border-transparent text-gray-600 hover:text-gray-900'
                }`}
              >
                <span className="mr-2">{tab.icon}</span>
                {tab.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Tab Content */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {activeTab === 'stats' && <StatsTab token={token} />}
        {activeTab === 'upload' && <UploadTab token={token} />}
        {activeTab === 'label' && <LabelTab token={token} />}
        {activeTab === 'review' && <ReviewTab token={token} />}
        {activeTab === 'categories' && <CategoriesTab token={token} />}
        {activeTab === 'training' && <TrainingTab token={token} />}
      </div>
    </div>
  );
}
