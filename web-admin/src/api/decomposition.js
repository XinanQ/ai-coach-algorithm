import { decompositionPlans, decompositionRows, organizations } from '../data/mockData'
import { mockResolve, request } from './request'
import { resolveOrgId } from '../auth/orgScope'
import { getProject, getProjectIndicators } from './projects'
import { getOrganizationTree } from './organization'

const receivedKey = 'receivedDecompositions'

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

function normalizePlanIds(plan) {
  if (!plan) return plan
  const normalized = clone(plan)

  if (typeof normalized.projectId === 'string' && /^\d+$/.test(normalized.projectId)) {
    normalized.projectId = Number(normalized.projectId)
  }
  if (typeof normalized.currentOrgId === 'string' && /^\d+$/.test(normalized.currentOrgId)) {
    normalized.currentOrgId = Number(normalized.currentOrgId)
  }

  if (normalized.targets) {
    normalized.targets.forEach((target) => {
      if (typeof target.id === 'string' && /^\d+$/.test(target.id)) {
        target.id = Number(target.id)
      }
      if (target.indicators) {
        target.indicators.forEach((ind) => {
          if (ind.indicatorId != null && typeof ind.indicatorId === 'string' && /^\d+$/.test(ind.indicatorId)) {
            ind.indicatorId = Number(ind.indicatorId)
          }
        })
      }
    })
  }

  // Strip fields backend doesn't expect
  delete normalized.project
  delete normalized.projectName

  return normalized
}

export async function getDecomposition({ projectId, role, organizationId } = {}) {
  try {
    const qs = []
    if (role) qs.push(`role=${encodeURIComponent(role)}`)
    if (organizationId != null) qs.push(`organizationId=${encodeURIComponent(organizationId)}`)
    if (projectId) qs.push(`projectId=${encodeURIComponent(projectId)}`)
    const path = `/api/admin/decompositions${qs.length ? '?' + qs.join('&') : ''}`
    const res = await request(path).catch(() => null)
    if (res === null) {
      return fallbackGetDecomposition(projectId, role, organizationId)
    }
    return res
  } catch (e) {
    return fallbackGetDecomposition(projectId, role, organizationId)
  }
}

function fallbackGetDecomposition(projectId, role, organizationId) {
  if (!role) {
    return mockResolve(decompositionRows)
  }

  const matches = (plan) =>
    plan.ownerRole === role &&
    (!organizationId || plan.currentOrgId === organizationId) &&
    (!projectId || String(plan.projectId) === String(projectId))

  const basePlans = decompositionPlans.filter(matches)
  const receivedPlans = getReceived().filter(matches)
  const plans = [...basePlans, ...receivedPlans]

  if (!projectId) return mockResolve(plans)
  if (plans[0]) return mockResolve(plans[0])
  return mockResolve(null)
}

export async function saveDecomposition(plan) {
  const normalizedPlan = normalizePlanIds(plan)

  try {
    const res = await request('/api/admin/decompositions', {
      method: 'POST',
      body: JSON.stringify(normalizedPlan)
    }).catch(() => null)

    if (res === null) {
      // fallback: mirror previous mock behavior
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

    return res
  } catch (e) {
    return mockResolve({ success: false, error: e.message })
  }
}

function findOrgNode(orgId, nodes) {
  for (const node of nodes) {
    // Compare both as strings (mock data) and as numbers (backend data)
    if (node.id === orgId || String(node.id) === String(orgId) || Number(node.id) === Number(orgId)) return node
    if (node.children) {
      const found = findOrgNode(orgId, node.children)
      if (found) return found
    }
  }
  return null
}

function findOrgNodeByName(orgName, nodes) {
  if (!orgName) return null
  for (const node of nodes) {
    if (node.name === orgName) return node
    if (node.children) {
      const found = findOrgNodeByName(orgName, node.children)
      if (found) return found
    }
  }
  return null
}

function resolveChineseLevel(level) {
  if (!level) return ''
  return { HEADQUARTERS: '总行', PROVINCE: '省行', CITY: '市行', BRANCH: '支行', OUTLET: '网点' }[level] || level
}

function buildPlanFromOrgNode(node, projectId, project, rawIndicators, user) {
  const indicators = (rawIndicators || []).map((ind) => ({
    indicatorId: ind.indicatorId ?? ind.id,
    indicator: ind.indicatorName || ind.indicator || `指标 ${ind.indicatorId ?? ind.id}`,
    totalTask: Number(ind.targetValue) || 0,
    allocated: 0,
    currentAllocation: 0,
    unit: ind.unit || ''
  }))
  if (indicators.length === 0) return null

  const childLevel = childLevelMap[node.level] || node.children?.[0]?.level || '下级'

  return {
    id: `dynamic-${projectId}`,
    projectId: String(projectId),
    projectName: project.name,
    ownerRole: user?.role,
    originType: 'created',
    receivedFrom: '',
    currentOrganization: node.name,
    currentOrgId: node.id,
    currentLevel: node.level,
    nextLevel: childLevel,
    status: '待分解',
    project,
    targets: (node.children || []).map((child) => ({
      id: child.id,
      target: child.name,
      level: child.level || '',
      indicators: indicators.map((item) => ({ ...item }))
    }))
  }
}

function numericId(value) {
  if (value == null) return null
  const num = Number(value)
  return Number.isNaN(num) ? null : num
}

export async function buildPlanForProject(projectId, user) {
  const [project, rawIndicators] = await Promise.all([
    getProject(projectId),
    getProjectIndicators(projectId)
  ])
  if (!project) return null

  // 1) Best: try new context endpoint
  try {
    const ctx = await request('/api/admin/decompositions/context')
    if (ctx && ctx.children && ctx.children.length > 0) {
      return {
        id: `dynamic-${projectId}`,
        projectId: String(projectId),
        projectName: project.name,
        ownerRole: user?.role,
        originType: 'created',
        receivedFrom: '',
        currentOrganization: ctx.orgName,
        currentOrgId: ctx.orgId,
        currentLevel: ctx.currentLevel,
        nextLevel: ctx.nextLevel,
        status: '待分解',
        project,
        targets: ctx.children.map((child) => ({
          id: child.id,
          target: child.name,
          level: resolveChineseLevel(child.level),
          indicators: (rawIndicators || []).map((ind) => ({
            indicatorId: ind.indicatorId ?? ind.id,
            indicator: ind.indicatorName || ind.indicator || `指标 ${ind.indicatorId ?? ind.id}`,
            totalTask: Number(ind.targetValue) || 0,
            allocated: 0,
            currentAllocation: 0,
            unit: ind.unit || ''
          }))
        }))
      }
    }
  } catch (e) {
    // Fall through to next fallback
  }

  // 2) Fallback: existing organization tree endpoint
  try {
    const tree = await getOrganizationTree()
    if (tree && tree.length) {
      const root = tree[0]
      const orgId = resolveOrgId(user)

      // Find current user's org by numeric ID or name
      let node = findOrgNode(orgId, [root])
      if (!node && user?.organization) {
        node = findOrgNodeByName(user.organization, [root])
      }
      if (node && node.children && node.children.length > 0) {
        // Map backend enum levels to Chinese labels
        const mappedNode = {
          ...node,
          level: resolveChineseLevel(node.level),
          children: (node.children || []).map((c) => ({ ...c, level: resolveChineseLevel(c.level) }))
        }
        const plan = buildPlanFromOrgNode(mappedNode, projectId, project, rawIndicators, user)
        if (plan) return plan
      }
    }
  } catch (e) {
    // Fall through to mock data fallback
  }

  // 3) Last resort: mock organizations tree
  const orgId = resolveOrgId(user)
  let node = findOrgNode(orgId, organizations)
  if (!node && user?.organization) {
    node = findOrgNodeByName(user.organization, organizations)
  }

  if (node && node.children && node.children.length > 0) {
    const plan = buildPlanFromOrgNode(node, projectId, project, rawIndicators, user)
    if (plan) return plan
  }

  return null
}
