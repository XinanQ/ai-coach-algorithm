import { decompositionPlans, decompositionRows, projects } from '../data/mockData'
import { getDirectChildren } from '../auth/orgScope'
import { mockResolve } from './request'

function clone(value) {
  return JSON.parse(JSON.stringify(value))
}

export function getDecomposition({ projectId, role, orgId } = {}) {
  if (!role) {
    return mockResolve(decompositionRows)
  }

  const plans = decompositionPlans
    .filter((plan) => plan.ownerRole === role)
    .filter((plan) => !orgId || plan.currentOrgId === orgId)
    .filter((plan) => !projectId || plan.projectId === projectId)
    .map((plan) => ({
      ...clone(plan),
      project: projects.find((project) => project.id === plan.projectId)
    }))

  if (!projectId) return mockResolve(plans)

  if (plans[0]) return mockResolve(plans[0])

  const tempProject = getLocalTempProjects().find(
    (project) => project.id === projectId && project.ownerOrgId === orgId
  )

  return mockResolve(tempProject ? buildInitialPlan(tempProject, role, orgId) : null)
}

export function saveDecomposition(plan) {
  return mockResolve({ success: true, plan })
}

function getLocalTempProjects() {
  try {
    return JSON.parse(localStorage.getItem('tempProjects') || '[]')
  } catch {
    localStorage.removeItem('tempProjects')
    return []
  }
}

function buildInitialPlan(project, role, orgId) {
  const children = getDirectChildren(orgId)

  return {
    id: `${project.id}-${orgId}-initial`,
    projectId: project.id,
    ownerRole: role,
    originType: 'created',
    receivedFrom: '',
    currentOrganization: project.owner,
    currentOrgId: orgId,
    currentLevel: project.ownerLevel,
    nextLevel: children[0]?.level || '下级',
    status: '未下发',
    project,
    targets: children.map((child) => ({
      id: child.id,
      target: child.name,
      level: child.level,
      indicators: []
    }))
  }
}
