import { request } from './request'

const STATUS_LABEL = {
  PENDING: '待审核',
  APPROVED: '已通过',
  REJECTED: '已驳回'
}

function mapProject(project) {
  return {
    id: project.backendId ?? Number(project.id),
    name: project.name,
    status: project.status,
    statusCode: project.statusCode,
    reportDeadline: project.reportDeadline || '18:00',
    attachmentRequired: Boolean(project.attachmentRequired),
    assignedFrom: project.owner || '机构'
  }
}

function mapIndicator(pi) {
  return {
    id: pi.indicatorId,
    projectId: pi.projectId,
    name: pi.indicatorName,
    unit: pi.unit || '',
    ratio: pi.ratio,
    pointsStandard: pi.pointsStandard,
    pointsUnit: pi.pointsUnit || ''
  }
}

function formatDateTime(value) {
  if (!value) return ''
  const text = String(value).replace('T', ' ')
  return text.length > 16 ? text.slice(0, 16) : text
}

async function fetchPointsByReportId(reportId) {
  try {
    const logs = await request(`/api/admin/points-logs?reportId=${reportId}`)
    return Array.isArray(logs) && logs.length ? logs[0] : null
  } catch {
    return null
  }
}

async function toReportRow(report, projectById, indicatorByKey) {
  const project = projectById.get(report.projectId)
  const indicator = indicatorByKey.get(`${report.projectId}-${report.indicatorId}`)
  const pointsLog = report.status === 'APPROVED' ? await fetchPointsByReportId(report.id) : null

  return {
    id: report.id,
    project: project?.name || `项目#${report.projectId}`,
    indicator: indicator?.name || `指标#${report.indicatorId}`,
    reporter: report.submitter,
    amount: report.result,
    unit: indicator?.unit || '',
    points: pointsLog ? Number(pointsLog.pointsDelta) : '—',
    status: STATUS_LABEL[report.status] || report.status,
    statusCode: String(report.status || '').toLowerCase(),
    reviewComment: report.auditComment || '',
    reportedAt: formatDateTime(report.receivedAt) || report.reportDate,
    attachment: report.attachmentUrl ? '有' : '无',
    attachmentUrl: report.attachmentUrl || ''
  }
}

const ACCEPTED_ATTACHMENT_TYPES = [
  '.pdf', '.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp',
  '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
  '.txt', '.csv', '.zip', '.rar', '.7z'
].join(',')

export { ACCEPTED_ATTACHMENT_TYPES }

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || ''
const ATTACHMENT_FILE_PREFIX = '/api/admin/reports/attachments/files/'

function decodeFileName(value) {
  try {
    return decodeURIComponent(value)
  } catch {
    return value
  }
}

export function resolveAttachmentDisplayName(attachmentUrl) {
  if (!attachmentUrl) return '附件'
  const fileName = decodeFileName(String(attachmentUrl).split('/').pop() || '')
  const idx = fileName.indexOf('_')
  if (idx >= 0 && idx < fileName.length - 1) {
    return fileName.slice(idx + 1)
  }
  return fileName || '附件'
}

const IMAGE_EXTENSIONS = new Set(['jpg', 'jpeg', 'png', 'gif', 'webp', 'bmp'])

function resolveAttachmentExtension(attachmentUrl) {
  const name = resolveAttachmentDisplayName(attachmentUrl).toLowerCase()
  const dot = name.lastIndexOf('.')
  return dot >= 0 ? name.slice(dot + 1) : ''
}

export function isImageAttachment(attachmentUrl) {
  return IMAGE_EXTENSIONS.has(resolveAttachmentExtension(attachmentUrl))
}

function triggerBlobDownload(blob, fileName) {
  const objectUrl = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = objectUrl
  link.download = fileName
  link.rel = 'noopener'
  document.body.appendChild(link)
  link.click()
  link.remove()
  window.setTimeout(() => URL.revokeObjectURL(objectUrl), 60_000)
}

function resolveAttachmentFetchUrl(attachmentUrl, download = false) {
  const path = attachmentUrl.startsWith('/') ? attachmentUrl : `/${attachmentUrl}`
  if (path.startsWith(ATTACHMENT_FILE_PREFIX)) {
    const rest = path.slice(ATTACHMENT_FILE_PREFIX.length)
    const slash = rest.indexOf('/')
    if (slash > 0) {
      const yearMonth = rest.slice(0, slash)
      const fileName = rest.slice(slash + 1)
      const query = download ? '?download=true' : ''
      return `${API_BASE_URL}${ATTACHMENT_FILE_PREFIX}${yearMonth}/${encodeURIComponent(decodeFileName(fileName))}${query}`
    }
  }
  return `${API_BASE_URL}${path}`
}

function parseContentDisposition(header) {
  if (!header) return ''
  const utf8Match = header.match(/filename\*=UTF-8''([^;]+)/i)
  if (utf8Match?.[1]) {
    return decodeFileName(utf8Match[1].trim())
  }
  const plainMatch = header.match(/filename="?([^";]+)"?/i)
  return plainMatch?.[1] ? decodeFileName(plainMatch[1].trim()) : ''
}

async function fetchAttachmentBlob(attachmentUrl, download = false) {
  if (!attachmentUrl) {
    throw new Error('附件不存在')
  }

  const token = localStorage.getItem('authToken')
  const response = await fetch(resolveAttachmentFetchUrl(attachmentUrl, download), {
    headers: token ? { 'X-Auth-Token': token } : {}
  })

  const contentType = response.headers.get('content-type') || ''

  if (!response.ok) {
    if (contentType.includes('application/json')) {
      const data = await response.json()
      throw new Error(data.message || '附件加载失败')
    }
    throw new Error('附件加载失败')
  }

  if (contentType.includes('application/json')) {
    const data = await response.json()
    throw new Error(data.message || '附件不存在')
  }

  const buffer = await response.arrayBuffer()
  const blob = new Blob([buffer], {
    type: contentType.split(';')[0] || 'application/octet-stream'
  })
  const fileName =
    parseContentDisposition(response.headers.get('content-disposition')) ||
    resolveAttachmentDisplayName(attachmentUrl)

  return { blob, fileName }
}

export async function previewReportAttachment(attachmentUrl) {
  if (!isImageAttachment(attachmentUrl)) {
    await downloadReportAttachment(attachmentUrl)
    return
  }

  const { blob } = await fetchAttachmentBlob(attachmentUrl, false)
  const objectUrl = URL.createObjectURL(blob)
  window.open(objectUrl, '_blank', 'noopener,noreferrer')
  window.setTimeout(() => URL.revokeObjectURL(objectUrl), 120_000)
}

export async function downloadReportAttachment(attachmentUrl) {
  const { blob, fileName } = await fetchAttachmentBlob(attachmentUrl, true)
  triggerBlobDownload(blob, fileName)
}

export async function openReportAttachment(attachmentUrl) {
  await previewReportAttachment(attachmentUrl)
}

export async function uploadReportAttachment(file) {
  if (!file) {
    throw new Error('请选择附件')
  }

  const formData = new FormData()
  formData.append('file', file)

  const response = await request('/api/admin/reports/attachments', {
    method: 'POST',
    body: formData
  })

  return {
    url: response.url,
    fileName: response.fileName,
    size: response.size
  }
}

export async function getReportOptions(user) {
  if (!user) return { projects: [], indicators: [] }
  const rawProjects = await request('/api/admin/projects')
  return { projects: (rawProjects || []).map(mapProject), indicators: [] }
}

export async function getProjectIndicators(projectId) {
  if (!projectId) return []
  const list = await request(`/api/admin/projects/${projectId}/indicators`)
  return (list || []).map(mapIndicator)
}

export async function getMyReports(user) {
  if (!user?.employeeId) return []

  const [reports, rawProjects] = await Promise.all([
    request(`/api/admin/reports?submitterId=${user.employeeId}`),
    request('/api/admin/projects')
  ])

  const list = Array.isArray(reports) ? reports : []
  const projectById = new Map((rawProjects || []).map((p) => [p.backendId ?? Number(p.id), mapProject(p)]))

  const indicatorByKey = new Map()
  const projectIds = [...new Set(list.map((r) => r.projectId).filter(Boolean))]
  await Promise.all(
    projectIds.map(async (projectId) => {
      try {
        const indicators = await getProjectIndicators(projectId)
        indicators.forEach((ind) => indicatorByKey.set(`${projectId}-${ind.id}`, ind))
      } catch {
        // 历史上报引用的项目可能已被删除（如重新导入数据后 id 变化），跳过其指标，不影响整页加载
      }
    })
  )

  const rows = await Promise.all(
    list.map((report) => toReportRow(report, projectById, indicatorByKey))
  )

  return rows.sort((a, b) => (a.reportedAt < b.reportedAt ? 1 : -1))
}

export async function submitReport(payload, user) {
  if (!user?.employeeId) {
    throw new Error('未登录或缺少员工信息')
  }

  const body = {
    projectId: Number(payload.projectId),
    indicatorId: Number(payload.indicatorId),
    organizationId: user.organizationId,
    submitter: user.name,
    submitterId: user.employeeId,
    reportDate: payload.reportDate || new Date().toISOString().slice(0, 10),
    result: String(payload.amount)
  }

  if (payload.attachmentUrl) {
    body.attachmentUrl = payload.attachmentUrl
  }

  const saved = await request('/api/admin/reports/submit', {
    method: 'POST',
    body: JSON.stringify(body)
  })

  return { success: true, report: saved }
}
