// 认证 mock
// 形状对齐后端《微信小程序接口联调说明》：登录/资料均为扁平对象，token 与用户字段同级
function login(empId) {
  return {
    employeeId: 48,
    employeeNo: empId || '56949775',
    name: '方可儿',
    position: '支行负责人',
    level: 'BRANCH',
    isAdmin: true,
    organizationId: 4,
    organizationName: '玄武支行',
    isInProject: true,
    token: 'mock-token-' + (empId || 'demo')
  }
}

function profile() {
  return {
    employeeId: 48,
    employeeNo: '56949775',
    name: '方可儿',
    email: 'fangkeer@example.com',
    position: '支行负责人',
    department: '营业部',
    level: 'BRANCH',
    isAdmin: true,
    isInProject: true,
    organizationId: 4,
    organizationName: '玄武支行',
    organizationCode: 'ORG0004',
    organizationLevel: 'BRANCH'
  }
}

module.exports = { login, profile }
