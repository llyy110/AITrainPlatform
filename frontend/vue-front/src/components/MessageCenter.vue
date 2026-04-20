<template>
  <div class="message-center">
    <!-- 消息图标 -->
    <el-badge :value="unreadCount" :max="99" :hidden="unreadCount === 0">
      <el-button :icon="ChatDotRound" circle @click="toggleDrawer"/>
    </el-badge>

    <!-- 消息抽屉 -->
    <el-drawer
        v-model="drawerVisible"
        title="消息中心"
        direction="rtl"
        size="420px"
        :append-to-body="true"
    >
      <el-tabs v-model="activeTab" class="message-tabs">
        <!-- 私信列表 -->
        <el-tab-pane label="私信" name="chat">
          <div v-loading="loadingConversations" class="conversation-list">
            <div
                v-for="conv in conversations"
                :key="conv.id"
                class="conversation-item"
                @click="openChat(conv)"
            >
              <el-avatar :size="40" :src="conv.other_participant?.avatar"/>
              <div class="conv-info">
                <div class="conv-header">
                  <span class="conv-name">{{ conv.other_participant?.username || '未知用户' }}</span>
                  <span class="conv-time">{{ formatTime(conv.last_message?.created_at) }}</span>
                </div>
                <div class="conv-last">
                  <span class="last-message">{{ conv.last_message?.content || '暂无消息' }}</span>
                  <el-badge v-if="conv.unread_count > 0" :value="conv.unread_count" type="danger"/>
                </div>
              </div>
            </div>
            <el-empty v-if="!loadingConversations && conversations.length === 0" description="暂无私信"/>
          </div>
          <div class="new-chat">
            <el-button type="primary" plain @click="showUserSelector = true">发起新私信</el-button>
          </div>
        </el-tab-pane>

        <!-- 公告列表 -->
        <el-tab-pane label="公告" name="announcement">
          <div v-if="isAdmin" class="publish-announcement">
            <el-button type="primary" size="small" @click="openPublishDialog">
              <el-icon>
                <Plus/>
              </el-icon>
              发布公告
            </el-button>
          </div>
          <div v-loading="loadingAnnouncements" class="announcement-list">
            <div v-for="ann in announcements" :key="ann.id" class="announcement-item">
              <div class="ann-header">
                <span class="ann-title">{{ ann.title }}</span>
                <span class="ann-time">{{ formatTime(ann.created_at) }}</span>
              </div>
              <div class="ann-content" v-html="ann.content"></div>
              <div class="ann-footer">发布者：{{ ann.publisher_name }}</div>
            </div>
            <el-empty v-if="!loadingAnnouncements && announcements.length === 0" description="暂无公告"/>
          </div>
        </el-tab-pane>
      </el-tabs>
    </el-drawer>

    <!-- 发布公告对话框 -->
    <el-dialog v-model="publishDialogVisible" title="发布公告" width="650px" :close-on-click-modal="false">
      <el-form label-position="top">
        <el-form-item label="标题" required>
          <el-input v-model="announcementForm.title" placeholder="请输入公告标题"/>
        </el-form-item>
        <el-form-item label="内容" required>
          <RichTextEditor v-model="announcementForm.content"/>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="publishDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="publishAnnouncement" :loading="publishing">发布</el-button>
      </template>
    </el-dialog>

    <!-- 用户选择对话框 -->
    <el-dialog v-model="showUserSelector" title="选择聊天对象" width="400px">
      <el-select
          v-model="selectedUserId"
          filterable
          remote
          reserve-keyword
          placeholder="输入用户名搜索"
          :remote-method="searchUsers"
          :loading="searching"
          style="width: 100%"
      >
        <el-option v-for="user in userOptions" :key="user.id" :label="user.username" :value="user.id"/>
      </el-select>
      <template #footer>
        <el-button @click="showUserSelector = false">取消</el-button>
        <el-button type="primary" @click="startConversation" :disabled="!selectedUserId">开始聊天</el-button>
      </template>
    </el-dialog>

    <!-- 聊天窗口 -->
    <el-drawer
        v-model="chatWindowVisible"
        :title="currentChatUser?.username || '聊天'"
        direction="rtl"
        size="450px"
        :with-header="true"
        @close="closeChat"
        class="chat-drawer"
    >
      <div class="chat-window">
        <div class="message-list" ref="messageList" v-loading="loadingMessages">
          <div
              v-for="msg in currentMessages"
              :key="msg.id"
              class="message-item"
              :class="{ 'self': msg.sender?.id === currentUserId }"
          >
            <el-avatar :size="32" :src="msg.sender?.avatar"/>
            <div class="message-bubble">
              <div class="message-content">{{ msg.content }}</div>
              <div class="message-time">{{ formatTime(msg.created_at) }}</div>
            </div>
          </div>
          <el-empty v-if="!loadingMessages && currentMessages.length === 0" description="暂无消息"/>
        </div>
        <div class="message-input">
          <el-input
              v-model="newMessage"
              type="textarea"
              :rows="3"
              placeholder="输入消息..."
              @keyup.enter.ctrl="sendMessage"
          />
          <el-button type="primary" @click="sendMessage" :loading="sending">发送</el-button>
        </div>
      </div>
    </el-drawer>
  </div>
</template>

<script setup>
import {computed, nextTick, onMounted, onUnmounted, ref} from 'vue'
import {ChatDotRound, Plus} from '@element-plus/icons-vue'
import {ElMessage} from 'element-plus'
import api from '@/api'
import {useUserStore} from '@/stores/user'
import RichTextEditor from '@/components/RichTextEditor.vue'

const userStore = useUserStore()

const currentUserId = computed(() => userStore.userInfo?.id)
const isAdmin = computed(() => userStore.userInfo?.is_staff || false)

const drawerVisible = ref(false)
const activeTab = ref('chat')
const unreadCount = ref(0)
const conversations = ref([])
const announcements = ref([])
const loadingConversations = ref(false)
const loadingAnnouncements = ref(false)
const loadingMessages = ref(false)
const showUserSelector = ref(false)
const selectedUserId = ref(null)
const userOptions = ref([])
const searching = ref(false)
const chatWindowVisible = ref(false)
const currentConversationId = ref(null)
const currentChatUser = ref(null)
const currentMessages = ref([])
const newMessage = ref('')
const sending = ref(false)
const messageList = ref(null)

const publishDialogVisible = ref(false)
const publishing = ref(false)
const announcementForm = ref({title: '', content: ''})

let pollTimer = null

const ensureArray = (data) => {
  if (Array.isArray(data)) return data
  if (data && Array.isArray(data.results)) return data.results
  return []
}

const fetchUnreadCount = async () => {
  try {
    const res = await api.get('/chat/messages/unread/')
    unreadCount.value = res.data?.unread_count || 0
  } catch (e) {
  }
}

const fetchConversations = async () => {
  loadingConversations.value = true
  try {
    const res = await api.get('/chat/conversations/')
    conversations.value = ensureArray(res.data)
  } catch (e) {
    conversations.value = []
  } finally {
    loadingConversations.value = false
  }
}

const fetchAnnouncements = async () => {
  loadingAnnouncements.value = true
  try {
    const res = await api.get('/chat/announcements/')
    announcements.value = ensureArray(res.data)
  } catch (e) {
    announcements.value = []
  } finally {
    loadingAnnouncements.value = false
  }
}

const fetchMessages = async () => {
  if (!currentConversationId.value) return
  loadingMessages.value = true
  try {
    const res = await api.get(`/chat/conversations/${currentConversationId.value}/messages/`)
    currentMessages.value = ensureArray(res.data)
    scrollToBottom()
  } catch (e) {
    ElMessage.error('获取消息失败')
    currentMessages.value = []
  } finally {
    loadingMessages.value = false
  }
}

const searchUsers = async (query) => {
  if (!query) {
    userOptions.value = []
    return
  }
  searching.value = true
  try {
    const res = await api.get('/user/search/', {params: {q: query}})
    userOptions.value = ensureArray(res.data)
  } catch (e) {
    ElMessage.error('搜索用户失败')
  } finally {
    searching.value = false
  }
}

const startConversation = async () => {
  try {
    const res = await api.post('/chat/conversations/', {user_id: selectedUserId.value})
    showUserSelector.value = false
    selectedUserId.value = null
    await fetchConversations()
    const conv = conversations.value.find(c => c.id === res.data.id)
    if (conv) openChat(conv)
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '创建会话失败')
  }
}

const openChat = (conv) => {
  currentConversationId.value = conv.id
  currentChatUser.value = conv.other_participant
  chatWindowVisible.value = true
  drawerVisible.value = false
  fetchMessages()
  api.post(`/chat/conversations/${conv.id}/read/`).then(() => {
    fetchUnreadCount()
    fetchConversations()
  })
}

const closeChat = () => {
  currentConversationId.value = null
  currentChatUser.value = null
  currentMessages.value = []
}

const sendMessage = async () => {
  if (!newMessage.value.trim()) return
  sending.value = true
  try {
    await api.post(`/chat/conversations/${currentConversationId.value}/messages/`, {
      content: newMessage.value.trim()
    })
    newMessage.value = ''
    await fetchMessages()
    await fetchConversations()
  } catch (e) {
    ElMessage.error('发送失败')
  } finally {
    sending.value = false
  }
}

const openPublishDialog = () => {
  announcementForm.value = {title: '', content: ''}
  publishDialogVisible.value = true
}

const publishAnnouncement = async () => {
  if (!announcementForm.value.title.trim() || !announcementForm.value.content.trim()) {
    ElMessage.warning('请填写完整')
    return
  }
  publishing.value = true
  try {
    await api.post('/chat/announcements/create/', announcementForm.value)
    ElMessage.success('公告发布成功')
    publishDialogVisible.value = false
    fetchAnnouncements()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '发布失败')
  } finally {
    publishing.value = false
  }
}

const formatTime = (time) => {
  if (!time) return ''
  const date = new Date(time)
  const now = new Date()
  const diff = now - date
  if (diff < 60000) return '刚刚'
  if (diff < 3600000) return `${Math.floor(diff / 60000)}分钟前`
  if (date.toDateString() === now.toDateString()) {
    return date.toLocaleTimeString('zh-CN', {hour: '2-digit', minute: '2-digit'})
  }
  return date.toLocaleDateString('zh-CN')
}

const scrollToBottom = () => {
  nextTick(() => {
    if (messageList.value) {
      messageList.value.scrollTop = messageList.value.scrollHeight
    }
  })
}

const toggleDrawer = () => {
  drawerVisible.value = !drawerVisible.value
  if (drawerVisible.value) {
    fetchConversations()
    fetchAnnouncements()
  }
}

const startPolling = () => {
  if (pollTimer) clearInterval(pollTimer)
  pollTimer = setInterval(() => {
    if (userStore.isLoggedIn) {
      fetchUnreadCount()
      if (drawerVisible.value) fetchConversations()
      if (chatWindowVisible.value && currentConversationId.value) fetchMessages()
    }
  }, 5000)
}

onMounted(() => {
  if (userStore.isLoggedIn) {
    fetchUnreadCount()
    startPolling()
  }
})

onUnmounted(() => {
  if (pollTimer) clearInterval(pollTimer)
})
</script>

<style scoped lang="scss">
.message-center {
  display: inline-block;
}

// ========== 强制修复 Element Plus 抽屉样式污染 ==========
.message-drawer,
.chat-drawer {
  :deep(.el-drawer) {
    padding: 0 !important; // 移除异常 padding
    box-sizing: border-box !important;
  }

  :deep(.el-drawer__header) {
    padding: 16px 20px;
    margin-bottom: 0;
    border-bottom: 1px solid #eee;
  }

  :deep(.el-drawer__body) {
    padding: 0 !important;
    height: 100%;
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }
}

.message-tabs {
  flex: 1;
  display: flex;
  flex-direction: column;
  height: 100%;

  :deep(.el-tabs__header) {
    padding: 0 16px;
  }

  :deep(.el-tabs__content) {
    flex: 1;
    overflow-y: auto;
    padding: 0 16px;
  }
}

.conversation-list {
  .conversation-item {
    display: flex;
    align-items: center;
    padding: 12px 0;
    cursor: pointer;
    border-bottom: 1px solid #eee;

    &:hover {
      background: #f5f7fa;
    }

    .conv-info {
      flex: 1;
      margin-left: 12px;

      .conv-header {
        display: flex;
        justify-content: space-between;
        margin-bottom: 4px;

        .conv-name {
          font-weight: 500;
        }

        .conv-time {
          font-size: 12px;
          color: #999;
        }
      }

      .conv-last {
        display: flex;
        justify-content: space-between;
        align-items: center;

        .last-message {
          color: #666;
          font-size: 13px;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
          max-width: 200px;
        }
      }
    }
  }
}

.new-chat {
  padding: 16px 0;
  text-align: center;
}

.publish-announcement {
  padding: 12px 0;
  text-align: right;
}

.announcement-list {
  .announcement-item {
    padding: 12px 0;
    border-bottom: 1px solid #eee;

    .ann-header {
      display: flex;
      justify-content: space-between;
      margin-bottom: 8px;

      .ann-title {
        font-weight: 600;
      }

      .ann-time {
        font-size: 12px;
        color: #999;
      }
    }

    .ann-content {
      color: #666;
      margin-bottom: 8px;

      :deep(img) {
        max-width: 100%;
        height: auto;
      }
    }

    .ann-footer {
      font-size: 12px;
      color: #999;
    }
  }
}

.chat-window {
  display: flex;
  flex-direction: column;
  height: 100%;

  .message-list {
    flex: 1;
    overflow-y: auto;
    padding: 16px;

    .message-item {
      display: flex;
      margin-bottom: 16px;

      &.self {
        flex-direction: row-reverse;

        .message-bubble {
          background: #409eff;
          color: white;
          margin-left: 0;
          margin-right: 12px;
        }
      }

      .message-bubble {
        background: #f0f0f0;
        padding: 10px 14px;
        border-radius: 12px;
        margin-left: 12px;
        max-width: 70%;

        .message-content {
          word-break: break-word;
        }

        .message-time {
          font-size: 11px;
          color: #999;
          margin-top: 4px;
          text-align: right;
        }
      }
    }
  }

  .message-input {
    padding: 16px;
    border-top: 1px solid #eee;

    textarea {
      margin-bottom: 10px;
    }
  }
}
</style>