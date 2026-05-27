import { decompositionPlans, projects } from '../data/mockData'
import { isOrgInScope } from './orgScope'

export const roleProfiles = {
  head_admin: {
    name: '总行管理员',
    level: '总行',
    organization: '总行',
    orgId: 'hq',
    dataScope: '全国所有机构与员工'
  },
  province_admin: {
    name: '省行管理员',
    level: '省行',
    organization: '江苏省行',
    orgId: 'js',
    dataScope: '本省下辖市行、支行、网点与员工'
  },
  city_admin: {
    name: '市行管理员',
    level: '市行',
    organization: '南京市行',
    orgId: 'nj',
    dataScope: '本市下辖支行、网点与员工'
  },
  branch_admin: {
    name: '支行管理员',
    level: '支行',
    organization: '鼓楼支行',
    orgId: 'gl',
    dataScope: '本支行下辖网点与员工'
  },
  outlet_admin: {
    name: '网点管理员',
    level: '网点',
    organization: '鼓楼营业室',
    orgId: 'a-branch',
    dataScope: '本网点员工'
  },
  employee: {
    name: '普通员工',
    level: '员工',
    organization: '鼓楼营业室',
    orgId: 'a-branch',
    dataScope: '本人任务、上报与排名'
  }
}

export const demoAccounts = [
  { username: 'head', password: '123456', role: 'head_admin' },
  { username: 'province', password: '123456', role: 'province_admin' },
  { username: 'city', password: '123456', role: 'city_admin' },
  { username: 'admin', password: '123456', role: 'branch_admin' },
  { username: 'outlet', password: '123456', role: 'outlet_admin' },
  { username: 'employee', password: '123456', role: 'employee', name: '张三', orgId: 'a-branch', organization: '鼓楼营业室' },
  { username: 'js_province', password: '123456', role: 'province_admin', organization: '江苏省行', orgId: 'js' },
  { username: 'js_city', password: '123456', role: 'city_admin', organization: '南京市行', orgId: 'nj' },
  { username: 'js_employee', password: '123456', role: 'employee', name: '张三', organization: '鼓楼营业室', orgId: 'a-branch' },
  { username: 'zj_province', password: '123456', role: 'province_admin', organization: '浙江省行', orgId: 'zj' },
  { username: 'zj_city', password: '123456', role: 'city_admin', organization: '杭州市行', orgId: 'hz' },
  { username: 'gd_province', password: '123456', role: 'province_admin', organization: '广东省行', orgId: 'gd' },
  { username: 'gd_city', password: '123456', role: 'city_admin', organization: '广州市行', orgId: 'gz' },
  { username: 'gd_employee', password: '123456', role: 'employee', name: '许一鸣', organization: '体育西网点', orgId: 'th-1' },
  { username: 'gz_employee', password: '123456', role: 'employee', name: '许一鸣', orgId: 'th-1', organization: '体育西网点' }
]

export const demoUsers = demoAccounts.map((account) => {
  const profile = roleProfiles[account.role]

  return {
    id: account.username,
    username: account.username,
    password: account.password,
    name: account.name || profile.name.replace('管理员', '') || '员工',
    role: account.role,
    roleName: profile.name,
    level: profile.level,
    organization: account.organization || profile.organization,
    orgId: account.orgId || profile.orgId,
    dataScope: profile.dataScope
  }
})

export function authenticateDemoUser(username, password) {
  const normalizedUsername = username.trim().toLowerCase()

  return demoUsers.find(
    (user) => user.username === normalizedUsername && user.password === password
  )
}

/*
 * 后端接入时，这里可以替换为：
 * POST /api/auth/login -> 返回 token
 * GET /api/auth/me -> 返回当前用户 role、level、organization、dataScope
 */
export const backendAuthContract = {
  login: 'POST /api/auth/login',
  currentUser: 'GET /api/auth/me'
}

export const menuItems = [
  {
    label: '首页仪表盘',
    path: '/dashboard',
    roles: ['head_admin', 'province_admin', 'city_admin', 'branch_admin', 'outlet_admin', 'employee']
  },
  {
    label: '组织架构',
    path: '/organization',
    roles: ['head_admin', 'province_admin', 'city_admin', 'branch_admin', 'outlet_admin']
  },
  {
    label: '人员管理',
    path: '/users',
    roles: ['head_admin', 'province_admin', 'city_admin', 'branch_admin', 'outlet_admin']
  },
  {
    label: '项目管理',
    path: '/projects',
    roles: ['head_admin', 'province_admin', 'city_admin', 'branch_admin']
  },
  {
    label: '分解工作台',
    path: '/decomposition',
    roles: ['head_admin', 'province_admin', 'city_admin', 'branch_admin', 'outlet_admin']
  },
  {
    label: '每日上报',
    path: '/report',
    roles: ['outlet_admin', 'employee']
  },
  {
    label: '积分排名',
    path: '/rankings',
    roles: ['head_admin', 'province_admin', 'city_admin', 'branch_admin', 'outlet_admin', 'employee']
  }
]

export function getCurrentUser() {
  const storedUser = localStorage.getItem('currentUser')

  if (!storedUser) return null

  try {
    return JSON.parse(storedUser)
  } catch {
    localStorage.removeItem('currentUser')
    return null
  }
}

export function setCurrentUser(user) {
  localStorage.setItem('isLoggedIn', 'true')
  localStorage.setItem('currentUser', JSON.stringify(user))
}

export function clearCurrentUser() {
  localStorage.removeItem('isLoggedIn')
  localStorage.removeItem('currentUser')
}

export function canAccessRoute(route, user) {
  const allowedRoles = route.meta?.roles

  if (!allowedRoles?.length) return true
  if (!user?.role || !allowedRoles.includes(user.role)) return false

  const projectId = route.params?.id
  if (!projectId) return true

  const tempProjects = getLocalTempProjects()
  const project = [...projects, ...tempProjects].find((item) => item.id === projectId)
  if (!project) return false

  if (route.meta?.projectAccess === 'visible') {
    const createdInScope = isOrgInScope(project.ownerOrgId, user.orgId)
    const assignedToOrg = decompositionPlans.some(
      (plan) => plan.projectId === projectId && plan.currentOrgId === user.orgId
    )

    return createdInScope || assignedToOrg
  }

  if (route.meta?.projectAccess === 'decompose') {
    if (project.ownerOrgId === user.orgId) return true

    return decompositionPlans.some(
      (plan) => plan.projectId === projectId && plan.currentOrgId === user.orgId
    )
  }

  return true
}

function getLocalTempProjects() {
  try {
    return JSON.parse(localStorage.getItem('tempProjects') || '[]')
  } catch {
    localStorage.removeItem('tempProjects')
    return []
  }
}

export function getDefaultPath(user) {
  if (!user) return '/login'
  return user.role === 'employee' ? '/report' : '/dashboard'
}

export function getVisibleMenus(user) {
  if (!user) return []
  return menuItems.filter((item) => item.roles.includes(user.role))
}
