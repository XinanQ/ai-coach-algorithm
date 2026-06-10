import { decompositionPlans, indicators, projects, reports } from '../data/mockData'
import { isOrgInScope } from '../auth/orgScope'
import { mockResolve } from './request'

function getAssignedPlans(user) {
  if (!user) return []

  return decompositionPlans
    .filter((plan) => plan.currentOrgId === user.orgId && plan.nextLevel === '员工')
    .filter((plan) =>
      plan.targets.some((target) => target.targetUserId === user.id || target.target === user.name)
    )
}

export function getReportOptions(user) {
  const assignedPlans = getAssignedPlans(user)
  const assignedProjectIds = assignedPlans.map((plan) => plan.projectId)
  const visibleProjects = projects
    .filter((project) => assignedProjectIds.includes(project.id))
    .map((project) => {
      const plan = assignedPlans.find((item) => item.projectId === project.id)
      return {
        ...project,
        assignedFrom: plan?.currentOrganization || '',
        assignmentLevel: plan?.currentLevel || ''
      }
    })
  const visibleIndicators = indicators.filter((indicator) => assignedProjectIds.includes(indicator.projectId))

  return mockResolve({ projects: visibleProjects, indicators: visibleIndicators })
}

export function getMyReports(user) {
  if (!user) return mockResolve([])

  const visibleReports =
    user.role === 'employee'
      ? reports.filter((report) => report.reporterId === user.id)
      : reports.filter((report) => isOrgInScope(report.orgId, user.orgId))

  return mockResolve(visibleReports)
}

export function submitReport(report) {
  return mockResolve({ success: true, report })
}
