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
    attachment: report.attachmentUrl ? '有' : '无'
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
      const indicators = await getProjectIndicators(projectId)
      indicators.forEach((ind) => indicatorByKey.set(`${projectId}-${ind.id}`, ind))
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

  const saved = await request('/api/admin/reports/submit', {
    method: 'POST',
    body: JSON.stringify(body)
  })

  return { success: true, report: saved }
}
