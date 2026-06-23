const request = require('../utils/request')
const config = require('../config')
const mock = require('../mock/admin')

// 管理员工作台（GET /api/mini/admin/workspace）
// 返回统计 + 员工排行：{ completionRate, completionDelta, avgScore, avgDelta,
//   pendingCount, highRiskCount, ranking: [{ rank, employeeId, name, position, completionRate, score }] }
// filters 可选：{ branchId, position, type, period }
function getWorkspace(filters) {
  if (config.USE_MOCK) return Promise.resolve(mock.workspace())
  return request.get('/mini/admin/workspace', filters)
}

// 任务模板库（GET /api/mini/admin/practice/templates）
function getTaskTemplates() {
  if (config.USE_MOCK) return Promise.resolve(mock.taskTemplates())
  return request.get('/mini/admin/practice/templates')
}

// 模板详情（GET /api/mini/admin/practice/templates/{templateId}）-> { templateId, name, scene, dimensions:[] }
function getTemplateDetail(templateId) {
  if (config.USE_MOCK) return Promise.resolve(mock.templateDetail(templateId))
  return request.get('/mini/admin/practice/templates/' + templateId)
}

// 下发陪练任务（POST /api/mini/admin/practice/tasks）
// body: { templateId, name, level, targetPosition, deadline, dimensions:[] } -> { taskId }
function assignTask(payload) {
  if (config.USE_MOCK) return Promise.resolve(mock.assign())
  return request.post('/mini/admin/practice/tasks', payload)
}

// 数据分析（GET /api/mini/admin/analysis?period=week|month）
function getAnalysis(period) {
  if (config.USE_MOCK) return Promise.resolve(mock.analysis())
  return request.get('/mini/admin/analysis', { period })
}

// 员工列表（GET /api/mini/admin/employees）-> [{ employeeId, name, position, completionRate, score, progress }]
function getEmployees() {
  if (config.USE_MOCK) return Promise.resolve(mock.employees())
  return request.get('/mini/admin/employees')
}

// 员工详情：规范未定义，前端演示用
function getEmployeeDetail(id) {
  if (config.USE_MOCK) return Promise.resolve(mock.employeeDetail(id))
  return request.get('/mini/admin/employees/' + id)
}

module.exports = {
  getWorkspace, getTaskTemplates, getTemplateDetail, assignTask,
  getAnalysis, getEmployees, getEmployeeDetail
}
