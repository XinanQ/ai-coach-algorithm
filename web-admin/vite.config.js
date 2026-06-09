import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import fsSync from 'node:fs'
import fs from 'node:fs/promises'
import os from 'node:os'
import path from 'node:path'

const tempProjectFile = path.join(os.tmpdir(), 'finance-performance-system-projects.json')

function tempProjectStorePlugin() {
  let isCleanedUp = false

  async function cleanupTempProjects() {
    if (isCleanedUp) return
    isCleanedUp = true

    try {
      await fs.unlink(tempProjectFile)
    } catch (error) {
      if (error.code !== 'ENOENT') {
        console.warn(`[temp-project-store] failed to delete ${tempProjectFile}: ${error.message}`)
      }
    }
  }

  return {
    name: 'temp-project-store',
    configureServer(server) {
      // Dev-only scratch API. Production builds do not mount this middleware,
      // so future backend APIs can own the real /api/projects contract.
      server.middlewares.use('/api/temp/projects', async (req, res) => {
        res.setHeader('Content-Type', 'application/json; charset=utf-8')

        try {
          if (req.method === 'GET') {
            const projects = await readTempProjects()
            res.end(JSON.stringify({ filePath: tempProjectFile, projects }))
            return
          }

          if (req.method === 'POST') {
            const body = await readBody(req)
            const project = JSON.parse(body || '{}')
            const projects = await readTempProjects()
            const nextProjects = [...projects.filter((item) => item.id !== project.id), project]
            await fs.writeFile(tempProjectFile, JSON.stringify(nextProjects, null, 2), 'utf-8')
            res.end(JSON.stringify({ filePath: tempProjectFile, project, projects: nextProjects }))
            return
          }

          if (req.method === 'PUT') {
            const requestUrl = new URL(req.url || '', 'http://localhost')
            const projectId = requestUrl.searchParams.get('id')
            if (!projectId) {
              res.statusCode = 400
              res.end(JSON.stringify({ message: 'Project id is required' }))
              return
            }

            const attachment = parseMultipartFile(await readBuffer(req), req.headers['content-type'] || '')
            if (!attachment) {
              res.statusCode = 400
              res.end(JSON.stringify({ message: 'No file found in request' }))
              return
            }

            const projects = await readTempProjects()
            const projectIndex = projects.findIndex((item) => item.id === projectId)
            if (projectIndex === -1) {
              res.statusCode = 404
              res.end(JSON.stringify({ message: 'Project not found' }))
              return
            }

            const nextProjects = projects.map((project, index) =>
              index === projectIndex ? { ...project, attachment } : project
            )
            await fs.writeFile(tempProjectFile, JSON.stringify(nextProjects, null, 2), 'utf-8')
            res.end(JSON.stringify({ filePath: tempProjectFile, project: nextProjects[projectIndex], projects: nextProjects }))
            return
          }

          if (req.method === 'DELETE') {
            const requestUrl = new URL(req.url || '', 'http://localhost')
            const projectId = requestUrl.searchParams.get('id')
            if (!projectId) {
              res.statusCode = 400
              res.end(JSON.stringify({ message: 'Project id is required' }))
              return
            }

            const projects = await readTempProjects()
            const nextProjects = projects.filter((item) => item.id !== projectId)
            await fs.writeFile(tempProjectFile, JSON.stringify(nextProjects, null, 2), 'utf-8')
            res.end(JSON.stringify({ filePath: tempProjectFile, projects: nextProjects }))
            return
          }

          res.statusCode = 405
          res.end(JSON.stringify({ message: 'Method not allowed' }))
        } catch (error) {
          res.statusCode = 500
          res.end(JSON.stringify({ message: error.message }))
        }
      })

      server.httpServer?.once('close', cleanupTempProjects)
      process.once('SIGINT', cleanupTempProjects)
      process.once('SIGTERM', cleanupTempProjects)
      process.once('exit', () => {
        if (!isCleanedUp) {
          isCleanedUp = true
          fsSync.rmSync(tempProjectFile, { force: true })
        }
      })
    }
  }
}

async function readTempProjects() {
  try {
    const content = await fs.readFile(tempProjectFile, 'utf-8')
    return JSON.parse(content)
  } catch (error) {
    if (error.code === 'ENOENT') return []
    throw error
  }
}

function readBody(req) {
  return new Promise((resolve, reject) => {
    let body = ''
    req.on('data', (chunk) => {
      body += chunk
    })
    req.on('end', () => resolve(body))
    req.on('error', reject)
  })
}

function readBuffer(req) {
  return new Promise((resolve, reject) => {
    const chunks = []
    req.on('data', (chunk) => {
      chunks.push(chunk)
    })
    req.on('end', () => resolve(Buffer.concat(chunks)))
    req.on('error', reject)
  })
}

function parseMultipartFile(bodyBuffer, contentType) {
  const boundaryMatch = contentType.match(/boundary=(?:"([^"]+)"|([^;]+))/)
  const boundary = boundaryMatch?.[1] || boundaryMatch?.[2]
  if (!boundary) return null

  const body = bodyBuffer.toString('binary')
  const parts = body.split(`--${boundary}`)

  for (const part of parts) {
    if (!part.includes('Content-Disposition') || !part.includes('filename=')) continue

    const headerEnd = part.indexOf('\r\n\r\n')
    if (headerEnd === -1) continue

    const headers = part.slice(0, headerEnd)
    const filenameMatch = headers.match(/filename="([^"]+)"/)
    const contentTypeMatch = headers.match(/Content-Type:\s*([^\r\n]+)/i)
    const dataStart = headerEnd + 4
    const dataEnd = part.lastIndexOf('\r\n')
    const fileBuffer = Buffer.from(part.slice(dataStart, dataEnd > dataStart ? dataEnd : undefined), 'binary')

    return {
      filename: filenameMatch?.[1] || 'unknown',
      contentType: contentTypeMatch?.[1] || 'application/octet-stream',
      size: fileBuffer.length,
      encoding: 'base64',
      data: fileBuffer.toString('base64')
    }
  }

  return null
}

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue(), tempProjectStorePlugin()],
})
