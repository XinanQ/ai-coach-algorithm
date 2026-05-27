export const organizations = [
  {
    id: 'hq',
    name: '总行',
    level: '总行',
    manager: '总行管理员',
    children: [
      {
        id: 'js',
        name: '江苏省行',
        level: '省行',
        manager: '王敏',
        children: [
          {
            id: 'nj',
            name: '南京市行',
            level: '市行',
            manager: '李伟',
            children: [
              {
                id: 'gl',
                name: '鼓楼支行',
                level: '支行',
                manager: '张三',
                children: [
                  {
                    id: 'a-branch',
                    name: '鼓楼营业室',
                    level: '网点',
                    manager: '赵琳',
                    staffCount: 8
                  },
                  {
                    id: 'b-branch',
                    name: '湖南路网点',
                    level: '网点',
                    manager: '陈晨',
                    staffCount: 6
                  },
                  {
                    id: 'c-branch',
                    name: '中央路网点',
                    level: '网点',
                    manager: '周宁',
                    staffCount: 5
                  }
                ]
              },
              {
                id: 'xw',
                name: '玄武支行',
                level: '支行',
                manager: '刘洋',
                children: [
                  {
                    id: 'xw-1',
                    name: '珠江路网点',
                    level: '网点',
                    manager: '孙悦',
                    staffCount: 7
                  },
                  {
                    id: 'xw-2',
                    name: '新街口网点',
                    level: '网点',
                    manager: '吴迪',
                    staffCount: 9
                  }
                ]
              },
              {
                id: 'qh',
                name: '秦淮支行',
                level: '支行',
                manager: '钱宁',
                children: [
                  {
                    id: 'qh-1',
                    name: '夫子庙网点',
                    level: '网点',
                    manager: '郑雪',
                    staffCount: 6
                  },
                  {
                    id: 'qh-2',
                    name: '中华门网点',
                    level: '网点',
                    manager: '何磊',
                    staffCount: 5
                  }
                ]
              }
            ]
          },
          {
            id: 'sz',
            name: '苏州市行',
            level: '市行',
            manager: '顾安',
            children: [
              {
                id: 'gusu',
                name: '姑苏支行',
                level: '支行',
                manager: '沈洁',
                children: [
                  {
                    id: 'gusu-1',
                    name: '平江路网点',
                    level: '网点',
                    manager: '唐琳',
                    staffCount: 8
                  },
                  {
                    id: 'gusu-2',
                    name: '观前街网点',
                    level: '网点',
                    manager: '陆明',
                    staffCount: 10
                  }
                ]
              },
              {
                id: 'wz',
                name: '吴中支行',
                level: '支行',
                manager: '韩青',
                children: [
                  {
                    id: 'wz-1',
                    name: '木渎网点',
                    level: '网点',
                    manager: '邵华',
                    staffCount: 6
                  }
                ]
              }
            ]
          }
        ]
      },
      {
        id: 'zj',
        name: '浙江省行',
        level: '省行',
        manager: '林峰',
        children: [
          {
            id: 'hz',
            name: '杭州市行',
            level: '市行',
            manager: '宋佳',
            children: [
              {
                id: 'xh',
                name: '西湖支行',
                level: '支行',
                manager: '冯帆',
                children: [
                  {
                    id: 'xh-1',
                    name: '文三路网点',
                    level: '网点',
                    manager: '曹宇',
                    staffCount: 8
                  },
                  {
                    id: 'xh-2',
                    name: '黄龙网点',
                    level: '网点',
                    manager: '马骁',
                    staffCount: 7
                  }
                ]
              }
            ]
          },
          {
            id: 'nb',
            name: '宁波市行',
            level: '市行',
            manager: '罗晴',
            children: [
              {
                id: 'hs',
                name: '海曙支行',
                level: '支行',
                manager: '高远',
                children: [
                  {
                    id: 'hs-1',
                    name: '天一广场网点',
                    level: '网点',
                    manager: '蒋雯',
                    staffCount: 6
                  }
                ]
              }
            ]
          }
        ]
      },
      {
        id: 'gd',
        name: '广东省行',
        level: '省行',
        manager: '许达',
        children: [
          {
            id: 'gz',
            name: '广州市行',
            level: '市行',
            manager: '叶楠',
            children: [
              {
                id: 'th',
                name: '天河支行',
                level: '支行',
                manager: '魏然',
                children: [
                  {
                    id: 'th-1',
                    name: '体育西网点',
                    level: '网点',
                    manager: '杜鹏',
                    staffCount: 11
                  },
                  {
                    id: 'th-2',
                    name: '珠江新城网点',
                    level: '网点',
                    manager: '梁洁',
                    staffCount: 9
                  }
                ]
              }
            ]
          }
        ]
      }
    ]
  }
]

export const users = [
  {
    id: 1,
    name: '张三',
    email: 'zhangsan@example.com',
    position: '客户经理',
    level: '员工',
    organization: '鼓楼营业室',
    orgId: 'a-branch',
    isNew: false,
    workType: '外勤',
    isAdmin: false,
    joinedProject: true
  },
  {
    id: 2,
    name: '李四',
    email: 'lisi@example.com',
    position: '柜员',
    level: '员工',
    organization: '鼓楼营业室',
    orgId: 'a-branch',
    isNew: true,
    workType: '内勤',
    isAdmin: false,
    joinedProject: true
  },
  {
    id: 3,
    name: '王五',
    email: 'wangwu@example.com',
    position: '客户经理',
    level: '员工',
    organization: '湖南路网点',
    orgId: 'b-branch',
    isNew: false,
    workType: '外勤',
    isAdmin: false,
    joinedProject: true
  },
  {
    id: 4,
    name: '赵琳',
    email: 'zhaolin@example.com',
    position: '网点主任',
    level: '网点',
    organization: '鼓楼营业室',
    orgId: 'a-branch',
    isNew: false,
    workType: '内勤',
    isAdmin: true,
    joinedProject: true
  },
  {
    id: 5,
    name: '陈晨',
    email: 'chenchen@example.com',
    position: '网点主任',
    level: '网点',
    organization: '湖南路网点',
    orgId: 'b-branch',
    isNew: false,
    workType: '内勤',
    isAdmin: true,
    joinedProject: true
  },
  {
    id: 6,
    name: '周宁',
    email: 'zhouning@example.com',
    position: '客户经理',
    level: '员工',
    organization: '中央路网点',
    orgId: 'c-branch',
    isNew: true,
    workType: '外勤',
    isAdmin: false,
    joinedProject: true
  },
  {
    id: 7,
    name: '孙悦',
    email: 'sunyue@example.com',
    position: '柜员',
    level: '员工',
    organization: '珠江路网点',
    orgId: 'xw-1',
    isNew: false,
    workType: '内勤',
    isAdmin: false,
    joinedProject: false
  },
  {
    id: 8,
    name: '吴迪',
    email: 'wudi@example.com',
    position: '客户经理',
    level: '员工',
    organization: '新街口网点',
    orgId: 'xw-2',
    isNew: false,
    workType: '外勤',
    isAdmin: false,
    joinedProject: true
  },
  {
    id: 9,
    name: '郑雪',
    email: 'zhengxue@example.com',
    position: '客户经理',
    level: '员工',
    organization: '夫子庙网点',
    orgId: 'qh-1',
    isNew: true,
    workType: '外勤',
    isAdmin: false,
    joinedProject: true
  },
  {
    id: 10,
    name: '唐琳',
    email: 'tanglin@example.com',
    position: '网点主任',
    level: '网点',
    organization: '平江路网点',
    orgId: 'gusu-1',
    isNew: false,
    workType: '内勤',
    isAdmin: true,
    joinedProject: true
  }
]

export const projects = [
  {
    id: 'spring-2026',
    name: '2026 春季旺季营销项目',
    description: '围绕存款、企业微信、保险销售开展阶段性营销竞赛。',
    startDate: '2026-03-01',
    endDate: '2026-03-31',
    reportDeadline: '18:00',
    attachmentRequired: true,
    status: '进行中',
    owner: '总行管理员',
    ownerLevel: '总行',
    ownerOrgId: 'hq',
    distributionStatus: '已下发',
    createdAt: '2026-02-20'
  },
  {
    id: 'inclusive-2026',
    name: '普惠金融客户拓展项目',
    description: '提升小微客户触达、授信转化与贷记卡办理。',
    startDate: '2026-04-01',
    endDate: '2026-04-30',
    reportDeadline: '17:30',
    attachmentRequired: false,
    status: '未开始',
    owner: '江苏省行',
    ownerLevel: '省行',
    ownerOrgId: 'js',
    distributionStatus: '待分解',
    createdAt: '2026-03-18'
  },
  {
    id: 'wealth-2026',
    name: '财富客户资产提升项目',
    description: '面向中高端客户推动理财、基金、保险与贵金属综合配置。',
    startDate: '2026-05-01',
    endDate: '2026-05-31',
    reportDeadline: '18:30',
    attachmentRequired: true,
    status: '进行中',
    owner: '江苏省行',
    ownerLevel: '省行',
    ownerOrgId: 'js',
    distributionStatus: '部分下发',
    createdAt: '2026-04-22'
  }
]

export const indicators = [
  {
    id: 1,
    projectId: 'spring-2026',
    name: '定期存款',
    indicatorType: '结果指标',
    valueType: '金额',
    unit: '万元',
    weight: 35,
    pointRule: 0.5,
    bigOrderEnabled: true,
    bigOrderThreshold: 100,
    talentCount: 5
  },
  {
    id: 2,
    projectId: 'spring-2026',
    name: '企业微信添加量',
    indicatorType: '过程指标',
    valueType: '数量',
    unit: '户',
    weight: 20,
    pointRule: 0.2,
    bigOrderEnabled: false,
    bigOrderThreshold: 0,
    talentCount: 3
  },
  {
    id: 3,
    projectId: 'spring-2026',
    name: '中国人寿 3 年期缴保险',
    indicatorType: '结果指标',
    valueType: '金额',
    unit: '万元',
    weight: 25,
    pointRule: 15,
    bigOrderEnabled: true,
    bigOrderThreshold: 20,
    talentCount: 3
  },
  {
    id: 4,
    projectId: 'inclusive-2026',
    name: '小微客户电访',
    indicatorType: '过程指标',
    valueType: '数量',
    unit: '次',
    weight: 20,
    pointRule: 0.1,
    bigOrderEnabled: false,
    bigOrderThreshold: 0,
    talentCount: 5
  },
  {
    id: 5,
    projectId: 'inclusive-2026',
    name: '贷记卡办理',
    indicatorType: '结果指标',
    valueType: '数量',
    unit: '张',
    weight: 30,
    pointRule: 6,
    bigOrderEnabled: true,
    bigOrderThreshold: 10,
    talentCount: 3
  },
  {
    id: 6,
    projectId: 'wealth-2026',
    name: '基金定投签约',
    indicatorType: '结果指标',
    valueType: '金额',
    unit: '万元',
    weight: 30,
    pointRule: 4,
    bigOrderEnabled: true,
    bigOrderThreshold: 50,
    talentCount: 4
  },
  {
    id: 7,
    projectId: 'wealth-2026',
    name: '贵金属销售',
    indicatorType: '结果指标',
    valueType: '金额',
    unit: '万元',
    weight: 25,
    pointRule: 8,
    bigOrderEnabled: true,
    bigOrderThreshold: 15,
    talentCount: 3
  }
]

export const decompositionRows = [
  {
    id: 1,
    target: '鼓楼营业室',
    level: '网点',
    indicator: '定期存款',
    totalTask: 1000,
    allocated: 300,
    currentAllocation: 320,
    unit: '万元'
  },
  {
    id: 2,
    target: '湖南路网点',
    level: '网点',
    indicator: '定期存款',
    totalTask: 1000,
    allocated: 400,
    currentAllocation: 360,
    unit: '万元'
  },
  {
    id: 3,
    target: '中央路网点',
    level: '网点',
    indicator: '定期存款',
    totalTask: 1000,
    allocated: 300,
    currentAllocation: 320,
    unit: '万元'
  }
]

export const decompositionPlans = [
  {
    id: 'spring-2026-head',
    projectId: 'spring-2026',
    ownerRole: 'head_admin',
    originType: 'created',
    receivedFrom: '',
    currentOrganization: '总行',
    currentOrgId: 'hq',
    currentLevel: '总行',
    nextLevel: '省行',
    status: '已分解',
    targets: [
      {
        id: 'js',
        target: '江苏省行',
        level: '省行',
        indicators: [
          { indicatorId: 1, indicator: '定期存款', totalTask: 18000, allocated: 12000, currentAllocation: 6000, unit: '万元' },
          { indicatorId: 2, indicator: '企业微信添加量', totalTask: 6000, allocated: 3800, currentAllocation: 1800, unit: '户' },
          { indicatorId: 3, indicator: '中国人寿 3 年期缴保险', totalTask: 2400, allocated: 1500, currentAllocation: 700, unit: '万元' }
        ]
      },
      {
        id: 'zj',
        target: '浙江省行',
        level: '省行',
        indicators: [
          { indicatorId: 1, indicator: '定期存款', totalTask: 18000, allocated: 9000, currentAllocation: 5200, unit: '万元' },
          { indicatorId: 2, indicator: '企业微信添加量', totalTask: 6000, allocated: 3000, currentAllocation: 1600, unit: '户' },
          { indicatorId: 3, indicator: '中国人寿 3 年期缴保险', totalTask: 2400, allocated: 1000, currentAllocation: 600, unit: '万元' }
        ]
      },
      {
        id: 'gd',
        target: '广东省行',
        level: '省行',
        indicators: [
          { indicatorId: 1, indicator: '定期存款', totalTask: 18000, allocated: 7000, currentAllocation: 4300, unit: '万元' },
          { indicatorId: 2, indicator: '企业微信添加量', totalTask: 6000, allocated: 2600, currentAllocation: 1200, unit: '户' },
          { indicatorId: 3, indicator: '中国人寿 3 年期缴保险', totalTask: 2400, allocated: 900, currentAllocation: 500, unit: '万元' }
        ]
      }
    ]
  },
  {
    id: 'spring-2026-province',
    projectId: 'spring-2026',
    ownerRole: 'province_admin',
    originType: 'received',
    receivedFrom: '总行',
    currentOrganization: '江苏省行',
    currentOrgId: 'js',
    currentLevel: '省行',
    nextLevel: '市行',
    status: '待调整',
    targets: [
      {
        id: 'nj',
        target: '南京市行',
        level: '市行',
        indicators: [
          { indicatorId: 1, indicator: '定期存款', totalTask: 6000, allocated: 4200, currentAllocation: 1600, unit: '万元' },
          { indicatorId: 2, indicator: '企业微信添加量', totalTask: 1800, allocated: 1200, currentAllocation: 450, unit: '户' },
          { indicatorId: 3, indicator: '中国人寿 3 年期缴保险', totalTask: 700, allocated: 420, currentAllocation: 180, unit: '万元' }
        ]
      },
      {
        id: 'sz',
        target: '苏州市行',
        level: '市行',
        indicators: [
          { indicatorId: 1, indicator: '定期存款', totalTask: 6000, allocated: 3000, currentAllocation: 1400, unit: '万元' },
          { indicatorId: 2, indicator: '企业微信添加量', totalTask: 1800, allocated: 850, currentAllocation: 360, unit: '户' },
          { indicatorId: 3, indicator: '中国人寿 3 年期缴保险', totalTask: 700, allocated: 280, currentAllocation: 120, unit: '万元' }
        ]
      }
    ]
  },
  {
    id: 'spring-2026-city',
    projectId: 'spring-2026',
    ownerRole: 'city_admin',
    originType: 'received',
    receivedFrom: '江苏省行',
    currentOrganization: '南京市行',
    currentOrgId: 'nj',
    currentLevel: '市行',
    nextLevel: '支行',
    status: '待分解',
    targets: [
      {
        id: 'gl',
        target: '鼓楼支行',
        level: '支行',
        indicators: [
          { indicatorId: 1, indicator: '定期存款', totalTask: 1600, allocated: 850, currentAllocation: 520, unit: '万元' },
          { indicatorId: 2, indicator: '企业微信添加量', totalTask: 450, allocated: 180, currentAllocation: 140, unit: '户' },
          { indicatorId: 3, indicator: '中国人寿 3 年期缴保险', totalTask: 180, allocated: 80, currentAllocation: 55, unit: '万元' }
        ]
      },
      {
        id: 'xw',
        target: '玄武支行',
        level: '支行',
        indicators: [
          { indicatorId: 1, indicator: '定期存款', totalTask: 1600, allocated: 700, currentAllocation: 420, unit: '万元' },
          { indicatorId: 2, indicator: '企业微信添加量', totalTask: 450, allocated: 150, currentAllocation: 120, unit: '户' },
          { indicatorId: 3, indicator: '中国人寿 3 年期缴保险', totalTask: 180, allocated: 60, currentAllocation: 45, unit: '万元' }
        ]
      },
      {
        id: 'qh',
        target: '秦淮支行',
        level: '支行',
        indicators: [
          { indicatorId: 1, indicator: '定期存款', totalTask: 1600, allocated: 650, currentAllocation: 360, unit: '万元' },
          { indicatorId: 2, indicator: '企业微信添加量', totalTask: 450, allocated: 120, currentAllocation: 110, unit: '户' },
          { indicatorId: 3, indicator: '中国人寿 3 年期缴保险', totalTask: 180, allocated: 55, currentAllocation: 40, unit: '万元' }
        ]
      }
    ]
  },
  {
    id: 'inclusive-2026-province',
    projectId: 'inclusive-2026',
    ownerRole: 'province_admin',
    originType: 'created',
    receivedFrom: '',
    currentOrganization: '江苏省行',
    currentOrgId: 'js',
    currentLevel: '省行',
    nextLevel: '市行',
    status: '待分解',
    targets: [
      {
        id: 'nj',
        target: '南京市行',
        level: '市行',
        indicators: [
          { indicatorId: 4, indicator: '小微客户电访', totalTask: 1200, allocated: 300, currentAllocation: 420, unit: '次' },
          { indicatorId: 5, indicator: '贷记卡办理', totalTask: 420, allocated: 120, currentAllocation: 130, unit: '张' }
        ]
      },
      {
        id: 'sz',
        target: '苏州市行',
        level: '市行',
        indicators: [
          { indicatorId: 4, indicator: '小微客户电访', totalTask: 1200, allocated: 260, currentAllocation: 360, unit: '次' },
          { indicatorId: 5, indicator: '贷记卡办理', totalTask: 420, allocated: 85, currentAllocation: 95, unit: '张' }
        ]
      }
    ]
  },
  {
    id: 'inclusive-2026-city',
    projectId: 'inclusive-2026',
    ownerRole: 'city_admin',
    originType: 'received',
    receivedFrom: '江苏省行',
    currentOrganization: '南京市行',
    currentOrgId: 'nj',
    currentLevel: '市行',
    nextLevel: '支行',
    status: '待分解',
    targets: [
      {
        id: 'gl',
        target: '鼓楼支行',
        level: '支行',
        indicators: [
          { indicatorId: 4, indicator: '小微客户电访', totalTask: 420, allocated: 160, currentAllocation: 110, unit: '次' },
          { indicatorId: 5, indicator: '贷记卡办理', totalTask: 130, allocated: 45, currentAllocation: 35, unit: '张' }
        ]
      },
      {
        id: 'xw',
        target: '玄武支行',
        level: '支行',
        indicators: [
          { indicatorId: 4, indicator: '小微客户电访', totalTask: 420, allocated: 120, currentAllocation: 90, unit: '次' },
          { indicatorId: 5, indicator: '贷记卡办理', totalTask: 130, allocated: 30, currentAllocation: 30, unit: '张' }
        ]
      }
    ]
  },
  {
    id: 'wealth-2026-city',
    projectId: 'wealth-2026',
    ownerRole: 'city_admin',
    originType: 'received',
    receivedFrom: '江苏省行',
    currentOrganization: '南京市行',
    currentOrgId: 'nj',
    currentLevel: '市行',
    nextLevel: '支行',
    status: '部分下发',
    targets: [
      {
        id: 'gl',
        target: '鼓楼支行',
        level: '支行',
        indicators: [
          { indicatorId: 6, indicator: '基金定投签约', totalTask: 520, allocated: 180, currentAllocation: 150, unit: '万元' },
          { indicatorId: 7, indicator: '贵金属销售', totalTask: 170, allocated: 55, currentAllocation: 42, unit: '万元' }
        ]
      },
      {
        id: 'xw',
        target: '玄武支行',
        level: '支行',
        indicators: [
          { indicatorId: 6, indicator: '基金定投签约', totalTask: 520, allocated: 150, currentAllocation: 120, unit: '万元' },
          { indicatorId: 7, indicator: '贵金属销售', totalTask: 170, allocated: 40, currentAllocation: 32, unit: '万元' }
        ]
      }
    ]
  },
  {
    id: 'spring-2026-branch',
    projectId: 'spring-2026',
    ownerRole: 'branch_admin',
    originType: 'received',
    receivedFrom: '南京市行',
    currentOrganization: '鼓楼支行',
    currentOrgId: 'gl',
    currentLevel: '支行',
    nextLevel: '网点',
    status: '待提交',
    targets: [
      {
        id: 'a-branch',
        target: '鼓楼营业室',
        level: '网点',
        indicators: [
          { indicatorId: 1, indicator: '定期存款', totalTask: 520, allocated: 260, currentAllocation: 160, unit: '万元' },
          { indicatorId: 2, indicator: '企业微信添加量', totalTask: 140, allocated: 60, currentAllocation: 45, unit: '户' },
          { indicatorId: 3, indicator: '中国人寿 3 年期缴保险', totalTask: 55, allocated: 20, currentAllocation: 15, unit: '万元' }
        ]
      },
      {
        id: 'b-branch',
        target: '湖南路网点',
        level: '网点',
        indicators: [
          { indicatorId: 1, indicator: '定期存款', totalTask: 520, allocated: 220, currentAllocation: 150, unit: '万元' },
          { indicatorId: 2, indicator: '企业微信添加量', totalTask: 140, allocated: 45, currentAllocation: 40, unit: '户' },
          { indicatorId: 3, indicator: '中国人寿 3 年期缴保险', totalTask: 55, allocated: 18, currentAllocation: 15, unit: '万元' }
        ]
      },
      {
        id: 'c-branch',
        target: '中央路网点',
        level: '网点',
        indicators: [
          { indicatorId: 1, indicator: '定期存款', totalTask: 520, allocated: 180, currentAllocation: 120, unit: '万元' },
          { indicatorId: 2, indicator: '企业微信添加量', totalTask: 140, allocated: 35, currentAllocation: 30, unit: '户' },
          { indicatorId: 3, indicator: '中国人寿 3 年期缴保险', totalTask: 55, allocated: 15, currentAllocation: 10, unit: '万元' }
        ]
      }
    ]
  },
  {
    id: 'inclusive-2026-branch',
    projectId: 'inclusive-2026',
    ownerRole: 'branch_admin',
    originType: 'received',
    receivedFrom: '南京市行',
    currentOrganization: '鼓楼支行',
    currentOrgId: 'gl',
    currentLevel: '支行',
    nextLevel: '网点',
    status: '待分解',
    targets: [
      {
        id: 'a-branch',
        target: '鼓楼营业室',
        level: '网点',
        indicators: [
          { indicatorId: 4, indicator: '小微客户电访', totalTask: 260, allocated: 80, currentAllocation: 70, unit: '次' },
          { indicatorId: 5, indicator: '贷记卡办理', totalTask: 90, allocated: 25, currentAllocation: 22, unit: '张' }
        ]
      },
      {
        id: 'b-branch',
        target: '湖南路网点',
        level: '网点',
        indicators: [
          { indicatorId: 4, indicator: '小微客户电访', totalTask: 260, allocated: 70, currentAllocation: 65, unit: '次' },
          { indicatorId: 5, indicator: '贷记卡办理', totalTask: 90, allocated: 20, currentAllocation: 20, unit: '张' }
        ]
      },
      {
        id: 'c-branch',
        target: '中央路网点',
        level: '网点',
        indicators: [
          { indicatorId: 4, indicator: '小微客户电访', totalTask: 260, allocated: 55, currentAllocation: 45, unit: '次' },
          { indicatorId: 5, indicator: '贷记卡办理', totalTask: 90, allocated: 14, currentAllocation: 9, unit: '张' }
        ]
      }
    ]
  },
  {
    id: 'wealth-2026-branch',
    projectId: 'wealth-2026',
    ownerRole: 'branch_admin',
    originType: 'received',
    receivedFrom: '南京市行',
    currentOrganization: '鼓楼支行',
    currentOrgId: 'gl',
    currentLevel: '支行',
    nextLevel: '网点',
    status: '部分下发',
    targets: [
      {
        id: 'a-branch',
        target: '鼓楼营业室',
        level: '网点',
        indicators: [
          { indicatorId: 6, indicator: '基金定投签约', totalTask: 360, allocated: 120, currentAllocation: 90, unit: '万元' },
          { indicatorId: 7, indicator: '贵金属销售', totalTask: 120, allocated: 35, currentAllocation: 28, unit: '万元' }
        ]
      },
      {
        id: 'b-branch',
        target: '湖南路网点',
        level: '网点',
        indicators: [
          { indicatorId: 6, indicator: '基金定投签约', totalTask: 360, allocated: 95, currentAllocation: 80, unit: '万元' },
          { indicatorId: 7, indicator: '贵金属销售', totalTask: 120, allocated: 26, currentAllocation: 24, unit: '万元' }
        ]
      },
      {
        id: 'c-branch',
        target: '中央路网点',
        level: '网点',
        indicators: [
          { indicatorId: 6, indicator: '基金定投签约', totalTask: 360, allocated: 70, currentAllocation: 55, unit: '万元' },
          { indicatorId: 7, indicator: '贵金属销售', totalTask: 120, allocated: 18, currentAllocation: 14, unit: '万元' }
        ]
      }
    ]
  },
  {
    id: 'spring-2026-outlet',
    projectId: 'spring-2026',
    ownerRole: 'outlet_admin',
    originType: 'received',
    receivedFrom: '鼓楼支行',
    currentOrganization: '鼓楼营业室',
    currentOrgId: 'a-branch',
    currentLevel: '网点',
    nextLevel: '员工',
    status: '待分配到人',
    targets: [
      {
        id: 'staff-1',
        target: '张三',
        targetUserId: 'employee',
        level: '员工',
        indicators: [
          { indicatorId: 1, indicator: '定期存款', totalTask: 160, allocated: 50, currentAllocation: 55, unit: '万元' },
          { indicatorId: 2, indicator: '企业微信添加量', totalTask: 45, allocated: 12, currentAllocation: 15, unit: '户' },
          { indicatorId: 3, indicator: '中国人寿 3 年期缴保险', totalTask: 15, allocated: 5, currentAllocation: 4, unit: '万元' }
        ]
      },
      {
        id: 'staff-2',
        target: '李四',
        targetUserId: 'staff-lisi',
        level: '员工',
        indicators: [
          { indicatorId: 1, indicator: '定期存款', totalTask: 160, allocated: 40, currentAllocation: 45, unit: '万元' },
          { indicatorId: 2, indicator: '企业微信添加量', totalTask: 45, allocated: 10, currentAllocation: 12, unit: '户' },
          { indicatorId: 3, indicator: '中国人寿 3 年期缴保险', totalTask: 15, allocated: 3, currentAllocation: 4, unit: '万元' }
        ]
      }
    ]
  },
  {
    id: 'inclusive-2026-outlet',
    projectId: 'inclusive-2026',
    ownerRole: 'outlet_admin',
    originType: 'received',
    receivedFrom: '鼓楼支行',
    currentOrganization: '鼓楼营业室',
    currentOrgId: 'a-branch',
    currentLevel: '网点',
    nextLevel: '员工',
    status: '待分配到人',
    targets: [
      {
        id: 'staff-1',
        target: '张三',
        targetUserId: 'employee',
        level: '员工',
        indicators: [
          { indicatorId: 4, indicator: '小微客户电访', totalTask: 70, allocated: 20, currentAllocation: 25, unit: '次' },
          { indicatorId: 5, indicator: '贷记卡办理', totalTask: 22, allocated: 5, currentAllocation: 8, unit: '张' }
        ]
      },
      {
        id: 'staff-2',
        target: '李四',
        targetUserId: 'staff-lisi',
        level: '员工',
        indicators: [
          { indicatorId: 4, indicator: '小微客户电访', totalTask: 70, allocated: 15, currentAllocation: 20, unit: '次' },
          { indicatorId: 5, indicator: '贷记卡办理', totalTask: 22, allocated: 4, currentAllocation: 5, unit: '张' }
        ]
      }
    ]
  },
  {
    id: 'wealth-2026-gz-outlet',
    projectId: 'wealth-2026',
    ownerRole: 'outlet_admin',
    originType: 'received',
    receivedFrom: '天河支行',
    currentOrganization: '体育西网点',
    currentOrgId: 'th-1',
    currentLevel: '网点',
    nextLevel: '员工',
    status: '待分配到人',
    targets: [
      {
        id: 'gz-staff-1',
        target: '许一鸣',
        targetUserId: 'gz_employee',
        level: '员工',
        indicators: [
          { indicatorId: 6, indicator: '基金定投签约', totalTask: 180, allocated: 60, currentAllocation: 45, unit: '万元' },
          { indicatorId: 7, indicator: '贵金属销售', totalTask: 70, allocated: 18, currentAllocation: 16, unit: '万元' }
        ]
      }
    ]
  }
]

export const reports = [
  {
    id: 1,
    project: '2026 春季旺季营销项目',
    indicator: '定期存款',
    reporter: '张三',
    organization: '鼓楼营业室',
    orgId: 'a-branch',
    reporterId: 'employee',
    amount: 80,
    unit: '万元',
    points: 40,
    reportedAt: '2026-03-10 09:20',
    attachment: '已上传'
  },
  {
    id: 2,
    project: '2026 春季旺季营销项目',
    indicator: '企业微信添加量',
    reporter: '李四',
    organization: '鼓楼营业室',
    orgId: 'a-branch',
    reporterId: 'staff-lisi',
    amount: 45,
    unit: '户',
    points: 9,
    reportedAt: '2026-03-10 10:10',
    attachment: '不需要'
  },
  {
    id: 3,
    project: '2026 春季旺季营销项目',
    indicator: '中国人寿 3 年期缴保险',
    reporter: '王五',
    organization: '湖南路网点',
    orgId: 'b-branch',
    reporterId: 'staff-wangwu',
    amount: 12,
    unit: '万元',
    points: 180,
    reportedAt: '2026-03-10 11:30',
    attachment: '已上传'
  },
  {
    id: 4,
    project: '普惠金融客户拓展项目',
    indicator: '小微客户电访',
    reporter: '吴迪',
    organization: '新街口网点',
    orgId: 'xw-2',
    reporterId: 'staff-wudi',
    amount: 96,
    unit: '次',
    points: 9.6,
    reportedAt: '2026-04-08 15:20',
    attachment: '不需要'
  },
  {
    id: 5,
    project: '财富客户资产提升项目',
    indicator: '基金定投签约',
    reporter: '郑雪',
    organization: '夫子庙网点',
    orgId: 'qh-1',
    reporterId: 'staff-zhengxue',
    amount: 38,
    unit: '万元',
    points: 152,
    reportedAt: '2026-05-06 14:10',
    attachment: '已上传'
  },
  {
    id: 6,
    project: '财富客户资产提升项目',
    indicator: '贵金属销售',
    reporter: '许一鸣',
    organization: '体育西网点',
    orgId: 'th-1',
    reporterId: 'gz_employee',
    amount: 16,
    unit: '万元',
    points: 128,
    reportedAt: '2026-05-07 10:15',
    attachment: '已上传'
  }
]

export const rankingRows = [
  {
    rank: 1,
    name: '王五',
    organization: '湖南路网点',
    orgId: 'b-branch',
    indicator: '保险销售',
    achievement: '12 万元',
    points: 180,
    completionRate: 92
  },
  {
    rank: 2,
    name: '张三',
    organization: '鼓楼营业室',
    orgId: 'a-branch',
    userId: 'employee',
    indicator: '定期存款',
    achievement: '80 万元',
    points: 40,
    completionRate: 86
  },
  {
    rank: 3,
    name: '李四',
    organization: '鼓楼营业室',
    orgId: 'a-branch',
    indicator: '企业微信添加量',
    achievement: '45 户',
    points: 9,
    completionRate: 72
  },
  {
    rank: 4,
    name: '郑雪',
    organization: '夫子庙网点',
    orgId: 'qh-1',
    indicator: '基金定投签约',
    achievement: '38 万元',
    points: 152,
    completionRate: 81
  },
  {
    rank: 5,
    name: '吴迪',
    organization: '新街口网点',
    orgId: 'xw-2',
    indicator: '小微客户电访',
    achievement: '96 次',
    points: 9.6,
    completionRate: 78
  },
  {
    rank: 6,
    name: '许一鸣',
    organization: '体育西网点',
    orgId: 'th-1',
    userId: 'gz_employee',
    indicator: '贵金属销售',
    achievement: '16 万元',
    points: 128,
    completionRate: 84
  }
]

export const dashboardStats = [
  { label: '项目总完成率', value: '86%', hint: '较序时进度领先 8%' },
  { label: '今日新增业绩', value: '137 万', hint: '覆盖 3 个指标' },
  { label: '今日新增积分', value: '229', hint: '员工上报 18 笔' },
  { label: '待分解任务', value: '3', hint: '跨项目任务池待处理' }
]
