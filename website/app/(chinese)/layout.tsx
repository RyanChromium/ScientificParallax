import { metadataForLanguage } from '@/lib/metadata';
import '../globals.css';

export const dynamic = 'error';

export function generateMetadata() {
  return metadataForLanguage('zh');
}

export default function ChineseLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="zh-CN">
      <body>{children}</body>
    </html>
  );
}
