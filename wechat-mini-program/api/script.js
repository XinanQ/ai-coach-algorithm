const request = require('../utils/request')
const config = require('../config')
const mock = require('../mock/script')

// 话术库列表（GET /api/mini/scripts）
function getList() {
  if (config.USE_MOCK) return Promise.resolve(mock.list())
  return request.get('/mini/scripts')
}

// 话术详情（GET /api/mini/scripts/{scriptId}）
function getDetail(id) {
  if (config.USE_MOCK) return Promise.resolve(mock.detail(id))
  return request.get('/mini/scripts/' + id)
}

// 收藏优化话术 { taskId, optimized }
// 注：规范未定义该写接口，目前为前端演示用（复盘页收藏）
function save(payload) {
  if (config.USE_MOCK) return Promise.resolve(mock.save())
  return request.post('/mini/scripts', payload)
}

module.exports = { getList, getDetail, save }
