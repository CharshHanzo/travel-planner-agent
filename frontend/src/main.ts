import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import './assets/styles/main.scss'

// 动态加载高德地图 JS API
function loadAMap() {
  const apiKey = import.meta.env.VITE_AMAP_KEY
  
  if (!apiKey || apiKey === 'your_amap_key_here') {
    console.error('高德地图 API Key 未配置，请检查 .env 文件中的 VITE_AMAP_KEY')
    return
  }
  
  const script = document.createElement('script')
  script.src = `https://webapi.amap.com/maps?v=2.0&key=${apiKey}&plugin=AMap.Polyline,AMap.Marker`
  script.onload = () => {
    console.log('高德地图 JS API 加载成功')
    ;(window as any).__amap_loaded__ = true
  }
  script.onerror = () => {
    console.error('高德地图 JS API 加载失败，请检查 API Key 是否有效')
  }
  document.head.appendChild(script)
}

loadAMap()

const app = createApp(App)

app.use(createPinia())
app.use(router)
app.use(ElementPlus)

app.mount('#app')