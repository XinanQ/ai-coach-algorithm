import { decompositionPlans, indicators, projects } from '../data/mockData'
import { getProjectRelation, isOrgInScope } from '../auth/orgScope'
import { mockResolve } from './request'

const tempProjectsKey = 'tempProjects'

function getLocalTempProjects() {
  try {
    return JSON.parse(localStorage.getItem(tempProjectsKey) || '[]')
  } catch {
    localStorage.removeItem(tempProjectsKey)
    return []
  }
}

function setLocalTempProjects(projects) {
  localStorage.setItem(tempProjectsKey, JSON.stringify(projects))
}

async function getTempProjects() {
  try {
    const response = await fetch('/api/temp/projects')
    if (!response.ok) throw new Error('Cannot read temp projects')
    const payload = await response.json()
    setLocalTempProjects(payload.projects || [])
    return payload.projects || []
  } catch {
    localStorage.removeItem(tempProjectsKey)
    return []
  }
}

function mergeProjects(baseProjects, tempProjects) {
  const byId = new Map(baseProjects.map((project) => [project.id, project]))
  tempProjects.forEach((project) => byId.set(project.id, { ...project, isTemp: true }))
  return [...byId.values()]
}

function canDecomposeProject(project, user) {
  const assignedToOrg = decompositionPlans.some(
    (plan) => plan.projectId === project.id && plan.currentOrgId === user.orgId
  )
  const createdByCurrentOrg = project.ownerOrgId === user.orgId

  return assignedToOrg || createdByCurrentOrg
}

export function getProjects(user) {
  if (!user) {
    return mockResolve(projects)
  }

  return getTempProjects().then((tempProjects) => {
    const allProjects = mergeProjects(projects, tempProjects)

    const visibleProjects = allProjects
      .filter((project) => {
        const createdInScope = isOrgInScope(project.ownerOrgId, user.orgId)
        const assignedToOrg = decompositionPlans.some(
          (plan) => plan.projectId === project.id && plan.currentOrgId === user.orgId
        )
        return createdInScope || assignedToOrg
      })
      .map((project) => ({
        ...project,
        canConfigureIndicators: project.ownerOrgId === user.orgId,
        canDecompose: canDecomposeProject(project, user),
        canDelete: Boolean(project.isTemp && project.ownerOrgId === user.orgId),
        canCreateProject: ['总行', '省行', '市行', '支行'].includes(user.level),
        relation: getProjectRelation(project, user)
      }))

    return visibleProjects
  })
}

export function getProject(projectId) {
  return getTempProjects().then((tempProjects) => {
    const allProjects = mergeProjects(projects, tempProjects)
    return allProjects.find((project) => project.id === projectId) || allProjects[0]
  })
}

export function getProjectIndicators(projectId) {
  return mockResolve(indicators.filter((indicator) => indicator.projectId === projectId))
}

export async function createProject(project, user) {
  const payload = {
    ...project,
    id: project.id || `${user.orgId}-${Date.now()}`,
    owner: user.organization,
    ownerLevel: user.level,
    ownerOrgId: user.orgId,
    distributionStatus: '未下发',
    createdAt: new Date().toISOString().slice(0, 10)
  }

  try {
    const response = await fetch('/api/temp/projects', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    })

    if (!response.ok) throw new Error('Cannot save temp project')
    const result = await response.json()
    setLocalTempProjects(result.projects || [])
    return result
  } catch {
    throw new Error('开发服务器临时存储不可用，请确认 npm run dev 正在运行。')
  }
}

export async function deleteProject(projectId) {
  const response = await fetch(`/api/temp/projects?id=${encodeURIComponent(projectId)}`, {
    method: 'DELETE'
  })

  if (!response.ok) throw new Error('删除临时项目失败。')

  const result = await response.json()
  setLocalTempProjects(result.projects || [])
  return result
}
