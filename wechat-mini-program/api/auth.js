const request = require('../utils/request')
const config = require('../config')
const mock = require('../mock/auth')

// 工号密码登录。
// request.js 会解包后端响应中的 data，因此这里返回的是登录用户信息扁平对象，包含 token、employeeNo、name、isAdmin、level 等字段。
function login(empId, password) {
  if (config.USE_MOCK) return Promise.resolve(mock.login(empId, password))
  return request.post('/auth/login', { employeeNo: empId, password }, { skipAuthRedirect: true })
}

// 微信登录：code 换 token（可选，当前第一阶段暂未启用）
function wxLogin(code) {
  if (config.USE_MOCK) return Promise.resolve(mock.login('wx'))
  return request.post('/auth/wx-login', { code })
}

// 我的页顶部卡片摘要信息
function getProfile() {
  if (config.USE_MOCK) return Promise.resolve(mock.profile())
  return request.get('/mini/profile', {}, { silent: true })
}

// 账号详情页完整信息
function getAccount() {
  if (config.USE_MOCK && mock.account) return Promise.resolve(mock.account())
  return request.get('/mini/account', {}, { silent: true })
}

// 退出登录
function logout() {
  if (config.USE_MOCK) return Promise.resolve()
  return request.post('/auth/logout')
}

module.exports = {
  login,
  wxLogin,
  getProfile,
  getAccount,
  logout
}