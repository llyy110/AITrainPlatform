<template>
  <div>
    <div style="margin-bottom: 16px; display: flex; gap: 10px;">
      <el-button type="primary" @click="openCompareDialog" :disabled="selectedRecords.length < 2">
        对比选中模型 ({{ selectedRecords.length }})
      </el-button>
    </div>

    <el-table :data="records" stripe @selection-change="handleSelectionChange">
      <el-table-column type="selection" width="55" />
      <el-table-column prop="id" label="ID" width="80"/>
      <el-table-column prop="model_type" label="模型"/>
      <el-table-column prop="data_path" label="数据路径" show-overflow-tooltip/>
      <el-table-column prop="status" label="状态">
        <template #default="{ row }">
          <el-tag :type="row.status === 'completed' ? 'success' : 'danger'">{{ row.status }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="final_error" label="最终误差"/>
      <el-table-column prop="created_at" label="创建时间" width="180">
        <template #default="{ row }">
          {{ formatToBeijing(row.created_at) }}
        </template>
      </el-table-column>
      <el-table-column label="操作">
        <template #default="{ row }">
          <el-button link @click="viewDetail(row.id)">详情</el-button>
          <el-button link @click="exportRecord(row.id)" :disabled="row.expired">导出</el-button>
        </template>
      </el-table-column>
    </el-table>
    <el-pagination v-model:current-page="page" :total="total" layout="prev, pager, next" @current-change="fetchData"/>

    <!-- 对比对话框 -->
    <el-dialog v-model="compareDialogVisible" title="模型效果对比" width="800px">
      <div ref="compareChart" style="height: 300px;"></div>
      <el-table :data="selectedRecords" style="margin-top: 20px">
        <el-table-column prop="id" label="ID" />
        <el-table-column prop="model_type" label="模型" />
        <el-table-column prop="final_accuracy" label="准确率">
          <template #default="{ row }">{{ row.final_accuracy?.toFixed(4) || '-' }}</template>
        </el-table-column>
        <el-table-column prop="final_error" label="损失" />
        <el-table-column label="训练时长(s)">
          <template #default="{ row }">{{ row.training_duration?.toFixed(2) || '-' }}</template>
        </el-table-column>
      </el-table>
    </el-dialog>
  </div>
</template>

<script setup>
import {onMounted, ref} from 'vue'
import {useRouter} from 'vue-router'
import {useTrainingStore} from '../stores/training'
import {ElMessage} from 'element-plus'
import * as echarts from 'echarts'

const records = ref([])
const total = ref(0)
const page = ref(1)
const store = useTrainingStore()
const router = useRouter()
const selectedRecords = ref([])
const compareDialogVisible = ref(false)
const compareChart = ref(null)

const formatToBeijing = (isoString) => {
  if (!isoString) return ''
  const date = new Date(isoString)
  return new Date(date.getTime() + 8 * 60 * 60 * 1000).toLocaleString('zh-CN', {
    year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false
  }).replace(/\//g, '-')
}

const fetchData = async () => {
  const res = await store.getHistory({page: page.value})
  records.value = res.data.results
  total.value = res.data.count
}

const handleSelectionChange = (val) => {
  selectedRecords.value = val
}

const openCompareDialog = () => {
  compareDialogVisible.value = true
  setTimeout(() => {
    const chart = echarts.init(compareChart.value)
    chart.setOption({
      title: { text: '模型准确率对比' },
      xAxis: { type: 'category', data: selectedRecords.value.map(r => `#${r.id}`) },
      yAxis: { type: 'value', name: '准确率' },
      series: [{
        type: 'bar',
        data: selectedRecords.value.map(r => r.final_accuracy || 0),
        itemStyle: { color: '#409eff' }
      }]
    })
  }, 100)
}

const viewDetail = (id) => router.push(`/training/detail/${id}`)

const exportRecord = async (id) => {
  try {
    const blob = await store.exportRecord(id)
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `training_${id}.csv`
    a.click()
    URL.revokeObjectURL(url)
  } catch (e) {
    if (e.response?.status === 403) ElMessage.warning('记录已超过一年，仅可查看不可下载')
    else ElMessage.error('导出失败')
  }
}

onMounted(() => fetchData())
</script>