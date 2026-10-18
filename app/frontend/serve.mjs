import { createServer, request as forward } from 'node:http'
import { readFile } from 'node:fs/promises'
import { extname, join, normalize } from 'node:path'

const root = join(process.cwd(), 'dist')
const types = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.svg': 'image/svg+xml',
  '.png': 'image/png',
  '.json': 'application/json',
}

const apiTarget = new URL(process.env.API_PROXY_TARGET ?? 'http://backend:8000')

const server = createServer((req, res) => {
  const url = new URL(req.url ?? '/', 'http://127.0.0.1')
  if (url.pathname === '/api' || url.pathname.startsWith('/api/')) {
    proxyApi(req, url, res)
    return
  }
  void serve(url.pathname, res)
})

function proxyApi(req, url, res) {
  const path = url.pathname.replace(/^\/api/, '') || '/'
  const upstream = forward(
    {
      hostname: apiTarget.hostname,
      port: apiTarget.port || 80,
      path: `${path}${url.search}`,
      method: req.method,
      headers: { ...req.headers, host: apiTarget.host },
    },
    (upstreamRes) => {
      res.writeHead(upstreamRes.statusCode ?? 502, upstreamRes.headers)
      upstreamRes.pipe(res)
    },
  )
  upstream.on('error', () => {
    if (!res.headersSent) {
      res.writeHead(502)
    }
    res.end()
  })
  req.pipe(upstream)
}

async function serve(pathname, res) {
  const path = normalize(join(root, decodeURIComponent(pathname)))
  if (!path.startsWith(root)) {
    res.writeHead(400)
    res.end()
    return
  }
  const body = await readBody(path)
  if (body) {
    res.writeHead(200, { 'Content-Type': types[extname(path)] ?? types['.html'] })
    res.end(body)
    return
  }
  const fallback = await readBody(join(root, 'index.html'))
  if (!fallback) {
    res.writeHead(404)
    res.end()
    return
  }
  res.writeHead(200, { 'Content-Type': types['.html'] })
  res.end(fallback)
}

async function readBody(path) {
  try {
    return await readFile(path)
  } catch {
    return null
  }
}

server.listen(Number(process.env.PORT ?? 5173), '0.0.0.0')
