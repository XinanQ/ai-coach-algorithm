export const roleProfiles = {
  head_admin: {
    name: '总行管理员',
    level: '总行',
    dataScope: '全国所有机构与员工'
  },
  province_admin: {
    name: '省行管理员',
    level: '省行',
    dataScope: '本省下辖市行、支行、网点与员工'
  },
  city_admin: {
    name: '市行管理员',
    level: '市行',
    dataScope: '本市下辖支行、网点与员工'
  },
  branch_admin: {
    name: '支行管理员',
    level: '支行',
    dataScope: '本支行下辖网点与员工'
  },
  outlet_admin: {
    name: '网点管理员',
    level: '网点',
    dataScope: '本网点员工'
  },
  employee: {
    name: '普通员工',
    level: '员工',
    dataScope: '本人任务、上报与排名'
  }
}