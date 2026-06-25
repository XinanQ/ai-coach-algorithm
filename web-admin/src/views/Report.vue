<template>
  <div class="page">
    <header class="page-header">
      <div>
        <h1>每日上报</h1>
        <p>员工选择项目与指标，填写完成数量，提交后等待管理员审核。</p>
      </div>
      <span class="badge">上报表单</span>
    </header>

    <section class="grid grid-2">
      <form class="panel form-grid" @submit.prevent="submitReport">
        <label class="form-field">
          项目
          <select v-model="form.projectId" class="select" @change="onProjectChange">
            <option value="">请选择项目</option>
            <option v-for="project in projects" :key="project.id" :value="String(project.id)">
              {{ project.name }}
            </option>
          </select>
        </label>

        <label class="form-field">
          指标
          <select v-model="form.indicatorId" class="select" :disabled="!form.projectId">
            <option value="">请选择指标</option>
            <option v-for="indicator in projectIndicators" :key="indicator.id" :value="String(indicator.id)">
              {{ indicator.name }}
            </option>
          </select>
        </label>

        <label class="form-field">
          上报日期
          <input v-model="form.reportDate" class="field" type="date" />
        </label>

        <label class="form-field">
          上报数量
          <input v-model.number="form.amount" class="field" type="number" min="0" step="any" />
        </label>

        <label class="form-field">
          附件
          <input
            ref="fileInputRef"
            class="field file-input"
            type="file"
            :accept="ACCEPTED_ATTACHMENT_TYPES"
            @change="onAttachmentChange"
          />
          <span class="field-hint">
            选填，支持 PDF、图片、Office 文档、压缩包等常见格式，单个文件不超过 10MB
          </span>
          <p v-if="attachmentName" class="attachment-name">
            已选择：{{ attachmentName }}
            <button type="button" class="link-button" @click="clearAttachment">移除</button>
          </p>
        </label>

        <div class="form-field full">
          <button
            class="button primary"
            type="submit"
            :disabled="submitting || !canSubmitSelectedProject"
          >
            {{ submitting ? '提交中…' : '提交上报' }}
          </button>
          <p v-if="message" :class="['form-message', messageType]">{{ message }}</p>
        </div>
      </form>

      <div class="panel">
        <h2>当前指标规则</h2>
        <p class="muted" v-if="!selectedIndicator">请选择项目和指标后查看计分规则。</p>
        <dl v-else class="rules">
          <div>
            <dt>项目状态</dt>
            <dd>{{ selectedProject?.status || '—' }}</dd>
          </div>
          <div>
            <dt>计分标准</dt>
            <dd>{{ selectedIndicator.pointsStandard }} {{ selectedIndicator.pointsUnit }}</dd>
          </div>
          <div>
            <dt>权重 ratio</dt>
            <dd>{{ selectedIndicator.ratio }}</dd>
          </div>
          <div>
            <dt>单位</dt>
            <dd>{{ selectedIndicator.unit || '—' }}</dd>
          </div>
          <div>
            <dt>预估积分</dt>
            <dd>{{ estimatedPoints }}</dd>
          </div>
        </dl>
      </div>
    </section>

    <section class="panel">
      <h2>我的上报记录</h2>
      <div v-if="loading" class="muted">加载中…</div>
      <div v-else-if="reports.length === 0" class="muted">暂无上报记录</div>
      <table v-else class="table report-table">
        <thead>
          <tr>
            <th>项目</th>
            <th>指标</th>
            <th>数量</th>
            <th>状态</th>
            <th>积分</th>
            <th>时间</th>
            <th>附件</th>
            <th>审核意见</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="report in reports"
            :key="report.id"
            :class="['report-row', `report-row--${report.statusCode}`]"
          >
            <td>{{ report.project }}</td>
            <td>{{ report.indicator }}</td>
            <td>{{ report.amount }} {{ report.unit }}</td>
            <td>
              <span class="status-badge" :class="`status-${report.statusCode}`">
                {{ report.status }}
              </span>
            </td>
            <td>{{ report.points }}</td>
            <td>{{ report.reportedAt }}</td>
            <td>
              <div v-if="report.attachmentUrl" class="attachment-actions">
                <button type="button" class="link-button" @click="previewAttachment(report.attachmentUrl)">
                  预览
                </button>
                <button type="button" class="link-button" @click="downloadAttachment(report.attachmentUrl)">
                  下载
                </button>
              </div>
              <span v-else class="muted">—</span>
            </td>
            <td class="review-cell">
              <span v-if="report.statusCode === 'rejected'" class="reject-reason">
                {{ report.reviewComment || '未填写驳回原因' }}
              </span>
              <span v-else-if="report.statusCode === 'approved' && report.reviewComment" class="approve-note">
                {{ report.reviewComment }}
              </span>
              <span v-else class="muted">—</span>
            </td>
          </tr>
        </tbody>
      </table>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { getCurrentUser } from '../auth/permissions'
import {
  ACCEPTED_ATTACHMENT_TYPES,
  getMyReports,
  getProjectIndicators,
  getReportOptions,
  downloadReportAttachment,
  previewReportAttachment,
  submitReport as submitReportApi,
  uploadReportAttachment
} from '../api/reports'
import { decimal, decimalToFixed } from '../utils/decimal'

const projects = ref([])
const projectIndicators = ref([])
const reports = ref([])
const loading = ref(false)
const submitting = ref(false)
const currentUser = getCurrentUser()
const form = reactive({
  projectId: '',
  indicatorId: '',
  reportDate: new Date().toISOString().slice(0, 10),
  amount: null
})
const message = ref('')
const messageType = ref('success')
const fileInputRef = ref(null)
const attachmentFile = ref(null)
const attachmentUrl = ref('')
const attachmentName = ref('')

const MAX_ATTACHMENT_SIZE = 10 * 1024 * 1024

const selectedProject = computed(() =>
  projects.value.find((project) => String(project.id) === String(form.projectId))
)

const canSubmitSelectedProject = computed(() => selectedProject.value?.statusCode === 'ACTIVE')
const selectedIndicator = computed(() =>
  projectIndicators.value.find((indicator) => String(indicator.id) === String(form.indicatorId))
)

const estimatedPoints = computed(() => {
  const ind = selectedIndicator.value
  const amount = form.amount
  if (!ind || !amount || amount <= 0) return '—'
  const pts = decimal(amount)
    .times(ind.pointsStandard || 0)
    .times(ind.ratio || 0)
  return Number.isFinite(pts.toNumber()) ? decimalToFixed(pts, 4) : '—'
})

async function loadReports() {
  loading.value = true
  try {
    reports.value = await getMyReports(currentUser)
  } finally {
    loading.value = false
  }
}

async function onProjectChange() {
  form.indicatorId = ''
  message.value = ''
  clearAttachment()
  if (!form.projectId) {
    projectIndicators.value = []
    return
  }
  try {
    projectIndicators.value = await getProjectIndicators(form.projectId)
  } catch (err) {
    projectIndicators.value = []
    message.value = err.message || '加载该项目的指标失败。'
    messageType.value = 'error'
  }
}

function onAttachmentChange(event) {
  const file = event.target.files?.[0]
  if (!file) {
    clearAttachment()
    return
  }

  if (file.size > MAX_ATTACHMENT_SIZE) {
    message.value = '附件大小不能超过 10MB。'
    messageType.value = 'error'
    clearAttachment()
    return
  }

  message.value = ''
  attachmentFile.value = file
  attachmentUrl.value = ''
  attachmentName.value = file.name
}

function clearAttachment() {
  attachmentFile.value = null
  attachmentUrl.value = ''
  attachmentName.value = ''
  if (fileInputRef.value) {
    fileInputRef.value.value = ''
  }
}

async function previewAttachment(url) {
  try {
    await previewReportAttachment(url)
  } catch (err) {
    message.value = err.message || '附件预览失败。'
    messageType.value = 'error'
  }
}

async function downloadAttachment(url) {
  try {
    await downloadReportAttachment(url)
  } catch (err) {
    message.value = err.message || '附件下载失败。'
    messageType.value = 'error'
  }
}

async function submitReport() {
  message.value = ''
  if (!form.projectId) {
    message.value = '请选择项目。'
    messageType.value = 'error'
    return
  }
  if (!form.indicatorId) {
    message.value = '请选择指标。'
    messageType.value = 'error'
    return
  }
  if (!form.reportDate) {
    message.value = '请选择上报日期。'
    messageType.value = 'error'
    return
  }
  if (!form.amount || form.amount <= 0) {
    message.value = '上报数量必须大于 0。'
    messageType.value = 'error'
    return
  }

  submitting.value = true
  try {
    let uploadedUrl = attachmentUrl.value
    if (attachmentFile.value) {
      const uploaded = await uploadReportAttachment(attachmentFile.value)
      uploadedUrl = uploaded.url
      attachmentUrl.value = uploadedUrl
    }

    await submitReportApi({ ...form, attachmentUrl: uploadedUrl || undefined }, currentUser)
    message.value = '上报已提交，请等待管理员审核。'
    messageType.value = 'success'
    form.indicatorId = ''
    form.amount = null
    clearAttachment()
    await loadReports()
  } catch (err) {
    message.value = err.message || '提交失败，请稍后重试。'
    messageType.value = 'error'
  } finally {
    submitting.value = false
  }
}

onMounted(async () => {
  const options = await getReportOptions(currentUser)
  projects.value = options.projects
  await loadReports()
})
</script>

<style scoped>
.form-message {
  margin: 8px 0 0;
}
.form-message.success {
  color: #0f766e;
}
.form-message.error {
  color: #b91c1c;
}
.field-hint {
  font-size: 12px;
  color: #6b7280;
}
.file-input {
  padding: 8px;
}
.attachment-name {
  margin: 6px 0 0;
  font-size: 13px;
  color: #374151;
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
.attachment-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.rules {
  display: grid;
  gap: 12px;
}
.rules div {
  display: flex;
  justify-content: space-between;
  padding-bottom: 12px;
  border-bottom: 1px solid #e5e7eb;
}
dt {
  color: #6b7280;
}
dd {
  margin: 0;
  color: #111827;
  font-weight: 600;
}

.report-table .report-row--pending {
  background: #f9fafb;
}

.report-table .report-row--approved {
  background: #f0fdf4;
}

.report-table .report-row--rejected {
  background: #fef2f2;
}

.status-badge {
  display: inline-block;
  padding: 2px 10px;
  border-radius: 999px;
  font-size: 13px;
  font-weight: 600;
  white-space: nowrap;
}

.status-badge.status-pending {
  background: #e5e7eb;
  color: #4b5563;
}

.status-badge.status-approved {
  background: #bbf7d0;
  color: #047857;
}

.status-badge.status-rejected {
  background: #fecaca;
  color: #b91c1c;
}

.review-cell {
  max-width: 220px;
  font-size: 13px;
  line-height: 1.5;
}

.reject-reason {
  color: #b91c1c;
}

.approve-note {
  color: #047857;
}

.muted {
  color: #9ca3af;
}
</style>
