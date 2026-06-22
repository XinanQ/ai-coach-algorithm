const request = require('../utils/request')
const config = require('../config')
const mock = require('../mock/script')

// 话术库列表
function getList() {
  if (config.USE_MOCK) return Promise.resolve(mock.list())
  return request.get('/scripts')
}

// 话术详情
function getDetail(id) {
  if (config.USE_MOCK) return Promise.resolve(mock.detail(id))
  return request.get('/scripts/' + id)
}

// 收藏优化话术 { taskId, optimized }
function save(payload) {
  if (config.USE_MOCK) return Promise.resolve(mock.save())
  return request.post('/scripts', payload)
}

module.exports = { getList, getDetail, save }
