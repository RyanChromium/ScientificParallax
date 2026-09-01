import type { NextConfig } from 'next';

const nextConfig: NextConfig = {
  ...(process.env.SITE_DEPLOY_TARGET === 'github-pages'
    ? { output: 'export' as const }
    : {}),
  // Vinext beta.5's exporter requests /en and skips it if it redirects to /en/.
  // Export without redirects; build-pages.mjs packages en.html as en/index.html.
  trailingSlash: process.env.SITE_DEPLOY_TARGET !== 'github-pages',
};

export default nextConfig;
