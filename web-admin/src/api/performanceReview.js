import { request } from './request'
import { resolveAttachmentDisplayName } from './reports'
import { getCurrentUser } from '../auth/permissions'

// 列表可见：本市行及下级；canReview 与积分流水审核范围一致。

export const REVIEW_STATUS = {
  pending: { label: '待审核', type: 'pending' },
  approved: { label: '已通过', type: 'approved' },
  rejected: { label: '已驳回', type: 'rejected' }
}

const STATUS_TO_FRONT = {
  PENDING: 'pending',
  APPROVED: 'approved',
  REJECTED: 'rejected'
}

let lookupCache = null

export function clearReviewCache() {
  lookupCache = null
}

async function loadLookups() {
  if (lookupCache) return lookupCache

  const [projects, employees, organizations, indicatorPage] = await Promise.all([
    request('/api/admin/projects'),
    request('/api/admin/employees'),
    request('/api/admin/organizations'),
    request('/api/admin/indicators?page=0&size=200')
  ])

  const indicators = indicatorPage?.content || (Array.isArray(indicatorPage) ? indicatorPage : [])

  const orgById = new Map(organizations.map((o) => [Number(o.id), o]))
  const childrenMap = new Map()
  for (const org of organizations) {
    const parentId = org.parentId != null ? Number(org.parentId) : null
    if (parentId != null) {
      if (!childrenMap.has(parentId)) childrenMap.set(parentId, [])
      childrenMap.get(parentId).push(Number(org.id))
    }
  }

  lookupCache = {
    projectById: new Map(projects.map((p) => [p.backendId ?? Number(p.id), p])),
    employeeById: new Map(employees.map((e) => [e.id, e])),
    orgById,
    childrenMap,
    indicatorById: new Map(indicators.map((i) => [i.id, i]))
  }
  return lookupCache
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

function resolveAdminLevel(user) {
  if (!user) return null

  const level = String(user?.backendLevel || '').trim().toUpperCase()
  if (['CITY', 'HEAD', 'HEADQUARTERS', 'PROVINCE'].includes(level)) return 'CITY'
  if (level === 'BRANCH') return 'BRANCH'
  if (level === 'OUTLET') return 'OUTLET'

  const roleMap = {
    city_admin: 'CITY',
    head_admin: 'CITY',
    province_admin: 'CITY',
    branch_admin: 'BRANCH',
    outlet_admin: 'OUTLET'
  }
  if (roleMap[user?.role]) return roleMap[user.role]

  const cn = String(user?.position || user?.level || '')
  if (cn.includes('市行') || cn.includes('总行') || cn.includes('省行')) return 'CITY'
  if (cn.includes('支行')) return 'BRANCH'
  if (cn.includes('网点')) return 'OUTLET'

  return null
}

function collectSelfAndDescendants(orgId, childrenMap) {
  const result = new Set([orgId])
  const stack = [orgId]
  while (stack.length) {
    const id = stack.pop()
    for (const child of childrenMap.get(id) || []) {
      if (!result.has(child)) {
        result.add(child)
        stack.push(child)
      }
    }
  }
  return result
}

function findScopeRootOrgId(startOrgId, targetLevel, orgById) {
  let currentId = startOrgId
  while (currentId != null) {
    const org = orgById.get(currentId)
    if (!org) break
    if (String(org.level || '').toUpperCase() === targetLevel) {
      return currentId
    }
    currentId = org.parentId != null ? Number(org.parentId) : null
  }
  return null
}

function resolveReviewableOrgIds(user, lookups) {
  const adminLevel = resolveAdminLevel(user)
  const orgId = Number(user?.organizationId || user?.orgId)
  if (!adminLevel || !orgId) return new Set()

  const cityRoot = findScopeRootOrgId(orgId, 'CITY', lookups.orgById)

  // 市行/总行/省行：审核全市行树
  if (adminLevel === 'CITY') {
    if (!cityRoot) return new Set()
    return collectSelfAndDescendants(cityRoot, lookups.childrenMap)
  }

  const scopeRoot = findScopeRootOrgId(orgId, adminLevel, lookups.orgById)
  if (!scopeRoot) return new Set()

  return collectSelfAndDescendants(scopeRoot, lookups.childrenMap)
}

function resolveSubmitterOrgId(report, lookups) {
  const employee = lookups.employeeById.get(report.submitterId)
  if (employee?.organizationId != null) return Number(employee.organizationId)
  if (report.organizationId != null) return Number(report.organizationId)
  return null
}

function computeCanReviewClient(report, lookups, currentUser) {
  const status = STATUS_TO_FRONT[report.status] || String(report.status || '').toLowerCase()
  if (status !== 'pending' || !currentUser) return false
  if (!resolveAdminLevel(currentUser)) return false

  const submitterOrgId = resolveSubmitterOrgId(report, lookups)
  if (!submitterOrgId) return false

  return resolveReviewableOrgIds(currentUser, lookups).has(submitterOrgId)
}

function resolveCanReview(report, lookups, currentUser) {
  const client = computeCanReviewClient(report, lookups, currentUser)
  if (typeof report.canReview === 'boolean') {
    // 后端已返回时：市行管理员若被误判为 false，以机构树计算为准
    if (!report.canReview && resolveAdminLevel(currentUser) === 'CITY') {
      return client
    }
    return report.canReview
  }
  return client
}

async function toReviewItem(report, lookups, pointsLog = null, currentUser = getCurrentUser()) {
  const project = lookups.projectById.get(report.projectId)
  const indicator = lookups.indicatorById.get(report.indicatorId)
  const employee = lookups.employeeById.get(report.submitterId)
  const orgId = employee?.organizationId || report.organizationId
  const org = orgId != null ? lookups.orgById.get(Number(orgId)) : null

  const status = STATUS_TO_FRONT[report.status] || String(report.status || '').toLowerCase()
  const points = pointsLog ? Number(pointsLog.pointsDelta) : 0

  return {
    id: report.id,
    code: `RVW-${String(report.id).padStart(3, '0')}`,
    reporter: report.submitter || employee?.name || '—',
    employeeId: report.submitterId ?? employee?.id ?? '—',
    orgName: org?.name || employee?.organizationName || '—',
    orgId: org?.id || orgId,
    project: project?.name || (report.projectId ? `项目#${report.projectId}` : '—'),
    indicator: indicator?.name || (report.indicatorId ? `指标#${report.indicatorId}` : '—'),
    amount: report.result,
    unit: indicator?.unit || '',
    attachmentCount: report.attachmentUrl ? 1 : 0,
    attachmentUrl: report.attachmentUrl || '',
    attachmentName: resolveAttachmentDisplayName(report.attachmentUrl),
    attachment: report.attachmentUrl,
    submittedAt: formatDateTime(report.receivedAt) || `${report.reportDate || ''} 00:00`,
    status,
    description: '',
    points,
    bigOrder: false,
    bigOrderPoints: 0,
    totalPoints: points,
    reviewer: report.auditedBy,
    reviewTime: formatDateTime(report.auditedAt),
    reviewComment: report.auditComment,
    reportDate: report.reportDate,
    projectId: report.projectId,
    indicatorId: report.indicatorId,
    calcDetail: pointsLog?.calcDetail || null,
    canReview: resolveCanReview(report, lookups, currentUser)
  }
}

async function fetchAllReviewItems() {
  const lookups = await loadLookups()
  const currentUser = getCurrentUser()
  const reports = await request('/api/admin/reports')
  const list = Array.isArray(reports) ? reports : []

  const approvedIds = list.filter((r) => r.status === 'APPROVED').map((r) => r.id)
  const pointsEntries = await Promise.all(
    approvedIds.map(async (reportId) => [reportId, await fetchPointsByReportId(reportId)])
  )
  const pointsByReportId = new Map(pointsEntries)

  const items = await Promise.all(
    list.map((report) => toReviewItem(report, lookups, pointsByReportId.get(report.id), currentUser))
  )

  return items.sort((a, b) => (a.submittedAt < b.submittedAt ? 1 : -1))
}

export async function getReviewList(params = {}) {
  const { status = 'all', keyword = '', startDate = '', endDate = '' } = params
  const all = await fetchAllReviewItems()
  const kw = keyword.trim()

  return all
    .filter((item) => (status === 'all' ? true : item.status === status))
    .filter((item) => {
      const day = item.submittedAt.slice(0, 10)
      if (startDate && day < startDate) return false
      if (endDate && day > endDate) return false
      return true
    })
    .filter((item) =>
      kw ? item.reporter.includes(kw) || item.orgName.includes(kw) || item.project.includes(kw) : true
    )
}

export async function getReviewDetail(id) {
  const lookups = await loadLookups()
  const currentUser = getCurrentUser()
  const report = await request(`/api/admin/reports/${id}`)
  if (!report) return null

  const pointsLog = report.status === 'APPROVED' ? await fetchPointsByReportId(id) : null
  return toReviewItem(report, lookups, pointsLog, currentUser)
}

export async function approveReview(id, payload = {}) {
  const reviewer = payload.reviewer || 'admin'
  const comment = payload.comment || '审核通过'
  const qs = new URLSearchParams({ reviewer, comment })

  await request(`/api/admin/reports/${id}/approve?${qs.toString()}`, { method: 'POST' })

  clearReviewCache()
  const pointsLog = await fetchPointsByReportId(id)
  const points = pointsLog ? Number(pointsLog.pointsDelta) : 0

  return {
    success: true,
    id,
    status: 'approved',
    points,
    totalPoints: points,
    calcDetail: pointsLog?.calcDetail || null
  }
}

export async function rejectReview(id, payload = {}) {
  const reviewer = payload.reviewer || 'admin'
  const reason = payload.comment || '已驳回'
  const qs = new URLSearchParams({ reviewer, reason })

  await request(`/api/admin/reports/${id}/reject?${qs.toString()}`, { method: 'POST' })

  clearReviewCache()
  return { success: true, id, status: 'rejected' }
}

export async function updateReviewReport(id, payload = {}) {
  const body = {}
  if (payload.result != null) body.result = String(payload.result)
  if (payload.reportDate) body.reportDate = payload.reportDate
  if (payload.attachmentUrl != null) body.attachmentUrl = payload.attachmentUrl

  const updated = await request(`/api/admin/reports/${id}`, {
    method: 'PUT',
    body: JSON.stringify(body)
  })

  clearReviewCache()
  return updated
}

export async function modifyAndApproveReview(id, payload = {}) {
  await updateReviewReport(id, {
    result: payload.result,
    reportDate: payload.reportDate,
    attachmentUrl: payload.attachmentUrl
  })
  return approveReview(id, payload)
}
