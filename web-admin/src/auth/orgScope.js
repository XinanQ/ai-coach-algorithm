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
<<<<<<< HEAD
=======
}

// 把登录用户解析成前端 mock 机构树里的 orgId：优先按机构名匹配
// （兼容后端账号的 orgId 与前端 mock id 不一致），名字找不到再用原 orgId。
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

  return findByName(user.organization, organizations) || user.orgId || null
>>>>>>> 8266f79764faec18502c87e1687d15a4402729c8
}
