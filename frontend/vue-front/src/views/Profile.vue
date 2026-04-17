<template>
  <el-card class="profile-card">
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
            <img
              v-if="userStore.userInfo.avatar"
              :src="userStore.userInfo.avatar"
              class="avatar-img"
            />
            <el-icon v-else class="avatar-placeholder"><Avatar /></el-icon>
          </el-upload>
          <div class="avatar-tip">点击上传/更换头像</div>
        </div>
      </el-form-item>

      <el-form-item label="用户名">
        <el-input v-model="form.username" placeholder="请输入用户名" />
      </el-form-item>

      <el-form-item label="邮箱">
        <el-input v-model="form.email" disabled />
      </el-form-item>

      <el-form-item>
        <el-button type="primary" @click="updateProfile">保存修改</el-button>
      </el-form-item>
    </el-form>
  </el-card>
</template>

<script setup>
import { reactive } from 'vue'
import { useUserStore } from '../stores/user'
import { ElMessage } from 'element-plus'
import { Avatar } from '@element-plus/icons-vue'

const userStore = useUserStore()
const form = reactive({
  username: userStore.userInfo.username || '',
  email: userStore.userInfo.email || ''
})

const handleAvatarSuccess = (res) => {
  if (res.url) {
    // 如果返回的是相对路径，补全为完整 URL
    const fullUrl = res.url.startsWith('http') ? res.url : `${window.location.origin}${res.url}`
    userStore.userInfo.avatar = fullUrl
    localStorage.setItem('userInfo', JSON.stringify(userStore.userInfo))
    ElMessage.success('头像更新成功')
  } else {
    ElMessage.warning('头像已上传，但未获取到URL')
  }
}

const handleAvatarError = () => {
  ElMessage.error('头像上传失败，请重试')
}

const updateProfile = async () => {
  try {
    await userStore.updateProfile({ username: form.username })
    ElMessage.success('资料更新成功')
  } catch (e) {
    ElMessage.error('更新失败')
  }
}
</script>

<style scoped>
.profile-card {
  max-width: 500px;
  margin: 0 auto;
}

.avatar-container {
  display: flex;
  align-items: center;
  gap: 16px;
}

.avatar-uploader {
  cursor: pointer;
}

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

.avatar-tip {
  font-size: 12px;
  color: #909399;
}
</style>