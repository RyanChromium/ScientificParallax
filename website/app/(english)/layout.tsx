import { metadataForLanguage } from '@/lib/metadata';
import '../globals.css';

export const dynamic = 'error';

export function generateMetadata() {
  return metadataForLanguage('en');
}

export default function EnglishLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
