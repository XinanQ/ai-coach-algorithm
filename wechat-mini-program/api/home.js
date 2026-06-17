const request = require('../utils/request')
const config = require('../config')
const mock = require('../mock/home')

// 员工首页概览
function getSummary() {
  if (config.USE_MOCK) return Promise.resolve(mock.summary())
  return request.get('/home/summary')
}

module.exports = { getSummary }
