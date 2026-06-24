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
    organizationId: user?.organizationId
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

  return data.map((project) => {
    const sameOrg = Number(project.organizationId) === Number(user?.organizationId)

    return {
      ...project,
      relation: sameOrg ? '本级创建' : project.distributionStatus || '可见项目',
      canConfigureIndicators: sameOrg,
      canDecompose: sameOrg,
      canDelete: false,
      canCreateProject: user
          ? ['总行', '省行', '市行', '支行'].includes(user.level)
          : false
    }
  })
}

export async function getProject(projectId) {
  return await request(`/api/admin/projects/${projectId}`)
}

export async function getProjectIndicators(projectId) {
  return await request(`/api/admin/projects/${projectId}/indicators`)
}

export async function createProjectIndicator(projectId, payload) {
  return await request(`/api/admin/projects/${projectId}/indicators`, {
    method: 'POST',
    body: JSON.stringify(payload)
  })
}

export async function updateProjectIndicator(projectId, id, payload) {
  return await request(`/api/admin/projects/${projectId}/indicators/${id}`, {
    method: 'PUT',
    body: JSON.stringify(payload)
  })
}

export async function deleteProjectIndicator(projectId, id) {
  return await request(`/api/admin/projects/${projectId}/indicators/${id}`, {
    method: 'DELETE'
  })
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

// --- 组员项目管理向导依赖（localStorage，原样保留其逻辑）---
const localProjectsKey = 'localProjects'
const projectConfigKey = (id) => `projectConfig:${id}`

export function getLocalProjects() {
  try {
    return JSON.parse(localStorage.getItem(localProjectsKey) || '[]')
  } catch {
    return []
  }
}

export function getProjectConfig(projectId) {
  try {
    const raw = localStorage.getItem(projectConfigKey(projectId))
    if (raw) return mockResolve(JSON.parse(raw))
  } catch {
    // 解析失败时回退到默认配置
  }
  return mockResolve({
    decompositionLevel: '市行→支行→网点',
    participatingOrgIds: [],
    employeeScope: 'auto',
    manualEmployees: '',
    reportTemplate: ''
  })
}

export function saveProjectConfig(projectId, config) {
  localStorage.setItem(projectConfigKey(projectId), JSON.stringify(config))
  return mockResolve({ success: true })
}
