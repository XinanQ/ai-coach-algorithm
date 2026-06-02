import { organizations } from '../data/mockData'

export const levelOrder = ['总行', '省行', '市行', '支行', '网点', '员工']

const orgIndex = new Map()
const childrenIndex = new Map()

function indexOrganization(node, parentIds = []) {
  const pathIds = [...parentIds, node.id]
  orgIndex.set(node.id, {
    id: node.id,
    name: node.name,
    level: node.level,
    pathIds,
    parentId: parentIds[parentIds.length - 1] || null
  })

  childrenIndex.set(node.id, (node.children || []).map((child) => ({
    id: child.id,
    name: child.name,
    level: child.level
  })))

  node.children?.forEach((child) => indexOrganization(child, pathIds))
}

organizations.forEach((organization) => indexOrganization(organization))

export function getOrganization(orgId) {
  return orgIndex.get(orgId) || null
}

export function getDirectChildren(orgId) {
  return childrenIndex.get(orgId) || []
}

export function getOrgIdByName(name) {
  for (const organization of orgIndex.values()) {
    if (organization.name === name) return organization.id
  }
  return ''
}

export function isOrgInScope(targetOrgId, scopeOrgId) {
  if (!targetOrgId || !scopeOrgId) return false
  const target = getOrganization(targetOrgId)
  return Boolean(target?.pathIds.includes(scopeOrgId))
}

export function isSameOrg(targetOrgId, scopeOrgId) {
  return Boolean(targetOrgId && scopeOrgId && targetOrgId === scopeOrgId)
}

export function getProjectRelation(project, user) {
  const projectLevelIndex = levelOrder.indexOf(project.ownerLevel)
  const userLevelIndex = levelOrder.indexOf(user.level)

  if (project.ownerOrgId === user.orgId) return '本级创建'
  if (isOrgInScope(project.ownerOrgId, user.orgId)) return '下级创建'
  if (projectLevelIndex < userLevelIndex) return '上级下发'
  return '可见项目'
}
