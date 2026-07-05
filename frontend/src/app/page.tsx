'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { createClient } from '@/utils/supabase';

export default function HomePage() {
  const router = useRouter();
  const supabase = createClient();

  useEffect(() => {
    const checkAuth = async () => {
      const {
        data: { session },
      } = await supabase.auth.getSession();

      if (session) {
        router.push('/dashboard');
      } else {
        router.push('/auth');
      }
    };

    checkAuth();
  }, [supabase, router]);

  return (
    <div className="min-h-screen flex items-center justify-center">
      <p className="text-gray-600">Loading...</p>
    </div>
  );
}
