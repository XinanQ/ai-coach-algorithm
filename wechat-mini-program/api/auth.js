const request = require('../utils/request')
const config = require('../config')
const mock = require('../mock/auth')

// 工号密码登录 -> { token, user }
function login(empId, password) {
  if (config.USE_MOCK) return Promise.resolve(mock.login(empId, password))
  // 后端登录字段为 employeeNo；token 在 data.token（由 request 统一解包 data）
  return request.post('/auth/login', { employeeNo: empId, password })
}

// 微信登录：code 换 token（可选）
function wxLogin(code) {
  if (config.USE_MOCK) return Promise.resolve(mock.login('wx'))
  return request.post('/auth/wx-login', { code })
}

// 当前登录用户资料（含真实角色/权限）
function getProfile() {
  if (config.USE_MOCK) return Promise.resolve(mock.profile())
  return request.get('/mini/profile')
}

function logout() {
  if (config.USE_MOCK) return Promise.resolve()
  return request.post('/auth/logout')
}

module.exports = { login, wxLogin, getProfile, logout }
