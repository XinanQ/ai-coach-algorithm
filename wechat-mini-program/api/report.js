const request = require('../utils/request')
const config = require('../config')
const mock = require('../mock/report')

// 上报指标列表
function getIndicators() {
  if (config.USE_MOCK) return Promise.resolve(mock.indicators())
  return request.get('/report/indicators')
}

// 提交上报 { indicatorId, value, images: [url] }
function submit(payload) {
  if (config.USE_MOCK) return Promise.resolve(mock.submit())
  return request.post('/report', payload)
}

// 本人上报历史
function getHistory() {
  if (config.USE_MOCK) return Promise.resolve(mock.history())
  return request.get('/report/history')
}

module.exports = { getIndicators, submit, getHistory }
