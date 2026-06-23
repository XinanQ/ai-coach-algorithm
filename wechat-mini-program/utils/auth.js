// 登录态 + 角色管理
// 数据来源统一走 api 层（mock/真实由 config.USE_MOCK 决定）；
// token/role 等本地态保持同步读写，供页面 onShow 守卫直接调用

const apiAuth = require('../api/auth')

const TOKEN_KEY = 'token'
const USER_KEY = 'userInfo'
const ROLE_KEY = 'role' // 'manager' 管理员 | 'staff' 普通员工

// 是否已登录
function isLoggedIn() {
  return !!wx.getStorageSync(TOKEN_KEY)
}

// 获取当前登录用户信息（未登录返回 null）
function getUserInfo() {
  return wx.getStorageSync(USER_KEY) || null
}

// 获取 / 设置当前角色
function getRole() {
  return wx.getStorageSync(ROLE_KEY) || ''
}
function setRole(role) {
  wx.setStorageSync(ROLE_KEY, role)
}

// 登录：调 api 换取 token 与用户信息后存本地
function login(empId, password) {
  if (!empId || !password) {
    return Promise.reject(new Error('请输入工号和密码'))
  }
  return apiAuth.login(empId, password).then((res) => {
    // 后端登录返回扁平对象（employeeId/name/organizationName/isAdmin/level + token），
    // token 与用户字段同级；整体存为 userInfo 供各页读取
    wx.setStorageSync(TOKEN_KEY, res.token)
    wx.setStorageSync(USER_KEY, res)
    const app = getApp()
    if (app) app.globalData.userInfo = res
    return res
  })
}

// 退出登录：通知后端（尽力而为）并清除本地登录态与角色
function logout() {
  apiAuth.logout().catch(() => {})
  wx.removeStorageSync(TOKEN_KEY)
  wx.removeStorageSync(USER_KEY)
  wx.removeStorageSync(ROLE_KEY)

  const app = getApp()
  if (app) app.globalData.userInfo = null
}

// 角色对应的首页
function homeUrl(role) {
  return role === 'manager'
    ? '/pages/admin/workspace/workspace'
    : '/pages/index/index'
}

// 仅校验登录：未登录跳登录页。供子页面在 onShow/onLoad 调用
function requireLogin() {
  if (isLoggedIn()) return true
  wx.reLaunch({ url: '/pages/login/login' })
  return false
}

// 登录 + 角色守卫：供各 tab 页在 onShow 调用
//   未登录 -> 登录页；未选角色 -> 角色选择页；角色不符 -> 跳到对应角色首页
//   expectedRole 传 'staff' / 'manager'；不传则只要求已登录且已选角色
function guard(expectedRole) {
  if (!isLoggedIn()) {
    wx.reLaunch({ url: '/pages/login/login' })
    return false
  }
  const role = getRole()
  if (!role) {
    wx.reLaunch({ url: '/pages/role/role' })
    return false
  }
  if (expectedRole && role !== expectedRole) {
    wx.reLaunch({ url: homeUrl(role) })
    return false
  }
  return true
}

module.exports = {
  isLoggedIn,
  getUserInfo,
  getRole,
  setRole,
  login,
  logout,
  homeUrl,
  requireLogin,
  guard
}
