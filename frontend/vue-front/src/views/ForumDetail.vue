<template>
  <div class="post-detail">
    <el-button link @click="$router.push('/forum')" style="margin-bottom: 20px">
      <el-icon><ArrowLeft /></el-icon> 返回论坛
    </el-button>

    <!-- 帖子内容卡片 -->
    <el-card v-if="post?.id" class="post-card">
      <h1>{{ post.title }}</h1>
      <div class="post-meta">
        <span><el-icon><User /></el-icon> {{ post.username }}</span>
        <span><el-icon><Clock /></el-icon> {{ formatTime(post.created_at) }}</span>
        <span><el-icon><View /></el-icon> {{ post.view_count }} 次浏览</span>
      </div>
      <el-divider />
      <div class="post-content ql-editor" v-html="sanitizeHtml(post.content)"></div>
    </el-card>

    <!-- 评论区 -->
    <el-card class="comment-card" style="margin-top: 20px" v-loading="loadingComments">
      <template #header>
        <span>评论 ({{ comments.length }})</span>
      </template>
      <div class="comment-list">
        <div v-for="c in comments" :key="c.id" class="comment-item">
          <div class="comment-header">
            <span class="comment-author">{{ c.username }}</span>
            <span class="comment-time">{{ formatTime(c.created_at) }}</span>
          </div>
          <div class="comment-content">{{ c.content }}</div>
        </div>
        <el-empty v-if="comments.length === 0 && !loadingComments" description="暂无评论，快来抢沙发吧～" />
      </div>

      <!-- 评论输入框：仅登录可见 -->
      <div v-if="userStore.isLoggedIn" class="comment-input">
        <el-input
          v-model="newComment"
          type="textarea"
          :rows="3"
          placeholder="写下你的评论..."
          maxlength="500"
          show-word-limit
        />
        <el-button type="primary" @click="submitComment" :loading="submitting" style="margin-top: 10px">
          发表评论
        </el-button>
      </div>
      <div v-else class="login-tip">
        <el-button @click="$router.push('/login')" type="primary">登录后发表评论</el-button>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { ElMessage } from 'element-plus'
import { ArrowLeft, User, Clock, View } from '@element-plus/icons-vue'
import api from '@/api'
import DOMPurify from 'dompurify'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

const post = ref(null)
const comments = ref([])
const newComment = ref('')
const loadingComments = ref(false)
const submitting = ref(false)

// 获取帖子详情
const fetchPost = async () => {
  try {
    const res = await api.get(`/forum/posts/${route.params.id}`)
    post.value = res.data || null
  } catch (e) {
    ElMessage.error('获取帖子失败')
    router.push('/forum')
  }
}

// 获取评论列表
const fetchComments = async () => {
  loadingComments.value = true
  try {
    const res = await api.get(`/forum/posts/${route.params.id}/comments`)
    // 兼容数组和分页对象（DRF 默认不分页返回数组，但若未来配置分页则返回对象）
    if (Array.isArray(res.data)) {
      comments.value = res.data
    } else if (res.data && Array.isArray(res.data.results)) {
      comments.value = res.data.results
    } else {
      comments.value = []
    }
    console.log('评论数据:', comments.value) // 调试用，可删除
  } catch (e) {
    ElMessage.error('获取评论失败')
    comments.value = []
  } finally {
    loadingComments.value = false
  }
}

// 提交评论
const submitComment = async () => {
  const content = newComment.value.trim()
  if (!content) {
    ElMessage.warning('评论内容不能为空')
    return
  }
  if (!post.value?.id) return

  submitting.value = true
  try {
    await api.post('/forum/comments', {
      post: post.value.id,
      content: content
    })
    ElMessage.success('评论成功')
    newComment.value = ''
    // 等待一小段时间确保数据库写入完成
    await new Promise(resolve => setTimeout(resolve, 100))
    await fetchComments()
  } catch (e) {
    const msg = e.response?.data?.detail || '评论失败'
    ElMessage.error(msg)
  } finally {
    submitting.value = false
  }
}

// 富文本安全过滤
const sanitizeHtml = (html) => {
  if (!html) return ''
  return DOMPurify.sanitize(html, {
    ALLOWED_TAGS: ['p', 'br', 'strong', 'em', 'u', 's', 'blockquote', 'pre', 'code', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'ul', 'ol', 'li', 'a', 'img', 'span', 'div'],
    ALLOWED_ATTR: ['href', 'src', 'alt', 'title', 'class', 'style']
  })
}

// 时间格式化
const formatTime = (time) => {
  if (!time) return ''
  return new Date(time).toLocaleString('zh-CN')
}

onMounted(() => {
  fetchPost()
  fetchComments()
})
</script>

<style scoped>
@import 'quill/dist/quill.core.css';
@import 'quill/dist/quill.snow.css';

.post-detail {
  max-width: 900px;
  margin: 0 auto;
}

.post-card h1 {
  margin-top: 0;
  margin-bottom: 15px;
}

.post-meta {
  display: flex;
  gap: 20px;
  color: #909399;
  font-size: 14px;
}

.post-meta span {
  display: flex;
  align-items: center;
  gap: 4px;
}

.post-content {
  padding: 20px 0;
  line-height: 1.8;
}

.post-content img {
  max-width: 100%;
  height: auto;
}

.comment-list {
  margin-bottom: 20px;
}

.comment-item {
  padding: 15px 0;
  border-bottom: 1px solid #ebeef5;
}

.comment-item:last-child {
  border-bottom: none;
}

.comment-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 8px;
}

.comment-author {
  font-weight: 600;
  color: #303133;
}

.comment-time {
  font-size: 12px;
  color: #909399;
}

.comment-content {
  color: #606266;
  line-height: 1.6;
  word-break: break-word;
}

.comment-input {
  margin-top: 20px;
}

.login-tip {
  text-align: center;
  padding: 20px;
  background: #f5f7fa;
  border-radius: 8px;
}
</style>