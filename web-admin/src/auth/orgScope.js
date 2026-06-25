import { organizations } from '../data/mockData'

export const levelOrder = ['总行', '省行', '市行', '支行', '网点', '员工']

function normalizeId(id) {
  return id === null || id === undefined || id === '' ? null : Number(id)
}

export function getOrganization() {
  return null
}

export function getDirectChildren() {
  return []
}

export function getOrgIdByName() {
  return null
}

export function isSameOrg(targetOrgId, scopeOrgId) {
  const target = normalizeId(targetOrgId)
  const scope = normalizeId(scopeOrgId)

  return target !== null && scope !== null && target === scope
}

export function isOrgInScope(targetOrgId, scopeOrgId) {
  return isSameOrg(targetOrgId, scopeOrgId)
}

export function getProjectRelation(project, user) {
  if (isSameOrg(project.organizationId, user.organizationId)) {
    return '本级创建'
  }

  return project.distributionStatus || '可见项目'
}

// 组员分解工作台依赖（原样保留其逻辑）
export function resolveOrgId(user) {
  if (!user) return null

  const findByName = (name, nodes) => {
    for (const node of nodes) {
      if (name && node.name === name) return node.id
      if (node.children) {
        const found = findByName(name, node.children)
        if (found) return found
      }
    }
    return null
  }

  // Prefer numeric orgId from backend; fall back to mock org tree lookup
  if (user.organizationId != null && !isNaN(Number(user.organizationId))) {
    return Number(user.organizationId)
  }
  if (user.orgId != null && !isNaN(Number(user.orgId))) {
    return Number(user.orgId)
  }
  return findByName(user.organization, organizations) || user.organizationId || user.orgId || null
}
