import { decompositionPlans, decompositionRows, projects } from '../data/mockData'
import { mockResolve } from './request'

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

<<<<<<< HEAD
export function getDecomposition({ projectId, role, organizationId } = {}) {
  if (!role) {
    return mockResolve(decompositionRows)
  }

  const currentOrgId = Number(organizationId)

  const plans = decompositionPlans
      .filter((plan) => plan.ownerRole === role)
      .filter((plan) => !currentOrgId || Number(plan.currentOrgId) === currentOrgId)
      .filter((plan) => !projectId || String(plan.projectId) === String(projectId))
      .map((plan) => ({
        ...clone(plan),
        project: projects.find((project) => String(project.id) === String(plan.projectId))
      }))

  if (!projectId) return mockResolve(plans)

  if (plans[0]) return mockResolve(plans[0])

  return mockResolve(null)
}

export function saveDecomposition(plan) {
  return mockResolve({ success: true, plan })
}

function getLocalTempProjects() {
=======
function getReceived() {
>>>>>>> 8266f79764faec18502c87e1687d15a4402729c8
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
