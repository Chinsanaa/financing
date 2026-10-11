import type { Metadata } from 'next';
import ImportGuide from '@/components/import/ImportGuide';

export const metadata: Metadata = {
  title: 'How to export your statements — Financing.',
  description:
    'Step-by-step English guide to exporting your Alipay, WeChat Pay and bank statements, then uploading them to Financing.',
};

export default function GuidePage() {
  return <ImportGuide />;
}
