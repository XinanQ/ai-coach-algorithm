<template>
  <div class="page">
    <header class="page-header">
      <div>
        <h1>项目管理</h1>
        <p>创建并维护营销项目，项目下继续配置指标和分解任务。</p>
      </div>
      <button class="button primary" :disabled="!canCreateProject" @click="showCreateForm = !showCreateForm">
        创建项目
      </button>
    </header>

    <section v-if="message && !showCreateForm" class="panel result-panel" :class="{ danger: messageType === 'error' }">
      {{ message }}
    </section>

    <section v-if="showCreateForm" class="panel">
      <div class="section-heading">
        <div>
          <h2>创建项目</h2>
          <p>项目会保存到后端数据库，并显示在项目管理列表中。</p>
        </div>
        <span class="badge neutral">{{ currentUser.organization }}</span>
      </div>

      <div class="form-grid">
        <label class="form-field">
          项目名称
          <input v-model.trim="form.name" class="field" placeholder="例如：端午客户拓展项目" />
        </label>
        <label class="form-field">
          项目状态
          <select v-model="form.status" class="select">
            <option>未开始</option>
            <option>进行中</option>
            <option>已结束</option>
          </select>
        </label>
        <label class="form-field">
          开始日期
          <input v-model="form.startDate" class="field" type="date" />
        </label>
        <label class="form-field">
          结束日期
          <input v-model="form.endDate" class="field" type="date" />
        </label>
        <label class="form-field">
          上报截止
          <input v-model="form.reportDeadline" class="field" type="time" />
        </label>
        <label class="form-field switch-field">
          附件要求
          <input v-model="form.attachmentRequired" type="checkbox" />
        </label>
        <label class="form-field full">
          项目说明
          <input v-model.trim="form.description" class="field" placeholder="说明项目目标和业务范围" />
        </label>
        <div class="form-field full">
          <div class="form-label">指标设置</div>
          <div class="indicator-list">
            <div v-for="(indicator, index) in form.indicators" :key="index" class="indicator-row">
              <input v-model.trim="indicator.name" class="field" placeholder="指标名称，例如：保险" />
              <input v-model.trim="indicator.unit" class="field" placeholder="单位，例如：万元" />
              <input v-model.number="indicator.amount" class="field" type="number" min="0" step="0.01" placeholder="数额" />
              <span class="indicator-equals">=</span>
              <input v-model.number="indicator.points" class="field" type="number" min="0" step="0.1" placeholder="积分" />
              <input v-model.number="indicator.weight" class="field" type="number" min="0" max="100" placeholder="占比%" />
              <button class="button danger-button" type="button" @click="removeIndicator(index)">删除</button>
            </div>
            <p v-if="!form.indicators.length" class="muted">暂未设置指标，可点击下方按钮添加。</p>
            <button class="button" type="button" @click="addIndicator">新增指标</button>
            <p class="indicator-hint">
              示例：名称「保险」、单位「万元」、数额 100、积分 100，表示每 100 万元保险积 100 分。
              占比合计建议为 100%，当前合计 {{ indicatorWeightTotal }}%。
            </p>
          </div>
        </div>
        <div class="form-field full">
          <div class="form-label">项目附件</div>
          <div class="upload-section">
            <input ref="fileInput" type="file" class="file-input" @change="handleFileChange" />
            <button class="button" type="button" @click="triggerFileUpload">选择文件</button>
            <span v-if="form.attachment" class="file-name">{{ form.attachment.name }}</span>
            <button v-if="form.attachment" class="button danger-button" type="button" @click="clearAttachment">
              清除
            </button>
          </div>
        </div>
      </div>

      <div class="form-actions">
        <button class="button primary" @click="saveProject">保存项目</button>
        <button class="button" @click="resetForm">清空</button>
        <p v-if="message" class="form-message" :class="{ danger: messageType === 'error' }">{{ message }}</p>
      </div>
    </section>

    <section class="grid grid-2">
      <article v-for="project in projects" :key="project.id" class="panel project-card">
        <div class="project-title">
          <h2>{{ project.name }}</h2>
          <div class="badge-group">
            <span class="badge">{{ project.status }}</span>
            <span class="badge neutral">{{ project.relation }}</span>
          </div>
        </div>
        <p>{{ project.description }}</p>
        <dl>
          <div>
            <dt>项目周期</dt>
            <dd>{{ project.startDate }} 至 {{ project.endDate }}</dd>
          </div>
          <div>
            <dt>上报截止</dt>
            <dd>{{ project.reportDeadline }}</dd>
          </div>
          <div>
            <dt>附件要求</dt>
            <dd>{{ project.attachmentRequired ? '必须上传附件' : '不强制附件' }}</dd>
          </div>
          <div>
            <dt>分解状态</dt>
            <dd>{{ project.distributionStatus }}</dd>
          </div>
        </dl>
        <div class="toolbar">
          <router-link class="button primary" :to="`/projects/${project.id}`">查看详情</router-link>
          <router-link v-if="project.canConfigureIndicators" class="button" :to="`/projects/${project.id}/indicators`">
            指标配置
          </router-link>
          <router-link v-if="project.canDecompose" class="button" :to="`/projects/${project.id}/decompose`">
            下发分解
          </router-link>
          <button v-else class="button" disabled>待上级下发明细</button>
          <button v-if="project.canDelete" class="button danger-button" @click="removeProject(project)">
            删除项目
          </button>
        </div>
      </article>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { getCurrentUser } from '../auth/permissions'
import { createProject, deleteProject, getProjects } from '../api/projects'

const projects = ref([])
const currentUser = getCurrentUser()
const showCreateForm = ref(false)
const message = ref('')
const messageType = ref('success')
const canCreateProject = computed(() =>
  ['总行', '省行', '市行', '支行'].includes(currentUser?.level)
)

const form = reactive({
  name: '',
  description: '',
  startDate: '',
  endDate: '',
  reportDeadline: '00:00',
  attachmentRequired: false,
  status: '未开始',
  attachment: null,
  indicators: []
})

const indicatorWeightTotal = computed(() =>
  form.indicators.reduce((sum, indicator) => sum + Number(indicator.weight || 0), 0)
)

function addIndicator() {
  form.indicators.push({ name: '', unit: '万元', amount: 0, points: 0, weight: 0 })
}

function removeIndicator(index) {
  form.indicators.splice(index, 1)
}

const fileInput = ref(null)

function triggerFileUpload() {
  fileInput.value?.click()
}

function handleFileChange(event) {
  const [file] = event.target.files
  if (file) {
    form.attachment = file
  }
}

function clearAttachment() {
  form.attachment = null
  if (fileInput.value) {
    fileInput.value.value = ''
  }
}

function resetForm({ keepMessage = false } = {}) {
  Object.assign(form, {
    name: '',
    description: '',
    startDate: '',
    endDate: '',
    reportDeadline: '00:00',
    attachmentRequired: false,
    status: '未开始',
    attachment: null,
    indicators: []
  })
  if (fileInput.value) {
    fileInput.value.value = ''
  }
  if (!keepMessage) message.value = ''
}

async function loadProjects() {
  projects.value = await getProjects(currentUser)
}

async function saveProject() {
  if (!form.name) {
    message.value = '项目名称不能为空。'
    messageType.value = 'error'
    return
  }

  if (!form.startDate || !form.endDate) {
    message.value = '项目周期不能为空。'
    messageType.value = 'error'
    return
  }

  if (form.endDate < form.startDate) {
    message.value = '结束日期不能早于开始日期。'
    messageType.value = 'error'
    return
  }
  try {
    const result = await createProject(
        { ...form, attachment: undefined },
        currentUser
    )

    await loadProjects()

    message.value = `项目“${result.name}”创建成功，已保存到数据库。`
    messageType.value = 'success'

    resetForm({ keepMessage: true })
    showCreateForm.value = false
  } catch (error) {
    message.value = error.message || '创建项目失败。'
    messageType.value = 'error'
  }

}

async function removeProject(project) {
  const confirmed = window.confirm(`确定删除项目“${project.name}”吗？该操作会从临时文件中移除该项目。`)
  if (!confirmed) return

  try {
    const result = await deleteProject(project.id)
    await loadProjects()
    message.value = `项目已删除，临时文件已更新：${result.filePath}。`
    messageType.value = 'success'
  } catch (error) {
    message.value = error.message
    messageType.value = 'error'
  }
}

onMounted(async () => {
  await loadProjects()
})
</script>

<style scoped>
.project-card {
  display: grid;
  gap: 16px;
}

.project-title {
  display: flex;
  justify-content: space-between;
  gap: 12px;
}

.badge-group {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 8px;
}

.project-card h2 {
  margin: 0;
}

.project-card p {
  color: #4b5563;
}

dl {
  display: grid;
  gap: 10px;
}

dl div {
  display: flex;
  justify-content: space-between;
  gap: 12px;
}

dt {
  color: #6b7280;
}

dd {
  margin: 0;
  color: #111827;
}

.section-heading {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: flex-start;
  margin-bottom: 16px;
}

.section-heading h2 {
  margin: 0 0 4px;
}

.section-heading p {
  color: #6b7280;
  font-size: 13px;
}

.switch-field {
  display: flex;
  min-height: 36px;
  justify-content: space-between;
  align-items: center;
}

.switch-field input {
  width: 18px;
  height: 18px;
}

.form-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  align-items: center;
  margin-top: 16px;
}

.form-message {
  margin: 0;
  color: #0f766e;
}

.danger {
  color: #dc2626;
}

.result-panel {
  color: #0f766e;
}

.danger-button {
  color: #b91c1c;
  border-color: #fecaca;
  background: #fff;
}

.danger-button:hover {
  background: #fef2f2;
}

.upload-section {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  align-items: center;
}

.file-input {
  display: none;
}

.file-name {
  color: #4b5563;
  font-size: 14px;
  word-break: break-all;
}

.form-label {
  color: #374151;
  font-size: 14px;
}

.indicator-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.indicator-row {
  display: grid;
  grid-template-columns: 1.4fr 1fr 1fr auto 1fr 0.8fr auto;
  gap: 8px;
  align-items: center;
}

.indicator-equals {
  text-align: center;
  color: #6b7280;
}

.indicator-hint {
  margin: 4px 0 0;
  color: #6b7280;
  font-size: 13px;
}

.muted {
  color: #9ca3af;
  font-size: 13px;
}

@media (max-width: 900px) {
  .indicator-row {
    grid-template-columns: 1fr 1fr;
  }

  .indicator-equals {
    display: none;
  }
}
</style>
