import type { Metadata, Viewport } from 'next';
import { ReactNode } from 'react';
import { Newsreader, Schibsted_Grotesk } from 'next/font/google';
import './globals.css';
import { MotionProvider } from '@/components/ui/MotionProvider';
import Toaster from '@/components/ui/Toaster';

// Variable fonts: Newsreader's optical-size axis (opsz) gives big figures the
// fine display cut and table cells the sturdy text cut, from one file.
const body = Schibsted_Grotesk({ subsets: ['latin'], variable: '--font-body' });
const display = Newsreader({ subsets: ['latin'], variable: '--font-display', axes: ['opsz'] });

// Browser chrome matches the page: paper in light, night ledger in dark.
export const viewport: Viewport = {
  themeColor: [
    { media: '(prefers-color-scheme: light)', color: '#f4f1ea' },
    { media: '(prefers-color-scheme: dark)', color: '#151411' },
  ],
};

export const metadata: Metadata = {
  title: 'Financing — Know where every yuan goes',
  description:
    'Upload your Alipay and WeChat statements, train a personal ML model, and understand your spending.',
};

// Runs before paint: applies the persisted theme so there is no flash.
// Ledger (v4) is paper-first: light unless the user chose dark.
const themeScript = `
(function () {
  try {
    if (localStorage.getItem('theme') === 'dark') document.documentElement.classList.add('dark');
  } catch (e) {}
})();
`;

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeScript }} />
      </head>
      <body className={`${body.variable} ${display.variable} font-sans`}>
        <div className="min-h-screen bg-bg text-ink">
          <MotionProvider>
            {children}
            <Toaster />
          </MotionProvider>
        </div>
      </body>
    </html>
  );
}
