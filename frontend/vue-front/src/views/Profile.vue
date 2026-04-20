<template>
  <div class="profile-page">
    <el-row :gutter="24">
      <!-- 左侧：个人资料卡片 -->
      <el-col :xs="24" :md="8">
        <el-card class="profile-card">
          <template #header>
            <span>个人资料</span>
          </template>
          <el-form label-width="80px" :model="form">
            <el-form-item label="头像">
              <div class="avatar-container">
                <el-upload
                  action="/api/user/avatar"
                  name="avatar"
                  :headers="{ Authorization: `Bearer ${userStore.token}` }"
                  :show-file-list="false"
                  :on-success="handleAvatarSuccess"
                  :on-error="handleAvatarError"
                  class="avatar-uploader"
                >
                  <img v-if="userStore.userInfo.avatar" :src="userStore.userInfo.avatar" class="avatar-img" />
                  <el-icon v-else class="avatar-placeholder"><Avatar /></el-icon>
                </el-upload>
                <div class="avatar-tip">点击更换</div>
              </div>
            </el-form-item>
            <el-form-item label="用户名">
              <el-input v-model="form.username" />
            </el-form-item>
            <el-form-item label="邮箱">
              <el-input v-model="form.email" disabled />
            </el-form-item>
            <el-form-item label="手机号">
              <el-input v-model="form.phone" placeholder="未绑定" />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="updateProfile">保存修改</el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </el-col>

      <!-- 右侧：统计与动态 -->
      <el-col :xs="24" :md="16">
        <!-- 统计卡片 -->
        <el-row :gutter="16" class="stats-row">
          <el-col :span="8">
            <div class="stat-card">
              <div class="stat-icon"><el-icon><DataAnalysis /></el-icon></div>
              <div class="stat-num">{{ stats.totalTrainings }}</div>
              <div class="stat-label">训练次数</div>
            </div>
          </el-col>
          <el-col :span="8">
            <div class="stat-card">
              <div class="stat-icon"><el-icon><ChatDotRound /></el-icon></div>
              <div class="stat-num">{{ stats.postCount }}</div>
              <div class="stat-label">发帖数</div>
            </div>
          </el-col>
          <el-col :span="8">
            <div class="stat-card">
              <div class="stat-icon"><el-icon><Star /></el-icon></div>
              <div class="stat-num">{{ stats.avgAccuracy }}%</div>
              <div class="stat-label">平均准确率</div>
            </div>
          </el-col>
        </el-row>

        <!-- 最近训练动态 -->
        <el-card class="recent-card">
          <template #header>
            <span>最近训练</span>
          </template>
          <el-table :data="recentTrainings" stripe>
            <el-table-column prop="model_type" label="模型" />
            <el-table-column prop="status" label="状态">
              <template #default="{ row }">
                <el-tag :type="row.status === 'completed' ? 'success' : 'warning'">{{ row.status }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="final_accuracy" label="准确率">
              <template #default="{ row }">
                {{ row.final_accuracy ? (row.final_accuracy * 100).toFixed(2) + '%' : '-' }}
              </template>
            </el-table-column>
            <el-table-column prop="created_at" label="时间" :formatter="formatTime" />
          </el-table>
        </el-card>

        <!-- 论坛动态 -->
        <el-card class="recent-card">
          <template #header>
            <span>我的帖子</span>
          </template>
          <div class="post-list">
            <div v-for="post in recentPosts" :key="post.id" class="post-item" @click="$router.push(`/forum/post/${post.id}`)">
              <span class="post-title">{{ post.title }}</span>
              <span class="post-meta">{{ formatTime(post.created_at) }} · {{ post.view_count }} 浏览</span>
            </div>
            <el-empty v-if="recentPosts.length === 0" description="暂无帖子" />
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useUserStore } from '@/stores/user'
import { ElMessage } from 'element-plus'
import { Avatar, DataAnalysis, ChatDotRound, Star } from '@element-plus/icons-vue'
import api from '@/api'

const userStore = useUserStore()
const form = reactive({
  username: userStore.userInfo.username || '',
  email: userStore.userInfo.email || '',
  phone: userStore.userInfo.phone || ''
})

const stats = ref({
  totalTrainings: 0,
  postCount: 0,
  avgAccuracy: 0
})
const recentTrainings = ref([])
const recentPosts = ref([])

const handleAvatarSuccess = (res) => {
  if (res.url) {
    userStore.userInfo.avatar = res.url.startsWith('http') ? res.url : `${window.location.origin}${res.url}`
    localStorage.setItem('userInfo', JSON.stringify(userStore.userInfo))
    ElMessage.success('头像更新成功')
  }
}
const handleAvatarError = () => ElMessage.error('上传失败')

const updateProfile = async () => {
  try {
    await userStore.updateProfile({ username: form.username, phone: form.phone })
    ElMessage.success('资料更新成功')
  } catch (e) {
    ElMessage.error('更新失败')
  }
}

const fetchStats = async () => {
  try {
    const [trainRes, postRes] = await Promise.all([
      api.get('/usage/records/stats/'),
      api.get('/forum/posts?my=1') // 需要后端支持
    ])
    stats.value.totalTrainings = trainRes.data.total || 0
    stats.value.avgAccuracy = trainRes.data.avg_accuracy ? (trainRes.data.avg_accuracy * 100).toFixed(2) : 0
    stats.value.postCount = postRes.data.count || 0
  } catch (e) {
    console.error('获取统计失败', e)
  }
}

const fetchRecent = async () => {
  try {
    const [trainRes, postRes] = await Promise.all([
      api.get('/train/training/records?page=1&page_size=5'),
      api.get('/forum/posts?my=1&page_size=5')
    ])
    recentTrainings.value = trainRes.data.results || []
    recentPosts.value = postRes.data.results || []
  } catch (e) {
    console.error('获取动态失败', e)
  }
}

const formatTime = (row) => {
  return new Date(row.created_at).toLocaleDateString('zh-CN')
}

onMounted(() => {
  fetchStats()
  fetchRecent()
})
</script>

<style scoped lang="scss">
.profile-page {
  max-width: 1200px;
  margin: 0 auto;
}
.avatar-container {
  display: flex;
  align-items: center;
  gap: 16px;
  .avatar-uploader { cursor: pointer; }
  .avatar-img {
    width: 80px;
    height: 80px;
    border-radius: 50%;
    object-fit: cover;
    border: 2px solid #e4e7ed;
  }
  .avatar-placeholder {
    width: 80px;
    height: 80px;
    font-size: 80px;
    color: #c0c4cc;
    border: 2px dashed #d9d9d9;
    border-radius: 50%;
    padding: 12px;
    box-sizing: border-box;
  }
}
.stats-row {
  margin-bottom: 20px;
  .stat-card {
    background: var(--card-bg);
    border-radius: 16px;
    padding: 20px;
    text-align: center;
    .stat-icon { font-size: 32px; color: #409eff; margin-bottom: 8px; }
    .stat-num { font-size: 28px; font-weight: 700; }
    .stat-label { color: #909399; margin-top: 4px; }
  }
}
.recent-card {
  margin-bottom: 20px;
}
.post-list {
  .post-item {
    padding: 12px 0;
    border-bottom: 1px solid #ebeef5;
    cursor: pointer;
    display: flex;
    justify-content: space-between;
    &:hover { background: #f5f7fa; }
    .post-title { font-weight: 500; }
    .post-meta { font-size: 12px; color: #999; }
  }
}
</style>