<template>
  <div class="training-new">
    <el-tabs v-model="activeTab" class="training-tabs">
      <!-- 新建训练标签页 -->
      <el-tab-pane label="新建训练" name="new">
        <!-- 第一行：左右两列 -->
        <el-row :gutter="24">
          <!-- 左侧列：模型配置 + 进度条 + 日志 -->
          <el-col :xs="24" :md="12">
            <!-- 1. 模型配置卡片（始终显示） -->
            <el-card class="glass-card config-card" shadow="never">
              <template #header>
                <div class="card-header">
                  <span><el-icon><Setting/></el-icon> 模型配置</span>
                  <div>
                    <el-button link @click="openTemplateManager">加载预设</el-button>
                    <el-button link @click="saveAsPreset">保存模板</el-button>
                  </div>
                </div>
              </template>
              <TrainingParams ref="paramsRef"/>
            </el-card>

            <!-- 2. 训练进度条卡片（仅当有任务时显示） -->
            <el-card v-if="currentTaskId" class="glass-card progress-card" shadow="never">
              <template #header>
                <span><el-icon><TrendCharts/></el-icon> 训练进度</span>
              </template>
              <ProgressIndicator :task-id="currentTaskId" @completed="onTrainingCompleted"/>
            </el-card>

            <!-- 3. 实时日志卡片（仅当有任务时显示） -->
            <el-card v-if="currentTaskId" class="glass-card log-card" shadow="never">
              <template #header>
                <span><el-icon><Document/></el-icon> 实时日志</span>
                <el-button link @click="logs = ''">清空</el-button>
              </template>
              <div class="log-container" ref="logContainer">
                <pre>{{ logs }}</pre>
              </div>
            </el-card>
          </el-col>

          <!-- 右侧列：数据源 + 预览（始终显示） -->
          <el-col :xs="24" :md="12">
            <el-card class="glass-card data-card" shadow="never">
              <template #header>
                <span><el-icon><FolderOpened/></el-icon> 数据源</span>
              </template>
              <FileSelector v-model="selectedPath" @preview="handleFilePreview"/>
              <el-divider/>
              <div class="data-preview">
                <div class="preview-header">
                  <el-button size="small" @click="previewData" :loading="previewLoading">
                    <el-icon>
                      <View/>
                    </el-icon>
                    预览前100行
                  </el-button>
                  <span v-if="previewType === 'table' && previewRows.length" class="hint">
                    已加载 {{ previewRows.length }} 行
                  </span>
                </div>

                <!-- 图片预览 -->
                <div v-if="previewType === 'image'" class="image-preview">
                  <el-image
                      :src="previewImageSrc"
                      :preview-src-list="[previewImageSrc]"
                      fit="contain"
                      style="max-width: 100%; max-height: 300px; cursor: pointer;"
                  />
                </div>

                <!-- 表格预览 -->
                <el-table
                    v-else-if="previewType === 'table' && previewRows.length"
                    :data="previewRows"
                    max-height="240"
                    size="small"
                    border
                >
                  <el-table-column v-for="(col, idx) in previewCols" :key="idx" :label="col">
                    <template #default="{ row }">
                      <div v-html="row[idx]"></div>
                    </template>
                  </el-table-column>
                </el-table>

                <el-empty v-else description="暂无预览数据"/>
              </div>
            </el-card>
          </el-col>
        </el-row>

        <!-- 操作栏（始终显示） -->
        <div class="action-bar">
          <el-button type="primary" size="large" @click="startTrain" :loading="starting" :icon="VideoPlay">
            开始训练
          </el-button>
          <el-button v-if="currentTaskId" type="danger" plain @click="stopCurrentTraining" :loading="stopping">
            停止训练
          </el-button>
        </div>

        <!-- 误差曲线图表（全宽，仅当有任务时显示） -->
        <TrainingChart v-if="currentTaskId" :task-id="currentTaskId" class="chart-card"/>
      </el-tab-pane>

      <!-- 历史训练标签页 -->
      <el-tab-pane label="历史训练" name="history">
        <el-table :data="historyRecords" stripe>
          <el-table-column prop="id" label="ID" width="80"/>
          <el-table-column prop="model_type" label="模型"/>
          <el-table-column prop="status" label="状态">
            <template #default="{ row }">
              <el-tag :type="row.status === 'completed' ? 'success' : 'danger'">{{ row.status }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="final_error" label="最终误差"/>
          <el-table-column prop="created_at" label="创建时间" width="180"/>
          <el-table-column label="操作" width="180">
            <template #default="{ row }">
              <el-button link type="primary" @click="rerunTraining(row)">重新运行</el-button>
              <el-button link @click="viewDetail(row.id)">详情</el-button>
            </template>
          </el-table-column>
        </el-table>
        <el-pagination
            v-model:current-page="historyPage"
            :page-size="historyPageSize"
            :total="historyTotal"
            layout="prev, pager, next"
            @current-change="fetchHistory"
            style="margin-top: 20px"
        />
      </el-tab-pane>
    </el-tabs>

    <!-- 模板管理对话框 -->
    <el-dialog v-model="templateDialogVisible" title="管理预设模板" width="600px">
      <el-table :data="templates" style="width: 100%">
        <el-table-column prop="name" label="模板名称"/>
        <el-table-column prop="savedAt" label="保存时间" :formatter="formatTemplateTime"/>
        <el-table-column label="操作" width="150">
          <template #default="{ row }">
            <el-button link type="primary" @click="applyTemplate(row)">加载</el-button>
            <el-button link type="danger" @click="deleteTemplate(row.name)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-empty v-if="templates.length === 0" description="暂无保存的模板"/>
      <template #footer>
        <el-button @click="templateDialogVisible = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import {nextTick, onMounted, onUnmounted, ref, watch} from 'vue'
import {ElMessage, ElMessageBox} from 'element-plus'
import {Document, FolderOpened, Setting, VideoPlay, View} from '@element-plus/icons-vue'
import TrainingParams from '@/components/TrainingParams.vue'
import FileSelector from '@/components/FileSelector.vue'
import ProgressIndicator from '@/components/ProgressIndicator.vue'
import TrainingChart from '@/components/TrainingChart.vue'
import {useTrainingStore} from '@/stores/training'
import {useRouter} from 'vue-router'
import api from '@/api'

const trainingStore = useTrainingStore()
const router = useRouter()
const currentTaskId = ref(trainingStore.currentTaskId)
let expireTimer = null

// Tab 控制
const activeTab = ref('new')

// 新建训练相关
const selectedPath = ref('')
const paramsRef = ref()
const starting = ref(false)
const stopping = ref(false)

// 预览相关
const previewLoading = ref(false)
const previewType = ref('')        // 'image' 或 'table'
const previewImageSrc = ref('')    // 图片 Data URL
const previewRows = ref([])
const previewCols = ref([])

// 日志相关
const logs = ref('')
const logContainer = ref(null)
let logTimer = null

// 历史训练相关
const historyRecords = ref([])
const historyPage = ref(1)
const historyPageSize = ref(10)
const historyTotal = ref(0)

// 模板管理相关
const templateDialogVisible = ref(false)
const templates = ref([])
const TEMPLATE_KEY = 'training_presets'

// ==================== 预览处理 ====================
const processPreviewResponse = (data) => {
  if (data.type === 'image') {
    previewType.value = 'image'
    previewImageSrc.value = `data:image/${data.format};base64,${data.data}`
    previewCols.value = []
    previewRows.value = []
  } else if (data.columns && data.rows) {
    previewType.value = 'table'
    previewCols.value = data.columns
    previewRows.value = data.rows
    previewImageSrc.value = ''
  } else {
    resetPreview()
  }
}

const resetPreview = () => {
  previewType.value = ''
  previewCols.value = []
  previewRows.value = []
  previewImageSrc.value = ''
}

const handleFilePreview = async (filePath) => {
  previewLoading.value = true
  try {
    const res = await api.get('/train/files/preview', {params: {path: filePath, rows: 100}})
    processPreviewResponse(res.data)
  } catch (e) {
    ElMessage.error('预览失败')
    resetPreview()
  } finally {
    previewLoading.value = false
  }
}

const previewData = async () => {
  if (!selectedPath.value) {
    ElMessage.warning('请先选择数据文件')
    return
  }
  previewLoading.value = true
  try {
    const res = await api.get('/train/files/preview', {params: {path: selectedPath.value, rows: 100}})
    processPreviewResponse(res.data)
  } catch (e) {
    ElMessage.error('预览失败')
    resetPreview()
  } finally {
    previewLoading.value = false
  }
}

// ==================== 模板管理 ====================
const getTemplates = () => {
  try {
    return JSON.parse(localStorage.getItem(TEMPLATE_KEY)) || []
  } catch {
    return []
  }
}

const saveTemplateToStorage = (name, params, rawForm) => {
  const allTemplates = getTemplates()
  const existingIndex = allTemplates.findIndex(t => t.name === name)
  const template = {name, params, rawForm, savedAt: new Date().toISOString()}

  if (existingIndex >= 0) {
    allTemplates[existingIndex] = template
  } else {
    allTemplates.push(template)
  }
  if (allTemplates.length > 10) allTemplates.shift()
  localStorage.setItem(TEMPLATE_KEY, JSON.stringify(allTemplates))
}

const openTemplateManager = () => {
  templates.value = getTemplates()
  templateDialogVisible.value = true
}

const applyTemplate = (template) => {
  if (paramsRef.value) {
    paramsRef.value.setParams(template.params)
    templateDialogVisible.value = false
    ElMessage.success(`已加载模板：${template.name}`)
  }
}

const deleteTemplate = (name) => {
  ElMessageBox.confirm(`确定删除模板 "${name}" 吗？`, '提示', {type: 'warning'})
      .then(() => {
        const filtered = getTemplates().filter(t => t.name !== name)
        localStorage.setItem(TEMPLATE_KEY, JSON.stringify(filtered))
        templates.value = filtered
        ElMessage.success(`模板 "${name}" 已删除`)
      })
      .catch(() => {
      })
}

const formatTemplateTime = (row) => {
  if (!row.savedAt) return ''
  return new Date(row.savedAt).toLocaleString('zh-CN')
}

const saveAsPreset = () => {
  if (!paramsRef.value) return
  const params = paramsRef.value.getParams()
  const rawForm = paramsRef.value.getRawForm()

  ElMessageBox.prompt('请输入模板名称', '保存模板', {
    confirmButtonText: '保存',
    cancelButtonText: '取消',
    inputPattern: /\S+/,
    inputErrorMessage: '模板名称不能为空'
  }).then(({value}) => {
    const allTemplates = getTemplates()
    const existing = allTemplates.find(t => t.name === value)
    if (existing) {
      ElMessageBox.confirm(`模板 "${value}" 已存在，是否覆盖？`, '提示', {type: 'warning'})
          .then(() => {
            saveTemplateToStorage(value, params, rawForm)
            ElMessage.success(`模板 "${value}" 已覆盖`)
          })
          .catch(() => {
          })
    } else {
      saveTemplateToStorage(value, params, rawForm)
      ElMessage.success(`模板 "${value}" 已保存`)
    }
  }).catch(() => {
  })
}

// ==================== 训练逻辑 ====================
watch(() => trainingStore.currentTaskId, (newId) => {
  currentTaskId.value = newId
  if (newId) startLogPolling()
  else clearLogPolling()
})

const fetchHistory = async () => {
  try {
    const res = await trainingStore.getHistory({page: historyPage.value, page_size: historyPageSize.value})
    historyRecords.value = res.data.results
    historyTotal.value = res.data.count
  } catch (e) {
    ElMessage.error('获取历史记录失败')
  }
}

const rerunTraining = async (record) => {
  try {
    await ElMessageBox.confirm(`确定要重新运行训练 #${record.id} 吗？`, '提示', {type: 'info'})
    const res = await api.post(`/train/training/rerun/${record.id}`)
    ElMessage.success('训练已重新启动')
    activeTab.value = 'new'
    trainingStore.setCurrentTaskId(res.data.task_id)
    await fetchHistory()
  } catch (e) {
    if (e !== 'cancel') ElMessage.error(e.response?.data?.detail || '重新运行失败')
  }
}

const viewDetail = (id) => router.push(`/training/detail/${id}`)

const stopCurrentTraining = async () => {
  if (!currentTaskId.value) return
  stopping.value = true
  try {
    await api.post(`/train/training/stop/${currentTaskId.value}`)
    ElMessage.success('已发送停止指令，训练将很快中止')
    stopExpireTimer()
    trainingStore.clearCurrentTaskId()
    clearLogPolling()
  } catch (e) {
    if (e.response?.status === 404) ElMessage.error('停止接口不存在，请联系管理员')
    else ElMessage.error('停止失败')
  } finally {
    stopping.value = false
  }
}

const onTrainingCompleted = () => {
  ElMessage.success('训练完成！可在历史记录中查看详情')
  clearLogPolling()
  startExpireTimer()
  if (activeTab.value === 'history') fetchHistory()
}

const startExpireTimer = () => {
  if (expireTimer) clearTimeout(expireTimer)
  expireTimer = setTimeout(() => {
    ElMessage.info('训练记录已保留10分钟，页面将不再显示该任务（数据已保存）')
    trainingStore.clearCurrentTaskId()
    currentTaskId.value = null
  }, 10 * 60 * 1000)
}

const stopExpireTimer = () => {
  if (expireTimer) {
    clearTimeout(expireTimer);
    expireTimer = null
  }
}

const startTrain = async () => {
  if (!selectedPath.value) {
    ElMessage.warning('请选择数据文件或目录')
    return
  }
  stopExpireTimer()
  const params = paramsRef.value.getParams()
  params.data_path = selectedPath.value
  starting.value = true
  try {
    const res = await trainingStore.startTraining(params)
    ElMessage.success('训练已启动，请等待进度更新')
    startLogPolling()
  } catch (e) {
    ElMessage.error('启动失败')
  } finally {
    starting.value = false
  }
}

const startLogPolling = () => {
  if (logTimer) clearInterval(logTimer)
  logTimer = setInterval(async () => {
    if (!currentTaskId.value) return
    try {
      const res = await api.get(`/train/training/log/${currentTaskId.value}?tail=50`)
      logs.value = res.data.logs || ''
      nextTick(() => {
        if (logContainer.value) logContainer.value.scrollTop = logContainer.value.scrollHeight
      })
    } catch (e) {
    }
  }, 2000)
}

const clearLogPolling = () => {
  if (logTimer) {
    clearInterval(logTimer);
    logTimer = null
  }
}

onMounted(() => {
  if (currentTaskId.value) startLogPolling()
  fetchHistory()
})

onUnmounted(() => {
  clearLogPolling()
  stopExpireTimer()
})
</script>

<style scoped lang="scss">
.training-new {
  max-width: 1400px;
  margin: 0 auto;
  height: calc(100vh - 120px); /* 固定高度，超出滚动 */
  overflow-y: auto;
  padding-right: 4px;
}

.training-tabs :deep(.el-tabs__header) {
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;

  span {
    display: flex;
    align-items: center;
    gap: 8px;
    font-weight: 600;
  }
}

/* 左列卡片间距 */
.config-card,
.progress-card,
.log-card {
  margin-bottom: 16px;
}

/* ========== 模型配置卡片 ========== */
/* 在此调整整体高度：默认由内容撑开，如需固定高度可添加 height: 260px; 并配合 overflow-y: auto; */
.config-card {
  display: flex;
  flex-direction: column;

  height: 325px;              // 在这里设置您想要的高度
  overflow-y: auto;           // 如果内容超出则滚动（可选）
  /* 可选固定高度 */
  /* height: 260px; */
  /* overflow-y: auto; */

  :deep(.el-card__header) {
    padding: 12px 16px !important;   /* 标题区内边距，调小可压缩高度 */
  }

  :deep(.el-card__body) {
    padding: 12px 16px !important;   /* 内容区内边距，调小可压缩高度 */
  }

  :deep(.el-form-item) {
    margin-bottom: 12px !important;   /* 表单项间距，调小可压缩高度 */
  }

  :deep(.el-form-item__label) {
    width: 80px !important;
    padding-right: 4px !important;
  }

  :deep(.el-form-item__content) {
    margin-left: 80px !important;
  }
}

/* ========== 进度条卡片 ========== */
.progress-card {
  :deep(.el-card__body) {
    padding: 8px 16px !important;   /* 上下内边距可调 */
  }

  :deep(.el-card__header) {
    display: none;                  /* 隐藏内部标题 */
  }
}

/* ========== 日志卡片 ========== */
.log-card {
  :deep(.el-card__body) {
    padding: 12px 16px !important;
  }

  .log-container {
    max-height: 200px;
    overflow-y: auto;
    background: rgba(0, 0, 0, 0.02);
    border-radius: 12px;
    padding: 12px;
    font-family: 'Monaco', 'Menlo', monospace;
    font-size: 13px;

    pre {
      margin: 0;
      white-space: pre-wrap;
      word-break: break-all;
    }

    .dark & {
      background: rgba(255, 255, 255, 0.03);
    }
  }
}

/* ========== 数据源卡片 ========== */
.data-card {
  display: flex;
  flex-direction: column;

  :deep(.el-card__body) {
    padding: 12px 16px !important;   /* 内容区内边距 */
  }

  :deep(.file-container) {
    max-height: 200px !important;    /* 文件列表最大高度 */
    min-height: 120px;
  }

  :deep(.file-selector .toolbar) {
    margin-bottom: 6px;              /* 工具栏与面包屑间距 */
  }

  :deep(.breadcrumb) {
    margin-bottom: 6px;              /* 面包屑与文件列表间距 */
  }

  .data-preview {
    margin-top: 8px !important;

    .preview-header {
      margin-bottom: 6px !important;
    }

    .el-table {
      max-height: 160px !important;
    }
  }
}

.data-preview {
  .preview-header {
    display: flex;
    align-items: center;
    gap: 16px;

    .hint {
      font-size: 12px;
      opacity: 0.7;
    }
  }
}

.image-preview {
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 16px;
  background: rgba(0, 0, 0, 0.02);
  border-radius: 12px;
}

/* ========== 操作按钮栏 ========== */
.action-bar {
  margin: 20px 0 10px;
  display: flex;
  gap: 16px;
  justify-content: center;
}

/* ========== 图表卡片 ========== */
.chart-card {
  margin-top: 20px;
  background: var(--card-bg);
  backdrop-filter: blur(12px);
  border-radius: 24px;
  padding: 16px;
}
</style>