import { decompositionPlans, indicators } from '../data/mockData'
import { mockResolve, request } from './request'

const tempProjectsKey = 'tempProjects'

function normalizeDate(value) {
  return value ? String(value).replaceAll('/', '-') : value
}

function normalizeProjectPayload(project, user) {
  return {
    ...project,
    startDate: normalizeDate(project.startDate),
    endDate: normalizeDate(project.endDate),
    ownerOrgId: user?.orgId
  }
}

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


export async function getProjects(user) {
  const data = await request('/api/admin/projects')

  return data.map((project) => ({
    ...project,
    relation: project.relation || project.distributionStatus || '待分解',
    canConfigureIndicators: true,
    canDecompose: true,
    canDelete: false,
    canCreateProject: user
        ? ['总行', '省行', '市行', '支行'].includes(user.level)
        : false
  }))
}

export async function getProject(projectId) {
  return await request(`/api/admin/projects/${projectId}`)
}

export function getProjectIndicators(projectId) {
  return mockResolve(indicators.filter((indicator) => indicator.projectId === projectId))
}

export async function createProject(project, user) {
  return await request('/api/admin/projects', {
    method: 'POST',
    body: JSON.stringify(normalizeProjectPayload(project, user))
  })
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
