<template>
  <div class="page">
    <header class="page-header">
      <div>
        <h1>项目管理</h1>
        <p>创建并维护营销项目，项目下继续配置指标和分解任务。</p>
      </div>
      <button class="button primary" :disabled="!canCreateProject" @click="openWizard">
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
          <p>分三步完成：填写基础信息 → 配置指标 → 设置分解。</p>
        </div>
        <span class="badge neutral">{{ currentUser.organization }}</span>
      </div>

      <div class="wizard-steps">
        <div class="wizard-step" :class="{ active: currentStep === 1, done: currentStep > 1 }">1 · 基础信息</div>
        <div class="wizard-step" :class="{ active: currentStep === 2, done: currentStep > 2 }">2 · 指标配置</div>
        <div class="wizard-step" :class="{ active: currentStep === 3 }">3 · 分解设置</div>
      </div>

      <!-- 步骤 1：基础信息 -->
      <div v-show="currentStep === 1" class="form-grid">
        <label class="form-field">
          项目名称
          <input v-model.trim="form.name" class="field" placeholder="例如：端午客户拓展项目" />
        </label>
        <label class="form-field">
          项目状态
          <select v-model="form.status" class="select">
            <option v-for="opt in PROJECT_STATUS_OPTIONS" :key="opt.code" :value="opt.code">{{ opt.label }}</option>
          </select>
        </label>
        <label class="form-field">
          项目归属机构
          <input :value="form.ownerOrg" class="field" readonly />
        </label>
        <label class="form-field">
          项目负责人
          <input v-model.trim="form.manager" class="field" placeholder="负责人姓名" />
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

      <!-- 步骤 2：指标配置 -->
      <div v-show="currentStep === 2" class="step-body">
        <div class="step-heading">
          <div>
            <h3>指标配置</h3>
            <p>过程指标用于日常触达，结果指标参与积分和排名。占比合计建议 100%，当前合计 {{ indicatorWeightTotal }}%。</p>
          </div>
        </div>

        <div v-for="(indicator, index) in indicatorList" :key="index" class="indicator-card">
          <div class="indicator-card-head">
            <strong>指标 {{ index + 1 }}</strong>
            <button class="button danger-button" type="button" @click="removeIndicator(index)">删除</button>
          </div>
          <div class="form-grid">
            <label class="form-field">
              指标名称
              <input v-model.trim="indicator.name" class="field" placeholder="例如：定期存款" />
            </label>
            <label class="form-field">
              指标类型
              <select v-model="indicator.indicatorType" class="select">
                <option>过程指标</option>
                <option>结果指标</option>
              </select>
            </label>
            <label class="form-field">
              数值类型
              <select v-model="indicator.valueType" class="select">
                <option>金额</option>
                <option>数量</option>
              </select>
            </label>
            <label class="form-field">
              单位
              <input v-model.trim="indicator.unit" class="field" placeholder="万元 / 户 / 次" />
            </label>
            <label class="form-field">
              权重占比（%）
              <input v-model.number="indicator.weight" class="field" type="number" min="0" max="100" />
            </label>
            <label class="form-field">
              积分标准
              <input v-model.number="indicator.pointRule" class="field" type="number" min="0" step="0.1" />
            </label>
            <label class="form-field">
              达人数量
              <input v-model.number="indicator.talentCount" class="field" type="number" min="0" />
            </label>
            <label class="form-field switch-field">
              大单奖
              <input v-model="indicator.bigOrderEnabled" type="checkbox" />
            </label>
            <label class="form-field">
              大单奖起征点
              <input
                v-model.number="indicator.bigOrderThreshold"
                class="field"
                type="number"
                min="0"
                :disabled="!indicator.bigOrderEnabled"
              />
            </label>
          </div>
        </div>

        <p v-if="!indicatorList.length" class="muted">暂未设置指标，可点击下方按钮添加。</p>
        <button class="button" type="button" @click="addIndicator">新增指标</button>
      </div>

      <!-- 步骤 3：分解设置 -->
      <div v-show="currentStep === 3" class="step-body">
        <div class="step-heading">
          <div>
            <h3>分解设置</h3>
            <p>配置本项目的分解层级、参与范围与上报模板。</p>
          </div>
        </div>

        <div class="config-grid">
          <label class="config-field">
            分解层级规则
            <select v-model="config.decompositionLevel" class="select">
              <option>市行→支行→网点</option>
              <option>市行→支行→员工</option>
              <option>省行→市行→支行→网点</option>
              <option>支行→网点→员工</option>
              <option>直接下发到员工</option>
            </select>
          </label>

          <div class="config-field">
            <div class="form-label">上报指标模板</div>
            <textarea
              v-model="config.reportTemplate"
              class="field"
              rows="3"
              placeholder="说明员工每次上报需填写的字段，例如：日期、客户姓名、金额、凭证照片"
            ></textarea>
          </div>

          <div class="config-field full">
            <div class="form-label">参与机构范围</div>
            <div v-if="availableOrgs.length" class="org-checklist">
              <label v-for="org in availableOrgs" :key="org.id" class="org-check-item">
                <input type="checkbox" :value="org.id" v-model="config.participatingOrgIds" />
                {{ org.name }}
                <span class="org-level-tag">{{ orgLevelLabel(org.level) }}</span>
              </label>
            </div>
            <p v-else class="muted">当前账号下暂无可选机构。</p>
          </div>

          <div class="config-field full">
            <div class="form-label">参与员工范围</div>
            <div class="radio-group">
              <label><input type="radio" v-model="config.employeeScope" value="auto" /> 由参与机构员工自动覆盖</label>
              <label><input type="radio" v-model="config.employeeScope" value="manual" /> 手动指定员工</label>
            </div>
            <textarea
              v-if="config.employeeScope === 'manual'"
              v-model="config.manualEmployees"
              class="field"
              rows="2"
              placeholder="输入员工姓名或工号，多个用逗号分隔"
            ></textarea>
          </div>
        </div>
      </div>

      <!-- 底部导航 -->
      <div class="wizard-actions">
        <button v-if="currentStep > 1" class="button" @click="prevStep">上一步</button>
        <button v-if="currentStep < 3" class="button primary" @click="nextStep">下一步</button>
        <button v-if="currentStep === 3" class="button primary" @click="saveProject">完成创建</button>
        <button class="button" @click="cancelWizard">取消</button>
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
          <router-link v-if="project.canDecompose" class="button" :to="`/projects/${project.id}/decompose`">
            下发分解
          </router-link>
          <button v-else class="button" disabled>待上级下发明细</button>
          <label class="status-select">
            状态
            <select
              v-if="nextStatusOptions(project.statusCode).length"
              class="select"
              :value="''"
              @change="onStatusSelect(project, $event)"
            >
              <option value="" disabled>{{ statusLabels[project.statusCode] || project.status }} ›</option>
              <option v-for="opt in nextStatusOptions(project.statusCode)" :key="opt.code" :value="opt.code">{{ opt.label }}</option>
            </select>
            <span v-else class="status-terminal">{{ statusLabels[project.statusCode] || project.status }} · 终态</span>
          </label>
          <button v-if="project.canDelete" class="button danger-button" @click="removeProject(project)">
            删除项目
          </button>
        </div>
      </article>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { getCurrentUser } from '../auth/permissions'
import { ElMessageBox } from 'element-plus'
import { createProject, deleteProject, getOrganizations, getProjects, saveProjectConfig, setProjectStatus } from '../api/projects'
import { saveIndicators } from '../api/indicators'

const projects = ref([])
const currentUser = getCurrentUser()
const showCreateForm = ref(false)
const currentStep = ref(1)
const message = ref('')
const messageType = ref('success')
const canCreateProject = computed(() =>
  ['总行', '省行', '市行', '支行'].includes(currentUser?.level)
)

function formatDate(date) {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

function addMonths(dateStr, months) {
  if (!dateStr) return ''
  const [year, month, day] = dateStr.split('-').map(Number)
  return formatDate(new Date(year, month - 1 + months, day))
}

const baseForm = () => {
  const startDate = formatDate(new Date())
  return {
    name: '',
    description: '',
    startDate,
    endDate: addMonths(startDate, 2),
    reportDeadline: '00:00',
    attachmentRequired: false,
    status: 'PLANNED',
    attachment: null,
    ownerOrg: currentUser?.organization || '',
    manager: currentUser?.name || ''
  }
}

const baseConfig = () => ({
  decompositionLevel: '市行→支行→网点',
  participatingOrgIds: [],
  employeeScope: 'auto',
  manualEmployees: '',
  reportTemplate: ''
})

const form = reactive(baseForm())
const indicatorList = ref([])
const config = reactive(baseConfig())

// 开始日期变化时，结束日期自动设为其两个月后
watch(() => form.startDate, (value) => {
  form.endDate = addMonths(value, 2)
})

const indicatorWeightTotal = computed(() =>
  indicatorList.value.reduce((sum, indicator) => sum + Number(indicator.weight || 0), 0)
)

function addIndicator() {
  indicatorList.value.push({
    name: '',
    indicatorType: '结果指标',
    valueType: '金额',
    unit: '万元',
    weight: 0,
    pointRule: 0,
    bigOrderEnabled: false,
    bigOrderThreshold: 0,
    talentCount: 0
  })
}

function removeIndicator(index) {
  indicatorList.value.splice(index, 1)
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

// 参与机构范围：来自后端「当前用户可见的机构」（本级 + 下级），id 为后端真实机构 id
const availableOrgs = ref([])

const orgLevelMap = { HEADQUARTERS: '总行', PROVINCE: '省行', CITY: '市行', BRANCH: '支行', OUTLET: '网点' }
function orgLevelLabel(level) {
  return orgLevelMap[level] || level || ''
}

async function loadAvailableOrgs() {
  try {
    availableOrgs.value = await getOrganizations()
  } catch {
    availableOrgs.value = []
  }
}

function validateBaseInfo() {
  if (!form.name) return '项目名称不能为空。'
  if (!form.startDate || !form.endDate) return '项目周期不能为空。'
  if (form.endDate < form.startDate) return '结束日期不能早于开始日期。'
  return ''
}

function nextStep() {
  if (currentStep.value === 1) {
    const error = validateBaseInfo()
    if (error) {
      message.value = error
      messageType.value = 'error'
      return
    }
  }
  message.value = ''
  if (currentStep.value < 3) currentStep.value += 1
}

function prevStep() {
  message.value = ''
  if (currentStep.value > 1) currentStep.value -= 1
}

function resetForm() {
  Object.assign(form, baseForm())
  Object.assign(config, baseConfig())
  indicatorList.value = []
  currentStep.value = 1
  if (fileInput.value) {
    fileInput.value.value = ''
  }
}

function openWizard() {
  resetForm()
  message.value = ''
  showCreateForm.value = true
  loadAvailableOrgs()
}

function cancelWizard() {
  showCreateForm.value = false
  resetForm()
  message.value = ''
}

async function loadProjects() {
  projects.value = await getProjects(currentUser)
}

async function saveProject() {
  const error = validateBaseInfo()
  if (error) {
    currentStep.value = 1
    message.value = error
    messageType.value = 'error'
    return
  }

  try {
    const result = await createProject(
      { ...form, attachment: undefined, visibleOrgIds: config.participatingOrgIds },
      currentUser
    )

    // 详细指标与分解设置按项目 id 持久化
    const indicatorsToSave = indicatorList.value.map((indicator, index) => ({
      ...indicator,
      id: `${result.id}-${index}`,
      projectId: result.id
    }))
    await saveIndicators(result.id, indicatorsToSave)
    await saveProjectConfig(result.id, { ...config })

    await loadProjects()

    message.value = `项目“${result.name}”创建成功。`
    messageType.value = 'success'
    showCreateForm.value = false
    resetForm()
  } catch (err) {
    message.value = err.message || '创建项目失败。'
    messageType.value = 'error'
  }
}

async function removeProject(project) {
  const confirmed = window.confirm(`确定删除项目“${project.name}”吗？`)
  if (!confirmed) return

  try {
    await deleteProject(project.id)
    await loadProjects()
    message.value = `项目“${project.name}”已删除。`
    messageType.value = 'success'
  } catch (err) {
    message.value = err.message
    messageType.value = 'error'
  }
}

// 项目状态：与后端 ProjectStatus 枚举对齐。code 用于提交（新建 / 改状态）与后端 statusCode 比对，label 仅用于显示。
const PROJECT_STATUS_OPTIONS = [
  { code: 'DRAFT', label: '草稿' },
  { code: 'PLANNED', label: '未开始' },
  { code: 'ACTIVE', label: '进行中' },
  { code: 'PAUSED', label: '已暂停' },
  { code: 'COMPLETED', label: '已结束' },
  { code: 'CANCELLED', label: '已取消' }
]
const statusLabels = Object.fromEntries(PROJECT_STATUS_OPTIONS.map((opt) => [opt.code, opt.label]))

// 合法状态流转（状态机），须与后端 ProjectServiceImpl.ALLOWED_TRANSITIONS 一致。
// 状态下拉只列出「当前状态允许的下一步」，从源头杜绝乱跳；终态无下一步。
const ALLOWED_TRANSITIONS = {
  DRAFT: ['PLANNED', 'CANCELLED'],
  PLANNED: ['ACTIVE', 'CANCELLED'],
  ACTIVE: ['PAUSED', 'COMPLETED', 'CANCELLED'],
  PAUSED: ['ACTIVE', 'COMPLETED', 'CANCELLED'],
  COMPLETED: [],
  CANCELLED: []
}
// 终态目标：变更到这两个状态不可逆，需强确认（手输项目名）。
const TERMINAL_TARGETS = ['COMPLETED', 'CANCELLED']

function nextStatusOptions(statusCode) {
  const codes = ALLOWED_TRANSITIONS[statusCode] || []
  return PROJECT_STATUS_OPTIONS.filter((opt) => codes.includes(opt.code))
}

// 选中即把下拉复位回「当前状态」占位（selectedIndex=0），
// 避免未确认时下拉视觉上停在新状态（顶部徽章始终是后端真值，不受影响）。
function onStatusSelect(project, event) {
  const statusCode = event.target.value
  event.target.selectedIndex = 0
  if (statusCode) {
    changeStatus(project, statusCode)
  }
}

async function changeStatus(project, statusCode) {
  if (!statusCode || statusCode === project.statusCode) return

  const label = statusLabels[statusCode] || statusCode

  try {
    if (TERMINAL_TARGETS.includes(statusCode)) {
      // 终态：强确认，要求手输项目完整名称，防误触
      await ElMessageBox.prompt(
        `此操作将把项目「${project.name}」置为「${label}」，终态不可逆。请输入项目完整名称以确认：`,
        '高危操作确认',
        {
          confirmButtonText: '确认变更',
          cancelButtonText: '取消',
          type: 'warning',
          inputPlaceholder: project.name,
          inputValidator: (val) => (val && val.trim() === project.name) || '项目名称不一致，无法确认',
          inputErrorMessage: '项目名称不一致'
        }
      )
    } else {
      // 可逆变更：普通确认弹窗
      await ElMessageBox.confirm(
        `将项目「${project.name}」状态变更为「${label}」？`,
        '确认状态变更',
        { confirmButtonText: '确认', cancelButtonText: '取消', type: 'warning' }
      )
    }
  } catch {
    // 用户取消：下拉已在 onStatusSelect 中复位，徽章仍是后端真值，无需其它处理
    return
  }

  try {
    await setProjectStatus(project.id, statusCode)
    await loadProjects()
    message.value = `项目“${project.name}”状态已更新为「${label}」。`
    messageType.value = 'success'
  } catch (err) {
    message.value = err.message || '更新项目状态失败。'
    messageType.value = 'error'
    await loadProjects()
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

.status-select {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: #6b7280;
}

.status-select .select {
  width: auto;
  min-width: 96px;
  padding: 6px 8px;
}

.status-terminal {
  font-size: 13px;
  color: #9ca3af;
  padding: 6px 8px;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
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

.wizard-steps {
  display: flex;
  gap: 8px;
  margin-bottom: 20px;
}

.wizard-step {
  flex: 1;
  padding: 10px 12px;
  border-radius: 8px;
  background: #f3f4f6;
  color: #6b7280;
  font-size: 14px;
  text-align: center;
}

.wizard-step.active {
  background: #0f766e;
  color: #fff;
}

.wizard-step.done {
  background: #d1fae5;
  color: #065f46;
}

.step-body {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.step-heading h3 {
  margin: 0 0 4px;
  font-size: 15px;
}

.step-heading p {
  margin: 0;
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

.wizard-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  align-items: center;
  margin-top: 20px;
  border-top: 1px solid #e5e7eb;
  padding-top: 16px;
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

.indicator-card {
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 14px;
}

.indicator-card-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.indicator-card-head strong {
  color: #111827;
}

.config-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.config-field {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.config-field.full {
  grid-column: 1 / -1;
}

.org-checklist {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 6px;
  max-height: 220px;
  overflow-y: auto;
  padding: 2px;
}

.org-check-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 14px;
  cursor: pointer;
}

.org-level-tag {
  font-size: 11px;
  color: #6b7280;
  background: #f3f4f6;
  padding: 1px 5px;
  border-radius: 4px;
}

.radio-group {
  display: flex;
  gap: 16px;
  font-size: 14px;
}

.radio-group label {
  display: flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
}

.muted {
  color: #9ca3af;
  font-size: 13px;
}

@media (max-width: 900px) {
  .config-grid {
    grid-template-columns: 1fr;
  }

  .org-checklist {
    grid-template-columns: 1fr;
  }

  .wizard-steps {
    flex-direction: column;
  }
}
</style>
