import type { Metadata, Viewport } from 'next';
import { ReactNode } from 'react';
import { Fraunces, Schibsted_Grotesk } from 'next/font/google';
import './globals.css';
import { MotionProvider } from '@/components/ui/MotionProvider';
import Toaster from '@/components/ui/Toaster';

// Variable fonts. Fraunces (v5): optical size (opsz) gives big figures the
// display cut and small ones the sturdy text cut; SOFT rounds the terminals
// (set to 100 in globals.css — friendlier, less "bank"); WONK stays 0.
const body = Schibsted_Grotesk({ subsets: ['latin'], variable: '--font-body', display: 'swap' });
const display = Fraunces({
  subsets: ['latin'],
  variable: '--font-display',
  axes: ['opsz', 'SOFT', 'WONK'],
  display: 'swap',
});

// Browser chrome matches the page: grey-green ledger paper in light, night
// ledger in dark (= the --bg tokens in globals.css).
export const viewport: Viewport = {
  themeColor: [
    { media: '(prefers-color-scheme: light)', color: '#e8ece4' },
    { media: '(prefers-color-scheme: dark)', color: '#121814' },
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
