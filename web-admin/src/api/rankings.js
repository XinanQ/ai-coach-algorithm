import { decompositionPlans, indicators, projects, rankingRows } from '../data/mockData'
import { isOrgInScope } from '../auth/orgScope'
import { mockResolve } from './request'

export function getRankingOptions(user) {
  if (!user) return mockResolve({ projects: [], indicators: [] })

  const visibleProjectIds = projects
    .filter((project) => isOrgInScope(project.ownerOrgId, user.orgId))
    .map((project) => project.id)
  const assignedProjectIds = decompositionPlans
    .filter((plan) => plan.currentOrgId === user.orgId)
    .map((plan) => plan.projectId)
  const projectIds = [...new Set([...visibleProjectIds, ...assignedProjectIds])]

  return mockResolve({
    projects: projects.filter((project) => projectIds.includes(project.id)),
    indicators: indicators.filter((indicator) => projectIds.includes(indicator.projectId))
  })
}

export function getRankings(user) {
  if (!user) return mockResolve([])

  const visibleRows =
    user.role === 'employee'
      ? rankingRows.filter((row) => row.userId === user.id)
      : rankingRows.filter((row) => isOrgInScope(row.orgId, user.orgId))

  return mockResolve(visibleRows)
}
