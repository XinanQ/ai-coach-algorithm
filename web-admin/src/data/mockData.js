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
                manager: '周杰',
                children: [
                  {
                    id: 'th-1',
                    name: '体育西网点',
                    level: '网点',
                    manager: '许一鸣',
                    staffCount: 8
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
    id: 'admin',
    username: 'admin',
    password: 'admin123',
    name: '总行管理员',
    role: 'admin',
    orgId: 'hq',
    orgName: '总行'
  },
  {
    id: 'js_admin',
    username: 'js_admin',
    password: 'js123',
    name: '王敏',
    role: 'province_admin',
    orgId: 'js',
    orgName: '江苏省行'
  },
  {
    id: 'nj_admin',
    username: 'nj_admin',
    password: 'nj123',
    name: '李伟',
    role: 'city_admin',
    orgId: 'nj',
    orgName: '南京市行'
  },
  {
    id: 'gl_admin',
    username: 'gl_admin',
    password: 'gl123',
    name: '张三',
    role: 'branch_admin',
    orgId: 'gl',
    orgName: '鼓楼支行'
  },
  {
    id: 'employee',
    username: 'employee',
    password: 'emp123',
    name: '张三',
    role: 'employee',
    orgId: 'a-branch',
    orgName: '鼓楼营业室'
  },
  {
    id: 'gz_employee',
    username: 'gz_employee',
    password: 'gz123',
    name: '许一鸣',
    role: 'employee',
    orgId: 'th-1',
    orgName: '体育西网点'
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
    currentAllocation: 420,
    unit: '万元'
  },
  {
    id: 2,
    target: '湖南路网点',
    level: '网点',
    indicator: '定期存款',
    totalTask: 800,
    allocated: 250,
    currentAllocation: 380,
    unit: '万元'
  },
  {
    id: 3,
    target: '夫子庙网点',
    level: '网点',
    indicator: '定期存款',
    totalTask: 900,
    allocated: 280,
    currentAllocation: 350,
    unit: '万元'
  }
]

export const decompositionPlans = [
  {
    id: 'spring-2026-nj',
    projectId: 'spring-2026',
    projectName: '2026 春季旺季营销项目',
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
          { indicatorId: 1, indicator: '定期存款', totalTask: 1200, allocated: 300, currentAllocation: 420, unit: '万元' },
          { indicatorId: 2, indicator: '企业微信添加量', totalTask: 420, allocated: 120, currentAllocation: 130, unit: '户' }
        ]
      },
      {
        id: 'xw',
        target: '玄武支行',
        level: '支行',
        indicators: [
          { indicatorId: 1, indicator: '定期存款', totalTask: 1100, allocated: 280, currentAllocation: 380, unit: '万元' },
          { indicatorId: 2, indicator: '企业微信添加量', totalTask: 380, allocated: 100, currentAllocation: 110, unit: '户' }
        ]
      }
    ]
  },
  {
    id: 'inclusive-2026-city',
    projectId: 'inclusive-2026',
    projectName: '普惠金融客户拓展项目',
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
          { indicatorId: 4, indicator: '小微客户电访', totalTask: 1200, allocated: 160, currentAllocation: 110, unit: '次' },
          { indicatorId: 5, indicator: '贷记卡办理', totalTask: 420, allocated: 120, currentAllocation: 130, unit: '张' }
        ]
      },
      {
        id: 'xw',
        target: '玄武支行',
        level: '支行',
        indicators: [
          { indicatorId: 4, indicator: '小微客户电访', totalTask: 1100, allocated: 140, currentAllocation: 95, unit: '次' },
          { indicatorId: 5, indicator: '贷记卡办理', totalTask: 380, allocated: 100, currentAllocation: 85, unit: '张' }
        ]
      }
    ]
  }
]

export const reports = [
  {
    id: 1,
    userId: 'employee',
    userName: '张三',
    userOrgId: 'a-branch',
    userOrgName: '鼓楼营业室',
    projectId: 'spring-2026',
    projectName: '2026 春季旺季营销项目',
    indicatorId: 1,
    indicatorName: '定期存款',
    indicatorUnit: '万元',
    value: 120,
    points: 60,
    date: '2026-03-15',
    status: 'approved',
    attachment: null,
    description: '完成定期存款任务120万元',
    bigOrder: false,
    bigOrderPoints: 0,
    totalPoints: 60,
    reviewer: 'gl_admin',
    reviewTime: '2026-03-15 18:30',
    reviewComment: '审核通过'
  },
  {
    id: 2,
    userId: 'employee',
    userName: '张三',
    userOrgId: 'a-branch',
    userOrgName: '鼓楼营业室',
    projectId: 'spring-2026',
    projectName: '2026 春季旺季营销项目',
    indicatorId: 2,
    indicatorName: '企业微信添加量',
    indicatorUnit: '户',
    value: 45,
    points: 9,
    date: '2026-03-16',
    status: 'pending',
    attachment: null,
    description: '添加企业微信客户45户',
    bigOrder: false,
    bigOrderPoints: 0,
    totalPoints: 9,
    reviewer: null,
    reviewTime: null,
    reviewComment: null
  },
  {
    id: 3,
    userId: 'gz_employee',
    userName: '许一鸣',
    userOrgId: 'th-1',
    userOrgName: '体育西网点',
    projectId: 'wealth-2026',
    projectName: '财富客户资产提升项目',
    indicatorId: 7,
    indicatorName: '贵金属销售',
    indicatorUnit: '万元',
    value: 25,
    points: 200,
    date: '2026-05-10',
    status: 'approved',
    attachment: 'sales_proof.pdf',
    description: '销售贵金属产品25万元',
    bigOrder: true,
    bigOrderPoints: 50,
    totalPoints: 250,
    reviewer: 'th_admin',
    reviewTime: '2026-05-10 19:00',
    reviewComment: '审核通过，大单奖励50积分'
  }
]

export const employeeRankings = {
  'spring-2026': {
    1: [
      { rank: 1, name: '王五', organization: '湖南路网点', orgId: 'b-branch', level: '员工', userId: 'employee', indicator: '定期存款', achievement: '120 万元', points: 60, completionRate: 95 },
      { rank: 2, name: '张三', organization: '鼓楼营业室', orgId: 'a-branch', level: '员工', userId: 'employee', indicator: '定期存款', achievement: '110 万元', points: 55, completionRate: 88 },
      { rank: 3, name: '李四', organization: '鼓楼营业室', orgId: 'a-branch', level: '员工', userId: 'employee', indicator: '定期存款', achievement: '95 万元', points: 47.5, completionRate: 82 },
      { rank: 4, name: '郑雪', organization: '夫子庙网点', orgId: 'qh-1', level: '员工', userId: 'employee', indicator: '定期存款', achievement: '88 万元', points: 44, completionRate: 76 },
      { rank: 5, name: '吴迪', organization: '新街口网点', orgId: 'xw-2', level: '员工', userId: 'employee', indicator: '定期存款', achievement: '75 万元', points: 37.5, completionRate: 70 }
    ],
    2: [
      { rank: 1, name: '李四', organization: '鼓楼营业室', orgId: 'a-branch', level: '员工', userId: 'employee', indicator: '企业微信添加量', achievement: '65 户', points: 13, completionRate: 92 },
      { rank: 2, name: '王五', organization: '湖南路网点', orgId: 'b-branch', level: '员工', userId: 'employee', indicator: '企业微信添加量', achievement: '58 户', points: 11.6, completionRate: 85 },
      { rank: 3, name: '张三', organization: '鼓楼营业室', orgId: 'a-branch', level: '员工', userId: 'employee', indicator: '企业微信添加量', achievement: '52 户', points: 10.4, completionRate: 78 },
      { rank: 4, name: '郑雪', organization: '夫子庙网点', orgId: 'qh-1', level: '员工', userId: 'employee', indicator: '企业微信添加量', achievement: '45 户', points: 9, completionRate: 72 },
      { rank: 5, name: '吴迪', organization: '新街口网点', orgId: 'xw-2', level: '员工', userId: 'employee', indicator: '企业微信添加量', achievement: '38 户', points: 7.6, completionRate: 65 }
    ],
    3: [
      { rank: 1, name: '王五', organization: '湖南路网点', orgId: 'b-branch', level: '员工', userId: 'employee', indicator: '中国人寿 3 年期缴保险', achievement: '25 万元', points: 375, completionRate: 94 },
      { rank: 2, name: '张三', organization: '鼓楼营业室', orgId: 'a-branch', level: '员工', userId: 'employee', indicator: '中国人寿 3 年期缴保险', achievement: '22 万元', points: 330, completionRate: 88 },
      { rank: 3, name: '李四', organization: '鼓楼营业室', orgId: 'a-branch', level: '员工', userId: 'employee', indicator: '中国人寿 3 年期缴保险', achievement: '18 万元', points: 270, completionRate: 82 },
      { rank: 4, name: '郑雪', organization: '夫子庙网点', orgId: 'qh-1', level: '员工', userId: 'employee', indicator: '中国人寿 3 年期缴保险', achievement: '15 万元', points: 225, completionRate: 75 },
      { rank: 5, name: '吴迪', organization: '新街口网点', orgId: 'xw-2', level: '员工', userId: 'employee', indicator: '中国人寿 3 年期缴保险', achievement: '12 万元', points: 180, completionRate: 68 }
    ]
  },
  'inclusive-2026': {
    4: [
      { rank: 1, name: '吴迪', organization: '新街口网点', orgId: 'xw-2', level: '员工', userId: 'employee', indicator: '小微客户电访', achievement: '125 次', points: 12.5, completionRate: 96 },
      { rank: 2, name: '张三', organization: '鼓楼营业室', orgId: 'a-branch', level: '员工', userId: 'employee', indicator: '小微客户电访', achievement: '118 次', points: 11.8, completionRate: 90 },
      { rank: 3, name: '李四', organization: '鼓楼营业室', orgId: 'a-branch', level: '员工', userId: 'employee', indicator: '小微客户电访', achievement: '105 次', points: 10.5, completionRate: 84 },
      { rank: 4, name: '王五', organization: '湖南路网点', orgId: 'b-branch', level: '员工', userId: 'employee', indicator: '小微客户电访', achievement: '92 次', points: 9.2, completionRate: 78 },
      { rank: 5, name: '郑雪', organization: '夫子庙网点', orgId: 'qh-1', level: '员工', userId: 'employee', indicator: '小微客户电访', achievement: '85 次', points: 8.5, completionRate: 72 }
    ],
    5: [
      { rank: 1, name: '张三', organization: '鼓楼营业室', orgId: 'a-branch', level: '员工', userId: 'employee', indicator: '贷记卡办理', achievement: '18 张', points: 108, completionRate: 93 },
      { rank: 2, name: '王五', organization: '湖南路网点', orgId: 'b-branch', level: '员工', userId: 'employee', indicator: '贷记卡办理', achievement: '16 张', points: 96, completionRate: 87 },
      { rank: 3, name: '李四', organization: '鼓楼营业室', orgId: 'a-branch', level: '员工', userId: 'employee', indicator: '贷记卡办理', achievement: '14 张', points: 84, completionRate: 81 },
      { rank: 4, name: '吴迪', organization: '新街口网点', orgId: 'xw-2', level: '员工', userId: 'employee', indicator: '贷记卡办理', achievement: '12 张', points: 72, completionRate: 75 },
      { rank: 5, name: '郑雪', organization: '夫子庙网点', orgId: 'qh-1', level: '员工', userId: 'employee', indicator: '贷记卡办理', achievement: '10 张', points: 60, completionRate: 68 }
    ]
  },
  'wealth-2026': {
    6: [
      { rank: 1, name: '郑雪', organization: '夫子庙网点', orgId: 'qh-1', level: '员工', userId: 'employee', indicator: '基金定投签约', achievement: '68 万元', points: 272, completionRate: 95 },
      { rank: 2, name: '王五', organization: '湖南路网点', orgId: 'b-branch', level: '员工', userId: 'employee', indicator: '基金定投签约', achievement: '62 万元', points: 248, completionRate: 89 },
      { rank: 3, name: '张三', organization: '鼓楼营业室', orgId: 'a-branch', level: '员工', userId: 'employee', indicator: '基金定投签约', achievement: '55 万元', points: 220, completionRate: 83 },
      { rank: 4, name: '李四', organization: '鼓楼营业室', orgId: 'a-branch', level: '员工', userId: 'employee', indicator: '基金定投签约', achievement: '48 万元', points: 192, completionRate: 76 },
      { rank: 5, name: '吴迪', organization: '新街口网点', orgId: 'xw-2', level: '员工', userId: 'employee', indicator: '基金定投签约', achievement: '42 万元', points: 168, completionRate: 70 }
    ],
    7: [
      { rank: 1, name: '许一鸣', organization: '体育西网点', orgId: 'th-1', level: '员工', userId: 'gz_employee', indicator: '贵金属销售', achievement: '28 万元', points: 224, completionRate: 94 },
      { rank: 2, name: '王五', organization: '湖南路网点', orgId: 'b-branch', level: '员工', userId: 'employee', indicator: '贵金属销售', achievement: '24 万元', points: 192, completionRate: 88 },
      { rank: 3, name: '张三', organization: '鼓楼营业室', orgId: 'a-branch', level: '员工', userId: 'employee', indicator: '贵金属销售', achievement: '20 万元', points: 160, completionRate: 82 },
      { rank: 4, name: '郑雪', organization: '夫子庙网点', orgId: 'qh-1', level: '员工', userId: 'employee', indicator: '贵金属销售', achievement: '16 万元', points: 128, completionRate: 75 },
      { rank: 5, name: '李四', organization: '鼓楼营业室', orgId: 'a-branch', level: '员工', userId: 'employee', indicator: '贵金属销售', achievement: '14 万元', points: 112, completionRate: 68 }
    ]
  }
}

export const outletRankings = {
  'spring-2026': {
    1: [
      { rank: 1, name: '湖南路网点', orgId: 'b-branch', level: '网点', indicator: '定期存款', achievement: '480 万元', points: 240, completionRate: 96 },
      { rank: 2, name: '鼓楼营业室', orgId: 'a-branch', level: '网点', indicator: '定期存款', achievement: '440 万元', points: 220, completionRate: 90 },
      { rank: 3, name: '夫子庙网点', orgId: 'qh-1', level: '网点', indicator: '定期存款', achievement: '380 万元', points: 190, completionRate: 84 },
      { rank: 4, name: '新街口网点', orgId: 'xw-2', level: '网点', indicator: '定期存款', achievement: '320 万元', points: 160, completionRate: 78 },
      { rank: 5, name: '珠江路网点', orgId: 'xh-1', level: '网点', indicator: '定期存款', achievement: '280 万元', points: 140, completionRate: 72 }
    ],
    2: [
      { rank: 1, name: '鼓楼营业室', orgId: 'a-branch', level: '网点', indicator: '企业微信添加量', achievement: '280 户', points: 56, completionRate: 94 },
      { rank: 2, name: '湖南路网点', orgId: 'b-branch', level: '网点', indicator: '企业微信添加量', achievement: '245 户', points: 49, completionRate: 88 },
      { rank: 3, name: '夫子庙网点', orgId: 'qh-1', level: '网点', indicator: '企业微信添加量', achievement: '210 户', points: 42, completionRate: 82 },
      { rank: 4, name: '新街口网点', orgId: 'xw-2', level: '网点', indicator: '企业微信添加量', achievement: '185 户', points: 37, completionRate: 76 },
      { rank: 5, name: '珠江路网点', orgId: 'xh-1', level: '网点', indicator: '企业微信添加量', achievement: '160 户', points: 32, completionRate: 70 }
    ],
    3: [
      { rank: 1, name: '湖南路网点', orgId: 'b-branch', level: '网点', indicator: '中国人寿 3 年期缴保险', achievement: '95 万元', points: 1425, completionRate: 95 },
      { rank: 2, name: '鼓楼营业室', orgId: 'a-branch', level: '网点', indicator: '中国人寿 3 年期缴保险', achievement: '85 万元', points: 1275, completionRate: 89 },
      { rank: 3, name: '夫子庙网点', orgId: 'qh-1', level: '网点', indicator: '中国人寿 3 年期缴保险', achievement: '72 万元', points: 1080, completionRate: 83 },
      { rank: 4, name: '新街口网点', orgId: 'xw-2', level: '网点', indicator: '中国人寿 3 年期缴保险', achievement: '60 万元', points: 900, completionRate: 77 },
      { rank: 5, name: '珠江路网点', orgId: 'xh-1', level: '网点', indicator: '中国人寿 3 年期缴保险', achievement: '48 万元', points: 720, completionRate: 71 }
    ]
  },
  'inclusive-2026': {
    4: [
      { rank: 1, name: '新街口网点', orgId: 'xw-2', level: '网点', indicator: '小微客户电访', achievement: '520 次', points: 52, completionRate: 97 },
      { rank: 2, name: '鼓楼营业室', orgId: 'a-branch', level: '网点', indicator: '小微客户电访', achievement: '480 次', points: 48, completionRate: 91 },
      { rank: 3, name: '湖南路网点', orgId: 'b-branch', level: '网点', indicator: '小微客户电访', achievement: '425 次', points: 42.5, completionRate: 85 },
      { rank: 4, name: '夫子庙网点', orgId: 'qh-1', level: '网点', indicator: '小微客户电访', achievement: '380 次', points: 38, completionRate: 79 },
      { rank: 5, name: '珠江路网点', orgId: 'xh-1', level: '网点', indicator: '小微客户电访', achievement: '340 次', points: 34, completionRate: 73 }
    ],
    5: [
      { rank: 1, name: '鼓楼营业室', orgId: 'a-branch', level: '网点', indicator: '贷记卡办理', achievement: '72 张', points: 432, completionRate: 94 },
      { rank: 2, name: '湖南路网点', orgId: 'b-branch', level: '网点', indicator: '贷记卡办理', achievement: '64 张', points: 384, completionRate: 88 },
      { rank: 3, name: '新街口网点', orgId: 'xw-2', level: '网点', indicator: '贷记卡办理', achievement: '56 张', points: 336, completionRate: 82 },
      { rank: 4, name: '夫子庙网点', orgId: 'qh-1', level: '网点', indicator: '贷记卡办理', achievement: '48 张', points: 288, completionRate: 76 },
      { rank: 5, name: '珠江路网点', orgId: 'xh-1', level: '网点', indicator: '贷记卡办理', achievement: '40 张', points: 240, completionRate: 70 }
    ]
  },
  'wealth-2026': {
    6: [
      { rank: 1, name: '夫子庙网点', orgId: 'qh-1', level: '网点', indicator: '基金定投签约', achievement: '275 万元', points: 1100, completionRate: 96 },
      { rank: 2, name: '湖南路网点', orgId: 'b-branch', level: '网点', indicator: '基金定投签约', achievement: '245 万元', points: 980, completionRate: 90 },
      { rank: 3, name: '鼓楼营业室', orgId: 'a-branch', level: '网点', indicator: '基金定投签约', achievement: '215 万元', points: 860, completionRate: 84 },
      { rank: 4, name: '新街口网点', orgId: 'xw-2', level: '网点', indicator: '基金定投签约', achievement: '185 万元', points: 740, completionRate: 78 },
      { rank: 5, name: '珠江路网点', orgId: 'xh-1', level: '网点', indicator: '基金定投签约', achievement: '160 万元', points: 640, completionRate: 72 }
    ],
    7: [
      { rank: 1, name: '体育西网点', orgId: 'th-1', level: '网点', indicator: '贵金属销售', achievement: '115 万元', points: 920, completionRate: 95 },
      { rank: 2, name: '湖南路网点', orgId: 'b-branch', level: '网点', indicator: '贵金属销售', achievement: '98 万元', points: 784, completionRate: 89 },
      { rank: 3, name: '鼓楼营业室', orgId: 'a-branch', level: '网点', indicator: '贵金属销售', achievement: '82 万元', points: 656, completionRate: 83 },
      { rank: 4, name: '夫子庙网点', orgId: 'qh-1', level: '网点', indicator: '贵金属销售', achievement: '68 万元', points: 544, completionRate: 77 },
      { rank: 5, name: '珠江路网点', orgId: 'xh-1', level: '网点', indicator: '贵金属销售', achievement: '55 万元', points: 440, completionRate: 71 }
    ]
  }
}

export const branchRankings = {
  'spring-2026': {
    1: [
      { rank: 1, name: '鼓楼支行', orgId: 'gl', level: '支行', indicator: '定期存款', achievement: '1520 万元', points: 760, completionRate: 94 },
      { rank: 2, name: '玄武支行', orgId: 'xw', level: '支行', indicator: '定期存款', achievement: '1380 万元', points: 690, completionRate: 88 },
      { rank: 3, name: '秦淮支行', orgId: 'qh', level: '支行', indicator: '定期存款', achievement: '1250 万元', points: 625, completionRate: 82 },
      { rank: 4, name: '姑苏支行', orgId: 'gusu', level: '支行', indicator: '定期存款', achievement: '1100 万元', points: 550, completionRate: 76 },
      { rank: 5, name: '西湖支行', orgId: 'xh', level: '支行', indicator: '定期存款', achievement: '980 万元', points: 490, completionRate: 70 }
    ],
    2: [
      { rank: 1, name: '鼓楼支行', orgId: 'gl', level: '支行', indicator: '企业微信添加量', achievement: '935 户', points: 187, completionRate: 93 },
      { rank: 2, name: '玄武支行', orgId: 'xw', level: '支行', indicator: '企业微信添加量', achievement: '840 户', points: 168, completionRate: 87 },
      { rank: 3, name: '秦淮支行', orgId: 'qh', level: '支行', indicator: '企业微信添加量', achievement: '755 户', points: 151, completionRate: 81 },
      { rank: 4, name: '姑苏支行', orgId: 'gusu', level: '支行', indicator: '企业微信添加量', achievement: '680 户', points: 136, completionRate: 75 },
      { rank: 5, name: '西湖支行', orgId: 'xh', level: '支行', indicator: '企业微信添加量', achievement: '610 户', points: 122, completionRate: 69 }
    ],
    3: [
      { rank: 1, name: '鼓楼支行', orgId: 'gl', level: '支行', indicator: '中国人寿 3 年期缴保险', achievement: '275 万元', points: 4125, completionRate: 92 },
      { rank: 2, name: '玄武支行', orgId: 'xw', level: '支行', indicator: '中国人寿 3 年期缴保险', achievement: '248 万元', points: 3720, completionRate: 86 },
      { rank: 3, name: '秦淮支行', orgId: 'qh', level: '支行', indicator: '中国人寿 3 年期缴保险', achievement: '220 万元', points: 3300, completionRate: 80 },
      { rank: 4, name: '姑苏支行', orgId: 'gusu', level: '支行', indicator: '中国人寿 3 年期缴保险', achievement: '195 万元', points: 2925, completionRate: 74 },
      { rank: 5, name: '西湖支行', orgId: 'xh', level: '支行', indicator: '中国人寿 3 年期缴保险', achievement: '172 万元', points: 2580, completionRate: 68 }
    ]
  },
  'inclusive-2026': {
    4: [
      { rank: 1, name: '玄武支行', orgId: 'xw', level: '支行', indicator: '小微客户电访', achievement: '1680 次', points: 168, completionRate: 96 },
      { rank: 2, name: '鼓楼支行', orgId: 'gl', level: '支行', indicator: '小微客户电访', achievement: '1540 次', points: 154, completionRate: 90 },
      { rank: 3, name: '秦淮支行', orgId: 'qh', level: '支行', indicator: '小微客户电访', achievement: '1400 次', points: 140, completionRate: 84 },
      { rank: 4, name: '姑苏支行', orgId: 'gusu', level: '支行', indicator: '小微客户电访', achievement: '1260 次', points: 126, completionRate: 78 },
      { rank: 5, name: '西湖支行', orgId: 'xh', level: '支行', indicator: '小微客户电访', achievement: '1140 次', points: 114, completionRate: 72 }
    ],
    5: [
      { rank: 1, name: '鼓楼支行', orgId: 'gl', level: '支行', indicator: '贷记卡办理', achievement: '232 张', points: 1392, completionRate: 93 },
      { rank: 2, name: '玄武支行', orgId: 'xw', level: '支行', indicator: '贷记卡办理', achievement: '208 张', points: 1248, completionRate: 87 },
      { rank: 3, name: '秦淮支行', orgId: 'qh', level: '支行', indicator: '贷记卡办理', achievement: '184 张', points: 1104, completionRate: 81 },
      { rank: 4, name: '姑苏支行', orgId: 'gusu', level: '支行', indicator: '贷记卡办理', achievement: '160 张', points: 960, completionRate: 75 },
      { rank: 5, name: '西湖支行', orgId: 'xh', level: '支行', indicator: '贷记卡办理', achievement: '140 张', points: 840, completionRate: 69 }
    ]
  },
  'wealth-2026': {
    6: [
      { rank: 1, name: '秦淮支行', orgId: 'qh', level: '支行', indicator: '基金定投签约', achievement: '875 万元', points: 3500, completionRate: 95 },
      { rank: 2, name: '鼓楼支行', orgId: 'gl', level: '支行', indicator: '基金定投签约', achievement: '780 万元', points: 3120, completionRate: 89 },
      { rank: 3, name: '玄武支行', orgId: 'xw', level: '支行', indicator: '基金定投签约', achievement: '695 万元', points: 2780, completionRate: 83 },
      { rank: 4, name: '姑苏支行', orgId: 'gusu', level: '支行', indicator: '基金定投签约', achievement: '610 万元', points: 2440, completionRate: 77 },
      { rank: 5, name: '西湖支行', orgId: 'xh', level: '支行', indicator: '基金定投签约', achievement: '540 万元', points: 2160, completionRate: 71 }
    ],
    7: [
      { rank: 1, name: '海曙支行', orgId: 'hs', level: '支行', indicator: '贵金属销售', achievement: '365 万元', points: 2920, completionRate: 94 },
      { rank: 2, name: '鼓楼支行', orgId: 'gl', level: '支行', indicator: '贵金属销售', achievement: '315 万元', points: 2520, completionRate: 88 },
      { rank: 3, name: '玄武支行', orgId: 'xw', level: '支行', indicator: '贵金属销售', achievement: '275 万元', points: 2200, completionRate: 82 },
      { rank: 4, name: '秦淮支行', orgId: 'qh', level: '支行', indicator: '贵金属销售', achievement: '240 万元', points: 1920, completionRate: 76 },
      { rank: 5, name: '西湖支行', orgId: 'xh', level: '支行', indicator: '贵金属销售', achievement: '210 万元', points: 1680, completionRate: 70 }
    ]
  }
}

export const cityRankings = {
  'spring-2026': {
    1: [
      { rank: 1, name: '南京市行', orgId: 'nj', level: '市行', indicator: '定期存款', achievement: '4150 万元', points: 2075, completionRate: 93 },
      { rank: 2, name: '苏州市行', orgId: 'sz', level: '市行', indicator: '定期存款', achievement: '3780 万元', points: 1890, completionRate: 87 },
      { rank: 3, name: '杭州市行', orgId: 'hz', level: '市行', indicator: '定期存款', achievement: '3420 万元', points: 1710, completionRate: 81 },
      { rank: 4, name: '宁波市行', orgId: 'nb', level: '市行', indicator: '定期存款', achievement: '3050 万元', points: 1525, completionRate: 75 },
      { rank: 5, name: '广州市行', orgId: 'gz', level: '市行', indicator: '定期存款', achievement: '2720 万元', points: 1360, completionRate: 69 }
    ],
    2: [
      { rank: 1, name: '南京市行', orgId: 'nj', level: '市行', indicator: '企业微信添加量', achievement: '2530 户', points: 506, completionRate: 92 },
      { rank: 2, name: '苏州市行', orgId: 'sz', level: '市行', indicator: '企业微信添加量', achievement: '2290 户', points: 458, completionRate: 86 },
      { rank: 3, name: '杭州市行', orgId: 'hz', level: '市行', indicator: '企业微信添加量', achievement: '2060 户', points: 412, completionRate: 80 },
      { rank: 4, name: '宁波市行', orgId: 'nb', level: '市行', indicator: '企业微信添加量', achievement: '1840 户', points: 368, completionRate: 74 },
      { rank: 5, name: '广州市行', orgId: 'gz', level: '市行', indicator: '企业微信添加量', achievement: '1650 户', points: 330, completionRate: 68 }
    ],
    3: [
      { rank: 1, name: '南京市行', orgId: 'nj', level: '市行', indicator: '中国人寿 3 年期缴保险', achievement: '743 万元', points: 11145, completionRate: 91 },
      { rank: 2, name: '苏州市行', orgId: 'sz', level: '市行', indicator: '中国人寿 3 年期缴保险', achievement: '672 万元', points: 10080, completionRate: 85 },
      { rank: 3, name: '杭州市行', orgId: 'hz', level: '市行', indicator: '中国人寿 3 年期缴保险', achievement: '605 万元', points: 9075, completionRate: 79 },
      { rank: 4, name: '宁波市行', orgId: 'nb', level: '市行', indicator: '中国人寿 3 年期缴保险', achievement: '540 万元', points: 8100, completionRate: 73 },
      { rank: 5, name: '广州市行', orgId: 'gz', level: '市行', indicator: '中国人寿 3 年期缴保险', achievement: '482 万元', points: 7230, completionRate: 67 }
    ]
  },
  'inclusive-2026': {
    4: [
      { rank: 1, name: '南京市行', orgId: 'nj', level: '市行', indicator: '小微客户电访', achievement: '4620 次', points: 462, completionRate: 95 },
      { rank: 2, name: '苏州市行', orgId: 'sz', level: '市行', indicator: '小微客户电访', achievement: '4180 次', points: 418, completionRate: 89 },
      { rank: 3, name: '杭州市行', orgId: 'hz', level: '市行', indicator: '小微客户电访', achievement: '3760 次', points: 376, completionRate: 83 },
      { rank: 4, name: '宁波市行', orgId: 'nb', level: '市行', indicator: '小微客户电访', achievement: '3350 次', points: 335, completionRate: 77 },
      { rank: 5, name: '广州市行', orgId: 'gz', level: '市行', indicator: '小微客户电访', achievement: '3000 次', points: 300, completionRate: 71 }
    ],
    5: [
      { rank: 1, name: '南京市行', orgId: 'nj', level: '市行', indicator: '贷记卡办理', achievement: '624 张', points: 3744, completionRate: 92 },
      { rank: 2, name: '苏州市行', orgId: 'sz', level: '市行', indicator: '贷记卡办理', achievement: '560 张', points: 3360, completionRate: 86 },
      { rank: 3, name: '杭州市行', orgId: 'hz', level: '市行', indicator: '贷记卡办理', achievement: '504 张', points: 3024, completionRate: 80 },
      { rank: 4, name: '宁波市行', orgId: 'nb', level: '市行', indicator: '贷记卡办理', achievement: '448 张', points: 2688, completionRate: 74 },
      { rank: 5, name: '广州市行', orgId: 'gz', level: '市行', indicator: '贷记卡办理', achievement: '400 张', points: 2400, completionRate: 68 }
    ]
  },
  'wealth-2026': {
    6: [
      { rank: 1, name: '南京市行', orgId: 'nj', level: '市行', indicator: '基金定投签约', achievement: '2380 万元', points: 9520, completionRate: 94 },
      { rank: 2, name: '苏州市行', orgId: 'sz', level: '市行', indicator: '基金定投签约', achievement: '2120 万元', points: 8480, completionRate: 88 },
      { rank: 3, name: '杭州市行', orgId: 'hz', level: '市行', indicator: '基金定投签约', achievement: '1900 万元', points: 7600, completionRate: 82 },
      { rank: 4, name: '宁波市行', orgId: 'nb', level: '市行', indicator: '基金定投签约', achievement: '1680 万元', points: 6720, completionRate: 76 },
      { rank: 5, name: '广州市行', orgId: 'gz', level: '市行', indicator: '基金定投签约', achievement: '1500 万元', points: 6000, completionRate: 70 }
    ],
    7: [
      { rank: 1, name: '广州市行', orgId: 'gz', level: '市行', indicator: '贵金属销售', achievement: '990 万元', points: 7920, completionRate: 93 },
      { rank: 2, name: '南京市行', orgId: 'nj', level: '市行', indicator: '贵金属销售', achievement: '855 万元', points: 6840, completionRate: 87 },
      { rank: 3, name: '苏州市行', orgId: 'sz', level: '市行', indicator: '贵金属销售', achievement: '750 万元', points: 6000, completionRate: 81 },
      { rank: 4, name: '杭州市行', orgId: 'hz', level: '市行', indicator: '贵金属销售', achievement: '655 万元', points: 5240, completionRate: 75 },
      { rank: 5, name: '宁波市行', orgId: 'nb', level: '市行', indicator: '贵金属销售', achievement: '570 万元', points: 4560, completionRate: 69 }
    ]
  }
}

export const rankingRows = employeeRankings['spring-2026'][1]

export const dashboardStats = [
  { label: '项目总完成率', value: '86%', hint: '较序时进度领先 8%' },
  { label: '今日新增业绩', value: '137 万', hint: '覆盖 3 个指标' },
  { label: '今日新增积分', value: '229', hint: '员工上报 18 笔' },
  { label: '待分解任务', value: '3', hint: '跨项目任务池待处理' }
]