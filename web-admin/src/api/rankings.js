import { request } from './request'

// 排名 ↔ GET /api/admin/rankings
// projectId / indicatorId 不传时的含义与后端一致：
//   都传 → 某项目某指标
//   只传 projectId → 某项目整项目汇总
//   只传 indicatorId → 全部项目下该指标
//   都不传 → 全部项目全部指标

export async function getProjects() {
  return request('/api/admin/projects')
}

export async function getProjectIndicators(projectId) {
  if (!projectId) return []
  const list = await request(`/api/admin/projects/${projectId}/indicators`)
  return (list || []).map((pi) => ({
    id: pi.indicatorId,
    name: pi.indicatorName,
    projectId: pi.projectId,
    unit: pi.unit,
    linkId: pi.id
  }))
}

export async function getIndicatorLibrary() {
  const page = await request('/api/admin/indicators?page=0&size=200')
  const list = page?.content || (Array.isArray(page) ? page : [])
  return list.map((item) => ({
    id: item.id,
    name: item.name,
    unit: item.unit
  }))
}

/** @deprecated 保留兼容；请用 getProjects + getProjectIndicators */
export async function getRankingOptions(user) {
  if (!user) return { projects: [], indicators: [] }
  const projects = await getProjects()
  const indicatorLists = await Promise.all(
    projects.map((project) => getProjectIndicators(project.id).catch(() => []))
  )
  const indicators = projects.flatMap((project, index) =>
    (indicatorLists[index] || []).map((ind) => ({ ...ind, projectId: project.id }))
  )
  return { projects, indicators }
}

function mapRankingRow(row) {
  return {
    rank: row.rank,
    id: row.id,
    name: row.name,
    organization: row.organization || '—',
    organizationId: row.organizationId,
    points: row.points,
    achievement: '—',
    completionRate: 0
  }
}

function todayIsoDate() {
  return new Date().toISOString().slice(0, 10)
}

export async function getRankings(
  user,
  level = 'employee',
  projectId = '',
  indicatorId = '',
  { period = 'MONTH', date = todayIsoDate() } = {}
) {
  if (!user) return []

  const params = new URLSearchParams()
  if (projectId) params.set('projectId', String(projectId))
  if (indicatorId) params.set('indicatorId', String(indicatorId))
  params.set('level', level)
  params.set('period', period)
  params.set('date', date)

  const response = await request(`/api/admin/rankings?${params.toString()}`)
  const items = response?.items || []
  return items.map(mapRankingRow)
}
