// 认证 mock
function login(empId) {
  // role 留空 → 由前端角色选择页决定；接后端后由 profile 返回真实角色
  return {
    token: 'mock-token-' + empId,
    user: { empId, name: '张三', branch: 'XX网点', role: '' }
  }
}

function profile() {
  return { empId: '0001', name: '张三', branch: 'XX网点', role: '' }
}

module.exports = { login, profile }
