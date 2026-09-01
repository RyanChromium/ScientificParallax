import type { Metadata } from 'next';
import { getCopy, languagePath, type Language } from './copy';

export function metadataForLanguage(language: Language): Metadata {
  const t = getCopy(language);
  // Configured origin only: never infer canonical URLs from request headers.
  const origin = process.env.SITE_ORIGIN;
  const url = origin ? new URL(languagePath(language), origin).href : undefined;
  const images = origin
    ? [
        {
          url: new URL('/og.png', origin).href,
          width: 1732,
          height: 908,
          alt:
            language === 'en'
              ? 'Scientific Parallax — project illustration'
              : 'Scientific Parallax · 科学视差',
        },
      ]
    : [];
  return {
    title: t.title,
    description: t.description,
    icons: { icon: '/favicon.svg' },
    alternates: origin
      ? {
          canonical: url,
          languages: {
            'zh-CN': new URL(languagePath('zh'), origin).href,
            en: new URL(languagePath('en'), origin).href,
            'x-default': new URL(languagePath('zh'), origin).href,
          },
        }
      : undefined,
    openGraph: {
      images,
      title: t.title,
      description: t.socialDescription,
      type: 'website',
      url,
      locale: language === 'en' ? 'en_US' : 'zh_CN',
      alternateLocale: language === 'en' ? ['zh_CN'] : ['en_US'],
    },
    twitter: {
      card: 'summary_large_image',
      images,
      title: t.title,
      description: t.socialDescription,
    },
  };
}
