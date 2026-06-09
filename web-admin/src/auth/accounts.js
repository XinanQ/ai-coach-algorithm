import { roleProfiles } from './roleProfiles'

export const loginAccounts = [
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

export const accountUsers = loginAccounts.map((account) => {
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

export function authenticateUser(username, password) {
  const normalizedUsername = username.trim().toLowerCase()

  return accountUsers.find(
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
