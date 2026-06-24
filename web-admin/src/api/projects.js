import { decompositionPlans, indicators, organizations, projects as mockProjects } from '../data/mockData'
import { mockResolve } from './request'

const deletedIdsKey = 'deletedProjectIds'
const localProjectsKey = 'localProjects'

function normalizeDate(value) {
  return value ? String(value).replaceAll('/', '-') : value
}

// 把登录用户解析成前端 mock 机构树里的 orgId。
// 优先用机构名匹配（兼容后端账号的 orgId 与前端 mock id 不一致的情况），名字找不到再用原 orgId。
function findOrgIdByName(name, nodes) {
  for (const node of nodes) {
    if (name && node.name === name) return node.id
    if (node.children) {
      const found = findOrgIdByName(name, node.children)
      if (found) return found
    }
  }
  return null
}

function resolveOrgId(user) {
  if (!user) return null
  return findOrgIdByName(user.organization, organizations) || user.orgId || null
}

function getDeletedIds() {
  try {
    return new Set(JSON.parse(localStorage.getItem(deletedIdsKey) || '[]'))
  } catch {
    return new Set()
  }
}

function addDeletedId(id) {
  const ids = getDeletedIds()
  ids.add(id)
  localStorage.setItem(deletedIdsKey, JSON.stringify([...ids]))
}

export function getLocalProjects() {
  try {
    return JSON.parse(localStorage.getItem(localProjectsKey) || '[]')
  } catch {
    return []
  }
}

function setLocalProjects(list) {
  localStorage.setItem(localProjectsKey, JSON.stringify(list))
}

function allProjects() {
  return [...mockProjects, ...getLocalProjects()]
}

function canDecomposeProject(project, orgId) {
  const assignedToOrg = decompositionPlans.some(
    (plan) => plan.projectId === project.id && plan.currentOrgId === orgId
  )
  const createdByCurrentOrg = project.ownerOrgId === orgId
  return assignedToOrg || createdByCurrentOrg
}

export async function getProjects(user) {
  const orgId = resolveOrgId(user)
  const deletedIds = getDeletedIds()
  const data = await mockResolve(allProjects().filter((p) => !deletedIds.has(p.id)))

  return data.map((project) => {
    const sameOrg = project.ownerOrgId === orgId
    return {
      ...project,
      relation: sameOrg ? '本级创建' : project.distributionStatus || '可见项目',
      canConfigureIndicators: sameOrg,
      canDecompose: canDecomposeProject(project, orgId),
      canDelete: true,
      canCreateProject: user ? ['总行', '省行', '市行', '支行'].includes(user.level) : false
    }
  })
}

export async function getProject(projectId) {
  return mockResolve(allProjects().find((p) => p.id === projectId) ?? null)
}

export function getProjectIndicators(projectId) {
  const local = getLocalProjects().find((project) => project.id === projectId)
  if (local) {
    const mapped = (local.indicators || []).map((ind, index) => ({
      id: `${projectId}-${index}`,
      projectId,
      name: ind.name,
      indicatorType: '业务指标',
      unit: ind.unit,
      pointRule: ind.amount ? Number((ind.points / ind.amount).toFixed(2)) : ind.points,
      weight: ind.weight
    }))
    return mockResolve(mapped)
  }
  return mockResolve(indicators.filter((indicator) => indicator.projectId === projectId))
}

export async function createProject(project, user) {
  const list = getLocalProjects()
  const newProject = {
    id: `local-${Date.now()}`,
    name: project.name,
    description: project.description,
    startDate: normalizeDate(project.startDate),
    endDate: normalizeDate(project.endDate),
    reportDeadline: project.reportDeadline,
    attachmentRequired: project.attachmentRequired,
    status: project.status,
    owner: user?.organization || '',
    ownerLevel: user?.level || '',
    ownerOrgId: resolveOrgId(user) || '',
    distributionStatus: '待分解',
    createdAt: new Date().toISOString().slice(0, 10),
    // 去掉 Vue 响应式（Proxy）包装，否则 mockResolve 的 structuredClone 无法克隆
    indicators: JSON.parse(JSON.stringify(project.indicators || []))
  }
  list.push(newProject)
  setLocalProjects(list)
  return mockResolve(newProject)
}

export async function deleteProject(projectId) {
  addDeletedId(projectId)
  return mockResolve({ success: true })
}

const projectConfigKey = (id) => `projectConfig:${id}`

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
