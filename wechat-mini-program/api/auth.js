const request = require('../utils/request')
const config = require('../config')
const mock = require('../mock/auth')

// 工号密码登录。
// request.js 会解包后端响应中的 data，因此这里返回的是登录用户信息扁平对象，包含 token、employeeNo、name、isAdmin、level 等字段。
function login(empId, password) {
  if (config.USE_MOCK) return Promise.resolve(mock.login(empId, password))
  // 后端登录字段为 employeeNo；token 在 data.token（由 request 统一解包 data）
  return request.post('/auth/login', { employeeNo: empId, password }, { skipAuthRedirect: true })
}

// 微信登录：code 换 token（可选，当前第一阶段暂未启用）
function wxLogin(code) {
  if (config.USE_MOCK) return Promise.resolve(mock.login('wx'))
  return request.post('/auth/wx-login', { code })
}

// 当前登录用户摘要信息，用于“我的页”顶部卡片。
// 完整账号资料后续走 /mini/account。
function getProfile() {
  if (config.USE_MOCK) return Promise.resolve(mock.profile())
  return request.get('/mini/profile', {}, { silent: true })
}

// 退出登录：真实接口可选；如果后端暂未实现，utils/auth.js 仍会清除本地登录态。
function logout() {
  if (config.USE_MOCK) return Promise.resolve()
  return request.post('/auth/logout')
}

module.exports = { login, wxLogin, getProfile, logout }
