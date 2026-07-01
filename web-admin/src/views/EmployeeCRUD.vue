<template>
  <div class="page employee-crud-page" v-loading="loading">
    <header class="page-header">
      <div>
        <h1>人员管理</h1>
        <p>新增、编辑、删除和查询员工信息（数据来自后端数据库）。</p>
      </div>
      <div class="header-actions">
        <router-link class="button" to="/users">← 返回人员列表</router-link>
        <button class="button" type="button" :disabled="loading" @click="handleExport">导出 Excel</button>
        <button class="button" type="button" @click="openImportDialog">批量导入</button>
        <button class="button primary" type="button" @click="openAddDialog">+ 新增人员</button>
      </div>
    </header>

    <p v-if="message" :class="['status-message', messageType]">{{ message }}</p>

    <section class="panel toolbar">
      <input
        v-model="searchKeyword"
        type="text"
        class="field search-field"
        placeholder="搜索姓名、邮箱..."
        style="max-width: 260px"
      />
      <select v-model="filterOrg" class="select">
        <option value="">全部机构</option>
        <option v-for="org in orgFilterOptions" :key="org" :value="org">{{ org }}</option>
      </select>
      <select v-model="filterWorkType" class="select">
        <option value="">内勤/外勤</option>
        <option value="内勤">内勤</option>
        <option value="外勤">外勤</option>
      </select>
      <select v-model="filterIsAdmin" class="select">
        <option value="">全部权限</option>
        <option value="true">管理员</option>
        <option value="false">普通员工</option>
      </select>
      <span class="result-count">共 {{ filteredEmployees.length }} 条</span>
    </section>

    <section class="panel">
      <table class="table">
        <thead>
          <tr>
            <th>#</th>
            <th>姓名</th>
            <th>邮箱</th>
            <th>职务</th>
            <th>所属机构</th>
            <th>员工类型</th>
            <th>权限</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(emp, index) in pagedEmployees" :key="emp.id">
            <td>{{ startIndex + index + 1 }}</td>
            <td><strong>{{ emp.name }}</strong></td>
            <td>{{ emp.email }}</td>
            <td>{{ emp.position || '—' }}</td>
            <td>{{ emp.organization || '—' }}</td>
            <td>{{ emp.workType || '—' }} · {{ emp.isNew ? '新员工' : '非新' }}</td>
            <td>
              <span :class="['badge', emp.isAdmin ? 'badge-admin' : 'badge-normal']">
                {{ emp.isAdmin ? '管理员' : '普通员工' }}
              </span>
            </td>
            <td class="action-cell">
              <button class="btn-sm btn-edit" type="button" @click="openEditDialog(emp)">编辑</button>
              <button class="btn-sm btn-delete" type="button" @click="confirmDelete(emp)">删除</button>
            </td>
          </tr>
          <tr v-if="!pagedEmployees.length && !loading">
            <td colspan="8" class="empty-row">暂无数据</td>
          </tr>
        </tbody>
      </table>

      <div v-if="totalPages > 1" class="pagination-bar">
        <button class="btn-page" type="button" :disabled="currentPage === 1" @click="currentPage--">上一页</button>
        <span class="page-info">{{ currentPage }} / {{ totalPages }}</span>
        <button class="btn-page" type="button" :disabled="currentPage === totalPages" @click="currentPage++">下一页</button>
      </div>
    </section>

    <el-dialog
      v-model="dialogVisible"
      :title="isEditing ? '编辑人员' : '新增人员'"
      width="580px"
      :close-on-click-modal="false"
      destroy-on-close
    >
      <form class="employee-form" @submit.prevent="handleSubmit">
        <div class="form-group">
          <label class="form-label"><span class="required">*</span> 姓名</label>
          <input v-model="formData.name" type="text" class="field" placeholder="请输入姓名" required />
        </div>
        <div class="form-group">
          <label class="form-label"><span class="required">*</span> 邮箱</label>
          <input v-model="formData.email" type="email" class="field" placeholder="请输入邮箱" required />
        </div>
        <div class="form-group">
          <label class="form-label">职务</label>
          <input v-model="formData.position" type="text" class="field" placeholder="如：客户经理、柜员" />
        </div>
        <div class="form-row">
          <div class="form-group">
            <label class="form-label">年龄</label>
            <input v-model.number="formData.age" type="number" min="18" max="70" class="field" placeholder="如：28" />
          </div>
          <div class="form-group">
            <label class="form-label">部门</label>
            <input v-model="formData.department" type="text" class="field" placeholder="如：个人金融部" />
          </div>
        </div>
        <div class="form-group">
          <label class="form-label"><span class="required">*</span> 所属机构</label>
          <select v-model="formData.organizationId" class="field select-field" required>
            <option value="">请选择机构</option>
            <option v-for="org in organizations" :key="org.id" :value="String(org.id)">
              {{ org.name }}
            </option>
          </select>
        </div>
        <div class="form-row">
          <div class="form-group">
            <label class="form-label">员工类型</label>
            <select v-model="formData.workType" class="field select-field">
              <option value="">请选择</option>
              <option value="内勤">内勤</option>
              <option value="外勤">外勤</option>
            </select>
          </div>
          <div class="form-group">
            <label class="form-label">是否管理员</label>
            <select v-model="formData.isAdmin" class="field select-field">
              <option :value="false">否</option>
              <option :value="true">是</option>
            </select>
          </div>
        </div>
        <p class="form-hint">层级（员工/网点/支行/市行）将根据「是否管理员」与「所属机构」自动设置，无需填写职务推断。</p>
        <div class="form-group">
          <label class="form-label">是否参与项目</label>
          <select v-model="formData.isInProject" class="field select-field">
            <option :value="false">否</option>
            <option :value="true">是</option>
          </select>
        </div>
        <div class="form-group">
          <label class="form-label">是否新员工</label>
          <select v-model="formData.isNew" class="field select-field">
            <option :value="false">否</option>
            <option :value="true">是</option>
          </select>
        </div>
      </form>

      <template #footer>
        <button class="button secondary" type="button" @click="dialogVisible = false">取消</button>
        <button class="button primary" type="button" :disabled="!formValid || saving" @click="handleSubmit">
          {{ saving ? '保存中…' : isEditing ? '保存修改' : '确认新增' }}
        </button>
      </template>
    </el-dialog>

    <el-dialog
      v-model="importDialogVisible"
      title="批量导入员工"
      width="760px"
      :close-on-click-modal="false"
      destroy-on-close
    >
      <div class="import-steps">
        <section class="import-step">
          <h3>1. 下载导入模板</h3>
          <p class="import-desc">
            请用 Microsoft Excel 打开模板（不要用 Numbers）。层级无需填写，系统按「是否管理员 + 所属机构」自动推断。填写后删除或覆盖「示例员工」行再上传。
          </p>
          <button class="button primary" type="button" :disabled="importing" @click="handleDownloadTemplate">
            下载 Excel 模板
          </button>
        </section>

        <section class="import-step">
          <h3>2. 填写后上传</h3>
          <div
            class="drop-zone"
            :class="{ 'drop-active': isDragOver }"
            @dragover.prevent="isDragOver = true"
            @dragleave.prevent="isDragOver = false"
            @drop.prevent="handleImportFileDrop"
            @click="importFileInputRef?.click()"
          >
            <input
              ref="importFileInputRef"
              type="file"
              accept=".xlsx,.xls"
              class="hidden-input"
              @change="handleImportFileSelect"
            />
            <span class="drop-icon">{{ isDragOver ? '📥' : '📄' }}</span>
            <p>{{ importFileName || (isDragOver ? '松开以上传' : '拖拽已填写的 Excel 到此处，或点击选择') }}</p>
            <span class="drop-hint">支持 .xlsx / .xls，上传后自动解析并预览</span>
          </div>
        </section>

        <section v-if="importPreview.length" class="import-step">
          <h3>3. 预览解析结果</h3>
          <p class="import-summary">
            共 {{ importPreview.length }} 条，有效 {{ importValidCount }} 条，无效 {{ importInvalidCount }} 条
          </p>
          <p v-if="importInvalidCount > 0" class="import-warning">
            存在无效记录，请修正 Excel 后重新上传；仅当全部有效时才可确认导入。
          </p>
          <div class="preview-table-wrap">
            <table class="preview-table">
              <thead>
                <tr>
                  <th>行号</th>
                  <th>姓名</th>
                  <th>邮箱</th>
                  <th>职务</th>
                  <th>所属机构</th>
                  <th>部门</th>
                  <th>层级（自动）</th>
                  <th>员工类型</th>
                  <th>状态</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="row in importPreview" :key="row.rowIndex" :class="{ 'row-invalid': !row.valid }">
                  <td>{{ row.rowIndex }}</td>
                  <td>{{ row.name || '—' }}</td>
                  <td>{{ row.email || '—' }}</td>
                  <td>{{ row.position || '—' }}</td>
                  <td>{{ row.organizationName || '—' }}</td>
                  <td>{{ row.department || '—' }}</td>
                  <td>{{ row.level ? formatLevelLabel(row.level) : '—' }}</td>
                  <td>{{ row.workType || '—' }}</td>
                  <td>{{ row.valid ? '✓ 可导入' : row.errorMessage }}</td>
                </tr>
              </tbody>
            </table>
          </div>
          <button
            v-if="importValidCount === 1"
            class="button secondary fill-form-btn"
            type="button"
            @click="fillFormFromPreview"
          >
            使用首条有效记录填入新增表单
          </button>
        </section>
      </div>

      <template #footer>
        <button class="button secondary" type="button" @click="closeImportDialog">取消</button>
        <button
          class="button primary"
          type="button"
          :disabled="!importFile || importValidCount === 0 || importInvalidCount > 0 || importing"
          @click="confirmImport"
        >
          {{ importing ? '导入中…' : `确认导入（${importValidCount} 条）` }}
        </button>
      </template>
    </el-dialog>

    <el-dialog
      v-model="deleteConfirmVisible"
      title="确认删除"
      width="400px"
    >
      <p class="delete-confirm-text">
        确定要删除员工 <strong>{{ deleteTarget?.name }}</strong> 吗？此操作不可撤销。
      </p>
      <template #footer>
        <button class="button secondary" type="button" @click="deleteConfirmVisible = false">取消</button>
        <button class="button danger" type="button" :disabled="saving" @click="handleDelete">确认删除</button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { ElDialog } from 'element-plus'
import { getOrganizations } from '../api/organization'
import {
  createEmployee,
  deleteEmployee,
  downloadEmployeeImportTemplate,
  exportEmployeesExcel,
  getUsers,
  importEmployeesExcel,
  previewEmployeesImport,
  updateEmployee
} from '../api/users'

const employees = ref([])
const organizations = ref([])
const loading = ref(false)
const saving = ref(false)
const message = ref('')
const messageType = ref('success')

const searchKeyword = ref('')
const filterOrg = ref('')
const filterWorkType = ref('')
const filterIsAdmin = ref('')
const currentPage = ref(1)
const pageSize = 10

const dialogVisible = ref(false)
const isEditing = ref(false)
const editingId = ref(null)

const formData = reactive({
  name: '',
  email: '',
  position: '',
  age: null,
  department: '',
  organizationId: '',
  workType: '',
  isAdmin: false,
  isNew: true,
  isInProject: false
})

const deleteConfirmVisible = ref(false)
const deleteTarget = ref(null)

const importDialogVisible = ref(false)
const importFileInputRef = ref(null)
const importFile = ref(null)
const importFileName = ref('')
const importPreview = ref([])
const importValidCount = ref(0)
const importInvalidCount = ref(0)
const importing = ref(false)
const isDragOver = ref(false)

const orgFilterOptions = computed(() =>
  [...new Set(employees.value.map((e) => e.organization).filter(Boolean))].sort((a, b) =>
    a.localeCompare(b, 'zh-Hans-CN')
  )
)

const filteredEmployees = computed(() => {
  let list = employees.value

  if (searchKeyword.value.trim()) {
    const kw = searchKeyword.value.trim().toLowerCase()
    list = list.filter(
      (e) => e.name.toLowerCase().includes(kw) || e.email.toLowerCase().includes(kw)
    )
  }

  if (filterOrg.value) {
    list = list.filter((e) => e.organization === filterOrg.value)
  }

  if (filterWorkType.value) {
    list = list.filter((e) => e.workType === filterWorkType.value)
  }

  if (filterIsAdmin.value !== '') {
    const admin = filterIsAdmin.value === 'true'
    list = list.filter((e) => Boolean(e.isAdmin) === admin)
  }

  return list
})

const totalPages = computed(() => Math.max(1, Math.ceil(filteredEmployees.value.length / pageSize)))
const startIndex = computed(() => (currentPage.value - 1) * pageSize)
const pagedEmployees = computed(() =>
  filteredEmployees.value.slice(startIndex.value, startIndex.value + pageSize)
)

const formValid = computed(() => {
  return formData.name.trim() && formData.email.trim() && formData.organizationId
})

watch([searchKeyword, filterOrg, filterWorkType, filterIsAdmin], () => {
  currentPage.value = 1
})

function showMessage(text, type = 'success') {
  message.value = text
  messageType.value = type
}

function formatLevelLabel(level) {
  const map = {
    EMPLOYEE: '员工',
    OUTLET: '网点',
    BRANCH: '支行',
    CITY: '市行'
  }
  return map[level] || level
}

function resetForm() {
  formData.name = ''
  formData.email = ''
  formData.position = ''
  formData.age = null
  formData.department = ''
  formData.organizationId = ''
  formData.workType = ''
  formData.isAdmin = false
  formData.isNew = true
  formData.isInProject = false
}

async function loadOrganizations() {
  try {
    const list = await getOrganizations()
    organizations.value = (list || []).slice().sort((a, b) => a.name.localeCompare(b.name, 'zh-Hans-CN'))
  } catch (err) {
    showMessage(err.message || '加载机构列表失败', 'error')
  }
}

async function loadEmployees() {
  loading.value = true
  try {
    employees.value = await getUsers()
  } catch (err) {
    showMessage(err.message || '加载员工列表失败', 'error')
  } finally {
    loading.value = false
  }
}

function openAddDialog() {
  isEditing.value = false
  editingId.value = null
  resetForm()
  message.value = ''
  dialogVisible.value = true
}

function openEditDialog(emp) {
  isEditing.value = true
  editingId.value = emp.id
  formData.name = emp.name || ''
  formData.email = emp.email || ''
  formData.position = emp.position || ''
  formData.age = emp.age ?? null
  formData.department = emp.department || ''
  formData.organizationId = emp.organizationId != null ? String(emp.organizationId) : ''
  formData.workType = emp.workType || ''
  formData.isAdmin = Boolean(emp.isAdmin)
  formData.isNew = Boolean(emp.isNew)
  formData.isInProject = Boolean(emp.isInProject ?? emp.joinedProject)
  message.value = ''
  dialogVisible.value = true
}

async function handleSubmit() {
  if (!formValid.value || saving.value) return

  saving.value = true
  try {
    const payload = {
      name: formData.name.trim(),
      email: formData.email.trim(),
      position: formData.position.trim(),
      age: formData.age === '' || formData.age == null ? null : Number(formData.age),
      department: formData.department.trim(),
      organizationId: Number(formData.organizationId),
      workType: formData.workType || null,
      isAdmin: formData.isAdmin,
      isNew: formData.isNew,
      isInProject: formData.isInProject
    }

    if (isEditing.value && editingId.value) {
      await updateEmployee(editingId.value, payload)
      showMessage('员工信息已更新。')
    } else {
      await createEmployee(payload)
      showMessage('员工已新增。')
    }

    dialogVisible.value = false
    await loadEmployees()
  } catch (err) {
    showMessage(err.message || '保存失败', 'error')
  } finally {
    saving.value = false
  }
}

function confirmDelete(emp) {
  deleteTarget.value = emp
  deleteConfirmVisible.value = true
}

async function handleDelete() {
  if (!deleteTarget.value || saving.value) return

  saving.value = true
  try {
    await deleteEmployee(deleteTarget.value.id)
    deleteConfirmVisible.value = false
    deleteTarget.value = null
    showMessage('员工已删除。')
    await loadEmployees()

    if (!pagedEmployees.value.length && currentPage.value > 1) {
      currentPage.value--
    }
  } catch (err) {
    showMessage(err.message || '删除失败', 'error')
  } finally {
    saving.value = false
  }
}

async function handleExport() {
  try {
    await exportEmployeesExcel()
    showMessage('员工数据已导出。')
  } catch (err) {
    showMessage(err.message || '导出失败', 'error')
  }
}

function openImportDialog() {
  importDialogVisible.value = true
  importFile.value = null
  importFileName.value = ''
  importPreview.value = []
  importValidCount.value = 0
  importInvalidCount.value = 0
  isDragOver.value = false
}

function closeImportDialog() {
  importDialogVisible.value = false
  importFile.value = null
  importFileName.value = ''
  importPreview.value = []
  importValidCount.value = 0
  importInvalidCount.value = 0
  isDragOver.value = false
}

async function handleDownloadTemplate() {
  try {
    await downloadEmployeeImportTemplate()
    showMessage('模板已下载，请填写「员工导入」Sheet 后上传。')
  } catch (err) {
    showMessage(err.message || '模板下载失败', 'error')
  }
}

function handleImportFileDrop(e) {
  isDragOver.value = false
  const file = e.dataTransfer?.files?.[0]
  if (file) processImportFile(file)
}

function handleImportFileSelect(e) {
  const file = e.target?.files?.[0]
  if (file) processImportFile(file)
  e.target.value = ''
}

async function processImportFile(file) {
  const name = file.name.toLowerCase()
  if (!name.endsWith('.xlsx') && !name.endsWith('.xls')) {
    showMessage('请上传 .xlsx 或 .xls 格式的 Excel 文件', 'error')
    return
  }

  importing.value = true
  try {
    const preview = await previewEmployeesImport(file)
    importFile.value = file
    importFileName.value = file.name
    importPreview.value = preview?.items || []
    importValidCount.value = preview?.validCount ?? 0
    importInvalidCount.value = preview?.invalidCount ?? 0

    if (!importPreview.value.length) {
      showMessage('未解析到有效数据行，请检查模板格式', 'error')
    }
  } catch (err) {
    importFile.value = null
    importFileName.value = ''
    importPreview.value = []
    importValidCount.value = 0
    importInvalidCount.value = 0
    showMessage(err.message || '文件解析失败', 'error')
  } finally {
    importing.value = false
    isDragOver.value = false
  }
}

async function confirmImport() {
  if (!importFile.value || importValidCount.value === 0 || importing.value) return

  importing.value = true
  try {
    const result = await importEmployeesExcel(importFile.value)
    closeImportDialog()
    showMessage(typeof result === 'string' ? result : `成功导入 ${importValidCount.value} 名员工`)
    await loadEmployees()
  } catch (err) {
    showMessage(err.message || '导入失败', 'error')
  } finally {
    importing.value = false
  }
}

function fillFormFromPreview() {
  const row = importPreview.value.find((item) => item.valid)
  if (!row) return

  isEditing.value = false
  editingId.value = null
  formData.name = row.name || ''
  formData.email = row.email || ''
  formData.position = row.position || ''
  formData.age = row.age ?? null
  formData.department = row.department || ''
  formData.organizationId = row.organizationId != null ? String(row.organizationId) : ''
  formData.workType = row.workType || ''
  formData.isAdmin = Boolean(row.isAdmin)
  formData.isNew = row.isNew == null ? true : Boolean(row.isNew)
  formData.isInProject = Boolean(row.isInProject)

  closeImportDialog()
  dialogVisible.value = true
  showMessage('已将导入预览填入新增表单，确认无误后点击「确认新增」。')
}

onMounted(async () => {
  await Promise.all([loadOrganizations(), loadEmployees()])
})
</script>

<style scoped>
.employee-crud-page {
  width: 100%;
}

.header-actions {
  display: flex;
  gap: 10px;
  align-items: center;
}

.header-actions a.button {
  display: inline-flex;
  align-items: center;
  text-decoration: none;
  box-sizing: border-box;
}

.status-message {
  margin: 0 0 12px;
  padding: 10px 14px;
  border-radius: 8px;
  font-size: 13px;
}

.status-message.success {
  background: #ecfdf5;
  color: #047857;
  border: 1px solid #a7f3d0;
}

.status-message.error {
  background: #fef2f2;
  color: #b91c1c;
  border: 1px solid #fecaca;
}

.toolbar {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.search-field {
  flex: 0 1 220px;
}

.result-count {
  margin-left: auto;
  font-size: 12px;
  color: #6b7280;
  white-space: nowrap;
}

.action-cell {
  white-space: nowrap;
}

.btn-sm {
  padding: 4px 12px;
  font-size: 12px;
  border-radius: 6px;
  cursor: pointer;
  border: 1px solid transparent;
  transition: all 0.2s ease;
}

.btn-edit {
  background: #eff6ff;
  color: #2563eb;
  border-color: #bfdbfe;
}

.btn-edit:hover {
  background: #dbeafe;
}

.btn-delete {
  background: #fef2f2;
  color: #dc2626;
  border-color: #fecaca;
  margin-left: 6px;
}

.btn-delete:hover {
  background: #fee2e2;
}

.empty-row {
  text-align: center;
  color: #9ca3af;
  padding: 32px 0 !important;
  font-size: 14px;
}

.pagination-bar {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 16px;
  padding-top: 16px;
  margin-top: 12px;
  border-top: 1px solid #f3f4f6;
}

.btn-page {
  padding: 6px 16px;
  font-size: 13px;
  border-radius: 6px;
  cursor: pointer;
  background: #fff;
  border: 1px solid #d1d5db;
  color: #374151;
  transition: all 0.15s ease;
}

.btn-page:hover:not(:disabled) {
  background: #f3f4f6;
  border-color: #9ca3af;
}

.btn-page:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.page-info {
  font-size: 13px;
  color: #6b7280;
  min-width: 60px;
  text-align: center;
}

.employee-form {
  display: grid;
  gap: 16px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.form-label {
  font-size: 13px;
  font-weight: 600;
  color: #374151;
}

.required {
  color: #dc2626;
  margin-right: 2px;
}

.form-hint {
  margin: 0;
  font-size: 12px;
  color: #6b7280;
  line-height: 1.5;
}

.select-field {
  appearance: auto;
}

.badge-admin {
  background: #fef3c7;
  color: #92400e;
}

.badge-normal {
  background: #f3f4f6;
  color: #4b5563;
}

.delete-confirm-text {
  font-size: 14px;
  color: #374151;
  line-height: 1.6;
}

.delete-confirm-text strong {
  color: #dc2626;
}

.danger {
  background: #dc2626;
  color: #fff;
  border-color: #dc2626;
}

.danger:hover {
  background: #b91c1c;
}

.upload-area {
  margin-bottom: 18px;
}

.upload-tip {
  font-size: 12px;
  color: #6b7280;
  text-align: center;
  margin: 0 0 10px;
}

.drop-zone {
  border: 2px dashed #d1d5db;
  border-radius: 10px;
  padding: 24px 16px;
  text-align: center;
  cursor: pointer;
  transition: all 0.2s ease;
  background: #fafbfc;
}

.drop-zone:hover {
  border-color: #0f766e;
  background: #f0fdfa;
}

.drop-zone.drop-active {
  border-color: #059669;
  background: #d1fae5;
  transform: scale(1.01);
}

.hidden-input {
  display: none;
}

.drop-icon {
  font-size: 28px;
  display: block;
  margin-bottom: 6px;
}

.drop-zone p {
  margin: 0 0 6px;
  font-size: 13px;
  color: #374151;
}

.drop-hint {
  font-size: 11px;
  color: #9ca3af;
}

.import-steps {
  display: grid;
  gap: 20px;
}

.import-step h3 {
  margin: 0 0 8px;
  font-size: 15px;
  color: #111827;
}

.import-desc,
.import-summary {
  margin: 0 0 12px;
  font-size: 13px;
  color: #6b7280;
  line-height: 1.5;
}

.import-warning {
  margin: 0 0 12px;
  font-size: 13px;
  color: #b45309;
  line-height: 1.5;
}

.preview-table-wrap {
  max-height: 280px;
  overflow: auto;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
}

.preview-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
}

.preview-table th,
.preview-table td {
  padding: 8px 10px;
  border-bottom: 1px solid #f3f4f6;
  text-align: left;
  white-space: nowrap;
}

.preview-table th {
  background: #f9fafb;
  font-weight: 600;
  position: sticky;
  top: 0;
  z-index: 1;
}

.row-invalid {
  background: #fef2f2;
}

.row-invalid td {
  color: #b91c1c;
}

.fill-form-btn {
  margin-top: 12px;
}

@media (max-width: 640px) {
  .form-row {
    grid-template-columns: 1fr;
  }

  .header-actions {
    flex-direction: column;
    align-items: stretch;
  }
}
</style>
