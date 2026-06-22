const auth = require('../../utils/auth')

// 员工 / 管理员两套底部导航
const STAFF_TABS = [
  { key: 'index', text: '首页', url: '/pages/index/index' },
  { key: 'task', text: '任务', url: '/pages/practice/list/list' },
  { key: 'ranking', text: '排行榜', url: '/pages/ranking/ranking' },
  { key: 'script', text: '话术库', url: '/pages/script/list/list' },
  { key: 'profile', text: '我的', url: '/pages/profile/profile' }
]
const MANAGER_TABS = [
  { key: 'workspace', text: '工作台', url: '/pages/admin/workspace/workspace' },
  { key: 'tasklib', text: '任务库', url: '/pages/admin/task-library/task-library' },
  { key: 'analysis', text: '数据分析', url: '/pages/admin/analysis/analysis' },
  { key: 'employees', text: '员工管理', url: '/pages/admin/employees/employees' },
  { key: 'profile', text: '我的', url: '/pages/profile/profile' }
]

Component({
  properties: {
    // 当前页对应的 tab key，用于高亮
    active: { type: String, value: '' }
  },
  data: {
    tabs: []
  },
  attached() {
    const role = auth.getRole()
    this.setData({ tabs: role === 'manager' ? MANAGER_TABS : STAFF_TABS })
  },
  methods: {
    onTab(e) {
      const { key, url } = e.currentTarget.dataset
      if (key === this.properties.active) return
      wx.reLaunch({ url })
    }
  }
})
