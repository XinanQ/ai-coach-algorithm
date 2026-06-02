import { decompositionPlans, projects, rankingRows, reports } from '../data/mockData'
import { isOrgInScope } from '../auth/orgScope'
import { mockResolve } from './request'

function getVisibleProjects(user) {
  if (!user) return []

  return projects.filter((project) => {
    const createdInScope = isOrgInScope(project.ownerOrgId, user.orgId)
    const assignedToOrg = decompositionPlans.some(
      (plan) => plan.projectId === project.id && plan.currentOrgId === user.orgId
    )
    const assignedToEmployee = decompositionPlans.some(
      (plan) =>
        plan.currentOrgId === user.orgId &&
        plan.nextLevel === '员工' &&
        plan.targets.some((target) => target.targetUserId === user.id || target.target === user.name) &&
        plan.projectId === project.id
    )

    return user.role === 'employee' ? assignedToEmployee : createdInScope || assignedToOrg
  })
}

function getVisibleRankings(user) {
  if (!user) return []

  return user.role === 'employee'
    ? rankingRows.filter((row) => row.userId === user.id)
    : rankingRows.filter((row) => isOrgInScope(row.orgId, user.orgId))
}

function getVisibleReports(user) {
  if (!user) return []

  return user.role === 'employee'
    ? reports.filter((report) => report.reporterId === user.id)
    : reports.filter((report) => isOrgInScope(report.orgId, user.orgId))
}

function getPendingDecompositions(user) {
  if (!user || user.role === 'employee') return 0
  return decompositionPlans.filter((plan) => plan.currentOrgId === user.orgId).length
}

function buildStats(user, visibleProjects, visibleRankings, visibleReports) {
  const inProgressCount = visibleProjects.filter((project) => project.status === '进行中').length
  const todayAmount = visibleReports.reduce((sum, report) => sum + Number(report.amount || 0), 0)
  const todayPoints = visibleReports.reduce((sum, report) => sum + Number(report.points || 0), 0)
  const pendingCount = getPendingDecompositions(user)

  return [
    {
      label: '可见项目',
      value: String(visibleProjects.length),
      hint: `${inProgressCount} 个进行中`
    },
    {
      label: user.role === 'employee' ? '本人上报业绩' : '范围内上报业绩',
      value: String(todayAmount),
      hint: `${visibleReports.length} 笔上报记录`
    },
    {
      label: user.role === 'employee' ? '本人积分' : '范围内积分',
      value: String(Math.round(todayPoints * 10) / 10),
      hint: `${visibleRankings.length} 条排名数据`
    },
    {
      label: user.role === 'employee' ? '待上报项目' : '待分解任务',
      value: String(user.role === 'employee' ? visibleProjects.length : pendingCount),
      hint: user.role === 'employee' ? '来自直属网点下发' : '当前机构任务池'
    }
  ]
}

export function getDashboardSummary(user) {
  const visibleProjects = getVisibleProjects(user)
  const visibleRankings = getVisibleRankings(user)
  const visibleReports = getVisibleReports(user)

  return mockResolve({
    stats: buildStats(user, visibleProjects, visibleRankings, visibleReports),
    projects: visibleProjects,
    rankings: visibleRankings.slice(0, 3)
  })
}
