<template>
  <el-card v-if="record">
    <h3>训练详情 #{{ record.id }}</h3>
    <el-descriptions :column="2" border>
      <el-descriptions-item label="模型类型">{{ record.model_type }}</el-descriptions-item>
      <el-descriptions-item label="隐藏层">{{ record.hidden_layer_sizes }}</el-descriptions-item>
      <el-descriptions-item label="最大迭代">{{ record.max_iter }}</el-descriptions-item>
      <el-descriptions-item label="学习率">{{ record.learning_rate }}</el-descriptions-item>
      <el-descriptions-item label="数据路径">{{ record.data_path }}</el-descriptions-item>
      <el-descriptions-item label="状态">{{ record.status }}</el-descriptions-item>
      <el-descriptions-item label="最终误差">{{ record.final_error }}</el-descriptions-item>
      <el-descriptions-item label="准确率/MAE">{{ record.final_accuracy || record.final_mae }}</el-descriptions-item>
    </el-descriptions>
    <TrainingChart :task-id="record.task_id" v-if="record.task_id" />
  </el-card>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useTrainingStore } from '../stores/training'
import TrainingChart from '../components/TrainingChart.vue'

const route = useRoute()
const store = useTrainingStore()
const record = ref(null)

onMounted(async () => {
  const res = await store.getRecordDetail(route.params.id)
  record.value = res.data
})
</script>