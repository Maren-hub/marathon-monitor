<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import {
  CallbackProperty,
  Cartesian2,
  Cartesian3,
  Cesium3DTileset,
  Color,
  ConstantProperty,
  EllipsoidTerrainProvider,
  HeadingPitchRange,
  HorizontalOrigin,
  LabelStyle,
  Matrix4,
  NearFarScalar,
  PolylineGlowMaterialProperty,
  Rectangle,
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
const realSceneStatus = ref('loading')
const realSceneVisible = ref(true)
const realSceneModeActive = ref(false)
let viewer = null
let clickHandler = null
let realSceneTileset = null
let realSceneHomeView = null
const REAL_SCENE_CENTER = new Cartesian3(
  -2685862.8180647003,
  4669424.177962229,
  3403338.0007711477
)
let realSceneRouteEntity = null
let realSceneDroneEntity = null
const segmentEntities = new Map()
const athleteEntities = new Map()
const droneEntities = new Map()
const realSceneCheckpointEntities = new Map()
const realSceneRunnerEntities = []

const REAL_SCENE_TRANSFORM = Matrix4.fromArray([
  -0.8668378543600049, -0.49859014656182593, 0, 0,
  0.2662988660278672, -0.4629813469798977, 0.8454189412953508, 0,
  -0.42070677772239806, 0.7314315435842124, 0.5366690826090628, 0,
  -2685916.035781034, 4669674.500193627, 3403316.9167269776, 1
])

const REAL_SCENE_ROUTE_LOCAL = [
  [61, 127, -184.5],
  [63, 141, -184.5],
  [68, 156, -184.5],
  [77, 170, -184.5],
  [88, 168, -184.5],
  [95, 157, -184.5],
  [92, 141, -184.5],
  [82, 126, -184.5]
]

const REAL_SCENE_CHECKPOINTS = [
  { id: 'start', name: '测试起点', code: 'P1', routeIndex: 0, segments: ['S1', 'S2'], defaultSegment: 'S1' },
  { id: 'monitor', name: '重点监测点', code: 'P2', routeIndex: 3, segments: ['S3'], defaultSegment: 'S3' },
  { id: 'finish', name: '测试终点', code: 'P3', routeIndex: 7, segments: ['S4', 'S5'], defaultSegment: 'S5' }
]

function localScenePoint([x, y, z]) {
  return Matrix4.multiplyByPoint(REAL_SCENE_TRANSFORM, new Cartesian3(x, y, z), new Cartesian3())
}

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

function addRealSceneDemoEntities() {
  if (!viewer || realSceneRouteEntity) return
  const routePositions = REAL_SCENE_ROUTE_LOCAL.map(localScenePoint)
  realSceneRouteEntity = viewer.entities.add({
    id: 'real-scene-demo-route',
    show: false,
    polyline: {
      positions: routePositions,
      width: 7,
      material: new PolylineGlowMaterialProperty({
        glowPower: 0.32,
        color: Color.fromCssColorString('#34d6c7')
      }),
      depthFailMaterial: Color.fromCssColorString('#34d6c7').withAlpha(0.75)
    }
  })

  for (const checkpoint of REAL_SCENE_CHECKPOINTS) {
    const position = routePositions[checkpoint.routeIndex]
    const entity = viewer.entities.add({
      id: `real-checkpoint-${checkpoint.id}`,
      show: false,
      position,
      properties: { segmentId: checkpoint.defaultSegment, realCheckpointId: checkpoint.id },
      point: {
        pixelSize: 13,
        color: Color.fromCssColorString('#49bfff'),
        outlineColor: Color.WHITE,
        outlineWidth: 3,
        disableDepthTestDistance: Number.POSITIVE_INFINITY
      },
      label: {
        text: `${checkpoint.code}  ${checkpoint.name}`,
        font: '700 13px sans-serif',
        fillColor: Color.WHITE,
        outlineColor: Color.fromCssColorString('#06111a'),
        outlineWidth: 5,
        style: LabelStyle.FILL_AND_OUTLINE,
        verticalOrigin: VerticalOrigin.BOTTOM,
        pixelOffset: new Cartesian2(0, -15),
        disableDepthTestDistance: Number.POSITIVE_INFINITY
      }
    })
    realSceneCheckpointEntities.set(checkpoint.id, entity)
  }

  for (const [runnerIndex, routeIndex] of [1, 2, 4, 5, 6].entries()) {
    const runner = viewer.entities.add({
      id: `real-runner-${runnerIndex + 1}`,
      show: false,
      position: routePositions[routeIndex],
      point: {
        pixelSize: 7,
        color: Color.WHITE,
        outlineColor: Color.fromCssColorString('#34d6c7'),
        outlineWidth: 2,
        disableDepthTestDistance: Number.POSITIVE_INFINITY
      }
    })
    realSceneRunnerEntities.push(runner)
  }

  const droneLocal = [...REAL_SCENE_ROUTE_LOCAL[3]]
  droneLocal[2] = -158
  realSceneDroneEntity = viewer.entities.add({
    id: 'real-scene-uav',
    show: false,
    position: localScenePoint(droneLocal),
    point: {
      pixelSize: 14,
      color: Color.fromCssColorString('#49bfff'),
      outlineColor: Color.WHITE,
      outlineWidth: 3,
      disableDepthTestDistance: Number.POSITIVE_INFINITY
    },
    label: {
      text: '◆ UAV-TEST · 实景巡检',
      font: '700 12px sans-serif',
      fillColor: Color.fromCssColorString('#6ed7ff'),
      outlineColor: Color.fromCssColorString('#06111a'),
      outlineWidth: 5,
      style: LabelStyle.FILL_AND_OUTLINE,
      verticalOrigin: VerticalOrigin.BOTTOM,
      pixelOffset: new Cartesian2(0, -15),
      disableDepthTestDistance: Number.POSITIVE_INFINITY
    }
  })
}

function setRealSceneDemoVisibility(visible) {
  if (realSceneRouteEntity) realSceneRouteEntity.show = visible
  if (realSceneDroneEntity) realSceneDroneEntity.show = visible
  for (const entity of realSceneCheckpointEntities.values()) entity.show = visible
  for (const entity of realSceneRunnerEntities) entity.show = visible
}

function renderRealSceneAlerts(alerts = []) {
  if (!realSceneCheckpointEntities.size) return
  const activeAlerts = alerts.filter((alert) => alert.status !== 'resolved' && alert.event_type !== 'system')
  for (const checkpoint of REAL_SCENE_CHECKPOINTS) {
    const entity = realSceneCheckpointEntities.get(checkpoint.id)
    if (!entity) continue
    const checkpointAlerts = activeAlerts.filter((alert) => checkpoint.segments.includes(alert.segment_id))
    const urgent = checkpointAlerts.some((alert) => alert.level === 'critical' && alert.status === 'new')
    const warning = checkpointAlerts.length > 0
    const selected = checkpoint.segments.includes(props.selectedSegmentId)
    const baseColor = urgent
      ? Color.fromCssColorString('#ff365f')
      : warning
        ? Color.fromCssColorString('#ffb547')
        : selected
          ? Color.fromCssColorString('#34d6c7')
          : Color.fromCssColorString('#49bfff')
    entity.point.color = urgent
      ? new CallbackProperty(() => baseColor.withAlpha(0.58 + ((Math.sin(Date.now() / 160) + 1) / 2) * 0.42), false)
      : new ConstantProperty(baseColor)
    entity.point.pixelSize = urgent
      ? new CallbackProperty(() => 15 + ((Math.sin(Date.now() / 160) + 1) / 2) * 6, false)
      : new ConstantProperty(selected ? 17 : warning ? 15 : 13)
    entity.point.outlineColor = new ConstantProperty(selected ? Color.WHITE : Color.fromCssColorString('#06111a'))
    entity.label.fillColor = new ConstantProperty(baseColor)
    entity.label.text = new ConstantProperty(
      checkpointAlerts.length
        ? `${checkpoint.code}  ${checkpoint.name} · ${checkpointAlerts.length}项报警`
        : `${checkpoint.code}  ${checkpoint.name}`
    )
  }
}

function renderSnapshot() {
  if (!viewer || !props.snapshot) return
  renderSegments(props.snapshot.segments, props.snapshot.alerts)
  renderAthletes(props.snapshot.athletes)
  renderDrones(props.snapshot.drones)
  renderRealSceneAlerts(props.snapshot.alerts)
}

function focusSegment(segmentId) {
  const segment = props.snapshot?.segments.find((item) => item.id === segmentId)
  if (!segment || !viewer) return
  const longitudes = segment.coordinates.map((coordinate) => coordinate[0])
  const latitudes = segment.coordinates.map((coordinate) => coordinate[1])
  viewer.camera.flyTo({
    destination: Rectangle.fromDegrees(
      Math.min(...longitudes) - 0.002,
      Math.min(...latitudes) - 0.002,
      Math.max(...longitudes) + 0.002,
      Math.max(...latitudes) + 0.002
    ),
    duration: 0.8
  })
}

function focusRaceCourse() {
  if (!viewer) return
  realSceneModeActive.value = false
  setRealSceneDemoVisibility(false)
  viewer.camera.flyTo({
    destination: Rectangle.fromDegrees(114.343, 30.513, 114.387, 30.544),
    duration: 1.1
  })
}

async function focusRealScene() {
  if (!viewer || realSceneStatus.value === 'loading') return
  if (!realSceneTileset) return
  realSceneVisible.value = true
  realSceneModeActive.value = true
  realSceneTileset.show = true
  setRealSceneDemoVisibility(true)
  renderRealSceneAlerts(props.snapshot?.alerts ?? [])
  viewer.camera.lookAt(
    REAL_SCENE_CENTER,
    new HeadingPitchRange(0, -0.58, 140)
  )
  realSceneHomeView = true
  viewer.scene.requestRender()
  viewer.scene.screenSpaceCameraController.enableInputs = true
}

function toggleRealScene() {
  if (!realSceneTileset) return
  realSceneVisible.value = !realSceneVisible.value
  realSceneTileset.show = realSceneVisible.value
  setRealSceneDemoVisibility(realSceneVisible.value && realSceneModeActive.value)
}

async function loadRealScene() {
  try {
    realSceneStatus.value = 'loading'
    realSceneTileset = await Cesium3DTileset.fromUrl('/3dtiles/BlockBAYBA/tileset.json', {
      maximumScreenSpaceError: 12,
      dynamicScreenSpaceError: true
    })
    viewer.scene.primitives.add(realSceneTileset)
    addRealSceneDemoEntities()
    renderRealSceneAlerts(props.snapshot?.alerts ?? [])
    realSceneStatus.value = 'ready'
  } catch (error) {
    console.error('真实倾斜模型加载失败', error)
    realSceneStatus.value = 'error'
  }
}

watch(() => props.snapshot, renderSnapshot, { deep: true })
watch(() => props.selectedAthleteId, renderSnapshot)
watch(selectedDroneId, renderSnapshot)
watch(
  () => props.selectedSegmentId,
  (value, previous) => {
    renderSnapshot()
    if (value && value !== previous && !realSceneModeActive.value) focusSegment(value)
  }
)

onMounted(async () => {
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
    destination: Rectangle.fromDegrees(114.343, 30.513, 114.387, 30.544)
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
  await loadRealScene()
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
    <div class="real-scene-controls">
      <span :class="realSceneStatus">
        {{ realSceneStatus === 'ready' ? '真实倾斜模型已接入' : realSceneStatus === 'error' ? '模型加载失败' : '正在加载模型' }}
      </span>
      <button @click="focusRaceCourse">赛事赛道</button>
      <button :disabled="realSceneStatus !== 'ready'" @click="focusRealScene">
        {{ realSceneModeActive ? '重置实景视角' : '实景模型' }}
      </button>
      <button :disabled="realSceneStatus !== 'ready'" @click="toggleRealScene">
        {{ realSceneVisible ? '隐藏模型' : '显示模型' }}
      </button>
    </div>
    <div v-if="realSceneModeActive" class="map-overlay real-scene-demo-badge">
      <b>实景测试路线</b>
      <span>约 120 m · 5名模拟运动员 · 1架无人机 · 3个监测点</span>
    </div>
    <div v-if="selectedRisk" class="map-overlay map-risk-card" :class="selectedRisk.level">
      <span>当前赛段风险</span>
      <strong>{{ selectedRisk.label }}</strong>
      <b>{{ selectedRisk.percent }}%</b>
    </div>
    <section
      v-if="selectedDrone"
      class="drone-monitor-card"
      :class="[selectedDrone.status, { compact: realSceneModeActive }]"
    >
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
