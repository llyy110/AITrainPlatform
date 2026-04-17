import {defineConfig} from 'vite'
import vue from '@vitejs/plugin-vue'
import {fileURLToPath, URL} from 'node:url'

// https://vite.dev/config/
export default defineConfig({
    plugins: [vue()],
    resolve: {
        alias: {
            '@': fileURLToPath(new URL('./src', import.meta.url))
        }
    },
    server: {
        port: 5173,
        proxy: {
            // 更具体的规则要放在前面
            '/api/train': {
                target: 'http://localhost:8001',   // FastAPI 服务地址
                changeOrigin: true,
                rewrite: (path) => path.replace(/^\/api/, '')
            },
            '/api': {
                target: 'http://localhost:8000',  // 后端网关地址
                changeOrigin: true,
                rewrite: (path) => path.replace(/^\/api/, '')
            },
            '/media': 'http://localhost:8000'


        }
    }
})
