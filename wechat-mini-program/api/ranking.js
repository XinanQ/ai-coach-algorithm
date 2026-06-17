const request = require('../utils/request')
const config = require('../config')
const mock = require('../mock/ranking')

// 排行榜，period: day | week | month
function getRanking(period) {
  if (config.USE_MOCK) return Promise.resolve(mock.ranking(period))
  return request.get('/ranking', { period })
}

module.exports = { getRanking }
