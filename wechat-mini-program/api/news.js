const request = require('../utils/request')
const config = require('../config')
const mock = require('../mock/news')

// 喜报列表
function getList() {
  if (config.USE_MOCK) return Promise.resolve(mock.getList())
  return request.get('/news')
}

// 喜报详情
function getDetail(id) {
  if (config.USE_MOCK) return Promise.resolve(mock.getDetail(id))
  return request.get('/news/' + id)
}

module.exports = { getList, getDetail }
