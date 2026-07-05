'use client';

import { useState, useEffect } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { createClient } from '@/utils/supabase';

export default function VerifyPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const supabase = createClient();

  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  useEffect(() => {
    const handleVerification = async () => {
      const token = searchParams.get('token');
      const type = searchParams.get('type');

      if (token && type === 'email') {
        setLoading(true);
        try {
          const { error } = await supabase.auth.verifyOtp({
            token_hash: token,
            type: 'email',
          });

          if (error) {
            setError(error.message);
          } else {
            setMessage('Email verified! Redirecting...');
            setTimeout(() => router.push('/dashboard'), 2000);
          }
        } catch (err: any) {
          setError(err.message);
        } finally {
          setLoading(false);
        }
      }
    };

    handleVerification();
  }, [searchParams, supabase, router]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-indigo-100">
      <div className="w-full max-w-md bg-white rounded-lg shadow-lg p-8">
        <h1 className="text-2xl font-bold mb-4">Email Verification</h1>

        {loading && <p className="text-gray-600">Verifying your email...</p>}

        {message && (
          <div className="bg-green-50 border border-green-200 text-green-700 px-4 py-3 rounded">
            {message}
          </div>
        )}

        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
            <p>{error}</p>
            <button
              onClick={() => router.push('/auth')}
              className="mt-2 text-sm underline hover:no-underline"
            >
              Back to login
            </button>
          </div>
        )}

        {!loading && !message && !error && (
          <p className="text-gray-600">
            Check your email for a verification link. Click it to complete signup.
          </p>
        )}
      </div>
    </div>
  );
}
