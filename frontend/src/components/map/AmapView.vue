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
  
  // 改用 DrivingRoute 规划真实道路路线
  renderRoute()
  
  const validBounds = bounds.filter(b => b && typeof b.getBounds === 'function')
  if (validBounds.length > 0) {
    try {
      map.setFitView(validBounds, false, [60, 60, 60, 60])
    } catch (e) {
      console.error('自动缩放失败:', e)
    }
  }
}

function renderRoute() {
  if (!map || !props.points || props.points.length < 2) return
  
  const AMap = (window as any).AMap
  if (!AMap) return
  
  // 清除旧路线
  if (polyline) {
    try { map.remove(polyline) } catch (e) {}
    polyline = null
  }
  
  // 检查路线是否包含真实道路数据（path 点数超过2个通常表示有真实路线）
  const hasRealRoute = props.route?.segments && props.route.segments.some(
    (seg: any) => seg.path && seg.path.length > 2
  )
  
  // 如果有 Agent 返回的真实路线（包含 polyline 数据，path 点数 > 2），使用它
  if (hasRealRoute) {
    props.route?.segments?.forEach((seg: any) => {
      if (seg.path && seg.path.length >= 2) {
        const line = new AMap.Polyline({
          path: seg.path.map((p: number[]) => new AMap.LngLat(p[0], p[1])),
          strokeColor: '#1677ff',
          strokeWeight: 5,
          strokeOpacity: 0.8,
          showDir: true,
        })
        line.setMap(map)
      }
    })
    return
  }
  
  // 兜底：使用 DrivingRoute 规划真实路线
  if (AMap.DrivingRoute) {
    const waypoints: any[] = []
    props.points.forEach(p => {
      waypoints.push(new AMap.LngLat(p.lng, p.lat))
    })
    
    const driving = new AMap.DrivingRoute({
      map: map,
      policy: AMap.DrivingPolicy.LEAST_TIME,
      showTraffic: false,
      hideMarkers: true, // 隐藏自动生成的标记点，使用我们自己的
    })
    
    driving.search(
      waypoints[0],
      waypoints[waypoints.length - 1],
      { waypoints: waypoints.slice(1, -1) },
      (status: string, result: any) => {
        if (status !== 'complete') {
          console.error('DrivingRoute 路线规划失败，降级为直线连线')
          drawFallbackPolyline()
        } else {
          console.log('DrivingRoute 路线规划成功')
        }
      }
    )
    return
  }
  
  // 最后兜底：直线连线（虚线表示非真实路线）
  drawFallbackPolyline()
}

function drawFallbackPolyline() {
  if (!map || !props.points || props.points.length < 2) return
  
  const AMap = (window as any).AMap
  if (!AMap) return
  
  const pathPoints: any[] = []
  props.points.forEach(p => {
    pathPoints.push(new AMap.LngLat(p.lng, p.lat))
  })
  
  polyline = new AMap.Polyline({
    path: pathPoints,
    strokeColor: '#1677ff',
    strokeWeight: 4,
    strokeOpacity: 0.6,
    strokeStyle: 'dashed',  // 虚线表示非真实路线
    showDir: true,
  })
  polyline.setMap(map)
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
