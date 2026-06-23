<template>
  <div class="page batch-import-page">
    <header class="page-header">
      <div>
        <h1>批量导入人员</h1>
        <p>上传 Excel 文件批量添加员工信息，支持 .xlsx / .xls 格式。</p>
      </div>
    </header>

    <section class="panel upload-section">
      <h3 class="section-title">1. 上传文件</h3>
      <div
        class="upload-zone"
        :class="{ 'is-dragover': isDragOver, 'has-file': parsedData.length > 0 }"
        @dragover.prevent="isDragOver = true"
        @dragleave.prevent="isDragOver = false"
        @drop.prevent="handleDrop"
        @click="triggerFileInput"
      >
        <input ref="fileInputRef" type="file" accept=".xlsx,.xls" class="hidden-input" @change="handleFileSelect" />
        <div v-if="!parsedData.length" class="upload-placeholder">
          <span class="upload-icon">📁</span>
          <p>拖拽 Excel 文件到此处，或点击选择文件</p>
          <span class="upload-hint">支持 .xlsx / .xls 格式</span>
        </div>
        <div v-else class="upload-success">
          <span class="upload-icon">✅</span>
          <p>{{ fileName }}</p>
          <span class="upload-hint">已解析 {{ parsedData.length }} 条记录 · 点击重新选择</span>
        </div>
      </div>

      <div class="template-hint">
        <a href="#" @click.prevent="downloadTemplate">下载 Excel 模板</a>
        <span class="hint-text">模板包含必填字段：姓名、邮箱、职务、所属机构、员工类型（内勤/外勤）、是否管理员</span>
      </div>
    </section>

    <section v-if="parsedData.length" class="panel preview-section">
      <h3 class="section-title">
        2. 数据预览
        <span class="record-count">{{ parsedData.length }} 条记录</span>
      </h3>

      <div class="table-wrapper">
        <table class="preview-table">
          <thead>
            <tr>
              <th>#</th>
              <th>姓名 *</th>
              <th>邮箱 *</th>
              <th>职务</th>
              <th>所属机构 *</th>
              <th>员工类型</th>
              <th>是否管理员</th>
              <th>状态</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="(row, index) in parsedData"
              :key="index"
              :class="{ 'row-error': row._error }"
            >
              <td>{{ index + 1 }}</td>
              <td :class="{ 'cell-error': !row.name }">{{ row.name || '<缺失>' }}</td>
              <td :class="{ 'cell-error': !row.email }">{{ row.email || '<缺失>' }}</td>
              <td>{{ row.position || '—' }}</td>
              <td :class="{ 'cell-error': !row.organization }">{{ row.organization || '<缺失>' }}</td>
              <td>{{ row.workType || '—' }}</td>
              <td>{{ row.isAdmin === true ? '是' : row.isAdmin === false ? '否' : '—' }}</td>
              <td>
                <span v-if="row._error" class="status-error">校验失败</span>
                <span v-else class="status-ok">✓</span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div v-if="errorCount > 0" class="validation-alert">
        ⚠️ {{ errorCount }} 条记录存在必填字段缺失，请修正后重新上传
      </div>
    </section>

    <section v-if="parsedData.length && errorCount === 0" class="panel action-section">
      <div class="action-bar">
        <button class="button secondary" type="button" @click="resetUpload">重新上传</button>
        <button
          class="button primary"
          type="button"
          :disabled="isSubmitting"
          @click="handleSubmit"
        >
          {{ isSubmitting ? '提交中...' : `确认导入 ${validCount} 人` }}
        </button>
      </div>
    </section>

    <section v-if="submitResult" class="panel result-section" :class="submitResult.success ? 'result-success' : 'result-fail'">
      <h3 class="result-title">{{ submitResult.success ? '导入成功' : '导入失败' }}</h3>
      <p class="result-message">{{ submitResult.message }}</p>
      <div v-if="submitResult.details?.length" class="result-details">
        <p v-for="(detail, i) in submitResult.details" :key="i">{{ detail }}</p>
      </div>
      <button v-if="submitResult.success" class="button primary" type="button" @click="goBack">
        返回人员管理
      </button>
    </section>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import * as XLSX from 'xlsx'

const router = useRouter()

const fileInputRef = ref(null)
const isDragOver = ref(false)
const fileName = ref('')
const parsedData = ref([])
const isSubmitting = ref(false)
const submitResult = ref(null)

const errorCount = computed(() => parsedData.value.filter((r) => r._error).length)
const validCount = computed(() => parsedData.value.filter((r) => !r._error).length)

function triggerFileInput() {
  fileInputRef.value?.click()
}

function handleDrop(e) {
  isDragOver.value = false
  const files = e.dataTransfer?.files
  if (files?.[0]) {
    processFile(files[0])
  }
}

function handleFileSelect(e) {
  const files = e.target?.files
  if (files?.[0]) {
    processFile(files[0])
  }
}

function processFile(file) {
  const validTypes = [
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'application/vnd.ms-excel'
  ]

  if (!validTypes.includes(file.type) && !file.name.match(/\.xlsx?$/i)) {
    submitResult.value = { success: false, message: '不支持的文件格式，请上传 .xlsx 或 .xls 文件' }
    return
  }

  fileName.value = file.name
  submitResult.value = null

  const reader = new FileReader()
  reader.onload = (e) => {
    try {
      const data = new Uint8Array(e.target.result)
      const workbook = XLSX.read(data, { type: 'array' })
      const firstSheet = workbook.Sheets[workbook.SheetNames[0]]
      const jsonData = XLSX.utils.sheet_to_json(firstSheet, { defval: '' })

      parsedData.value = jsonData.map((row) => {
        const name = String(row['姓名'] || row['name'] || '').trim()
        const email = String(row['邮箱'] || row['email'] || '').trim()
        const organization = String(row['所属机构'] || row['organization'] || row['organizationName'] || '').trim()
        const _error = !name || !email || !organization

        return {
          name,
          email,
          position: String(row['职务'] || row['position'] || '').trim(),
          organization,
          workType: normalizeWorkType(row['员工类型'] || row['workType'] || ''),
          isAdmin: parseBool(row['是否管理员'] || row['isAdmin']),
          _error
        }
      })

      if (!parsedData.value.length) {
        submitResult.value = { success: false, message: 'Excel 文件中没有找到有效数据行' }
      }
    } catch (err) {
      submitResult.value = { success: false, message: `文件解析失败: ${err.message}` }
    }
  }

  reader.readAsArrayBuffer(file)
}

function normalizeWorkType(val) {
  const s = String(val || '').trim()
  if (!s) return ''
  if (s.includes('内勤')) return '内勤'
  if (s.includes('外勤')) return '外勤'
  return s
}

function parseBool(val) {
  if (val === true || val === false) return val
  const s = String(val || '').trim().toLowerCase()
  if (s === 'true' || s === '是' || s === '1' || s === 'yes') return true
  if (s === 'false' || s === '否' || s === '0' || s === 'no') return false
  return undefined
}

function downloadTemplate() {
  const headers = ['姓名', '邮箱', '职务', '所属机构', '员工类型', '是否管理员']
  const sample = [['张三', 'zhangsan@bank.com', '客户经理', '南京市行鼓楼支行', '内勤', '否']]
  const ws = XLSX.utils.aoa_to_sheet([headers, ...sample])
  const wb = XLSX.utils.book_new()
  XLSX.utils.book_append_sheet(wb, ws, '人员导入模板')
  XLSX.writeFile(wb, '人员导入模板.xlsx')
}

function resetUpload() {
  parsedData.value = []
  fileName.value = ''
  submitResult.value = null
  if (fileInputRef.value) {
    fileInputRef.value.value = ''
  }
}

async function handleSubmit() {
  if (validCount.value === 0) return

  isSubmitting.value = true
  submitResult.value = null

  try {
    const payload = parsedData.value
      .filter((r) => !r._error)
      .map((r) => ({
        name: r.name,
        email: r.email,
        position: r.position || null,
        organizationName: r.organization,
        workType: r.workType || null,
        isAdmin: Boolean(r.isAdmin),
        isNew: true
      }))

    const response = await fetch('/api/admin/employees/batch', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Auth-Token': localStorage.getItem('authToken') || ''
      },
      body: JSON.stringify(payload)
    })

    if (!response.ok) {
      const errData = await response.json().catch(() => ({}))
      throw new Error(errData.message || `请求失败 (${response.status})`)
    }

    const result = await response.json()

    submitResult.value = {
      success: true,
      message: `成功导入 ${payload.length} 名员工`,
      details: result.details || []
    }
  } catch (err) {
    submitResult.value = {
      success: false,
      message: err.message || '提交失败，请稍后重试'
    }
  } finally {
    isSubmitting.value = false
  }
}

function goBack() {
  router.push('/users')
}
</script>

<style scoped>
.batch-import-page {
  max-width: 960px;
}

.section-title {
  margin: 0 0 14px;
  font-size: 15px;
  font-weight: 600;
  color: #374151;
  display: flex;
  align-items: center;
  gap: 10px;
}

.record-count {
  font-size: 12px;
  font-weight: 400;
  color: #6b7280;
  background: #f3f4f6;
  padding: 2px 10px;
  border-radius: 999px;
}

.upload-section {
  margin-bottom: 20px;
}

.upload-zone {
  border: 2px dashed #d1d5db;
  border-radius: 12px;
  padding: 48px 24px;
  text-align: center;
  cursor: pointer;
  transition: all 0.25s ease;
  background: #fafbfc;
}

.upload-zone:hover {
  border-color: #0f766e;
  background: #f0fdfa;
}

.upload-zone.is-dragover {
  border-color: #0f766e;
  background: #ccfbf1;
  transform: scale(1.01);
}

.upload-zone.has-file {
  border-color: #059669;
  border-style: solid;
  background: #ecfdf5;
}

.hidden-input {
  display: none;
}

.upload-placeholder,
.upload-success {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}

.upload-icon {
  font-size: 40px;
}

.upload-placeholder p,
.upload-success p {
  margin: 0;
  font-size: 15px;
  color: #374151;
  font-weight: 500;
}

.upload-hint {
  font-size: 12px;
  color: #9ca3af;
}

.template-hint {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 12px;
  padding: 10px 14px;
  background: #f8fafc;
  border-radius: 8px;
  font-size: 13px;
}

.template-hint a {
  color: #0369a1;
  font-weight: 600;
  white-space: nowrap;
  text-decoration: none;
}

.template-hint a:hover {
  text-decoration: underline;
}

.hint-text {
  color: #6b7280;
}

.preview-section {
  margin-bottom: 20px;
}

.table-wrapper {
  overflow-x: auto;
  max-height: 400px;
  overflow-y: auto;
}

.preview-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}

.preview-table th {
  position: sticky;
  top: 0;
  z-index: 1;
  background: #f9fafb;
  padding: 10px 12px;
  text-align: left;
  font-weight: 600;
  color: #374151;
  border-bottom: 2px solid #e5e7eb;
  white-space: nowrap;
}

.preview-table td {
  padding: 8px 12px;
  border-bottom: 1px solid #f3f4f6;
  color: #1f2937;
  white-space: nowrap;
}

.preview-table tr:hover {
  background: #f8fafc;
}

.row-error {
  background: #fef2f2;
}

.cell-error {
  color: #dc2626;
  font-weight: 600;
}

.status-error {
  color: #dc2626;
  font-size: 11px;
  font-weight: 600;
}

.status-ok {
  color: #059669;
  font-weight: 700;
}

.validation-alert {
  margin-top: 12px;
  padding: 10px 14px;
  background: #fef3c7;
  color: #92400e;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 500;
}

.action-section {
  margin-bottom: 20px;
}

.action-bar {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

.action-bar button {
  min-width: 140px;
}

.result-section {
  margin-bottom: 20px;
  padding: 20px 24px;
  border-radius: 10px;
}

.result-success {
  background: #ecfdf5;
  border: 1px solid #a7f3d0;
}

.result-fail {
  background: #fef2f2;
  border: 1px solid #fecaca;
}

.result-title {
  margin: 0 0 8px;
  font-size: 16px;
  font-weight: 700;
}

.result-success .result-title {
  color: #065f46;
}

.result-fail .result-title {
  color: #991b1b;
}

.result-message {
  margin: 0 0 12px;
  font-size: 14px;
  color: #374151;
}

.result-details {
  font-size: 13px;
  color: #6b7280;
  line-height: 1.7;
  margin-bottom: 16px;
}

.result-details p {
  margin: 2px 0;
}
</style>