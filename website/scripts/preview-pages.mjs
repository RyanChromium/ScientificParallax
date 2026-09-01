import { createServer } from 'node:http';
import { readFile, stat } from 'node:fs/promises';
import { extname, resolve, sep } from 'node:path';
import { fileURLToPath } from 'node:url';

export const pagesDirectory = fileURLToPath(
  new URL('../dist/client/', import.meta.url),
);
const types = {
  '.html': 'text/html; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.rsc': 'text/x-component',
  '.svg': 'image/svg+xml',
  '.png': 'image/png',
  '.woff2': 'font/woff2',
  '.txt': 'text/plain; charset=utf-8',
};

// A strict file server, not a SPA fallback: missing routes must really return 404.
export function createPagesPreview(root = pagesDirectory) {
  root = resolve(root);
  return createServer(async (request, response) => {
    try {
      if (!['GET', 'HEAD'].includes(request.method)) {
        response.writeHead(405, { Allow: 'GET, HEAD' }).end();
        return;
      }
      const url = new URL(request.url, 'http://localhost');
      let pathname;
      try {
        pathname = decodeURIComponent(url.pathname);
      } catch {
        response.writeHead(400).end();
        return;
      }
      let file = resolve(root, '.' + pathname);
      if (file !== root && !file.startsWith(root + sep)) {
        response.writeHead(403).end();
        return;
      }
      const info = await stat(file).catch(() => null);
      if (info?.isDirectory()) {
        if (!url.pathname.endsWith('/')) {
          response
            .writeHead(301, { Location: url.pathname + '/' + url.search })
            .end();
          return;
        }
        file = resolve(file, 'index.html');
      }
      let body = await readFile(file).catch(() => null);
      const status = body === null ? 404 : 200;
      if (status === 404) {
        file = resolve(root, '404.html');
        body = await readFile(file);
      }
      response.writeHead(status, {
        'Content-Type': types[extname(file)] || 'application/octet-stream',
        'Content-Length': body.length,
        'Cache-Control': 'no-store',
        'X-Content-Type-Options': 'nosniff',
      });
      response.end(request.method === 'HEAD' ? undefined : body);
    } catch {
      response
        .writeHead(500)
        .end('Preview unavailable. Run npm run build:pages first.');
    }
  });
}

if (
  process.argv[1] &&
  resolve(process.argv[1]) === fileURLToPath(import.meta.url)
) {
  await stat(resolve(pagesDirectory, 'index.html'));
  await stat(resolve(pagesDirectory, 'en/index.html'));
  const port = Number(process.env.PORT || 4173);
  if (!Number.isInteger(port) || port < 1 || port > 65535)
    throw new Error('Invalid PORT');
  const server = createPagesPreview();
  server.listen(port, '127.0.0.1', () => {
    console.log(`Static Pages preview: http://localhost:${port}/`);
  });
}
