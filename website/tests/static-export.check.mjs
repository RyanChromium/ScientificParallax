import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile, readdir, stat } from 'node:fs/promises';
import { resolve } from 'node:path';
import { once } from 'node:events';
import { chinese, english } from '../lib/copy.ts';
import { contactEmail } from '../lib/contact.ts';
import {
  createPagesPreview,
  pagesDirectory,
} from '../scripts/preview-pages.mjs';

const origin = process.env.SITE_ORIGIN || 'https://scientific-parallax.com';
const read = (path) => readFile(resolve(pagesDirectory, path), 'utf8');
const attrs = (tag) =>
  Object.fromEntries(
    [...tag.matchAll(/([\w:-]+)="([^"]*)"/g)].map(([, key, value]) => [
      key.toLowerCase(),
      value,
    ]),
  );
const tags = (html, tag) =>
  [...html.matchAll(new RegExp(`<${tag}\\b[^>]*>`, 'g'))].map(([value]) =>
    attrs(value),
  );

for (const [path, lang, copy, canonical] of [
  ['index.html', 'zh-CN', chinese, '/'],
  ['en/index.html', 'en', english, '/en/'],
]) {
  test(`${path}: complete, localized HTML, metadata, navigation and interaction markup`, async () => {
    const html = await read(path);
    assert.equal(tags(html, 'html').length, 1);
    assert.equal(tags(html, 'html')[0].lang, lang);
    assert.ok(html.includes(`<title>${copy.title}</title>`));
    assert.ok(html.includes(copy.methodLimit));
    assert.ok(html.includes(copy.observation.disclaimer));
    assert.ok(html.includes(copy.examples[0].body));
    assert.ok(html.includes('role="tablist"'));
    assert.equal(
      tags(html, 'button').filter((tag) => tag.role === 'tab').length,
      3,
    );
    assert.equal(
      tags(html, 'svg').filter((tag) => tag['data-example-diagram']).length,
      3,
    );
    const links = tags(html, 'link');
    const meta = tags(html, 'meta');
    assert.equal(
      links.find((tag) => tag.rel === 'canonical')?.href,
      new URL(canonical, origin).href,
    );
    assert.equal(
      links.find((tag) => tag.hreflang === 'zh-CN')?.href,
      new URL('/', origin).href,
    );
    assert.equal(
      links.find((tag) => tag.hreflang === 'en')?.href,
      new URL('/en/', origin).href,
    );
    assert.equal(
      meta.find((tag) => tag.property === 'og:image')?.content,
      new URL('/og.png', origin).href,
    );
    assert.equal(
      meta.find((tag) => tag.property === 'og:title')?.content,
      copy.title,
    );
    assert.equal(
      meta.find((tag) => tag.name === 'twitter:title')?.content,
      copy.title,
    );
    const anchors = tags(html, 'a');
    const email = anchors.find((tag) => tag.href?.startsWith('mailto:'));
    assert.equal(email?.href, `mailto:${contactEmail}`);
    assert.equal(email?.['aria-label'], copy.email);
    assert.ok(html.includes(`<span>${copy.email}</span>`));
    assert.ok(!html.includes(`<span>${contactEmail}</span>`));
    assert.equal(anchors.find((tag) => tag.hreflang === 'zh-CN')?.href, '/');
    assert.equal(anchors.find((tag) => tag.hreflang === 'en')?.href, '/en/');
    assert.equal(
      anchors.find((tag) => tag['aria-current'] === 'page')?.hreflang,
      lang,
    );
    for (const anchor of anchors.filter(
      (tag) => tag.href?.startsWith('#') && tag.href !== '#',
    )) {
      assert.ok(html.includes(`id="${anchor.href.slice(1)}"`), anchor.href);
    }
    const resources = [
      ...tags(html, 'script').map((tag) => tag.src),
      ...links
        .filter((tag) =>
          ['stylesheet', 'modulepreload', 'icon'].includes(tag.rel),
        )
        .map((tag) => tag.href),
    ].filter(Boolean);
    assert.ok(
      resources.some((url) => url.endsWith('.js')),
      'hydration scripts must be exported',
    );
    assert.ok(
      resources.some((url) => url.endsWith('.css')),
      'styles must be exported',
    );
    for (const url of resources) {
      assert.ok(url.startsWith('/') && !url.startsWith('//'), url);
      assert.ok(
        (
          await stat(
            resolve(pagesDirectory, '.' + new URL(url, origin).pathname),
          )
        ).isFile(),
        url,
      );
    }
    assert.doesNotMatch(html, /chatgpt\.site|x-site-language/);
  });
}

test('export contains fonts, sharing image, 404 and no server, secrets or research files', async () => {
  const files = await readdir(pagesDirectory, { recursive: true });
  for (const path of [
    '404.html',
    '.nojekyll',
    'og.png',
    'favicon.svg',
    'index.rsc',
    'en.rsc',
  ]) {
    assert.ok((await stat(resolve(pagesDirectory, path))).isFile(), path);
  }
  assert.equal(files.filter((file) => file.endsWith('.woff2')).length, 4);
  const missingPage = await read('404.html');
  assert.ok(missingPage.includes('Scientific Parallax'));
  assert.ok(missingPage.includes('href="/en/"'));
  assert.ok(missingPage.includes('href="/"'));
  for (const file of files) {
    assert.doesNotMatch(
      file,
      /(^|\/)(\.env[^/]*|\.git|\.openai|server|node_modules|data|plans)(\/|$)|\.map$|\.pem$|\.sqlite$/,
    );
  }
  for (const file of files.filter((file) => file.endsWith('.css'))) {
    const css = await read(file);
    for (const [, url] of css.matchAll(
      /url\(["']?(\/fonts\/[^)'"\s]+)["']?\)/g,
    )) {
      assert.ok((await stat(resolve(pagesDirectory, '.' + url))).isFile(), url);
    }
  }
});

test('strict static serving supports direct English URLs and real 404s without an app server', async (t) => {
  const server = createPagesPreview();
  server.listen(0, '127.0.0.1');
  await once(server, 'listening');
  t.after(() => {
    server.closeAllConnections();
    server.close();
  });
  const base = `http://127.0.0.1:${server.address().port}`;
  for (const path of [
    '/',
    '/en/',
    '/en/index.html',
    '/og.png',
    '/favicon.svg',
  ]) {
    const response = await fetch(base + path);
    assert.equal(response.status, 200, path);
    await response.arrayBuffer();
  }
  const redirect = await fetch(base + '/en?from=test', { redirect: 'manual' });
  assert.equal(redirect.status, 301);
  assert.equal(redirect.headers.get('location'), '/en/?from=test');
  await redirect.arrayBuffer();
  for (const path of [
    '/not-a-page/',
    '/en/not-a-page/',
    '/.env',
    '/package.json',
  ]) {
    const response = await fetch(base + path);
    assert.equal(response.status, 404, path);
    await response.arrayBuffer();
  }
});
