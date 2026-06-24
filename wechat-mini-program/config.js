// 全局配置
module.exports = {
  // 后端基础地址
  // TODO: 替换为真实后端域名，并在小程序后台「开发设置 - 服务器域名」配置 request 合法域名
  BASE_URL: 'http://localhost:8081',

  // 接口统一前缀，最终请求地址 = BASE_URL + API_PREFIX + path
  API_PREFIX: '/api',

  // 数据来源开关：true = 使用本地 mock；后端就绪后改为 false 即走真实接口
  USE_MOCK: false

}
