export function extractCoordinatesFromText(text: string): {
  points: any[]
  route: any | null
} | null {
  try {
    const jsonMatch = text.match(/```json\s*\n([\s\S]*?)\n```/g)
    if (!jsonMatch) return null
    
    const lastJson = jsonMatch[jsonMatch.length - 1]
    const jsonStr = lastJson.replace(/```json\s*\n/, '').replace(/\n```/, '')
    const data = JSON.parse(jsonStr)
    
    if (!data.coordinates) return null
    
    const { coordinates } = data
    const points: any[] = []
    
    coordinates.activities?.forEach((a: any) => {
      if (a.location) {
        const [lng, lat] = a.location.split(',').map(Number)
        points.push({
          name: a.name,
          lng,
          lat,
          type: 'activity' as const,
          description: a.description || '',
          duration: a.duration || '',
        })
      }
    })
    
    coordinates.restaurants?.forEach((r: any) => {
      if (r.location) {
        const [lng, lat] = r.location.split(',').map(Number)
        points.push({
          name: r.name,
          lng,
          lat,
          type: 'restaurant' as const,
          cuisine: r.cuisine || '',
          price_per_person: r.price_per_person || 0,
          rating: r.rating || 0,
        })
      }
    })
    
    let route = null
    if (coordinates.route && coordinates.route.segments) {
      route = {
        segments: coordinates.route.segments.map((seg: any) => ({
          from: seg.from || '起点',
          to: seg.to || '终点',
          path: seg.path || [],
          distance: seg.distance || '',
          duration: seg.duration || '',
        }))
      }
    }
    
    return { points, route }
  } catch (e) {
    console.error('解析坐标失败:', e)
    return null
  }
}
