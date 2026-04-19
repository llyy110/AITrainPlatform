import {defineStore} from 'pinia'
import api from '../api'

export const useTrainingStore = defineStore('training', {
    state: () => ({
        currentTaskId: localStorage.getItem('currentTaskId') || null,
        progress: null,
        chartData: []
    }),
    actions: {
        async startTraining(params) {
            const res = await api.post('/train/training/start', params)
            this.setCurrentTaskId(res.data.task_id)
            return res.data
        },
        async getProgress(taskId) {
            const res = await api.get(`/train/training/progress/${taskId}`)
            this.progress = res.data
            return res.data
        },
        async getHistory(params) {
            return await api.get('/train/training/records', {params})
        },
        async getRecordDetail(recordId) {
            return await api.get(`/train/training/records/${recordId}`)
        },
        async exportRecord(recordId) {
            return await api.get(`/train/training/records/${recordId}/export`, {responseType: 'blob'})
        },
        // 新增：获取用户最新训练记录
        async getLatestTraining() {
            try {
                const res = await api.get('/train/training/latest')
                return res.data
            } catch (e) {
                console.error('获取最新训练记录失败', e)
                return null
            }
        },
        setCurrentTaskId(taskId) {
            this.currentTaskId = taskId
            if (taskId) {
                localStorage.setItem('currentTaskId', taskId)
                // 同时存储任务开始时间，用于10分钟过期判断
                localStorage.setItem('currentTaskStartTime', Date.now().toString())
            } else {
                localStorage.removeItem('currentTaskId')
                localStorage.removeItem('currentTaskStartTime')
            }
        },
        clearCurrentTaskId() {
            this.currentTaskId = null
            localStorage.removeItem('currentTaskId')
            localStorage.removeItem('currentTaskStartTime')
        },
        updateChartData(newData) {
            this.chartData = newData
        },
        // 检查任务是否超过10分钟（用于登录恢复时判断）
        isTaskExpired() {
            const startTime = localStorage.getItem('currentTaskStartTime')
            if (!startTime) return true
            const elapsed = Date.now() - parseInt(startTime)
            return elapsed > 10 * 60 * 1000 // 10分钟
        },
        async savePreset(name, params) {
            return await api.post('/train/presets', {name, params})
        },
        async getPresets() {
            return await api.get('/train/presets')
        }
    }
})