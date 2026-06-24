import { decompositionPlans, decompositionRows, organizations, projects } from '../data/mockData'
import { mockResolve } from './request'
import { resolveOrgId } from '../auth/orgScope'
import { getProject, getProjectIndicators } from './projects'

const receivedKey = 'receivedDecompositions'

// 下发后，下一层级对应的「再下一级」与角色
const childLevelMap = {
  '总行': '省行',
  '省行': '市行',
  '市行': '支行',
  '支行': '网点',
  '网点': '员工'
}
const roleByLevel = {
  '省行': 'province_admin',
  '市行': 'city_admin',
  '支行': 'branch_admin',
  '网点': 'outlet_admin'
}

function clone(value) {
  return JSON.parse(JSON.stringify(value))
}

function getReceived() {
  try {
    return JSON.parse(localStorage.getItem(receivedKey) || '[]')
  } catch {
    return []
  }
}

function setReceived(list) {
  localStorage.setItem(receivedKey, JSON.stringify(list))
}

function withProject(plan) {
  return {
    ...clone(plan),
    project: projects.find((project) => String(project.id) === String(plan.projectId))
  }
}

export function getDecomposition({ projectId, role, organizationId } = {}) {
  if (!role) {
    return mockResolve(decompositionRows)
  }

  const matches = (plan) =>
    plan.ownerRole === role &&
    (!organizationId || plan.currentOrgId === organizationId) &&
    (!projectId || String(plan.projectId) === String(projectId))

  // mock 中预置的待分解任务 + 上级下发后存到本地的「已收到（只读）」任务
  const basePlans = decompositionPlans.filter(matches).map(withProject)
  const receivedPlans = getReceived().filter(matches).map(withProject)
  const plans = [...basePlans, ...receivedPlans]

  if (!projectId) return mockResolve(plans)
  if (plans[0]) return mockResolve(plans[0])
  return mockResolve(null)
}

export function saveDecomposition(plan) {
  // 下发给直属下级后，为每个下级生成一条「已收到、只读」的任务记录，
  // 供下一层级（如支行管理员）登录分解工作台时查看，但不可编辑。
  const childLevel = plan.nextLevel
  const grandChildLevel = childLevelMap[childLevel] || '下级'
  const childRole = roleByLevel[childLevel]

  if (childRole) {
    const received = getReceived()

    plan.targets.forEach((target) => {
      const id = `received-${plan.projectId}-${target.id}`
      const record = {
        id,
        projectId: plan.projectId,
        projectName: plan.project?.name || '',
        ownerRole: childRole,
        originType: 'received',
        receivedFrom: plan.currentOrganization,
        currentOrganization: target.target,
        currentOrgId: target.id,
        currentLevel: childLevel,
        nextLevel: grandChildLevel,
        status: '已下发',
        readOnly: true,
        targets: [
          {
            id: target.id,
            target: target.target,
            level: childLevel,
            indicators: target.indicators.map((indicator) => ({
              indicatorId: indicator.indicatorId,
              indicator: indicator.indicator,
              totalTask: Number(indicator.currentAllocation || 0),
              allocated: 0,
              currentAllocation: 0,
              unit: indicator.unit
            }))
          }
        ]
      }

      const index = received.findIndex((item) => item.id === id)
      if (index >= 0) received[index] = record
      else received.push(record)
    })

    setReceived(received)
  }

  return mockResolve({ success: true, plan })
}

function findOrgNode(orgId, nodes) {
  for (const node of nodes) {
    if (node.id === orgId) return node
    if (node.children) {
      const found = findOrgNode(orgId, node.children)
      if (found) return found
    }
  }
  return null
}

// 后端项目在 mock 中没有预置分解计划时，按「当前机构的直属下级 × 项目指标」动态生成一个待分解计划。
// 让来自后端的项目也能进入下发分解流程；保存后走 saveDecomposition 生成下级的只读任务。
export async function buildPlanForProject(projectId, user) {
  const orgId = resolveOrgId(user)
  const node = findOrgNode(orgId, organizations)
  if (!node || !node.children || node.children.length === 0) return null

  const [project, rawIndicators] = await Promise.all([
    getProject(projectId),
    getProjectIndicators(projectId)
  ])
  if (!project) return null

  const indicators = (rawIndicators || []).map((ind) => ({
    indicatorId: ind.indicatorId ?? ind.id,
    indicator: ind.indicatorName || ind.indicator || `指标 ${ind.indicatorId ?? ind.id}`,
    totalTask: Number(ind.targetValue) || 0,
    allocated: 0,
    currentAllocation: 0,
    unit: ind.unit || ''
  }))
  if (indicators.length === 0) return null

  return {
    id: `dynamic-${projectId}`,
    projectId: String(projectId),
    projectName: project.name,
    ownerRole: user?.role,
    originType: 'created',
    receivedFrom: '',
    currentOrganization: node.name,
    currentOrgId: orgId,
    currentLevel: node.level,
    nextLevel: node.children[0]?.level || '下级',
    status: '待分解',
    project,
    targets: node.children.map((child) => ({
      id: child.id,
      target: child.name,
      level: child.level,
      indicators: indicators.map((item) => ({ ...item }))
    }))
  }
}
