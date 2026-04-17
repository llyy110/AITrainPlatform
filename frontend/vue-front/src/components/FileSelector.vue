<template>
  <div class="file-selector">
    <!-- 工具栏 -->
    <div class="toolbar">
      <el-input
        v-model="searchKey"
        placeholder="搜索文件"
        clearable
        :prefix-icon="Search"
        size="small"
        style="width: 200px"
      />
      <el-button-group>
        <el-button :type="viewMode === 'list' ? 'primary' : ''" @click="viewMode = 'list'" size="small">
          <el-icon><List /></el-icon>
        </el-button>
        <el-button :type="viewMode === 'grid' ? 'primary' : ''" @click="viewMode = 'grid'" size="small">
          <el-icon><Grid /></el-icon>
        </el-button>
      </el-button-group>
      <el-upload
        :http-request="customUpload"
        :show-file-list="false"
        multiple
      >
        <el-button size="small" :icon="Upload">上传</el-button>
      </el-upload>
      <el-button size="small" :icon="Refresh" @click="refresh" circle />
    </div>

    <!-- 面包屑导航 -->
    <div class="breadcrumb">
      <el-breadcrumb separator="/">
        <el-breadcrumb-item @click="loadPath('/user')">根目录</el-breadcrumb-item>
        <el-breadcrumb-item
          v-for="(p, idx) in pathParts"
          :key="idx"
          @click="loadPath(buildPath(idx + 1))"
        >
          {{ p }}
        </el-breadcrumb-item>
      </el-breadcrumb>
      <el-button size="small" @click="loadPath(parentPath)" v-if="currentPath !== '/user'">
        <el-icon><Back /></el-icon> 返回上级
      </el-button>
    </div>

    <!-- 文件列表区域 -->
    <div class="file-container" :class="viewMode">
      <div v-if="filteredItems.length === 0" class="empty">
        <el-empty description="暂无内容" :image-size="80" />
      </div>
      <div
        v-for="item in filteredItems"
        :key="item.path"
        class="file-item"
        :class="{ selected: item.path === selected }"
        @click="handleClick(item)"
        @dblclick="handleDoubleClick(item)"
      >
        <div class="file-icon">
          <span v-if="item.type === 'DIR'">📁</span>
          <span v-else>📄</span>
        </div>
        <div class="file-info">
          <span class="file-name">{{ item.name }}</span>
          <span class="file-meta" v-if="viewMode === 'list'">{{ item.size || '--' }}</span>
        </div>
        <el-button
          v-if="item.type === 'DIR'"
          link
          size="small"
          class="select-dir-btn"
          @click.stop="selectDirectory(item)"
        >
          选择目录
        </el-button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { Search, List, Grid, Upload, Refresh, Back } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '@/api'
import { useUserStore } from '@/stores/user'

const props = defineProps({ modelValue: String })
const emit = defineEmits(['update:modelValue', 'preview'])  // 增加 preview 事件

const userStore = useUserStore()
const currentPath = ref('/user')
const items = ref([])
const selected = ref(null)
const searchKey = ref('')
const viewMode = ref('list')

const pathParts = computed(() => currentPath.value.split('/').filter(Boolean))
const parentPath = computed(() => {
  const parts = currentPath.value.split('/').filter(Boolean)
  parts.pop()
  return '/' + parts.join('/') || '/user'
})

const buildPath = (len) => {
  const parts = currentPath.value.split('/').filter(Boolean)
  return '/' + parts.slice(0, len).join('/')
}

const filteredItems = computed(() => {
  if (!searchKey.value) return items.value
  return items.value.filter(item =>
    item.name.toLowerCase().includes(searchKey.value.toLowerCase())
  )
})

const loadPath = async (path) => {
  currentPath.value = path
  try {
    const res = await api.get('/train/files/list', { params: { path } })
    items.value = res.data.map((item) => {
      const [type, fullPath] = item.split(':')
      const name = fullPath.substring(fullPath.lastIndexOf('/') + 1)
      return { type, path: fullPath, name, size: '' }
    })
  } catch (e) {
    console.error('加载目录失败', e)
    ElMessage.error('加载目录失败')
  }
}

const refresh = () => loadPath(currentPath.value)

// 单击处理：目录则进入，文件则选中并触发预览
const handleClick = (item) => {
  if (item.type === 'DIR') {
    loadPath(item.path)
  } else {
    selectItem(item)
    emit('preview', item.path)   // 触发预览事件
  }
}

// 双击处理：目录则选择目录，文件则选中并触发预览（与单击类似，但可保留不同逻辑）
const handleDoubleClick = (item) => {
  if (item.type === 'DIR') {
    selectDirectory(item)
  } else {
    selectItem(item)
    emit('preview', item.path)   // 同样触发预览
  }
}

const selectItem = (item) => {
  selected.value = item.path
  emit('update:modelValue', item.path)
}

const selectDirectory = (item) => {
  selected.value = item.path
  emit('update:modelValue', item.path)
}

// 自定义上传逻辑
const customUpload = async (options) => {
  const { file } = options
  const formData = new FormData()
  formData.append('file', file)

  const uploadFile = async (overwrite = false) => {
    const url = overwrite ? '/train/files/upload?overwrite=true' : '/train/files/upload'
    return api.post(url, formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
  }

  try {
    await uploadFile(false)
    ElMessage.success(`文件 ${file.name} 上传成功`)
    refresh()
  } catch (error) {
    const status = error.response?.status
    const detail = error.response?.data?.detail || '上传失败'
    if (status === 409) {
      try {
        await ElMessageBox.confirm(
          `文件 "${file.name}" 已存在，是否覆盖？`,
          '文件已存在',
          { confirmButtonText: '覆盖', cancelButtonText: '取消', type: 'warning' }
        )
        await uploadFile(true)
        ElMessage.success(`文件 ${file.name} 已覆盖上传`)
        refresh()
      } catch (cancelError) {
        ElMessage.info('已取消上传')
      }
    } else {
      ElMessage.error(`上传失败: ${detail}`)
    }
  }
}

// 初始化
loadPath('/user')
</script>

<style scoped lang="scss">
.file-selector {
  .toolbar {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 16px;
    flex-wrap: wrap;
  }
  .breadcrumb {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 16px;
    :deep(.el-breadcrumb__item) { cursor: pointer; }
  }
}

.file-container {
  background: rgba(0,0,0,0.02);
  border-radius: 16px;
  padding: 12px;
  min-height: 200px;
  max-height: 400px;
  overflow-y: auto;
  border: 1px solid rgba(0,0,0,0.05);
  .dark & {
    background: rgba(255,255,255,0.02);
    border-color: rgba(255,255,255,0.05);
  }

  &.grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
    gap: 12px;
    .file-item {
      flex-direction: column;
      text-align: center;
      padding: 12px 8px;
      .file-icon { font-size: 36px; margin-bottom: 4px; }
    }
  }

  &.list {
    .file-item {
      display: flex;
      align-items: center;
      padding: 10px 12px;
      border-radius: 10px;
      &:hover { background: rgba(64,158,255,0.05); }
      .file-icon { margin-right: 12px; font-size: 20px; }
      .file-info { flex: 1; display: flex; justify-content: space-between; }
    }
  }

  .file-item {
    cursor: pointer;
    transition: all 0.2s;
    border-radius: 12px;
    &.selected {
      background: #ecf5ff;
      color: #409eff;
      .dark & { background: #2a3a5e; }
    }
    .select-dir-btn { opacity: 0.6; margin-left: auto; }
  }

  .empty {
    display: flex;
    justify-content: center;
    align-items: center;
    height: 150px;
  }
}
</style>