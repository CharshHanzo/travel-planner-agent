<template>
  <div class="amap-container">
    <div ref="mapContainer" class="amap"></div>
    <div v-if="!loaded" class="map-loading">
      <el-icon><Loading /></el-icon>
      <span>地图加载中...</span>
    </div>
    <div v-if="error" class="map-error">
      <span>{{ error }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch, nextTick } from 'vue'
import { Loading } from '@element-plus/icons-vue'

const props = defineProps<{
  points: Array<{
    name: string
    lng: number
    lat: number
    type: 'activity' | 'restaurant'
    description?: string
    duration?: string
    cuisine?: string
    price_per_person?: number
    rating?: number
  }>
  route?: {
    segments: Array<{
      from: string
      to: string
      path: number[][]
      distance: string
      duration: string
    }>
  } | null
  height?: string
}>()

const mapContainer = ref<HTMLElement | null>(null)
const loaded = ref(false)
const error = ref('')

let map: any = null
let markers: any[] = []
let polyline: any = null
let infoWindow: any = null

function initMap() {
  if (!mapContainer.value) return
  
  const AMap = (window as any).AMap
  if (!AMap) {
    error.value = '高德地图加载失败，请刷新重试'
    return
  }
  
  // 根据第一个标记点确定初始中心
  let center: [number, number] = [113.3245, 23.1064]  // 默认广州
  if (props.points && props.points.length > 0) {
    center = [props.points[0].lng, props.points[0].lat]
  }
  
  try {
    map = new AMap.Map(mapContainer.value, {
      zoom: 13,
      center: center,  // 动态中心
      resizeEnable: true,
    })
    
    infoWindow = new AMap.InfoWindow({
      offset: new AMap.Pixel(0, -30),
    })
    
    loaded.value = true
  } catch (e) {
    console.error('地图初始化失败:', e)
    error.value = '地图初始化失败'
    return
  }
  
  try {
    renderPoints()
  } catch (e) {
    console.error('渲染标记点失败:', e)
  }
}

function renderPoints() {
  if (!map || !loaded.value) return
  
  const AMap = (window as any).AMap
  if (!AMap) return
  
  markers.forEach(m => {
    try { map.remove(m) } catch (e) {}
  })
  markers = []
  
  if (polyline) {
    try { map.remove(polyline) } catch (e) {}
    polyline = null
  }
  
  const bounds: any[] = []
  
  if (!props.points || props.points.length === 0) {
    return
  }
  
  props.points.forEach(point => {
    if (!point.lng || !point.lat) return
    
    const position = new AMap.LngLat(point.lng, point.lat)
    bounds.push(position)
    
    const iconUrl = point.type === 'activity'
      ? 'https://webapi.amap.com/theme/v1.3/markers/n/mark_b.png'
      : 'https://webapi.amap.com/theme/v1.3/markers/n/mark_r.png'
    
    const marker = new AMap.Marker({
      position: position,
      title: point.name,
      icon: new AMap.Icon({
        size: new AMap.Size(24, 24),
        image: iconUrl,
      }),
    })
    
    const content = buildInfoContent(point)
    marker.on('click', () => {
      infoWindow.setContent(content)
      infoWindow.open(map, marker.getPosition())
    })
    
    marker.setMap(map)
    markers.push(marker)
  })
  
  if (props.route?.segments && props.route.segments.length > 0) {
    const allPaths: any[] = []
    props.route.segments.forEach(seg => {
      if (seg.path && seg.path.length > 0) {
        seg.path.forEach((p: number[]) => {
          if (p && p.length >= 2) {
            allPaths.push(new AMap.LngLat(p[0], p[1]))
          }
        })
      }
    })
    
    if (allPaths.length > 0) {
      try {
        polyline = new AMap.Polyline({
          path: allPaths,
          strokeColor: '#1677ff',
          strokeWeight: 4,
          strokeOpacity: 0.8,
          showDir: true,
        })
        polyline.setMap(map)
      } catch (e) {
        console.error('路线渲染失败:', e)
      }
    }
  }
  
  const validBounds = bounds.filter(b => b && typeof b.getBounds === 'function')
  if (validBounds.length > 0) {
    try {
      map.setFitView(validBounds, false, [60, 60, 60, 60])
    } catch (e) {
      console.error('自动缩放失败:', e)
    }
  }
}

function buildInfoContent(point: any): string {
  let html = `<div style="padding:8px;max-width:200px;">`
  html += `<h4 style="margin:0 0 4px 0;">${point.name}</h4>`
  
  if (point.type === 'activity') {
    if (point.description) html += `<p style="margin:2px 0;font-size:12px;color:#666;">${point.description}</p>`
    if (point.duration) html += `<p style="margin:2px 0;font-size:12px;">⏱ ${point.duration}</p>`
  } else {
    if (point.cuisine) html += `<p style="margin:2px 0;font-size:12px;color:#666;">${point.cuisine}</p>`
    if (point.price_per_person) html += `<p style="margin:2px 0;font-size:12px;">💰 人均¥${point.price_per_person}</p>`
    if (point.rating) html += `<p style="margin:2px 0;font-size:12px;">⭐ ${point.rating}</p>`
  }
  
  html += `</div>`
  return html
}

watch(() => props.points, async () => {
  await nextTick()
  if (loaded.value) {
    renderPoints()
  }
}, { deep: true })

onMounted(() => {
  let attempts = 0
  const maxAttempts = 50
  
  const checkAMap = setInterval(() => {
    attempts++
    if ((window as any).AMap) {
      clearInterval(checkAMap)
      initMap()
    } else if ((window as any).__amap_loaded__ && attempts > 5) {
      console.log('等待 AMap 初始化...')
    } else if (attempts >= maxAttempts) {
      clearInterval(checkAMap)
      error.value = '地图加载超时，请检查网络或 API Key'
    }
  }, 200)
})

defineExpose({
  refresh: renderPoints,
})
</script>

<style lang="scss" scoped>
.amap-container {
  position: relative;
  border-radius: 12px;
  overflow: hidden;
  margin: 16px 0;
  
  .amap {
    width: 100%;
    height: 400px;
    min-height: 300px;
  }
  
  .map-loading,
  .map-error {
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 16px 24px;
    background: white;
    border-radius: 8px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
    font-size: 14px;
    color: #606266;
  }
  
  .map-error {
    color: #f56c6c;
  }
}
</style>
