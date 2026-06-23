const request = require('../utils/request')
const config = require('../config')
const mock = require('../mock/home')

// 员工/管理员首页概览（GET /api/mini/home）
function getSummary() {
  if (config.USE_MOCK) return Promise.resolve(mock.home())
  return request.get('/mini/home')
}

module.exports = { getSummary }
