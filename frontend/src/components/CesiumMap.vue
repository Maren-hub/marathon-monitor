<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import {
  CallbackProperty,
  Cartesian2,
  Cartesian3,
  Color,
  ConstantProperty,
  EllipsoidTerrainProvider,
  HeadingPitchRoll,
  HorizontalOrigin,
  LabelStyle,
  NearFarScalar,
  PolylineGlowMaterialProperty,
  ScreenSpaceEventHandler,
  ScreenSpaceEventType,
  VerticalOrigin,
  Viewer
} from 'cesium'

const props = defineProps({
  snapshot: { type: Object, default: null },
  selectedSegmentId: { type: String, default: '' },
  selectedAthleteId: { type: String, default: '' }
})

const emit = defineEmits(['select-segment', 'select-athlete'])
const container = ref(null)
const selectedDroneId = ref('UAV-01')
let viewer = null
let clickHandler = null
const segmentEntities = new Map()
const athleteEntities = new Map()
const droneEntities = new Map()

function segmentRisk(segment) {
  const dominantRisk = Math.max(segment.crowd_risk, segment.health_risk)
  if (dominantRisk >= 0.75) return { level: 'critical', label: '高风险', color: Color.fromCssColorString('#ff365f') }
  if (dominantRisk >= 0.55) return { level: 'high', label: '较高风险', color: Color.fromCssColorString('#ff914d') }
  if (dominantRisk >= 0.35) return { level: 'attention', label: '需要关注', color: Color.fromCssColorString('#f4d35e') }
  return { level: 'normal', label: '运行正常', color: Color.fromCssColorString('#34d6c7') }
}

const selectedRisk = computed(() => {
  const segment = props.snapshot?.segments.find((item) => item.id === props.selectedSegmentId)
  if (!segment) return null
  const hasUrgentAlert = props.snapshot?.alerts.some(
    (alert) => alert.segment_id === segment.id && alert.status === 'new' && alert.level === 'critical'
  )
  if (hasUrgentAlert) {
    return { level: 'critical', label: '紧急报警', color: Color.fromCssColorString('#ff365f'), percent: 100 }
  }
  const risk = segmentRisk(segment)
  return { ...risk, percent: Math.round(Math.max(segment.crowd_risk, segment.health_risk) * 100) }
})

const selectedAthlete = computed(() => (
  props.snapshot?.athletes.find((athlete) => athlete.id === props.selectedAthleteId) ?? null
))

const selectedDrone = computed(() => (
  props.snapshot?.drones.find((drone) => drone.id === selectedDroneId.value)
  ?? props.snapshot?.drones[0]
  ?? null
))

const droneTargetName = computed(() => {
  const targetId = selectedDrone.value?.target_segment_id
  return props.snapshot?.segments.find((segment) => segment.id === targetId)?.name ?? targetId ?? '等待任务'
})

const athleteDetail = computed(() => {
  const athlete = selectedAthlete.value
  if (!athlete) return null
  const statusMap = {
    fallen: ['critical', '疑似跌倒'],
    warning: ['warning', '体征异常'],
    finished: ['finished', '已完赛'],
    normal: ['normal', '状态正常']
  }
  let [riskClass, riskLabel] = statusMap[athlete.status] ?? statusMap.normal
  if (athlete.status === 'normal' && (athlete.heart_rate >= 180 || athlete.blood_oxygen <= 93)) {
    riskClass = 'warning'
    riskLabel = '需要关注'
  }
  const progress = Math.min(100, Math.round(athlete.distance_km / (props.snapshot?.race.total_distance_km || 42.195) * 100))
  return { ...athlete, riskClass, riskLabel, progress }
})

function formatPace(value) {
  const minutes = Math.floor(value)
  const seconds = Math.round((value - minutes) * 60)
  return `${minutes}'${String(seconds).padStart(2, '0')}\"/km`
}

function athleteColor(status) {
  if (status === 'fallen') return Color.fromCssColorString('#ff365f')
  if (status === 'warning') return Color.fromCssColorString('#ffb547')
  if (status === 'finished') return Color.fromCssColorString('#708196')
  return Color.fromCssColorString('#f3f7fb')
}

function renderSegments(segments, alerts = []) {
  const urgentSegmentIds = new Set(
    alerts
      .filter((alert) => alert.status === 'new' && alert.level === 'critical')
      .map((alert) => alert.segment_id)
  )
  for (const segment of segments) {
    const flatCoordinates = segment.coordinates.flat()
    const midpoint = segment.coordinates[Math.floor(segment.coordinates.length / 2)]
    const risk = segmentRisk(segment)
    const urgent = urgentSegmentIds.has(segment.id)
    const selected = segment.id === props.selectedSegmentId
    const displayColor = urgent ? Color.fromCssColorString('#ff365f') : risk.color
    const color = urgent
      ? new CallbackProperty(() => {
        const alpha = 0.55 + ((Math.sin(Date.now() / 170) + 1) / 2) * 0.45
        return displayColor.withAlpha(alpha)
      }, false)
      : displayColor
    const lineWidth = urgent
      ? new CallbackProperty(() => (selected ? 13 : 8) + ((Math.sin(Date.now() / 170) + 1) / 2) * 5, false)
      : selected ? 12 : 7
    let entity = segmentEntities.get(segment.id)
    if (!entity) {
      entity = viewer.entities.add({
        id: `segment-${segment.id}`,
        position: Cartesian3.fromDegrees(midpoint[0], midpoint[1], 35),
        properties: { segmentId: segment.id },
        polyline: {
          positions: Cartesian3.fromDegreesArray(flatCoordinates),
          clampToGround: true,
          width: lineWidth,
          material: new PolylineGlowMaterialProperty({ glowPower: urgent ? 0.42 : 0.18, color })
        },
        label: {
          text: `${segment.id}  ${segment.name}`,
          font: '600 14px sans-serif',
          fillColor: Color.WHITE,
          outlineColor: Color.fromCssColorString('#07131f'),
          outlineWidth: 4,
          style: LabelStyle.FILL_AND_OUTLINE,
          verticalOrigin: VerticalOrigin.BOTTOM,
          pixelOffset: new Cartesian2(0, -12),
          scaleByDistance: new NearFarScalar(1000, 1, 9000, 0.45)
        }
      })
      segmentEntities.set(segment.id, entity)
    } else {
      entity.polyline.positions = new ConstantProperty(Cartesian3.fromDegreesArray(flatCoordinates))
      entity.polyline.width = typeof lineWidth === 'number' ? new ConstantProperty(lineWidth) : lineWidth
      entity.polyline.material = new PolylineGlowMaterialProperty({ glowPower: urgent ? 0.42 : selected ? 0.28 : 0.16, color })
      entity.label.text = new ConstantProperty(`${segment.id}  ${segment.name}`)
    }
  }
}

function renderAthletes(athletes) {
  const activeIds = new Set()
  for (const athlete of athletes) {
    activeIds.add(athlete.id)
    let entity = athleteEntities.get(athlete.id)
    const abnormal = athlete.status === 'fallen' || athlete.status === 'warning'
    const selected = athlete.id === props.selectedAthleteId
    if (!entity) {
      entity = viewer.entities.add({
        id: `athlete-${athlete.id}`,
        position: Cartesian3.fromDegrees(athlete.longitude, athlete.latitude, 12),
        properties: { athleteId: athlete.id },
        point: {
          pixelSize: selected ? 14 : abnormal ? 11 : 5,
          color: athleteColor(athlete.status),
          outlineColor: selected ? Color.fromCssColorString('#49bfff') : Color.fromCssColorString('#07131f'),
          outlineWidth: selected ? 4 : 2,
          disableDepthTestDistance: Number.POSITIVE_INFINITY
        },
        label: {
          text: abnormal || selected ? `${athlete.bib} · ${athlete.heart_rate} bpm` : '',
          show: abnormal || selected,
          font: '600 12px sans-serif',
          fillColor: athleteColor(athlete.status),
          outlineColor: Color.fromCssColorString('#07131f'),
          outlineWidth: 4,
          style: LabelStyle.FILL_AND_OUTLINE,
          horizontalOrigin: HorizontalOrigin.LEFT,
          pixelOffset: new Cartesian2(10, 0),
          disableDepthTestDistance: Number.POSITIVE_INFINITY
        }
      })
      athleteEntities.set(athlete.id, entity)
    } else {
      entity.position = new ConstantProperty(Cartesian3.fromDegrees(athlete.longitude, athlete.latitude, 12))
      entity.point.color = new ConstantProperty(athleteColor(athlete.status))
      entity.point.pixelSize = new ConstantProperty(selected ? 14 : abnormal ? 11 : 5)
      entity.point.outlineColor = new ConstantProperty(selected ? Color.fromCssColorString('#49bfff') : Color.fromCssColorString('#07131f'))
      entity.point.outlineWidth = new ConstantProperty(selected ? 4 : 2)
      entity.label.show = new ConstantProperty(abnormal || selected)
      entity.label.text = new ConstantProperty(abnormal || selected ? `${athlete.bib} · ${athlete.heart_rate} bpm` : '')
      entity.label.fillColor = new ConstantProperty(athleteColor(athlete.status))
    }
  }
  for (const [id, entity] of athleteEntities) {
    if (!activeIds.has(id)) {
      viewer.entities.remove(entity)
      athleteEntities.delete(id)
    }
  }
}

function renderDrones(drones) {
  for (const drone of drones) {
    let entity = droneEntities.get(drone.id)
    const selected = drone.id === selectedDrone.value?.id
    if (!entity) {
      entity = viewer.entities.add({
        id: `drone-${drone.id}`,
        position: Cartesian3.fromDegrees(drone.longitude, drone.latitude, drone.altitude_m),
        properties: { droneId: drone.id },
        point: {
          pixelSize: selected ? 16 : 12,
          color: drone.status === 'dispatch' ? Color.fromCssColorString('#ff365f') : Color.fromCssColorString('#49bfff'),
          outlineColor: Color.WHITE,
          outlineWidth: selected ? 4 : 2,
          disableDepthTestDistance: Number.POSITIVE_INFINITY
        },
        label: {
          text: `◆ ${drone.name}`,
          font: '700 13px sans-serif',
          fillColor: Color.fromCssColorString('#6ed7ff'),
          outlineColor: Color.fromCssColorString('#07131f'),
          outlineWidth: 4,
          style: LabelStyle.FILL_AND_OUTLINE,
          verticalOrigin: VerticalOrigin.BOTTOM,
          pixelOffset: new Cartesian2(0, -14),
          disableDepthTestDistance: Number.POSITIVE_INFINITY
        }
      })
      droneEntities.set(drone.id, entity)
    } else {
      entity.position = new ConstantProperty(Cartesian3.fromDegrees(drone.longitude, drone.latitude, drone.altitude_m))
      entity.point.pixelSize = new ConstantProperty(selected ? 16 : 12)
      entity.point.color = new ConstantProperty(drone.status === 'dispatch' ? Color.fromCssColorString('#ff365f') : Color.fromCssColorString('#49bfff'))
      entity.point.outlineWidth = new ConstantProperty(selected ? 4 : 2)
      entity.label.text = new ConstantProperty(`◆ ${drone.name} · ${Math.round(drone.battery_percent)}%`)
    }
  }
}

function renderSnapshot() {
  if (!viewer || !props.snapshot) return
  renderSegments(props.snapshot.segments, props.snapshot.alerts)
  renderAthletes(props.snapshot.athletes)
  renderDrones(props.snapshot.drones)
}

function focusSegment(segmentId) {
  const segment = props.snapshot?.segments.find((item) => item.id === segmentId)
  if (!segment || !viewer) return
  const midpoint = segment.coordinates[Math.floor(segment.coordinates.length / 2)]
  viewer.camera.flyTo({
    destination: Cartesian3.fromDegrees(midpoint[0], midpoint[1], 1300),
    orientation: new HeadingPitchRoll(0, -Math.PI / 2.7, 0),
    duration: 0.8
  })
}

watch(() => props.snapshot, renderSnapshot, { deep: true })
watch(() => props.selectedAthleteId, renderSnapshot)
watch(selectedDroneId, renderSnapshot)
watch(
  () => props.selectedSegmentId,
  (value, previous) => {
    renderSnapshot()
    if (value && value !== previous) focusSegment(value)
  }
)

onMounted(() => {
  viewer = new Viewer(container.value, {
    animation: false,
    baseLayer: false,
    baseLayerPicker: false,
    fullscreenButton: false,
    geocoder: false,
    homeButton: false,
    infoBox: false,
    navigationHelpButton: false,
    sceneModePicker: false,
    selectionIndicator: false,
    timeline: false,
    terrainProvider: new EllipsoidTerrainProvider()
  })
  viewer.scene.globe.baseColor = Color.fromCssColorString('#0b2232')
  viewer.scene.backgroundColor = Color.fromCssColorString('#06111a')
  viewer.scene.globe.showGroundAtmosphere = false
  viewer.scene.fog.enabled = false
  viewer.camera.setView({
    destination: Cartesian3.fromDegrees(114.365, 30.529, 4300),
    orientation: new HeadingPitchRoll(0, -Math.PI / 2.45, 0)
  })

  clickHandler = new ScreenSpaceEventHandler(viewer.scene.canvas)
  clickHandler.setInputAction((movement) => {
    const picked = viewer.scene.pick(movement.position)
    const athleteId = picked?.id?.properties?.athleteId?.getValue()
    const droneId = picked?.id?.properties?.droneId?.getValue()
    const segmentId = picked?.id?.properties?.segmentId?.getValue()
    if (droneId) {
      selectedDroneId.value = droneId
    } else if (athleteId) {
      emit('select-athlete', athleteId)
    } else if (segmentId) {
      emit('select-segment', segmentId)
    }
  }, ScreenSpaceEventType.LEFT_CLICK)
  renderSnapshot()
})

onBeforeUnmount(() => {
  clickHandler?.destroy()
  viewer?.destroy()
})
</script>

<template>
  <div class="map-shell">
    <div ref="container" class="cesium-map"></div>
    <div class="map-overlay map-title">
      <span>LIVE DIGITAL COURSE</span>
      <strong>三维赛道态势</strong>
    </div>
    <div v-if="selectedRisk" class="map-overlay map-risk-card" :class="selectedRisk.level">
      <span>当前赛段风险</span>
      <strong>{{ selectedRisk.label }}</strong>
      <b>{{ selectedRisk.percent }}%</b>
    </div>
    <section v-if="selectedDrone" class="drone-monitor-card" :class="selectedDrone.status">
      <div class="drone-monitor-heading">
        <div>
          <span>UAV COOPERATIVE MONITORING</span>
          <strong>无人机协同监控</strong>
        </div>
        <b>{{ selectedDrone.status === 'dispatch' ? '紧急调度' : '自主巡航' }}</b>
      </div>
      <div class="drone-tabs">
        <button
          v-for="drone in snapshot.drones"
          :key="drone.id"
          :class="{ selected: drone.id === selectedDrone.id }"
          @click="selectedDroneId = drone.id"
        >{{ drone.id }}</button>
      </div>
      <div class="simulated-feed">
        <div class="feed-grid"></div>
        <div class="feed-reticle"><i></i><i></i></div>
        <div class="feed-scanline"></div>
        <span><i></i> SIMULATED LIVE FEED</span>
        <strong>{{ droneTargetName }}</strong>
        <small>{{ selectedDrone.camera_mode }}</small>
      </div>
      <div class="drone-metrics">
        <div><span>高度</span><b>{{ Math.round(selectedDrone.altitude_m) }} m</b></div>
        <div><span>电量</span><b>{{ Math.round(selectedDrone.battery_percent) }}%</b></div>
        <div><span>预计到达</span><b>{{ selectedDrone.eta_seconds > 0 ? `${selectedDrone.eta_seconds} 秒` : '已抵达' }}</b></div>
      </div>
      <p>{{ selectedDrone.task }}</p>
    </section>
    <article v-if="athleteDetail" class="athlete-detail-card" :class="athleteDetail.riskClass">
      <div class="athlete-card-heading">
        <div>
          <span>ATHLETE DIGITAL PROFILE</span>
          <strong>运动员 {{ athleteDetail.bib }}</strong>
        </div>
        <button title="关闭" @click="$emit('select-athlete', '')">×</button>
      </div>
      <div class="athlete-card-tags">
        <b>{{ athleteDetail.group }}</b>
        <b>{{ athleteDetail.segment_id }}</b>
        <b class="athlete-risk-label">{{ athleteDetail.riskLabel }}</b>
      </div>
      <div class="athlete-vitals">
        <div><span>心率</span><strong>{{ athleteDetail.heart_rate }}</strong><small>bpm</small></div>
        <div><span>血氧</span><strong>{{ athleteDetail.blood_oxygen }}</strong><small>%</small></div>
        <div><span>疲劳度</span><strong>{{ athleteDetail.fatigue_percent }}</strong><small>%</small></div>
        <div><span>当前配速</span><strong>{{ formatPace(athleteDetail.pace_min_km) }}</strong></div>
      </div>
      <div class="athlete-progress-row">
        <div><span>已完成 {{ athleteDetail.distance_km.toFixed(2) }} km</span><b>{{ athleteDetail.progress }}%</b></div>
        <div class="athlete-progress"><i :style="{ width: `${athleteDetail.progress}%` }"></i></div>
      </div>
      <p class="simulation-note">以上体征为原型系统生成的模拟数据</p>
    </article>
    <div class="map-overlay legend">
      <span><i class="normal"></i>正常</span>
      <span><i class="attention"></i>关注</span>
      <span><i class="high"></i>较高风险</span>
      <span><i class="critical"></i>高风险 / 闪烁报警</span>
    </div>
  </div>
</template>
