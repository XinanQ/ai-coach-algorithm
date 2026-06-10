import { request } from './request'

function normalizeLoginUser(loginData) {
  return {
    id: loginData.employeeId,
    employeeId: loginData.employeeId,
    employeeNo: loginData.employeeNo,
    username: loginData.employeeNo,
    name: loginData.name,
    level: loginData.level,
    isAdmin: loginData.isAdmin,
    organizationId: loginData.organizationId,
    orgId: loginData.organizationId,
    isInProject: loginData.isInProject,

    role: loginData.isAdmin ? 'admin' : 'employee'
  }
}

export async function login(username, password) {
  const response = await request('/api/auth/login', {
    method: 'POST',
    body: JSON.stringify({
      employeeNo: username,
      password
    })
  })

  if (!response?.data) {
    throw new Error(response?.message || '登录失败')
  }

  return normalizeLoginUser(response.data)
}

export async function getMe() {
  const storedUser = localStorage.getItem('currentUser')
  return storedUser ? JSON.parse(storedUser) : null
}

export async function logout() {
  return true
}