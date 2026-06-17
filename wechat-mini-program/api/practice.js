const request = require('../utils/request')
const config = require('../config')
const mock = require('../mock/practice')

// 成长信息
function getGrowth() {
  if (config.USE_MOCK) return Promise.resolve(mock.growth())
  return request.get('/practice/growth')
}

// 任务三分类 { assigned, library, done }
function getTasks() {
  if (config.USE_MOCK) return Promise.resolve(mock.tasks())
  return request.get('/practice/tasks')
}

// 任务详情（场景/AI角色/要求/进度）
function getTaskDetail(taskId) {
  if (config.USE_MOCK) return Promise.resolve(mock.taskDetail(taskId))
  return request.get('/practice/tasks/' + taskId)
}

// 开始对话
function startDialog(taskId) {
  if (config.USE_MOCK) return Promise.resolve(mock.dialogStart(taskId))
  return request.post('/practice/dialog/start', { taskId })
}

// 提交一轮回复，获取 AI 下一轮
function replyDialog(taskId, text, round) {
  if (config.USE_MOCK) return Promise.resolve(mock.dialogReply(round))
  return request.post('/practice/dialog/reply', { taskId, text })
}

// 结束对话（触发评分）
function finishDialog(taskId) {
  if (config.USE_MOCK) return Promise.resolve({})
  return request.post('/practice/dialog/finish', { taskId })
}

// 评分报告
function getResult(taskId, score) {
  if (config.USE_MOCK) return Promise.resolve(mock.result(score))
  return request.get('/practice/result/' + taskId)
}

// 复盘（原话术 / AI 优化话术）
function getReview(taskId) {
  if (config.USE_MOCK) return Promise.resolve(mock.review(taskId))
  return request.get('/practice/review/' + taskId)
}

// 陪练历史
function getHistory() {
  if (config.USE_MOCK) return Promise.resolve(mock.history())
  return request.get('/practice/history')
}

module.exports = {
  getGrowth, getTasks, getTaskDetail,
  startDialog, replyDialog, finishDialog,
  getResult, getReview, getHistory
}
