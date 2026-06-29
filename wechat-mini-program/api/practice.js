const request = require('../utils/request')
const config = require('../config')
const mock = require('../mock/practice')

// 陪练任务列表 + 成长信息（GET /api/mini/practice/tasks?tab=assigned|self|done）
// 返回 { levelName, points, target, streakDays, weekGain, list: [...] }
function getTasks(tab) {
  if (config.USE_MOCK) return Promise.resolve(mock.tasks(tab))
  return request.get('/mini/practice/tasks', { tab })
}

// 任务详情 / 场景介绍（GET /api/mini/practice/tasks/{taskId}）
function getTaskDetail(taskId) {
  if (config.USE_MOCK) return Promise.resolve(mock.taskDetail(taskId))
  return request.get('/mini/practice/tasks/' + taskId)
}

// 开始对话（POST /api/mini/practice/dialog/start）
// 返回 { sessionId, taskId, round, totalRounds, difficultyLevel, difficultyRecommendation?, messages }
function startDialog(taskId) {
  if (config.USE_MOCK) return Promise.resolve(mock.dialogStart(taskId))
  return request.post('/mini/practice/dialog/start', { taskId })
}

// 提交一轮回复（POST /api/mini/practice/dialog/reply）
// 返回 { round, totalRounds, message, finished }
// round 仅用于 mock 推进；真实请求只发送 { sessionId, text }
function replyDialog(sessionId, text, round) {
  if (config.USE_MOCK) return Promise.resolve(mock.dialogReply(round))
  return request.post('/mini/practice/dialog/reply', { sessionId, text })
}

// 结束对话并取评分（POST /api/mini/practice/dialog/finish）
// 返回 { resultId, taskId, score, weakTags, suggestion }
function finishDialog(sessionId) {
  if (config.USE_MOCK) return Promise.resolve(mock.dialogFinish())
  return request.post('/mini/practice/dialog/finish', { sessionId })
}

// —— 以下为前端演示页接口，规范暂未定义，后端就绪前仅 mock 可用 ——
// 评分报告（结果详情页：维度/认证/奖励等富文本，规范 finish 仅返回 score/weakTags/suggestion）
function getResult(taskId, score) {
  if (config.USE_MOCK) return Promise.resolve(mock.result(score))
  return request.get('/mini/practice/result/' + taskId)
}

// 复盘（原话术 / AI 优化话术）
function getReview(taskId) {
  if (config.USE_MOCK) return Promise.resolve(mock.review(taskId))
  return request.get('/mini/practice/review/' + taskId)
}

// 陪练历史
function getHistory() {
  if (config.USE_MOCK) return Promise.resolve(mock.history())
  return request.get('/mini/practice/history')
}

module.exports = {
  getTasks, getTaskDetail,
  startDialog, replyDialog, finishDialog,
  getResult, getReview, getHistory
}
