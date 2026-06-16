import { request } from './request'
import { roleProfiles } from '../auth/roleProfiles'

const ROLE_BY_BACKEND_LEVEL = {
  HEAD: 'head_admin',
  HEADQUARTERS: 'head_admin',
  PROVINCE: 'province_admin',
  CITY: 'city_admin',
  BRANCH: 'branch_admin',
  OUTLET: 'outlet_admin',
  EMPLOYEE: 'employee'
}

function resolveFrontendRole(loginData) {
  const level = String(loginData.level || '').trim().toUpperCase()

  if (!loginData.isAdmin) {
    return 'employee'
  }

  if (!ROLE_BY_BACKEND_LEVEL[level]) {
    console.warn(`[auth] Unknown backend level "${loginData.level}", fallback to outlet_admin`)
  }

  return ROLE_BY_BACKEND_LEVEL[level] || 'outlet_admin'
}

function normalizeLoginUser(loginData) {
  const role = resolveFrontendRole(loginData)
  const profile = roleProfiles[role] || roleProfiles.employee

  return {
    id: loginData.employeeId,
    employeeId: loginData.employeeId,
    employeeNo: loginData.employeeNo,
    username: loginData.employeeNo,
    name: loginData.name,

    backendLevel: loginData.level,
    isAdmin: loginData.isAdmin,
    organizationId: loginData.organizationId,
    backendOrganizationId: loginData.organizationId,
    isInProject: loginData.isInProject,

    role,
    level: profile.level,
    roleName: profile.name,
    organization: profile.organization,
    orgName: profile.organization,
    orgId: profile.orgId,
    dataScope: profile.dataScope
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

  if (response.data.token) {
    localStorage.setItem('authToken', response.data.token)
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