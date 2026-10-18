import { createServer } from 'node:http'
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

const server = createServer((req, res) => {
  void serve(req.url ?? '/', res)
})

async function serve(rawUrl, res) {
  const url = new URL(rawUrl, 'http://127.0.0.1')
  const path = normalize(join(root, decodeURIComponent(url.pathname)))
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

server.listen(5173, '0.0.0.0')
