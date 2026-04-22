<template>
  <el-form label-width="auto" class="training-params-form">
    <el-form-item label="模型类型">
      <el-select v-model="form.modelType" size="small">
        <el-option label="BP神经网络分类" value="train_bpnn_classifier" />
        <el-option label="BP神经网络回归" value="train_bpnn_regressor" />
        <el-option label="CNN图像分类" value="train_cnn_img_classifier" />
      </el-select>
    </el-form-item>
    <el-form-item label="隐藏层神经元数">
      <el-input-number v-model="form.hiddenLayerSizes" :min="1" :max="1024" size="small" />
    </el-form-item>
    <el-form-item label="最大迭代次数">
      <el-input-number v-model="form.maxIter" :min="1" :max="1000" size="small" />
    </el-form-item>
    <el-form-item label="学习率">
      <el-input-number v-model="form.learningRate" :step="0.001" :min="0.001" :max="1" size="small" />
    </el-form-item>
  </el-form>
</template>

<script setup>
import { reactive } from 'vue'

const form = reactive({
  modelType: 'train_bpnn_classifier',
  hiddenLayerSizes: 3,
  maxIter: 32,
  learningRate: 0.01
})

const getParams = () => ({
  model_type: form.modelType,
  hidden_layer_sizes: form.hiddenLayerSizes,
  max_iter: form.maxIter,
  learning_rate: form.learningRate
})

const setParams = (params) => {
  if (params.model_type) form.modelType = params.model_type
  if (params.hidden_layer_sizes !== undefined) form.hiddenLayerSizes = params.hidden_layer_sizes
  if (params.max_iter !== undefined) form.maxIter = params.max_iter
  if (params.learning_rate !== undefined) form.learningRate = params.learning_rate
}

const getRawForm = () => ({
  modelType: form.modelType,
  hiddenLayerSizes: form.hiddenLayerSizes,
  maxIter: form.maxIter,
  learningRate: form.learningRate
})

defineExpose({ getParams, setParams, getRawForm })
</script>

<style scoped>
.training-params-form {
  --el-form-label-font-size: 13px;
}

/* 让标签与输入框贴近 */
:deep(.el-form-item__label) {
  padding-right: 8px !important;
  white-space: nowrap;
}
</style>