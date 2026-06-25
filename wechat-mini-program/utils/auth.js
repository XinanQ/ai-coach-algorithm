// 登录态 + 角色管理
// 数据请求统一走 api 层；mock/真实接口切换由 api 层根据 config.USE_MOCK 决定。
// 本文件只负责 token、userInfo、role 等本地登录态的同步读写，供页面守卫和跳转逻辑使用。
const apiAuth = require('../api/auth')

const TOKEN_KEY = 'token'
const USER_KEY = 'userInfo'
const ROLE_KEY = 'role' // 'manager' 管理员 | 'staff' 普通员工

// 是否存在本地 token；用于判断前端登录态，不代表 token 一定仍在后端有效
function isLoggedIn() {
  return !!wx.getStorageSync(TOKEN_KEY)
}

// 获取当前登录用户信息（未登录返回 null）
function getUserInfo() {
  return wx.getStorageSync(USER_KEY) || null
}

// 获取 / 设置当前前端角色。
// mock 模式下可由角色选择页手动设置；真实模式下由登录返回的 isAdmin 自动设置。
function getRole() {
  return wx.getStorageSync(ROLE_KEY) || ''
}
function setRole(role) {
  const user = getUserInfo() || {}

  if (role === 'manager' && !user.isAdmin) {
    return false
  }

  wx.setStorageSync(ROLE_KEY, role)
  return true
}

// 登录：调用 api 层完成工号密码登录。
// 成功后保存 token、userInfo，并根据后端返回的 isAdmin 写入前端角色。
// role = manager 表示管理员；role = staff 表示普通员工。
function login(empId, password) {
  if (!empId || !password) {
    return Promise.reject(new Error('请输入工号和密码'))
  }

  return apiAuth.login(empId, password).then((res) => {
    wx.setStorageSync(TOKEN_KEY, res.token)
    wx.setStorageSync(USER_KEY, res)

    const role = res.isAdmin ? 'manager' : 'staff'
    wx.setStorageSync(ROLE_KEY, role)

    const app = getApp()
    if (app) app.globalData.userInfo = res

    return Object.assign({}, res, { role })
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

// 根据前端角色返回登录后的首页地址。
// manager 进入管理员工作台；staff 进入员工首页。
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

// 登录 + 角色守卫：供各 tab 页在 onShow 调用。
// 未登录 -> 登录页；未选角色 -> 角色选择页；角色不符 -> 跳到对应角色首页。
// expectedRole 传 'staff' / 'manager'；不传则只要求已登录且已选角色。
// 真实接口模式下 role 应由登录返回的 isAdmin 自动写入；角色选择页主要用于 mock/demo。
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
