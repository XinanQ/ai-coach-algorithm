import { reports } from '../data/mockData'
import { mockResolve } from './request'

// ============================================================================
// 业绩审核数据层（reviewer 侧）
//
// 业务流程（后端负责，前端仅留好接口）：
//   1. 员工上报业绩            ->  status = 'pending'（待审核）
//   2. 审核员在本页通过/驳回
//        - 通过 approveReview  ->  status = 'approved'，后端进入【积分引擎】计算
//                                  积分，再【加入排名】
//        - 驳回 rejectReview   ->  status = 'rejected'，不加分、不进排名
//
// 当前为假数据驱动：用 mockResolve 返回本地数据，函数签名与真实后端对齐，
// 接后端时把 mockResolve(...) 换成 request(...) 即可，页面层无感切换。
//
// 待后端确认的接口契约（路径仅为前端建议，需与后端对齐）：
//   GET  /api/admin/performance-reviews?status=&keyword=&startDate=&endDate=   列表
//   GET  /api/admin/performance-reviews/{id}               详情
//   POST /api/admin/performance-reviews/{id}/approve       通过 { comment, bigOrder, bigOrderPoints }
//   POST /api/admin/performance-reviews/{id}/reject        驳回 { comment }
// ============================================================================

// 状态与中文文案的映射，供页面统一使用
export const REVIEW_STATUS = {
  pending: { label: '待审核', type: 'pending' },
  approved: { label: '已通过', type: 'approved' },
  rejected: { label: '已驳回', type: 'rejected' }
}

// 把 mockData 里的上报记录映射成审核列表所需的形状
function toReviewItem(report) {
  return {
    id: report.id,
    code: `RVW-${String(report.id).padStart(3, '0')}`,
    reporter: report.userName,
    employeeNo: report.userId,
    orgName: report.userOrgName,
    orgId: report.userOrgId,
    project: report.projectName,
    indicator: report.indicatorName,
    amount: report.value,
    unit: report.indicatorUnit,
    attachmentCount: report.attachment ? 1 : 0,
    attachment: report.attachment,
    submittedAt: report.reviewTime || `${report.date} 00:00`,
    status: report.status,
    description: report.description,
    points: report.points,
    bigOrder: report.bigOrder,
    bigOrderPoints: report.bigOrderPoints,
    totalPoints: report.totalPoints,
    reviewer: report.reviewer,
    reviewTime: report.reviewTime,
    reviewComment: report.reviewComment
  }
}

// 仅用于本地演示的补充数据（覆盖三种状态、凑足列表体量）。
// 接入后端列表接口后，这块连同 mockData 的来源一起替换掉即可。
const demoReviews = [
  {
    id: 101,
    code: 'RVW-101',
    reporter: '李伟',
    employeeNo: 'EMP-1025',
    orgName: '朝阳支行·建国路网点',
    orgId: 'a-branch',
    project: '六月存款冲刺月',
    indicator: '存款余额',
    amount: 420,
    unit: '万元',
    attachmentCount: 3,
    attachment: 'deposit_proof.pdf',
    submittedAt: '2026-06-02 10:10',
    status: 'pending',
    description: '六月存款余额冲刺，新增对公存款 420 万元',
    points: 0,
    bigOrder: false,
    bigOrderPoints: 0,
    totalPoints: 0,
    reviewer: null,
    reviewTime: null,
    reviewComment: null
  },
  {
    id: 102,
    code: 'RVW-102',
    reporter: '赵阳',
    employeeNo: 'EMP-5032',
    orgName: '朝阳支行·国贸网点',
    orgId: 'a-branch',
    project: '2026年二季度存款净增项目',
    indicator: '存款净增额',
    amount: 95,
    unit: '万元',
    attachmentCount: 1,
    attachment: 'net_increase.png',
    submittedAt: '2026-06-02 16:50',
    status: 'rejected',
    description: '二季度存款净增 95 万元',
    points: 0,
    bigOrder: false,
    bigOrderPoints: 0,
    totalPoints: 0,
    reviewer: 'branch_admin',
    reviewTime: '2026-06-03 09:10',
    reviewComment: '附件金额与上报数额不一致，请核实后重新提交'
  },
  {
    id: 103,
    code: 'RVW-103',
    reporter: '马丽',
    employeeNo: 'EMP-8945',
    orgName: '海淀支行·五道口网点',
    orgId: 'b-branch',
    project: '2026年二季度存款净增项目',
    indicator: '存款净增额',
    amount: 380,
    unit: '万元',
    attachmentCount: 2,
    attachment: 'net_increase.pdf',
    submittedAt: '2026-06-02 11:30',
    status: 'approved',
    description: '二季度存款净增 380 万元',
    points: 190,
    bigOrder: false,
    bigOrderPoints: 0,
    totalPoints: 190,
    reviewer: 'branch_admin',
    reviewTime: '2026-06-02 18:40',
    reviewComment: '审核通过'
  }
]

// 拉取审核列表。params: { status, keyword, startDate, endDate }
// status: 'all' | 'pending' | 'approved' | 'rejected'
// startDate / endDate: 'YYYY-MM-DD'，按提交时间(submittedAt)的日期闭区间过滤
export function getReviewList(params = {}) {
  const { status = 'all', keyword = '', startDate = '', endDate = '' } = params

  const all = [...reports.map(toReviewItem), ...demoReviews].sort((a, b) =>
    a.submittedAt < b.submittedAt ? 1 : -1
  )

  const kw = keyword.trim()
  const filtered = all
    .filter((item) => (status === 'all' ? true : item.status === status))
    .filter((item) => {
      const day = item.submittedAt.slice(0, 10)
      if (startDate && day < startDate) return false
      if (endDate && day > endDate) return false
      return true
    })
    .filter((item) =>
      kw
        ? item.reporter.includes(kw) || item.orgName.includes(kw) || item.project.includes(kw)
        : true
    )

  return mockResolve(filtered)
}

// 审核详情
export function getReviewDetail(id) {
  const all = [...reports.map(toReviewItem), ...demoReviews]
  return mockResolve(all.find((item) => item.id === id) || null)
}

// 审核通过：后端据此进入积分引擎计算并加入排名
// payload: { comment, bigOrder, bigOrderPoints }
export function approveReview(id, payload = {}) {
  // 接后端时改为：
  // return request(`/api/admin/performance-reviews/${id}/approve`, {
  //   method: 'POST',
  //   body: JSON.stringify(payload)
  // })
  return mockResolve({ success: true, id, status: 'approved', ...payload })
}

// 审核驳回：不加分、不进排名
// payload: { comment }
export function rejectReview(id, payload = {}) {
  // 接后端时改为：
  // return request(`/api/admin/performance-reviews/${id}/reject`, {
  //   method: 'POST',
  //   body: JSON.stringify(payload)
  // })
  return mockResolve({ success: true, id, status: 'rejected', ...payload })
}
