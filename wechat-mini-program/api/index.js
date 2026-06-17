// API 聚合入口：页面统一 require('.../api/index') 后用 api.<域>.<方法>()
module.exports = {
  auth: require('./auth'),
  home: require('./home'),
  report: require('./report'),
  ranking: require('./ranking'),
  news: require('./news'),
  practice: require('./practice'),
  script: require('./script'),
  admin: require('./admin')
}
