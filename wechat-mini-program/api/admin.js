const request = require('../utils/request')
const config = require('../config')
const mock = require('../mock/admin')

// 驾驶舱统计（filters: { branch, position, type, period }）
function getWorkspaceStats(filters) {
  if (config.USE_MOCK) return Promise.resolve(mock.workspaceStats())
  return request.get('/admin/workspace/stats', filters)
}

// 员工排行
function getWorkspaceRanking(filters) {
  if (config.USE_MOCK) return Promise.resolve(mock.workspaceRanking())
  return request.get('/admin/workspace/ranking', filters)
}

// 下发任务 { name, level, target, deadline, dimensions: [label] }
function assignTask(payload) {
  if (config.USE_MOCK) return Promise.resolve(mock.assign())
  return request.post('/admin/tasks/assign', payload)
}

// 任务模板库
function getTaskTemplates() {
  if (config.USE_MOCK) return Promise.resolve(mock.taskTemplates())
  return request.get('/admin/task-templates')
}

// 数据分析 { team, completionTop3, abilityTop3 }
function getAnalysis() {
  if (config.USE_MOCK) return Promise.resolve(mock.analysis())
  return request.get('/admin/analysis')
}

// 员工列表
function getEmployees() {
  if (config.USE_MOCK) return Promise.resolve(mock.employees())
  return request.get('/admin/employees')
}

// 员工详情
function getEmployeeDetail(id) {
  if (config.USE_MOCK) return Promise.resolve(mock.employeeDetail(id))
  return request.get('/admin/employees/' + id)
}

module.exports = {
  getWorkspaceStats, getWorkspaceRanking, assignTask,
  getTaskTemplates, getAnalysis, getEmployees, getEmployeeDetail
}
