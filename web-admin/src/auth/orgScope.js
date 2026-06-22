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
