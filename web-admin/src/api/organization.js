import { request, mockResolve } from './request'
import { getRankings } from './rankings'

const BASE_URL = '/api/admin/organizations'

const CHILD_LEVEL_TO_RANKING = {
  CITY: 'city',
  BRANCH: 'branch',
  OUTLET: 'outlet',
  HEADQUARTERS: 'city',
  PROVINCE: 'city'
}

function todayIsoDate() {
  return new Date().toISOString().slice(0, 10)
}

function resolveChildRankingLevel(node) {
  const child = node?.children?.[0]
  if (!child?.level) return null
  return CHILD_LEVEL_TO_RANKING[String(child.level).toUpperCase()] || null
}

export function getOrganizations() {
  return request(BASE_URL)
}

export function getOrganizationTree() {
  return request(`${BASE_URL}/tree`)
}

export function getOrganizationById(id) {
  return request(`${BASE_URL}/${id}`)
}

export function createOrganization(data, parentId) {
  const query = parentId ? `?parentId=${parentId}` : ''

  return request(`${BASE_URL}${query}`, {
    method: 'POST',
    body: JSON.stringify(data)
  })
}

export function updateOrganization(id, data, parentId) {
  const query = parentId ? `?parentId=${parentId}` : ''

  return request(`${BASE_URL}/${id}${query}`, {
    method: 'PUT',
    body: JSON.stringify(data)
  })
}

export function deleteOrganization(id) {
  return request(`${BASE_URL}/${id}`, {
    method: 'DELETE'
  })
}

export function getOrganizationsByLevel(level) {
  return request(`${BASE_URL}/by-level/${level}`)
}

// ===== 机构统计（来自前端 merge 分支的新增功能）=====
// team 后端暂未提供机构维度的统计接口，以下为前端占位实现：
// 基于当前机构节点派生示例数据，使页面图表可正常渲染。
// 待后端提供 staff-breakdown / children-ranking / indicator-stats（或等价接口）后，
// 将下列 mockResolve(...) 替换为对应 request(...) 调用即可，函数签名保持不变。

export function getOrgStaffBreakdown(node) {
  const children = node?.children || []
  if (!children.length) {
    return mockResolve({ name: node?.name || '机构', value: node?.staffCount || 0 })
  }
  return mockResolve({
    name: node?.name || '机构',
    children: children.map((child) => ({
      name: child.name,
      value: child.staffCount || (child.children?.length || 1) * 8
    }))
  })
}

export async function getChildrenRanking(node, user) {
  const children = node?.children || []
  if (!children.length || !user) return []

  const level = resolveChildRankingLevel(node)
  if (!level) return []

  const childIds = new Set(children.map((child) => Number(child.id)))
  const rankings = await getRankings(user, level, '', '', {
    period: 'MONTH',
    date: todayIsoDate()
  })

  return rankings
    .filter((row) => childIds.has(Number(row.organizationId)))
    .sort((a, b) => Number(b.points) - Number(a.points))
    .slice(0, 5)
    .map((row) => ({
      name: row.name,
      points: Number(row.points || 0),
      rank: row.rank
    }))
}

export function getOrgIndicatorStats(node) {
  return mockResolve([
    { name: '存款', completionRate: 82 },
    { name: '贷款', completionRate: 68 },
    { name: '中间业务', completionRate: 74 },
    { name: '客户拓展', completionRate: 90 },
    { name: '风险合规', completionRate: 88 }
  ])
}
