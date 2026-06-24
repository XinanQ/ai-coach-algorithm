export const menuItems = [
  {
    label: '首页仪表盘',
    path: '/dashboard',
    roles: ['head_admin', 'province_admin', 'city_admin', 'branch_admin', 'outlet_admin', 'employee']
  },
  {
    label: '组织架构',
    path: '/organization',
    roles: ['head_admin', 'province_admin', 'city_admin', 'branch_admin', 'outlet_admin']
  },
  {
    label: '人员管理',
    path: '/users',
    roles: ['head_admin', 'province_admin', 'city_admin', 'branch_admin', 'outlet_admin']
  },
  {
    label: '项目管理',
    path: '/projects',
    roles: ['head_admin', 'province_admin', 'city_admin', 'branch_admin']
  },
  {
    label: '分解工作台',
    path: '/decomposition',
    roles: ['head_admin', 'province_admin', 'city_admin', 'branch_admin', 'outlet_admin']
  },
  {
    label: '每日上报',
    path: '/report',
    roles: ['outlet_admin', 'employee']
  },
  {
    label: '业绩审核',
    path: '/performance-review',
    roles: ['head_admin', 'province_admin', 'city_admin', 'branch_admin', 'outlet_admin']
  },
  {
    label: '项目排名',
    path: '/rankings',
    roles: ['head_admin', 'province_admin', 'city_admin', 'branch_admin', 'outlet_admin', 'employee']
  }
]

export function getDefaultPath(user) {
  if (!user) return '/login'
  return user.role === 'employee' ? '/report' : '/dashboard'
}

export function getVisibleMenus(user) {
  if (!user) return []
  return menuItems.filter((item) => item.roles.includes(user.role))
}
