import { decompositionPlans, decompositionRows, organizations } from '../data/mockData'
import { mockResolve, request } from './request'
import { resolveOrgId } from '../auth/orgScope'
import { getProject, getProjectIndicators } from './projects'
import { getOrganizationTree } from './organization'

const receivedKey = 'receivedDecompositions'
const savedKey = 'savedDecompositions'

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

function getSavedPlans() {
  try {
    return JSON.parse(localStorage.getItem(savedKey) || '[]')
  } catch {
    return []
  }
}

function setSavedPlans(list) {
  localStorage.setItem(savedKey, JSON.stringify(list))
}

// fetch 在后端不可达时抛 TypeError；HTTP 4xx/5xx 由 request() 抛带后端文案的普通 Error。
// 只有前者才算"离线"，可以降级到本地暂存；后者必须如实抛给页面。
function isNetworkError(e) {
  if (e instanceof TypeError) return true
  const msg = (e && e.message) || ''
  return /failed to fetch|networkerror|network error|load failed/i.test(msg)
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
  const qs = []
  if (role) qs.push(`role=${encodeURIComponent(role)}`)
  if (organizationId != null) qs.push(`organizationId=${encodeURIComponent(organizationId)}`)
  if (projectId) qs.push(`projectId=${encodeURIComponent(projectId)}`)
  const path = `/api/admin/decompositions${qs.length ? '?' + qs.join('&') : ''}`

  try {
    // 后端可达时以后端为准：即便是"暂无记录"（null / 空 / 空数组）也如实返回，
    // 交给上层用实时上下文重建，绝不再用本地缓存把真实状态盖掉。
    return await request(path)
  } catch (e) {
    // 仅在后端不可达 / 报错时才回退本地缓存（读操作降级是安全的）。
    return fallbackGetDecomposition(projectId, role, organizationId)
  }
}

function fallbackGetDecomposition(projectId, role, organizationId) {
  if (!role) {
    return mockResolve(decompositionRows)
  }

  // 机构 id 在 mock（字符串）与后端（数字）之间混用，统一按字符串宽松比较
  const sameId = (a, b) => a != null && b != null && String(a) === String(b)
  const matches = (plan) =>
    plan.ownerRole === role &&
    (!organizationId || sameId(plan.currentOrgId, organizationId)) &&
    (!projectId || String(plan.projectId) === String(projectId))

  const basePlans = decompositionPlans.filter(matches)
  const savedPlans = getSavedPlans().filter(matches)
  const receivedPlans = getReceived().filter(matches)

  // 本地保存的本级计划（savedPlans）覆盖静态 mock 中的同 id 项，
  // received 是下级派生记录、id 不冲突，直接并入。
  const byId = new Map()
  ;[...basePlans, ...savedPlans, ...receivedPlans].forEach((plan) => {
    byId.set(plan.id, plan)
  })
  const plans = [...byId.values()]

  if (!projectId) return mockResolve(plans)
  // 单项目视图：优先返回可编辑记录（readOnly=false），其次只读的收到记录
  const preferred = [...plans].sort(
    (a, b) => Number(Boolean(a.readOnly)) - Number(Boolean(b.readOnly))
  )
  if (preferred[0]) return mockResolve(preferred[0])
  return mockResolve(null)
}

export async function saveDecomposition(plan) {
  const normalizedPlan = normalizePlanIds(plan)

  try {
    // 后端可达：直接返回后端真实结果，成功或失败都不再吞掉。
    return await request('/api/admin/decompositions', {
      method: 'POST',
      body: JSON.stringify(normalizedPlan)
    })
  } catch (e) {
    // 后端明确拒绝（权限 / 机构校验 / 序列化失败等 4xx、5xx）必须抛出，
    // 让页面把真实原因显示给用户，而不是假装保存成功。
    if (!isNetworkError(e)) {
      throw e
    }
    // 仅当后端不可达时才降级到本地暂存。
    return saveDecompositionOffline(plan)
  }
}

// 离线暂存：既要保留本级自己填写的分配（重进可读回），也要生成下级派生记录。
function saveDecompositionOffline(plan) {
  // 1) 持久化本级计划——这是原实现遗漏的部分，导致本级退出后再进就"消失"。
  if (!plan.readOnly) {
    const saved = getSavedPlans()
    const record = clone(plan)
    delete record.project // 与后端一致，剥离仅用于展示的大对象
    record.status = '已下发'
    const idx = saved.findIndex((item) => item.id === record.id)
    if (idx >= 0) saved[idx] = record
    else saved.push(record)
    setSavedPlans(saved)
  }

  // 2) 生成下级 received 记录（沿用原有逻辑）。
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

  return mockResolve({ success: true, offline: true, plan })
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

// 收到方继续向下下发：复用"本机构 → 直属下级"的可编辑计划骨架（含子节点/层级/机构名），
// 再把每个指标的总量替换为"本级收到的任务额度"，从而保证不会超过收到的份额。
export async function buildReceivedPlanForProject(projectId, user, received) {
  const base = await buildPlanForProject(projectId, user)
  if (!base) return null

  const inbound = received?.targets?.[0]?.indicators || []
  if (inbound.length === 0) return null

  base.id = `received-plan-${projectId}-${base.currentOrgId}`
  base.originType = 'received'
  base.receivedFrom = received?.receivedFrom || ''
  base.status = '待分解'
  base.readOnly = false
  base.targets = base.targets.map((target) => ({
    ...target,
    indicators: inbound.map((ind) => ({
      indicatorId: ind.indicatorId,
      indicator: ind.indicator,
      unit: ind.unit || '',
      totalTask: Number(ind.totalTask || 0),
      allocated: 0,
      currentAllocation: 0
    }))
  }))
  return base
}

// 本机构有任何分解记录（本级创建 或 上级下发收到）的项目，都允许继续向下下发。
// 供项目列表判断是否显示「下发分解」按钮。
export async function getDecomposableProjectIds(user) {
  if (!user?.role) return []
  const records = await getDecomposition({
    role: user.role,
    organizationId: resolveOrgId(user)
  }).catch(() => null)
  const list = Array.isArray(records) ? records : records ? [records] : []
  return [...new Set(list.map((r) => r.projectId).filter((id) => id != null))]
}
