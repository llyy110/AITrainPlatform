<template>
  <div class="dashboard">
    <!-- 欢迎横幅 -->
    <div class="welcome-banner">
      <div>
        <h1>欢迎回来，{{ userStore.userInfo.username || '研究者' }} 👋</h1>
        <p>今日适合开启新的神经网络实验</p>
      </div>
      <el-button type="primary" round size="large" @click="$router.push('/training/new')">
        <el-icon><Plus /></el-icon> 新建训练
      </el-button>
    </div>

    <!-- 统计卡片 -->
    <el-row :gutter="20" class="stat-cards">
      <el-col :xs="24" :sm="12" :md="6" v-for="stat in stats" :key="stat.label">
        <div class="stat-card" :class="stat.color">
          <div class="stat-icon"><el-icon :size="32"><component :is="stat.icon" /></el-icon></div>
          <div class="stat-content">
            <span class="stat-value">{{ stat.value }}</span>
            <span class="stat-label">{{ stat.label }}</span>
          </div>
        </div>
      </el-col>
    </el-row>

    <!-- 最近任务 + 公告 -->
    <el-row :gutter="24" class="info-row">
      <el-col :xs="24" :lg="16">
        <el-card class="glass-card" shadow="never">
          <template #header>
            <div class="card-header">
              <span><el-icon><List /></el-icon> 最近训练任务</span>
              <el-button link type="primary" @click="$router.push('/training/history')">查看全部</el-button>
            </div>
          </template>
          <el-table :data="recentTasks" style="width: 100%" v-loading="loading" stripe>
            <el-table-column prop="id" label="ID" width="70" />
            <el-table-column prop="model_type" label="模型类型" />
            <el-table-column prop="data_path" label="数据路径" show-overflow-tooltip />
            <el-table-column prop="status" label="状态">
              <template #default="{ row }">
                <el-tag :type="statusTag(row.status)" size="small">{{ row.status }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="final_error" label="最终误差" />
            <el-table-column label="操作" width="140">
              <template #default="{ row }">
                <el-button link type="primary" @click="viewDetail(row.id)">详情</el-button>
                <el-button link v-if="row.status === 'training'" @click="stopTask(row.id)">停止</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
      <el-col :xs="24" :lg="8">
        <el-card class="glass-card announcement-card" shadow="never">
          <template #header>
            <div class="card-header">
              <span><el-icon><Bell /></el-icon> 平台公告</span>
            </div>
          </template>
          <div class="announcement-list">
            <div v-for="item in announcements" :key="item.id" class="announcement-item">
              <span class="tag" :style="{ background: item.tagColor }">{{ item.tag }}</span>
              <p>{{ item.content }}</p>
              <small>{{ item.time }}</small>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 快速入口 / 模型推荐 -->
    <el-row :gutter="24" style="margin-top: 24px">
      <el-col :span="24">
        <el-card class="glass-card">
          <template #header>
            <span><el-icon><TrendCharts /></el-icon> 模型表现趋势</span>
          </template>
          <div ref="trendChart" style="height: 200px;"></div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useUserStore } from '@/stores/user'
import { useTrainingStore } from '@/stores/training'
import { useRouter } from 'vue-router'
import { Plus, List, Bell, DataAnalysis, Timer, Finished, Cpu, TrendCharts } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import api from '@/api'
import * as echarts from 'echarts'

const userStore = useUserStore()
const trainingStore = useTrainingStore()
const router = useRouter()
const loading = ref(false)
const recentTasks = ref([])
const trendChart = ref(null)

// 统计数据（可从后端获取，此处为模拟）
const stats = ref([
  { label: '总训练次数', value: 24, icon: 'DataAnalysis', color: 'blue' },
  { label: '进行中', value: 3, icon: 'Timer', color: 'orange' },
  { label: '已完成', value: 19, icon: 'Finished', color: 'green' },
  { label: '模型类型', value: 5, icon: 'Cpu', color: 'purple' }
])

const announcements = ref([
  { id: 1, tag: '新功能', tagColor: '#409eff', content: '支持训练任务中途停止与恢复', time: '2小时前' },
  { id: 2, tag: '优化', tagColor: '#67c23a', content: '文件管理器支持拖拽上传', time: '昨天' },
  { id: 3, tag: '公告', tagColor: '#e6a23c', content: '服务器将于周日凌晨维护', time: '3天前' }
])

const statusTag = (status) => {
  const map = { training: 'warning', completed: 'success', failed: 'danger', pending: 'info' }
  return map[status] || 'info'
}

const fetchRecentTasks = async () => {
  loading.value = true
  try {
    const res = await trainingStore.getHistory({ page: 1, page_size: 5 })
    recentTasks.value = res.data.results || []
  } catch (e) {
    console.error('获取任务失败', e)
  } finally {
    loading.value = false
  }
}

const viewDetail = (id) => router.push(`/training/detail/${id}`)

const stopTask = async (id) => {
  try {
    await api.post(`/train/training/stop/${id}`)
    ElMessage.success('已发送停止指令')
    fetchRecentTasks()
  } catch (e) {
    ElMessage.error('停止失败')
  }
}

const initTrendChart = () => {
  if (!trendChart.value) return
  const chart = echarts.init(trendChart.value)
  chart.setOption({
    grid: { left: '3%', right: '4%', bottom: '10%', containLabel: true },
    xAxis: { type: 'category', data: ['周一', '周二', '周三', '周四', '周五', '周六', '周日'] },
    yAxis: { type: 'value' },
    series: [
      { name: '训练次数', type: 'bar', data: [5, 8, 12, 9, 15, 7, 4], itemStyle: { borderRadius: [8,8,0,0], color: '#409eff' } },
      { name: '平均准确率', type: 'line', smooth: true, data: [0.82, 0.85, 0.88, 0.87, 0.91, 0.89, 0.86], yAxisIndex: 0, color: '#67c23a' }
    ],
    tooltip: { trigger: 'axis' },
    legend: { bottom: 0 }
  })
}

onMounted(() => {
  fetchRecentTasks()
  initTrendChart()
})
</script>

<style scoped lang="scss">
.dashboard {
  max-width: 1400px;
  margin: 0 auto;
}

.welcome-banner {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 30px;
  h1 {
    font-weight: 700;
    font-size: 2rem;
    margin: 0 0 8px;
    background: linear-gradient(135deg, #1f2d5c, #409eff);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
  }
  p { opacity: 0.7; margin: 0; font-size: 1rem; }
}

.stat-cards { margin-bottom: 30px; }

.stat-card {
  background: var(--card-bg);
  backdrop-filter: blur(12px);
  border-radius: 24px;
  padding: 22px 20px;
  display: flex;
  align-items: center;
  gap: 18px;
  box-shadow: var(--card-shadow);
  transition: all 0.3s;
  border: var(--border-light);
  &:hover { transform: translateY(-3px); box-shadow: var(--primary-glow); }
  .stat-icon { opacity: 0.8; }
  .stat-content { display: flex; flex-direction: column; }
  .stat-value { font-size: 32px; font-weight: 700; line-height: 1.2; }
  .stat-label { opacity: 0.7; font-size: 14px; }
  &.blue .stat-icon { color: #409eff; }
  &.orange .stat-icon { color: #e6a23c; }
  &.green .stat-icon { color: #67c23a; }
  &.purple .stat-icon { color: #8e71ff; }
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  span { display: flex; align-items: center; gap: 8px; font-weight: 600; }
}

.announcement-list {
  .announcement-item {
    padding: 14px 0;
    border-bottom: 1px dashed rgba(0,0,0,0.08);
    .dark & { border-bottom-color: rgba(255,255,255,0.08); }
    &:last-child { border-bottom: none; }
    .tag {
      color: white;
      padding: 2px 10px;
      border-radius: 20px;
      font-size: 12px;
      margin-right: 8px;
    }
    p { margin: 8px 0 4px; font-weight: 500; }
    small { opacity: 0.6; }
  }
}
</style>