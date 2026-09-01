import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { copyFile, mkdir, rename } from 'node:fs/promises';
import { resolve } from 'node:path';

const root = fileURLToPath(new URL('../', import.meta.url));
const origin = new URL(
  process.env.SITE_ORIGIN || 'https://scientific-parallax.com',
);
if (
  origin.protocol !== 'https:' ||
  origin.pathname !== '/' ||
  origin.search ||
  origin.hash ||
  origin.username ||
  origin.password
) {
  throw new Error(
    'SITE_ORIGIN must be an HTTPS origin without a path, credentials, query or fragment.',
  );
}

const result = spawnSync(
  process.execPath,
  ['node_modules/vinext/dist/cli.js', 'build'],
  {
    cwd: root,
    stdio: 'inherit',
    env: {
      ...process.env,
      SITE_DEPLOY_TARGET: 'github-pages',
      SITE_ORIGIN: origin.origin,
    },
  },
);
if (result.error) throw result.error;
if (result.status !== 0) process.exit(result.status ?? 1);

// Publish directory indexes for Pages without relying on server redirects.
// Missing English output must fail loudly, even if the framework build succeeds.
await mkdir(resolve(root, 'dist/client/en'), { recursive: true });
await rename(
  resolve(root, 'dist/client/en.html'),
  resolve(root, 'dist/client/en/index.html'),
);
// Vinext emits its own generic 404 after copying public assets; keep our bilingual one.
await copyFile(
  resolve(root, 'public/404.html'),
  resolve(root, 'dist/client/404.html'),
);

const verification = spawnSync(
  process.execPath,
  ['--experimental-strip-types', '--test', 'tests/static-export.check.mjs'],
  {
    cwd: root,
    stdio: 'inherit',
    env: { ...process.env, SITE_ORIGIN: origin.origin },
  },
);
if (verification.error) throw verification.error;
process.exit(verification.status ?? 1);
