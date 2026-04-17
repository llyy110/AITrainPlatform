<template>
  <el-form label-width="140px">
    <el-form-item label="模型类型">
      <el-select v-model="form.modelType">
        <el-option label="BP神经网络分类" value="train_bpnn_classifier" />
        <el-option label="BP神经网络回归" value="train_bpnn_regressor" />
        <el-option label="CNN图像分类" value="train_cnn_img_classifier" />
      </el-select>
    </el-form-item>
    <el-form-item label="隐藏层神经元数">
      <el-input-number v-model="form.hiddenLayerSizes" :min="1" :max="1024" />
    </el-form-item>
    <el-form-item label="最大迭代次数">
      <el-input-number v-model="form.maxIter" :min="1" :max="1000" />
    </el-form-item>
    <el-form-item label="学习率">
      <el-input-number v-model="form.learningRate" :step="0.001" :min="0.001" :max="1" />
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

defineExpose({ getParams })
</script>