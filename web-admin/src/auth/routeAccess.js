import { decompositionPlans, projects } from '../data/mockData'
import { isOrgInScope } from './orgScope'

export function canAccessRoute(route, user) {
  const allowedRoles = route.meta?.roles

  if (!allowedRoles?.length) return true
  if (!user?.role || !allowedRoles.includes(user.role)) return false

  const projectId = route.params?.id
  if (!projectId) return true

  const tempProjects = getLocalTempProjects()
  const project = [...projects, ...tempProjects].find((item) => item.id === projectId)
  if (!project) return false

  if (route.meta?.projectAccess === 'visible') {
    const createdInScope = isOrgInScope(project.ownerOrgId, user.orgId)
    const assignedToOrg = decompositionPlans.some(
      (plan) => plan.projectId === projectId && plan.currentOrgId === user.orgId
    )

    return createdInScope || assignedToOrg
  }

  if (route.meta?.projectAccess === 'decompose') {
    if (project.ownerOrgId === user.orgId) return true

    return decompositionPlans.some(
      (plan) => plan.projectId === projectId && plan.currentOrgId === user.orgId
    )
  }

  return true
}

function getLocalTempProjects() {
  try {
    return JSON.parse(localStorage.getItem('tempProjects') || '[]')
  } catch {
    localStorage.removeItem('tempProjects')
    return []
  }
}
