<template>
  <div class="agent-float" @click="toggleChat">
    <el-icon size="28"><ChatDotRound /></el-icon>
  </div>

  <el-drawer
    v-model="visible"
    title="Neuro 智能助手"
    direction="rtl"
    size="420px"
    :with-header="true"
    class="agent-drawer"
  >
    <div class="chat-container">
      <div class="quick-questions">
        <el-button
          v-for="q in quickQuestions"
          :key="q"
          size="small"
          round
          @click="input = q; send()"
        >{{ q }}</el-button>
      </div>

      <div class="chat-messages" ref="msgContainer">
        <div
          v-for="(msg, idx) in messages"
          :key="idx"
          class="message-item"
          :class="[msg.role, { typing: msg.isTyping }]"
        >
          <div class="avatar">
            <el-avatar :size="32" :icon="msg.role === 'user' ? User : Service" />
          </div>
          <div class="bubble">
            <div class="content" v-html="formatContent(msg.content)"></div>
            <div class="meta" v-if="msg.role === 'assistant' && !msg.isTyping">
              <el-button link size="small" @click="copyContent(msg.content)">复制</el-button>
            </div>
          </div>
        </div>
        <div v-if="isTyping" class="message-item assistant typing">
          <div class="avatar"><el-avatar :size="32" :icon="Service" /></div>
          <div class="bubble"><span class="dot-flashing"></span></div>
        </div>
      </div>

      <div class="chat-input-area">
        <el-input
          v-model="input"
          placeholder="问问训练进度、调参建议..."
          @keyup.enter="send"
          :disabled="isTyping"
          clearable
        >
          <template #append>
            <el-button @click="send" :loading="isTyping" :icon="Promotion" />
          </template>
        </el-input>
        <el-button v-if="isTyping" link @click="stopGeneration">停止生成</el-button>
      </div>
    </div>
  </el-drawer>
</template>

<script setup>
import { ref, nextTick, watch } from 'vue'
import { ChatDotRound, User, Service, Promotion } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import api from '@/api'

const visible = ref(false)
const input = ref('')
const messages = ref([
  { role: 'assistant', content: '你好！我是 Neuro 助手，可以帮你查询训练进度、推荐参数、解释模型原理。试试下面的快捷提问吧！' }
])
const isTyping = ref(false)
const msgContainer = ref(null)
let abortController = null

const quickQuestions = ['当前训练进度？', '推荐一组CNN分类参数', '如何提高模型准确率？', 'BP神经网络原理']

const toggleChat = () => { visible.value = !visible.value }

const formatContent = (text) => {
  return text.replace(/\n/g, '<br>').replace(/`([^`]+)`/g, '<code>$1</code>')
}

const scrollToBottom = () => {
  nextTick(() => {
    if (msgContainer.value) {
      msgContainer.value.scrollTop = msgContainer.value.scrollHeight
    }
  })
}

const copyContent = (text) => {
  navigator.clipboard?.writeText(text).then(() => {
    ElMessage.success('已复制到剪贴板')
  }).catch(() => {
    ElMessage.error('复制失败')
  })
}

const typewriterEffect = (fullText, msgIndex) => {
  let i = 0
  messages.value[msgIndex].content = ''
  const timer = setInterval(() => {
    if (i < fullText.length) {
      messages.value[msgIndex].content += fullText.charAt(i)
      i++
      scrollToBottom()
    } else {
      clearInterval(timer)
      messages.value[msgIndex].isTyping = false
      isTyping.value = false
    }
  }, 25)
  return timer
}

const send = async () => {
  if (!input.value.trim() || isTyping.value) return
  const userMsg = { role: 'user', content: input.value.trim() }
  messages.value.push(userMsg)
  const query = input.value
  input.value = ''
  scrollToBottom()

  // 添加助手占位消息
  const assistantMsg = { role: 'assistant', content: '', isTyping: true }
  messages.value.push(assistantMsg)
  const msgIndex = messages.value.length - 1
  isTyping.value = true

  try {
    abortController = new AbortController()
    const res = await api.post('/train/agent/chat', { query }, { signal: abortController.signal })
    const answer = res.data.answer
    const timer = typewriterEffect(answer, msgIndex)
    abortController.signal.addEventListener('abort', () => clearInterval(timer))
  } catch (e) {
    if (e.name === 'AbortError') {
      messages.value[msgIndex].content += ' [已停止]'
    } else {
      messages.value[msgIndex].content = '服务繁忙，请稍后再试'
    }
    messages.value[msgIndex].isTyping = false
    isTyping.value = false
  }
}

const stopGeneration = () => {
  if (abortController) {
    abortController.abort()
    isTyping.value = false
  }
}

watch(visible, (val) => {
  if (val) scrollToBottom()
})
</script>

<style scoped lang="scss">
.agent-float {
  position: fixed;
  bottom: 30px;
  right: 30px;
  width: 60px;
  height: 60px;
  background: linear-gradient(135deg, #409eff, #6cb2ff);
  border-radius: 30px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  cursor: pointer;
  box-shadow: 0 10px 25px -5px #409eff80;
  z-index: 2000;
  transition: all 0.3s;
  &:hover {
    transform: scale(1.05);
    box-shadow: 0 15px 30px -5px #409eff;
  }
}

.agent-drawer {
  :deep(.el-drawer__header) {
    margin-bottom: 0;
    padding: 16px 20px;
    border-bottom: 1px solid rgba(0,0,0,0.05);
    font-weight: 600;
  }
  :deep(.el-drawer__body) {
    padding: 0;
    display: flex;
    flex-direction: column;
  }
}

.chat-container {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: #fafbfc;
  .dark & { background: #1a1e2a; }
}

.quick-questions {
  padding: 12px 16px;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  border-bottom: 1px solid #eee;
  .dark & { border-bottom-color: #2a2f3a; }
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.message-item {
  display: flex;
  gap: 10px;
  &.user { flex-direction: row-reverse; }
  .bubble {
    max-width: 80%;
    background: white;
    padding: 12px 16px;
    border-radius: 20px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.02);
    .dark & { background: #2a2f3a; }
    .user & {
      background: #409eff;
      color: white;
    }
    .meta {
      margin-top: 6px;
      text-align: right;
      .el-button { color: inherit; opacity: 0.7; }
    }
  }
  .content code {
    background: rgba(0,0,0,0.05);
    padding: 2px 6px;
    border-radius: 6px;
    font-family: monospace;
  }
}

.dot-flashing {
  position: relative;
  width: 8px;
  height: 8px;
  border-radius: 4px;
  background-color: #409eff;
  animation: dot-flashing 1s infinite linear alternate;
  &::before, &::after {
    content: '';
    display: inline-block;
    position: absolute;
    top: 0;
  }
  &::before {
    left: -15px;
    width: 8px;
    height: 8px;
    border-radius: 4px;
    background-color: #409eff;
    animation: dot-flashing 1s infinite alternate;
    animation-delay: 0s;
  }
  &::after {
    left: 15px;
    width: 8px;
    height: 8px;
    border-radius: 4px;
    background-color: #409eff;
    animation: dot-flashing 1s infinite alternate;
    animation-delay: 0.5s;
  }
}

@keyframes dot-flashing {
  0% { opacity: 0.3; }
  100% { opacity: 1; }
}

.chat-input-area {
  padding: 16px;
  border-top: 1px solid #eee;
  background: white;
  .dark & {
    background: #1e2430;
    border-top-color: #2a2f3a;
  }
}
</style>