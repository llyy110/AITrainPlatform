<template>
  <div ref="chartRef" class="chart-container"></div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch } from 'vue'
import * as echarts from 'echarts'
import api from '@/api'

const props = defineProps({ taskId: String })
const chartRef = ref(null)
let chart = null
let timer = null
let notFoundCount = 0

const currentPhase = ref('')
const epochs = ref([])
const epochNumbers = ref([])

const initChart = () => {
  if (!chartRef.value) return
  chart = echarts.init(chartRef.value)
  chart.setOption({
    title: { text: '训练误差曲线', left: 'center' },
    xAxis: {
      name: '训练时长 (秒)',
      type: 'value',
      axisLabel: { formatter: (v) => (v / 1000).toFixed(2) + ' s' }
    },
    yAxis: { name: '误差', type: 'log' },
    series: [{
      type: 'line', data: [], smooth: true, name: '误差',
      symbol: 'circle', symbolSize: 8,
      lineStyle: { color: '#409eff', width: 2 },
      itemStyle: { color: '#409eff' }
    }],
    tooltip: {
      trigger: 'item',
      formatter: (params) => {
        if (!params.value) return ''
        const dataIndex = params.dataIndex
        const seriesData = chart.getOption().series[0].data
        const pointData = seriesData[dataIndex]
        if (!pointData) return ''
        const durationMs = pointData[0]
        const error = pointData[1]

        const formatDuration = (ms) => {
          if (ms < 1000) return `${ms.toFixed(0)} 毫秒`
          const sec = ms / 1000
          if (sec < 60) return `${sec.toFixed(2)} 秒`
          const min = Math.floor(sec / 60)
          const remainSec = (sec % 60).toFixed(0)
          return `${min} 分 ${remainSec} 秒`
        }

        const epoch = epochNumbers.value[dataIndex] || '?'

        // 判断状态：如果是最后一个点且整体已完成，则显示 completed，否则显示 training
        let status = 'training'
        if (currentPhase.value === 'completed') {
          status = (dataIndex === epochNumbers.value.length - 1) ? 'completed' : 'training'
        }

        const getStatusColor = (status) => {
          const map = { training: '#1890ff', completed: '#52c41a', failed: '#f5222d' }
          return map[status] || '#666'
        }
        const getStatusText = (status) => {
          const map = { training: '训练中', completed: '已完成', failed: '失败' }
          return map[status] || status
        }

        const errorColor = error > 0.1 ? '#f5222d' : '#52c41a'

        let html = `<div style="font-weight: bold; margin-bottom: 8px; color: #1890ff;">📋 训练详情</div>`
        html += `<div><span style="color: #666;">⏱️ 训练时长:</span> <b>${formatDuration(durationMs)}</b></div>`
        html += `<div><span style="color: #666;">📊 Epoch:</span> <b style="color: #722ed1;">${epoch}</b></div>`
        html += `<div><span style="color: #666;">📈 当前误差:</span> <b style="color: ${errorColor};">${typeof error === 'number' ? error.toFixed(6) : error}</b></div>`
        html += `<div><span style="color: #666;">📋 训练状态:</span> <b style="color: ${getStatusColor(status)};">${getStatusText(status)}</b></div>`
        return html
      },
      backgroundColor: '#ffffffdd',
      borderColor: '#409eff',
      borderWidth: 1,
      padding: [10, 15],
      textStyle: { color: '#333', fontSize: 13 }
    },
    grid: { containLabel: true, left: '8%', right: '5%', bottom: '10%' },
    backgroundColor: 'transparent'
  })
}

const updateChart = async () => {
  if (!props.taskId || !chart) return
  try {
    const res = await api.get(`/train/training/progress/${props.taskId}`)
    notFoundCount = 0
    const data = res.data
    currentPhase.value = data.phase || ''
    epochs.value = data.epochs || []

    const validEpochs = epochs.value.filter(e => e.epoch > 0 && e.training_duration != null && e.error != null)
    epochNumbers.value = validEpochs.map(e => e.epoch)
    const chartData = validEpochs.map(e => [e.training_duration * 1000, e.error])

    // 图表标题：如果整体已完成，加上 ✅ 标记
    const titleText = currentPhase.value === 'completed' ? '✅ 训练误差曲线 (已完成)' : '训练误差曲线'
    chart.setOption({
      title: { text: titleText },
      series: [{ data: chartData }]
    })
  } catch (e) {
    if (e.response?.status === 404) {
      notFoundCount++
      if (notFoundCount > 15) {
        if (timer) clearInterval(timer)
        chart.setOption({
          title: { text: '⚠️ 训练任务启动超时', left: 'center', top: 'center' }
        })
      }
    } else {
      console.error('更新图表失败:', e)
    }
  }
}

onMounted(() => {
  initChart()
  updateChart()
  timer = setInterval(updateChart, 3000)
})

onUnmounted(() => {
  if (timer) clearInterval(timer)
  if (chart) chart.dispose()
})

watch(() => props.taskId, (newId) => {
  if (newId) {
    if (chart) chart.dispose()
    initChart()
    updateChart()
    if (timer) clearInterval(timer)
    timer = setInterval(updateChart, 3000)
  }
})
</script>

<style scoped>
.chart-container {
  width: 100%;
  height: 400px;
  margin-top: 20px;
  background: var(--card-bg);
  backdrop-filter: blur(12px);
  border-radius: 24px;
  padding: 16px;
  border: var(--border-light);
  box-sizing: border-box;
}
</style>