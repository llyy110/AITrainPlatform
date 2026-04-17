<template>
  <div class="training-new">
    <el-tabs v-model="activeTab" class="training-tabs">
      <!-- 新建训练标签页 -->
      <el-tab-pane label="新建训练" name="new">
        <el-row :gutter="24">
          <!-- 左侧：模型配置 -->
          <el-col :xs="24" :md="12">
            <el-card class="glass-card config-card" shadow="never">
              <template #header>
                <div class="card-header">
                  <span><el-icon><Setting/></el-icon> 模型配置</span>
                  <div>
                    <el-button link @click="loadPreset">加载预设</el-button>
                    <el-button link @click="saveAsPreset">保存模板</el-button>
                  </div>
                </div>
              </template>
              <TrainingParams ref="paramsRef"/>
            </el-card>
          </el-col>

          <!-- 右侧：数据选择 + 预览 -->
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
                    <el-icon><View/></el-icon>
                    预览前100行
                  </el-button>
                  <span v-if="previewRows.length" class="hint">已加载 {{ previewRows.length }} 行</span>
                </div>
                <el-table :data="previewRows" max-height="240" v-if="previewRows.length" size="small" border>
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

        <!-- 操作栏 -->
        <div class="action-bar">
          <el-button type="primary" size="large" @click="startTrain" :loading="starting" :icon="VideoPlay">
            开始训练
          </el-button>
          <el-button v-if="currentTaskId" type="danger" plain @click="stopCurrentTraining" :loading="stopping">
            停止训练
          </el-button>
        </div>

        <!-- 进度与日志区域（仅当有进行中的训练时显示） -->
        <el-row :gutter="24" v-if="currentTaskId">
          <el-col :xs="24" :lg="12">
            <ProgressIndicator :task-id="currentTaskId" @completed="onTrainingCompleted"/>
          </el-col>
          <el-col :xs="24" :lg="12">
            <el-card class="glass-card log-card">
              <template #header>
                <span><el-icon><Document/></el-icon> 实时日志</span>
                <el-button link @click="logs = ''">清空</el-button>
              </template>
              <div class="log-container" ref="logContainer">
                <pre>{{ logs }}</pre>
              </div>
            </el-card>
          </el-col>
        </el-row>

        <!-- 图表 -->
        <TrainingChart v-if="currentTaskId" :task-id="currentTaskId" class="chart-card"/>
      </el-tab-pane>

      <!-- 历史训练标签页 -->
      <el-tab-pane label="历史训练" name="history">
        <el-table :data="historyRecords" stripe>
          <el-table-column prop="id" label="ID" width="80" />
          <el-table-column prop="model_type" label="模型" />
          <el-table-column prop="status" label="状态">
            <template #default="{ row }">
              <el-tag :type="row.status === 'completed' ? 'success' : 'danger'">{{ row.status }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="final_error" label="最终误差" />
          <el-table-column prop="created_at" label="创建时间" width="180" />
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
  </div>
</template>

<script setup>
import { nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Document, FolderOpened, Setting, VideoPlay, View } from '@element-plus/icons-vue'
import TrainingParams from '@/components/TrainingParams.vue'
import FileSelector from '@/components/FileSelector.vue'
import ProgressIndicator from '@/components/ProgressIndicator.vue'
import TrainingChart from '@/components/TrainingChart.vue'
import { useTrainingStore } from '@/stores/training'
import { useRouter } from 'vue-router'
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

// 监听 store 变化，同步到本地
watch(() => trainingStore.currentTaskId, (newId) => {
  currentTaskId.value = newId
  if (newId) {
    startLogPolling()
  } else {
    clearLogPolling()
  }
})

// 获取历史训练记录
const fetchHistory = async () => {
  try {
    const res = await trainingStore.getHistory({ page: historyPage.value, page_size: historyPageSize.value })
    historyRecords.value = res.data.results
    historyTotal.value = res.data.count
  } catch (e) {
    ElMessage.error('获取历史记录失败')
  }
}

// 重新运行训练
const rerunTraining = async (record) => {
  try {
    await ElMessageBox.confirm(`确定要重新运行训练 #${record.id} 吗？`, '提示', { type: 'info' })
    const res = await api.post(`/train/training/rerun/${record.id}`)
    ElMessage.success('训练已重新启动')
    activeTab.value = 'new'
    trainingStore.setCurrentTaskId(res.data.task_id)
    // 刷新历史列表
    await fetchHistory()
  } catch (e) {
    if (e !== 'cancel') {
      ElMessage.error(e.response?.data?.detail || '重新运行失败')
    }
  }
}

// 查看详情
const viewDetail = (id) => router.push(`/training/detail/${id}`)

// 添加预览处理函数
const handleFilePreview = async (filePath) => {
  previewLoading.value = true
  try {
    const res = await api.get('/train/files/preview', { params: { path: filePath, rows: 100 } })
    if (res.data.type === 'image') {
      previewCols.value = ['预览']
      previewRows.value = [[`<img src="data:image/${res.data.format};base64,${res.data.data}" style="max-width:100%; max-height:300px;" />`]]
    } else if (res.data.columns && res.data.rows) {
      previewCols.value = res.data.columns
      previewRows.value = res.data.rows
    } else {
      previewRows.value = []
    }
  } catch (e) {
    ElMessage.error('预览失败')
    previewRows.value = []
  } finally {
    previewLoading.value = false
  }
}

// 停止当前训练
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
    if (e.response?.status === 404) {
      ElMessage.error('停止接口不存在，请联系管理员')
    } else {
      ElMessage.error('停止失败')
    }
  } finally {
    stopping.value = false
  }
}

// 训练完成后的回调
const onTrainingCompleted = () => {
  ElMessage.success('训练完成！可在历史记录中查看详情')
  clearLogPolling()
  startExpireTimer()
  // 刷新历史记录（如果当前在历史标签页）
  if (activeTab.value === 'history') {
    fetchHistory()
  }
}

// 启动过期计时器
const startExpireTimer = () => {
  if (expireTimer) clearTimeout(expireTimer)
  expireTimer = setTimeout(() => {
    ElMessage.info('训练记录已保留10分钟，页面将不再显示该任务（数据已保存）')
    trainingStore.clearCurrentTaskId()
    if (currentTaskId.value) {
      currentTaskId.value = null
    }
  }, 10 * 60 * 1000)
}

// 停止过期计时器
const stopExpireTimer = () => {
  if (expireTimer) {
    clearTimeout(expireTimer)
    expireTimer = null
  }
}

// 开始新训练
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

// 预览数据（手动点击按钮）
const previewData = async () => {
  if (!selectedPath.value) {
    ElMessage.warning('请先选择数据文件')
    return
  }
  previewLoading.value = true
  try {
    const res = await api.get('/train/files/preview', { params: { path: selectedPath.value, rows: 100 } })
    if (res.data.type === 'image') {
      previewCols.value = ['预览']
      previewRows.value = [[`<img src="data:image/${res.data.format};base64,${res.data.data}" style="max-width:100%; max-height:200px;" />`]]
    } else if (res.data.columns && res.data.rows) {
      previewCols.value = res.data.columns
      previewRows.value = res.data.rows
    } else {
      previewRows.value = []
    }
  } catch (e) {
    ElMessage.error('预览失败')
    previewRows.value = []
  } finally {
    previewLoading.value = false
  }
}

// 日志轮询
const startLogPolling = () => {
  if (logTimer) clearInterval(logTimer)
  logTimer = setInterval(async () => {
    if (!currentTaskId.value) return
    try {
      const res = await api.get(`/train/training/log/${currentTaskId.value}?tail=50`)
      logs.value = res.data.logs || ''
      nextTick(() => {
        if (logContainer.value) {
          logContainer.value.scrollTop = logContainer.value.scrollHeight
        }
      })
    } catch (e) {
      // 忽略
    }
  }, 2000)
}

const clearLogPolling = () => {
  if (logTimer) {
    clearInterval(logTimer)
    logTimer = null
  }
}

// 预设模板功能（示例）
const loadPreset = () => {
  ElMessage.info('功能开发中，敬请期待')
}
const saveAsPreset = () => {
  const params = paramsRef.value.getParams()
  console.log('当前参数:', params)
  ElMessage.success('模板已保存（演示）')
}

// 如果已有进行中的训练，立即启动日志轮询
onMounted(() => {
  if (currentTaskId.value) {
    startLogPolling()
  }
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
}

.training-tabs {
  :deep(.el-tabs__header) {
    margin-bottom: 20px;
  }
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

.config-card, .data-card {
  height: 100%;
  display: flex;
  flex-direction: column;

  :deep(.el-card__body) {
    flex: 1;
  }
}

.data-preview {
  margin-top: 8px;

  .preview-header {
    display: flex;
    align-items: center;
    gap: 16px;
    margin-bottom: 12px;

    .hint {
      font-size: 12px;
      opacity: 0.7;
    }
  }
}

.action-bar {
  margin: 28px 0;
  display: flex;
  gap: 16px;
  justify-content: center;
}

.log-card {
  margin-top: 20px;

  .log-container {
    background: rgba(0, 0, 0, 0.02);
    border-radius: 12px;
    padding: 12px;
    max-height: 300px;
    overflow-y: auto;
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

.chart-card {
  margin-top: 24px;
  background: var(--card-bg);
  backdrop-filter: blur(12px);
  border-radius: 24px;
  padding: 16px;
}
</style>