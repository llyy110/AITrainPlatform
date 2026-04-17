<template>
  <div>
    <!-- 搜索框 -->
    <el-input
      v-model="searchKeyword"
      placeholder="搜索标题或内容"
      clearable
      style="width: 300px; margin-right: 16px"
      @clear="fetchPosts"
      @keyup.enter="fetchPosts"
    >
      <template #append>
        <el-button @click="fetchPosts" :icon="Search" />
      </template>
    </el-input>
    <el-button type="primary" @click="openCreateDialog">发布新帖</el-button>

    <el-table :data="posts" style="margin-top: 20px">
      <el-table-column prop="title" label="标题" />
      <el-table-column prop="username" label="作者" />
      <el-table-column prop="created_at" label="发布时间" />
      <el-table-column label="操作" width="200">
        <template #default="{ row }">
          <el-button link @click="viewPost(row.id)">查看详情</el-button>
          <el-button v-if="row.username === userStore.userInfo.username" link @click="editPost(row)">编辑</el-button>
          <el-button v-if="row.username === userStore.userInfo.username" link type="danger" @click="deletePost(row.id)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 分页 -->
    <el-pagination
      v-model:current-page="currentPage"
      :page-size="pageSize"
      :total="total"
      layout="prev, pager, next"
      @current-change="fetchPosts"
      style="margin-top: 20px"
    />

    <!-- 发布/编辑帖子对话框 -->
    <el-dialog v-model="dialogVisible" :title="editMode ? '编辑帖子' : '发布帖子'">
      <el-input v-model="form.title" placeholder="标题" />
      <el-input type="textarea" v-model="form.content" placeholder="内容" rows="6" />
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitPost">{{ editMode ? '保存' : '发布' }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '../stores/user'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search } from '@element-plus/icons-vue'
import api from '../api'

const userStore = useUserStore()
const router = useRouter()
const posts = ref([])
const dialogVisible = ref(false)
const searchKeyword = ref('')
const currentPage = ref(1)
const pageSize = ref(10)
const total = ref(0)
const editMode = ref(false)
const currentPostId = ref(null)

const form = reactive({ title: '', content: '' })

const fetchPosts = async () => {
  try {
    const res = await api.get('/forum/posts', {
      params: {
        page: currentPage.value,
        page_size: pageSize.value,
        search: searchKeyword.value
      }
    })
    // 处理分页数据结构
    posts.value = res.data.results || []
    total.value = res.data.count || 0
  } catch (e) {
    ElMessage.error('获取帖子列表失败')
  }
}

const viewPost = (id) => router.push(`/forum/post/${id}`)

const openCreateDialog = () => {
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
    // 重置到第一页并刷新列表
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

onMounted(() => {
  fetchPosts()
})
</script>