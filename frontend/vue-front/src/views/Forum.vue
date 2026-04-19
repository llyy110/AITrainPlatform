<template>
  <div class="forum-page">
    <!-- 搜索与发布栏 -->
    <div class="forum-header">
      <el-input
        v-model="searchKeyword"
        placeholder="搜索标题或内容"
        clearable
        style="width: 300px"
        @clear="fetchPosts"
        @keyup.enter="fetchPosts"
      >
        <template #append>
          <el-button @click="fetchPosts" :icon="Search" />
        </template>
      </el-input>
      <div class="header-actions">
        <el-button v-if="userStore.isLoggedIn" type="primary" @click="openCreateDialog">
          <el-icon><Edit /></el-icon> 发布新帖
        </el-button>
        <el-button v-else type="primary" @click="$router.push('/login')">
          登录后发布
        </el-button>
      </div>
    </div>

    <!-- 标签页：全部帖子 / 我的帖子 -->
    <el-tabs v-model="activeTab" @tab-change="handleTabChange">
      <el-tab-pane label="全部帖子" name="all" />
      <el-tab-pane v-if="userStore.isLoggedIn" label="我发布的帖子" name="my" />
    </el-tabs>

    <!-- 帖子卡片列表 -->
    <div class="post-list">
      <el-card
        v-for="post in filteredPosts"
        :key="post.id"
        class="post-card"
        shadow="hover"
        @click="viewPost(post.id)"
      >
        <div class="post-header">
          <h3 class="post-title">{{ post.title }}</h3>
          <div class="post-meta">
            <span class="author"><el-icon><User /></el-icon> {{ post.username }}</span>
            <span class="time"><el-icon><Clock /></el-icon> {{ formatTime(post.created_at) }}</span>
          </div>
        </div>
        <div class="post-content-preview">
          {{ stripHtml(post.content).substring(0, 200) }}{{ stripHtml(post.content).length > 200 ? '...' : '' }}
        </div>
        <div class="post-footer">
          <div class="stats">
            <span><el-icon><View /></el-icon> {{ post.view_count }}</span>
            <span><el-icon><Star /></el-icon> {{ post.like_count }}</span>
          </div>
          <div class="actions" @click.stop>
            <el-button link size="small" @click="viewPost(post.id)">查看详情</el-button>
            <template v-if="userStore.isLoggedIn && post.username === userStore.userInfo.username">
              <el-button link size="small" @click="editPost(post)">编辑</el-button>
              <el-button link size="small" type="danger" @click="deletePost(post.id)">删除</el-button>
            </template>
          </div>
        </div>
      </el-card>

      <el-empty v-if="filteredPosts.length === 0" description="暂无帖子" />
    </div>

    <!-- 分页 -->
    <div class="pagination-wrapper">
      <el-pagination
        v-model:current-page="currentPage"
        :page-size="pageSize"
        :total="totalFiltered"
        layout="prev, pager, next"
        @current-change="fetchPosts"
      />
    </div>

    <!-- 发布/编辑对话框（保持不变） -->
    <el-dialog v-model="dialogVisible" :title="editMode ? '编辑帖子' : '发布帖子'" width="700px">
      <el-form label-position="top">
        <el-form-item label="标题">
          <el-input v-model="form.title" placeholder="请输入标题" />
        </el-form-item>
        <el-form-item label="内容">
          <RichTextEditor v-model="form.content" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitPost">{{ editMode ? '保存' : '发布' }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, reactive, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, Edit, User, Clock, View, Star } from '@element-plus/icons-vue'
import api from '@/api'
import RichTextEditor from '@/components/RichTextEditor.vue'

const userStore = useUserStore()
const router = useRouter()
const posts = ref([])                // 原始全部帖子数据
const dialogVisible = ref(false)
const searchKeyword = ref('')
const currentPage = ref(1)
const pageSize = ref(10)
const total = ref(0)
const editMode = ref(false)
const currentPostId = ref(null)
const activeTab = ref('all')         // 当前标签页：all / my

const form = reactive({ title: '', content: '' })

// 获取帖子列表（每次切换标签或搜索时重新拉取，这里不做缓存简化逻辑）
const fetchPosts = async () => {
  try {
    const res = await api.get('/forum/posts', {
      params: {
        page: currentPage.value,
        page_size: pageSize.value,
        search: searchKeyword.value
      }
    })
    if (Array.isArray(res.data)) {
      posts.value = res.data
      total.value = res.data.length
    } else {
      posts.value = res.data.results || []
      total.value = res.data.count || 0
    }
  } catch (e) {
    ElMessage.error('获取帖子列表失败')
  }
}

// 根据标签页过滤后的帖子
const filteredPosts = computed(() => {
  if (activeTab.value === 'my' && userStore.isLoggedIn) {
    return posts.value.filter(p => p.username === userStore.userInfo.username)
  }
  return posts.value
})

// 过滤后的总数（用于分页显示）
const totalFiltered = computed(() => {
  if (activeTab.value === 'my' && userStore.isLoggedIn) {
    return filteredPosts.value.length
  }
  return total.value
})

// 切换标签时重新获取数据（可选：若想每次切换都刷新数据，可调用 fetchPosts；但当前已通过 computed 过滤，无需额外请求）
const handleTabChange = (tabName) => {
  // 如果切换到“我的帖子”，且之前未获取全部数据，可以强制刷新（但通常已获取）
  // 这里简单起见，不重复请求
}

const viewPost = (id) => router.push(`/forum/post/${id}`)

const openCreateDialog = () => {
  if (!userStore.isLoggedIn) {
    router.push('/login')
    return
  }
  editMode.value = false
  form.title = ''
  form.content = ''
  dialogVisible.value = true
}

const submitPost = async () => {
  try {
    if (editMode.value) {
      await api.put(`/forum/posts/${currentPostId.value}`, form)
      ElMessage.success('帖子更新成功')
    } else {
      await api.post('/forum/posts', form)
      ElMessage.success('帖子发布成功')
    }
    dialogVisible.value = false
    currentPage.value = 1
    await fetchPosts()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '操作失败')
  }
}

const editPost = (row) => {
  editMode.value = true
  currentPostId.value = row.id
  form.title = row.title
  form.content = row.content
  dialogVisible.value = true
}

const deletePost = async (id) => {
  try {
    await ElMessageBox.confirm('确定删除该帖子吗？', '提示', { type: 'warning' })
    await api.delete(`/forum/posts/${id}`)
    ElMessage.success('删除成功')
    await fetchPosts()
  } catch (e) {
    if (e !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

const formatTime = (time) => {
  return new Date(time).toLocaleString('zh-CN')
}

const stripHtml = (html) => {
  if (!html) return ''
  return html.replace(/<[^>]+>/g, '').replace(/&nbsp;/g, ' ')
}

onMounted(() => {
  fetchPosts()
})
</script>

<style scoped lang="scss">
.forum-page {
  max-width: 900px;
  margin: 0 auto;
}

.forum-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.post-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
  margin-top: 16px;
}

.post-card {
  cursor: pointer;
  transition: transform 0.2s, box-shadow 0.2s;
  &:hover {
    transform: translateY(-2px);
  }
  .post-header {
    margin-bottom: 12px;
    .post-title {
      margin: 0 0 8px 0;
      font-size: 18px;
      font-weight: 600;
      color: #303133;
    }
    .post-meta {
      display: flex;
      gap: 20px;
      font-size: 13px;
      color: #909399;
      span {
        display: flex;
        align-items: center;
        gap: 4px;
      }
    }
  }
  .post-content-preview {
    color: #606266;
    line-height: 1.6;
    margin-bottom: 16px;
    word-break: break-word;
  }
  .post-footer {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding-top: 8px;
    border-top: 1px solid #ebeef5;
    .stats {
      display: flex;
      gap: 16px;
      color: #909399;
      font-size: 13px;
      span {
        display: flex;
        align-items: center;
        gap: 4px;
      }
    }
    .actions {
      display: flex;
      gap: 8px;
    }
  }
}

.pagination-wrapper {
  margin-top: 24px;
  display: flex;
  justify-content: center;
}
</style>