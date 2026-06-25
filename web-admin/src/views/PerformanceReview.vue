<template>
  <div class="page">
    <header class="page-header">
      <div>
        <h1>业绩审核</h1>
        <p>审核员工业绩上报记录。通过后进入积分引擎计算并加入排名，驳回则不加分。</p>
      </div>
      <span class="badge">业绩审核</span>
    </header>

    <section class="panel">
      <div class="toolbar">
        <div class="tabs">
          <button
            v-for="tab in tabs"
            :key="tab.value"
            class="tab"
            :class="{ active: activeTab === tab.value }"
            type="button"
            @click="activeTab = tab.value"
          >
            {{ tab.label }}
            <span class="tab-count">{{ countByStatus(tab.value) }}</span>
          </button>
        </div>
        <div class="filters">
          <div class="date-range">
            <span class="filter-label">提交时间</span>
            <input v-model="dateRange.start" class="field date" type="date" />
            <span class="date-sep">至</span>
            <input v-model="dateRange.end" class="field date" type="date" />
          </div>
          <input
            v-model="keyword"
            class="field search"
            type="text"
            placeholder="搜索上报人 / 机构 / 项目"
          />
          <button v-if="hasFilters" class="button small" type="button" @click="resetFilters">
            重置
          </button>
        </div>
      </div>

      <table class="table review-table">
        <colgroup>
          <col style="width: 7%" />
          <col style="width: 12%" />
          <col style="width: 13%" />
          <col style="width: 14%" />
          <col style="width: 9%" />
          <col style="width: 8%" />
          <col style="width: 5%" />
          <col style="width: 10%" />
          <col style="width: 8%" />
          <col style="width: 14%" />
        </colgroup>
        <thead>
          <tr>
            <th>编号</th>
            <th>上报人</th>
            <th>所属机构</th>
            <th>项目</th>
            <th>指标</th>
            <th>金额</th>
            <th>附件</th>
            <th>提交时间</th>
            <th>状态</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="item in filteredList" :key="item.id">
            <td>{{ item.code }}</td>
            <td>
              <span class="reporter">{{ item.reporter }}</span>
              <span class="muted emp-id">ID {{ item.employeeId }}</span>
            </td>
            <td>{{ item.orgName }}</td>
            <td>{{ item.project }}</td>
            <td>{{ item.indicator }}</td>
            <td>{{ item.amount }} {{ item.unit }}</td>
            <td>
              <div v-if="item.attachmentUrl" class="attachment-actions">
                <button class="link-button" type="button" @click="previewAttachment(item)">预览</button>
                <button class="link-button" type="button" @click="downloadAttachment(item)">下载</button>
              </div>
              <span v-else class="muted">无</span>
            </td>
            <td>{{ item.submittedAt }}</td>
            <td>
              <span class="badge" :class="`status-${item.status}`">
                {{ statusLabel(item.status) }}
              </span>
            </td>
            <td>
              <div class="actions">
                <template v-if="item.status === 'pending' && item.canReview">
                  <button class="button primary small" type="button" @click="openReview(item, 'approve')">
                    通过
                  </button>
                  <button class="button warning small" type="button" @click="openReview(item, 'modify-approve')">
                    修改并通过
                  </button>
                  <button class="button danger small" type="button" @click="openReview(item, 'reject')">
                    驳回
                  </button>
                </template>
                <template v-else-if="item.status === 'pending'">
                  <button class="button small no-permission" type="button" @click="showNoPermission">
                    通过
                  </button>
                  <button class="button small no-permission" type="button" @click="showNoPermission">
                    修改并通过
                  </button>
                  <button class="button small no-permission" type="button" @click="showNoPermission">
                    驳回
                  </button>
                </template>
                <button class="button small" type="button" @click="openDetail(item)">查看</button>
              </div>
            </td>
          </tr>
          <tr v-if="!filteredList.length">
            <td class="empty" colspan="10">暂无审核记录</td>
          </tr>
        </tbody>
      </table>
    </section>

    <p v-if="attachmentMessage" class="attachment-message">{{ attachmentMessage }}</p>

    <!-- 审核（通过 / 驳回 / 修改并通过）弹窗 -->
    <div v-if="reviewDialog.visible" class="modal-overlay" @click.self="closeReview">
      <div class="modal">
        <h2>{{ reviewDialogTitle }}</h2>
        <dl class="summary">
          <div><dt>上报人</dt><dd>{{ reviewDialog.item?.reporter }}</dd></div>
          <div><dt>项目</dt><dd>{{ reviewDialog.item?.project }}</dd></div>
          <div><dt>指标</dt><dd>{{ reviewDialog.item?.indicator }}</dd></div>
          <template v-if="reviewDialog.action !== 'modify-approve'">
            <div><dt>金额</dt><dd>{{ reviewDialog.item?.amount }} {{ reviewDialog.item?.unit }}</dd></div>
          </template>
        </dl>
        <template v-if="reviewDialog.action === 'modify-approve'">
          <label class="form-field">
            上报数量
            <input
              v-model="reviewDialog.editAmount"
              class="field"
              type="number"
              min="0"
              step="any"
              :placeholder="`原值 ${reviewDialog.item?.amount}`"
            />
          </label>
          <label class="form-field">
            上报日期
            <input v-model="reviewDialog.editReportDate" class="field" type="date" />
          </label>
        </template>
        <label class="form-field">
          审核意见{{ reviewDialog.action === 'reject' ? '（必填）' : '（选填）' }}
          <textarea
            v-model="reviewDialog.comment"
            class="field textarea"
            rows="3"
            :placeholder="reviewDialogPlaceholder"
          ></textarea>
        </label>
        <p v-if="reviewDialog.error" class="form-message error">{{ reviewDialog.error }}</p>
        <div class="modal-actions">
          <button class="button" type="button" @click="closeReview">取消</button>
          <button
            class="button"
            :class="[
              reviewDialog.action === 'reject'
                ? 'danger'
                : reviewDialog.action === 'modify-approve'
                  ? 'warning'
                  : 'primary',
              { 'is-loading': reviewDialog.submitting }
            ]"
            type="button"
            @click="submitReview"
          >
            {{ reviewDialogConfirmLabel }}
          </button>
        </div>
      </div>
    </div>

    <!-- 查看详情弹窗 -->
    <div v-if="detailDialog.visible" class="modal-overlay" @click.self="closeDetail">
      <div class="modal">
        <h2>上报详情 · {{ detailDialog.item?.code }}</h2>
        <dl class="summary detail">
          <div><dt>上报人</dt><dd>{{ detailDialog.item?.reporter }}（ID {{ detailDialog.item?.employeeId }}）</dd></div>
          <div><dt>所属机构</dt><dd>{{ detailDialog.item?.orgName }}</dd></div>
          <div><dt>项目</dt><dd>{{ detailDialog.item?.project }}</dd></div>
          <div><dt>指标</dt><dd>{{ detailDialog.item?.indicator }}</dd></div>
          <div><dt>金额</dt><dd>{{ detailDialog.item?.amount }} {{ detailDialog.item?.unit }}</dd></div>
          <div>
            <dt>附件</dt>
            <dd>
              <template v-if="detailDialog.item?.attachmentUrl">
                <span class="attachment-name">{{ detailDialog.item?.attachmentName }}</span>
                <div class="attachment-actions">
                  <button class="link-button" type="button" @click="previewAttachment(detailDialog.item)">预览</button>
                  <button class="link-button" type="button" @click="downloadAttachment(detailDialog.item)">下载</button>
                </div>
              </template>
              <span v-else>无</span>
            </dd>
          </div>
          <div><dt>提交时间</dt><dd>{{ detailDialog.item?.submittedAt }}</dd></div>
          <div><dt>说明</dt><dd>{{ detailDialog.item?.description || '—' }}</dd></div>
          <div><dt>状态</dt><dd>{{ statusLabel(detailDialog.item?.status) }}</dd></div>
          <template v-if="detailDialog.item?.status !== 'pending'">
            <div><dt>审核人</dt><dd>{{ detailDialog.item?.reviewer || '—' }}</dd></div>
            <div><dt>审核时间</dt><dd>{{ detailDialog.item?.reviewTime || '—' }}</dd></div>
            <div><dt>审核意见</dt><dd>{{ detailDialog.item?.reviewComment || '—' }}</dd></div>
          </template>
          <div v-if="detailDialog.item?.status === 'approved'">
            <dt>积分</dt>
            <dd>{{ detailDialog.item?.totalPoints ?? detailDialog.item?.points ?? '—' }}</dd>
          </div>
        </dl>
        <div class="modal-actions">
          <button class="button" type="button" @click="closeDetail">关闭</button>
        </div>
      </div>
    </div>

    <div v-if="permissionDialog.visible" class="modal-overlay" @click.self="closePermissionDialog">
      <div class="modal">
        <h2>无审核权限</h2>
        <p class="permission-hint">该上报不在您的审核范围内，无法修改、通过或驳回。审核范围与积分流水权限一致。</p>
        <div class="modal-actions">
          <button class="button primary" type="button" @click="closePermissionDialog">知道了</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { getCurrentUser } from '../auth/permissions'
import {
  REVIEW_STATUS,
  approveReview,
  getReviewList,
  modifyAndApproveReview,
  rejectReview
} from '../api/performanceReview'
import { downloadReportAttachment, previewReportAttachment } from '../api/reports'

const currentUser = getCurrentUser()
const list = ref([])
const activeTab = ref('all')
const keyword = ref('')
const dateRange = reactive({ start: '', end: '' })
const attachmentMessage = ref('')

const tabs = [
  { label: '全部', value: 'all' },
  { label: '待审核', value: 'pending' },
  { label: '已通过', value: 'approved' },
  { label: '已驳回', value: 'rejected' }
]

const reviewDialog = reactive({
  visible: false,
  action: 'approve',
  item: null,
  comment: '',
  editAmount: '',
  editReportDate: '',
  error: '',
  submitting: false
})

const reviewDialogTitle = computed(() => {
  if (reviewDialog.action === 'modify-approve') return '修改并通过'
  if (reviewDialog.action === 'reject') return '驳回审核'
  return '通过审核'
})

const reviewDialogPlaceholder = computed(() => {
  if (reviewDialog.action === 'reject') return '请填写驳回原因'
  if (reviewDialog.action === 'modify-approve') return '可填写修正说明，如：数量录入有误已更正'
  return '可填写通过备注'
})

const reviewDialogConfirmLabel = computed(() => {
  if (reviewDialog.action === 'modify-approve') return '确认修改并通过'
  if (reviewDialog.action === 'reject') return '确认驳回'
  return '确认通过'
})

const detailDialog = reactive({
  visible: false,
  item: null
})

const permissionDialog = reactive({
  visible: false
})

function showNoPermission() {
  permissionDialog.visible = true
}

function closePermissionDialog() {
  permissionDialog.visible = false
}

function statusLabel(status) {
  return REVIEW_STATUS[status]?.label || status
}

function countByStatus(status) {
  if (status === 'all') return list.value.length
  return list.value.filter((item) => item.status === status).length
}

const hasFilters = computed(() =>
  Boolean(keyword.value || dateRange.start || dateRange.end)
)

const filteredList = computed(() => {
  const kw = keyword.value.trim()
  return list.value
    .filter((item) => (activeTab.value === 'all' ? true : item.status === activeTab.value))
    .filter((item) => {
      // submittedAt 形如 "2026-06-02 16:50"，取日期部分按 ISO 字符串比较
      const day = item.submittedAt.slice(0, 10)
      if (dateRange.start && day < dateRange.start) return false
      if (dateRange.end && day > dateRange.end) return false
      return true
    })
    .filter((item) =>
      kw
        ? item.reporter.includes(kw) || item.orgName.includes(kw) || item.project.includes(kw)
        : true
    )
})

function resetFilters() {
  keyword.value = ''
  dateRange.start = ''
  dateRange.end = ''
}

function openReview(item, action) {
  if (!item?.canReview) {
    showNoPermission()
    return
  }
  reviewDialog.visible = true
  reviewDialog.action = action
  reviewDialog.item = item
  reviewDialog.comment = ''
  reviewDialog.editAmount = item.amount != null ? String(item.amount) : ''
  reviewDialog.editReportDate = item.reportDate || item.submittedAt?.slice(0, 10) || ''
  reviewDialog.error = ''
  reviewDialog.submitting = false
}

function closeReview() {
  reviewDialog.visible = false
  reviewDialog.item = null
  reviewDialog.submitting = false
}

async function submitReview() {
  if (reviewDialog.submitting) return

  if (reviewDialog.action === 'reject' && !reviewDialog.comment.trim()) {
    reviewDialog.error = '驳回时请填写原因。'
    return
  }

  if (reviewDialog.action === 'modify-approve') {
    const amount = Number(reviewDialog.editAmount)
    if (!reviewDialog.editAmount || Number.isNaN(amount) || amount <= 0) {
      reviewDialog.error = '请填写大于 0 的上报数量。'
      return
    }
    if (!reviewDialog.editReportDate) {
      reviewDialog.error = '请选择上报日期。'
      return
    }
  }

  reviewDialog.submitting = true
  reviewDialog.error = ''
  const id = reviewDialog.item.id
  const payload = {
    comment: reviewDialog.comment.trim(),
    reviewer: currentUser?.name || currentUser?.employeeNo || 'admin'
  }

  try {
    if (reviewDialog.action === 'approve') {
      await approveReview(id, payload)
    } else if (reviewDialog.action === 'modify-approve') {
      await modifyAndApproveReview(id, {
        ...payload,
        result: reviewDialog.editAmount,
        reportDate: reviewDialog.editReportDate
      })
    } else {
      await rejectReview(id, payload)
    }
    closeReview()
    list.value = await getReviewList()
  } catch (err) {
    reviewDialog.error = err.message || '操作失败，请重试'
  } finally {
    reviewDialog.submitting = false
  }
}

function openDetail(item) {
  detailDialog.item = item
  detailDialog.visible = true
}

function closeDetail() {
  detailDialog.visible = false
  detailDialog.item = null
}

async function previewAttachment(item) {
  attachmentMessage.value = ''
  try {
    await previewReportAttachment(item?.attachmentUrl)
  } catch (err) {
    attachmentMessage.value = err.message || '附件预览失败'
  }
}

async function downloadAttachment(item) {
  attachmentMessage.value = ''
  try {
    await downloadReportAttachment(item?.attachmentUrl)
  } catch (err) {
    attachmentMessage.value = err.message || '附件下载失败'
  }
}

onMounted(async () => {
  list.value = await getReviewList()
})
</script>

<style scoped>
.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}

.tabs {
  display: inline-flex;
  gap: 4px;
  padding: 4px;
  background: #f3f4f6;
  border-radius: 999px;
}

.tab {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  height: 32px;
  padding: 0 14px;
  border: none;
  border-radius: 999px;
  background: transparent;
  color: #4b5563;
  font-size: 14px;
  cursor: pointer;
}

.tab.active {
  background: #0f766e;
  color: #fff;
}

.tab-count {
  font-size: 12px;
  opacity: 0.8;
}

.filters {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.date-range {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.filter-label {
  color: #6b7280;
  font-size: 14px;
  white-space: nowrap;
}

.date-sep {
  color: #6b7280;
}

.field.date {
  width: 130px;
}

.search {
  width: 220px;
  max-width: 100%;
}

/* 固定布局 + 列宽合计 100%，整张表恰好铺满一页，无需横向滚动 */
.review-table {
  table-layout: fixed;
  width: 100%;
}

.review-table :deep(th),
.review-table :deep(td) {
  padding: 10px 8px;
  word-break: break-word;
}

.reporter {
  font-weight: 600;
  color: #111827;
}

.emp-id {
  margin-left: 8px;
  font-size: 12px;
}

.badge {
  white-space: nowrap;
}

.badge.status-pending {
  background: #f3f4f6;
  color: #4b5563;
}

.badge.status-approved {
  background: #ecfdf5;
  color: #047857;
}

.badge.status-rejected {
  background: #fef2f2;
  color: #b91c1c;
}

.actions {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.button.small {
  height: 28px;
  padding: 0 8px;
  font-size: 12px;
  white-space: nowrap;
}

.button.danger {
  border-color: #dc2626;
  background: #dc2626;
  color: #fff;
}

.button.warning {
  border-color: #fde047;
  background: #fef9c3;
  color: #854d0e;
}

.button.warning:hover {
  border-color: #facc15;
  background: #fef08a;
}

.empty {
  text-align: center;
  color: #9ca3af;
  padding: 24px;
}

.modal-overlay {
  position: fixed;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(17, 24, 39, 0.45);
  z-index: 1000;
}

.modal {
  width: 460px;
  max-width: calc(100vw - 32px);
  max-height: calc(100vh - 64px);
  overflow: auto;
  padding: 24px;
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 20px 40px rgba(0, 0, 0, 0.15);
}

.modal h2 {
  margin: 0 0 16px;
}

.summary {
  display: grid;
  gap: 10px;
  margin: 0 0 16px;
}

.summary div {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  padding-bottom: 10px;
  border-bottom: 1px solid #f3f4f6;
}

.summary dt {
  color: #6b7280;
  flex: none;
}

.summary dd {
  margin: 0;
  color: #111827;
  font-weight: 600;
  text-align: right;
}

.textarea {
  height: auto;
  padding: 8px 10px;
  resize: vertical;
  font: inherit;
}

.form-message.error {
  margin: 8px 0 0;
  color: #b91c1c;
}

.form-field {
  display: grid;
  gap: 6px;
  margin-bottom: 12px;
  color: #374151;
  font-size: 14px;
}

.button.small.no-permission {
  opacity: 0.55;
  cursor: pointer;
  border-color: #d1d5db;
  background: #f3f4f6;
  color: #9ca3af;
}

.button.is-loading {
  opacity: 0.7;
  cursor: wait;
}

.permission-hint {
  margin: 0 0 16px;
  color: #4b5563;
  line-height: 1.6;
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 8px;
}

.attachment-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.attachment-name {
  display: block;
  margin-bottom: 6px;
  font-weight: 500;
  word-break: break-all;
}

.link-button {
  border: none;
  background: none;
  padding: 0;
  color: #2563eb;
  cursor: pointer;
  font: inherit;
}

.link-button:hover {
  text-decoration: underline;
}

.attachment-message {
  margin: 0 0 12px;
  color: #b91c1c;
  font-size: 14px;
}

.summary dd .attachment-actions {
  justify-content: flex-end;
}
</style>
