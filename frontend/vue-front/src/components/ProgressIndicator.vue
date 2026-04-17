<template>
  <el-card v-if="phase" style="margin-top: 20px">
    <template #header>TrainingProgress</template>
    <div>Phase: {{ phaseText }}</div>
    <el-progress :percentage="progressPercent" :status="statusColor" />
    <div>Current Epoch: {{ currentEpoch }} / {{ maxEpochs }}</div>
    <div>Current Error: {{ currentError }}</div>
    <div>Training Duration: {{ trainingDuration }} 秒</div>
  </el-card>
  <el-card v-else style="margin-top: 20px">
    <template #header>TrainingProgress</template>
    <div>Wait task start...</div>
    <el-progress :percentage="0" />
  </el-card>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../api'

const emit = defineEmits(['completed'])

const props = defineProps({ taskId: String })
const phase = ref('')
const progressPercent = ref(0)
const currentEpoch = ref(0)
const maxEpochs = ref(0)
const currentError = ref(0)
const trainingDuration = ref(0)
let timer = null
let notFoundCount = 0

const phaseText = computed(() => {
  const map = {
    loading_data: 'Loading data',
    training: 'Training',
    completed: 'Completed',
    failed: 'Failed'
  }
  return map[phase.value] || phase.value
})
const statusColor = computed(() => {
  if (phase.value === 'completed') return 'success'
  if (phase.value === 'failed') return 'exception'
  return ''
})

const fetchProgress = async () => {
  if (!props.taskId) return
  try {
    const res = await api.get(`/train/training/progress/${props.taskId}`)
    notFoundCount = 0
    phase.value = res.data.phase || ''
    progressPercent.value = res.data.progress_percent || 0
    currentEpoch.value = res.data.epoch || 0
    maxEpochs.value = res.data.max_epochs || 0
    currentError.value = res.data.error || 0
    trainingDuration.value = res.data.training_duration || 0
    if (phase.value === 'completed' || phase.value === 'failed') {
      clearTimer()
      emit('completed')
    }
  } catch (e) {
    if (e.response?.status === 404) {
      notFoundCount++
      if (notFoundCount > 15) {
        clearTimer()
        ElMessage.error('训练任务启动超时，请检查后端服务')
      }
    } else {
      console.error(e)
    }
  }
}

const startPolling = () => {
  clearTimer()
  // 重置状态
  phase.value = ''
  progressPercent.value = 0
  currentEpoch.value = 0
  maxEpochs.value = 0
  currentError.value = 0
  trainingDuration.value = 0
  notFoundCount = 0
  // 立即获取一次
  fetchProgress()
  // 启动定时器
  timer = setInterval(fetchProgress, 2000)
}

const clearTimer = () => {
  if (timer) {
    clearInterval(timer)
    timer = null
  }
}

// 监听 taskId 变化，重新开始轮询
watch(() => props.taskId, (newId, oldId) => {
  if (newId) {
    startPolling()
  } else {
    clearTimer()
    // 清空显示
    phase.value = ''
  }
})

onMounted(() => {
  if (props.taskId) {
    startPolling()
  }
})

onUnmounted(() => {
  clearTimer()
})
</script>