const request = require('../utils/request')
const config = require('../config')
const mock = require('../mock/report')

const STATUS_LABEL = {
  PENDING: '待审核',
  APPROVED: '已通过',
  REJECTED: '已驳回'
}

function today() {
  const date = new Date()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return date.getFullYear() + '-' + month + '-' + day
}

function formatDateTime(value) {
  if (!value) return ''
  return String(value).replace('T', ' ').slice(0, 16)
}

function mapProject(project) {
  const id = project.backendId || Number(project.id)
  return {
    id,
    name: project.name || ('项目#' + id),
    status: project.status || '',
    statusCode: project.statusCode || '',
    reportDeadline: project.reportDeadline || '',
    attachmentRequired: Boolean(project.attachmentRequired),
    attachmentInstructions: project.attachmentInstructions || ''
  }
}

function mapIndicator(indicator) {
  const id = indicator.indicatorId || indicator.id
  return {
    id,
    projectId: indicator.projectId,
    name: indicator.indicatorName || indicator.name || ('指标#' + id),
    unit: indicator.unit || '',
    pointsStandard: indicator.pointsStandard || 0,
    pointsUnit: indicator.pointsUnit || ''
  }
}

function mapHistoryItem(report, projectMap, indicatorMap) {
  const statusClass = String(report.status || '').toLowerCase()
  const project = projectMap[report.projectId]
  const indicator = indicatorMap[report.projectId + '-' + report.indicatorId]
  const unit = indicator && indicator.unit ? indicator.unit : ''

  return {
    id: report.id,
    project: project ? project.name : ('项目#' + report.projectId),
    indicator: indicator ? indicator.name : ('指标#' + report.indicatorId),
    value: (report.result || '') + unit,
    amount: report.result || '',
    unit,
    date: report.reportDate || '',
    time: formatDateTime(report.receivedAt) || report.reportDate || '',
    status: STATUS_LABEL[report.status] || report.status || '待审核',
    statusClass,
    reason: report.auditComment || '',
    attachmentUrl: report.attachmentUrl || ''
  }
}

async function getProjects() {
  if (config.USE_MOCK) return Promise.resolve(mock.projects ? mock.projects() : [])
  const projects = await request.get('/admin/projects')
  return (projects || []).map(mapProject)
}

async function getProjectIndicators(projectId) {
  if (config.USE_MOCK) return Promise.resolve(mock.indicators())
  if (!projectId) return []
  const indicators = await request.get('/admin/projects/' + projectId + '/indicators')
  return (indicators || []).map(mapIndicator)
}

async function getReportOptions() {
  const projects = await getProjects()
  return { projects, indicators: [] }
}

async function uploadAttachment(filePath) {
  if (!filePath) return null
  if (config.USE_MOCK) return Promise.resolve({ url: filePath })
  return request.upload('/admin/reports/attachments', filePath, 'file')
}

async function submit(payload) {
  if (config.USE_MOCK) return Promise.resolve(mock.submit())

  const body = {
    projectId: Number(payload.projectId),
    indicatorId: Number(payload.indicatorId),
    submitter: payload.submitter || '员工',
    reportDate: payload.reportDate || today(),
    result: String(payload.amount)
  }

  if (payload.organizationId) body.organizationId = Number(payload.organizationId)
  if (payload.submitterId) body.submitterId = Number(payload.submitterId)
  if (payload.attachmentUrl) body.attachmentUrl = payload.attachmentUrl

  return request.post('/admin/reports/submit', body)
}

async function getHistory() {
  if (config.USE_MOCK) return Promise.resolve(mock.history())

  const reports = await request.get('/admin/reports')
  const projects = await getProjects()
  const projectMap = {}
  projects.forEach((project) => {
    projectMap[project.id] = project
  })

  const indicatorMap = {}
  const projectIds = []
  ;(reports || []).forEach((report) => {
    if (report.projectId && projectIds.indexOf(report.projectId) === -1) {
      projectIds.push(report.projectId)
    }
  })

  await Promise.all(projectIds.map((projectId) => (
    getProjectIndicators(projectId)
      .then((indicators) => {
        indicators.forEach((indicator) => {
          indicatorMap[projectId + '-' + indicator.id] = indicator
        })
      })
      .catch(() => {})
  )))

  return (reports || [])
    .map((report) => mapHistoryItem(report, projectMap, indicatorMap))
    .sort((a, b) => (a.time < b.time ? 1 : -1))
}

module.exports = {
  getProjects,
  getProjectIndicators,
  getReportOptions,
  uploadAttachment,
  submit,
  getHistory
}
