import type { Metadata } from 'next';
import Landing from '@/components/landing/Landing';

export const metadata: Metadata = {
  title: 'Financing — Every yuan, accounted for',
  description:
    'For English speakers living in China: upload your Alipay and WeChat Pay statements, read them in English, and let a model trained on your own labels sort your spending.',
};

export default function HomePage() {
  return <Landing />;
}
