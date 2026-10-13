<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import {
  CallbackProperty,
  Cartesian2,
  Cartesian3,
  Cesium3DTileset,
  ClassificationType,
  Color,
  ConstantProperty,
  EllipsoidTerrainProvider,
  HeadingPitchRange,
  HeightReference,
  HorizontalOrigin,
  LabelStyle,
  NearFarScalar,
  PolylineGlowMaterialProperty,
  Rectangle,
  ScreenSpaceEventHandler,
  ScreenSpaceEventType,
  VerticalOrigin,
  Viewer
} from 'cesium'
import { routeLengthKm } from '../data/nanlinCourse'
import { platformApi } from '../services/api'

const props = defineProps({
  snapshot: { type: Object, default: null },
  historicalAlerts: { type: Array, default: () => [] },
  selectedSegmentId: { type: String, default: '' },
  selectedAthleteId: { type: String, default: '' }
})

const emit = defineEmits(['select-segment', 'select-athlete'])
const container = ref(null)
const selectedDroneId = ref('UAV-01')
const nanlinSceneStatus = ref('idle')
const nanlinSceneVisible = ref(false)
const nanlinSceneModeActive = ref(false)
const nanlinCourseVisible = ref(true)
const layerPanelOpen = ref(false)
const layers = ref({ crowd: false, health: false, uav: false, alerts: false })
const selectedCampusFeature = ref(null)
const campusRoute = ref({ segments: [], sites: [], route_length_km: 0, simulation_linked: false, status: '未导入路线' })
const campusImportOpen = ref(false)
const campusImportBusy = ref(false)
const campusImportError = ref('')
const campusImportSuccess = ref('')
const routeInput = ref(null)
const sitesInput = ref(null)
const modelImportOpen = ref(false)
const availableModels = ref([])
const selectedModelId = ref('nanlin')
const modelUploadBusy = ref(false)
const modelUploadProgress = ref(0)
const modelImportError = ref('')
const modelJob = ref(null)
const modelZipInput = ref(null)
const selectedModel = computed(() => availableModels.value.find((item) => item.id === selectedModelId.value) ?? null)
const campusRouteLength = computed(() => (
  campusRoute.value.route_length_km ?? campusRoute.value.segments.reduce((sum, segment) => sum + routeLengthKm(segment.coordinates), 0)
).toFixed(2))
const campusSiteCounts = computed(() => Object.fromEntries(
  ['medical', 'water', 'marshal'].map((kind) => [kind, campusRoute.value.sites.filter((site) => site.kind === kind).length])
))

function campusSegmentById(segmentId) {
  if (!campusRoute.value.simulation_linked) return null
  return campusRoute.value.segments.find((segment) => segment.id === segmentId) ?? null
}

function interpolateCampusSegment(segment, progress = 0.5) {
  const coordinates = segment?.coordinates ?? []
  if (coordinates.length < 2) return null
  const heights = Array.isArray(segment.heights_m) && segment.heights_m.length === coordinates.length
    ? segment.heights_m
    : null
  const lengths = []
  let totalLength = 0
  for (let index = 1; index < coordinates.length; index += 1) {
    const length = routeLengthKm([coordinates[index - 1], coordinates[index]])
    lengths.push(length)
    totalLength += length
  }
  const target = Math.max(0, Math.min(1, progress)) * totalLength
  let travelled = 0
  for (let index = 0; index < lengths.length; index += 1) {
    const next = travelled + lengths[index]
    if (target <= next || index === lengths.length - 1) {
      const local = lengths[index] > 0 ? (target - travelled) / lengths[index] : 0
      const first = coordinates[index]
      const second = coordinates[index + 1]
      const height = heights
        ? heights[index] + (heights[index + 1] - heights[index]) * local
        : 0
      return {
        longitude: first[0] + (second[0] - first[0]) * local,
        latitude: first[1] + (second[1] - first[1]) * local,
        height,
        hasModelHeight: Boolean(heights)
      }
    }
    travelled = next
  }
  return null
}

function campusLocationForAthlete(athlete) {
  const campusSegment = campusSegmentById(athlete.segment_id)
  const logicalSegment = props.snapshot?.segments.find((segment) => segment.id === athlete.segment_id)
  if (!campusSegment || !logicalSegment) return null
  const length = Math.max(0.001, logicalSegment.end_km - logicalSegment.start_km)
  const progress = (athlete.distance_km - logicalSegment.start_km) / length
  return interpolateCampusSegment(campusSegment, progress)
}

function campusLocationForSegment(segmentId, progress = 0.5) {
  return interpolateCampusSegment(campusSegmentById(segmentId), progress)
}
let viewer = null
let clickHandler = null
let nanlinTileset = null
let loadedModelId = null
let jobPollTimer = null
const segmentEntities = new Map()
const athleteEntities = new Map()
const droneEntities = new Map()
const nanlinCourseEntities = []
const layerEntities = new Map()

function putLayerEntity(id, options) {
  let entity = layerEntities.get(id)
  if (!entity) {
    entity = viewer.entities.add({ id: `layer-${id}`, ...options })
    layerEntities.set(id, entity)
  } else {
    entity.position = new ConstantProperty(options.position)
    if (options.ellipse) {
      entity.ellipse.semiMajorAxis = new ConstantProperty(options.ellipse.semiMajorAxis)
      entity.ellipse.semiMinorAxis = new ConstantProperty(options.ellipse.semiMinorAxis)
      entity.ellipse.material = options.ellipse.material
      entity.ellipse.height = new ConstantProperty(options.ellipse.height)
    }
    if (options.point) entity.point.color = new ConstantProperty(options.point.color)
  }
  entity.show = options.show
}

function renderThematicLayers() {
  if (!viewer || !props.snapshot) return
  const active = new Set()
  const campusLinked = nanlinSceneModeActive.value && campusRoute.value.simulation_linked
  for (const segment of props.snapshot.segments) {
    const midpoint = segment.coordinates[Math.floor(segment.coordinates.length / 2)]
    const campusLocation = campusLinked ? campusLocationForSegment(segment.id) : null
    const longitude = campusLocation?.longitude ?? midpoint[0]
    const latitude = campusLocation?.latitude ?? midpoint[1]
    const height = campusLocation?.hasModelHeight ? campusLocation.height + 3 : 8
    for (const [kind, risk, hex] of [
      ['crowd', segment.crowd_risk, '#ffb547'],
      ['health', segment.health_risk, '#ff638b']
    ]) {
      const id = `${kind}-${segment.id}`
      active.add(id)
      const strength = Math.max(0, Math.min(1, Number(risk) || 0))
      putLayerEntity(id, {
        show: layers.value[kind],
        position: Cartesian3.fromDegrees(longitude, latitude, height),
        properties: { segmentId: segment.id },
        ellipse: {
          semiMajorAxis: campusLinked ? 35 + strength * 75 : 180 + strength * 380,
          semiMinorAxis: campusLinked ? 24 + strength * 52 : 130 + strength * 260,
          material: Color.fromCssColorString(hex).withAlpha(0.07 + strength * 0.25),
          outline: true,
          outlineColor: Color.fromCssColorString(hex).withAlpha(0.45),
          height
        }
      })
    }
  }
  for (const drone of props.snapshot.drones) {
    const id = `uav-${drone.id}`
    active.add(id)
    const campusLocation = campusLinked ? campusLocationForSegment(drone.target_segment_id) : null
    putLayerEntity(id, {
      show: layers.value.uav,
      position: Cartesian3.fromDegrees(
        campusLocation?.longitude ?? drone.longitude,
        campusLocation?.latitude ?? drone.latitude,
        campusLocation?.hasModelHeight ? campusLocation.height + 5 : 10
      ),
      properties: { droneId: drone.id },
      ellipse: {
        semiMajorAxis: campusLinked ? 85 : 150, semiMinorAxis: campusLinked ? 85 : 150,
        material: Color.fromCssColorString('#4dbfff').withAlpha(0.13),
        outline: true,
        outlineColor: Color.fromCssColorString('#4dbfff').withAlpha(0.7),
        height: campusLocation?.hasModelHeight ? campusLocation.height + 5 : 10
      }
    })
  }
  for (const [index, alert] of props.historicalAlerts.entries()) {
    const segment = props.snapshot.segments.find((item) => item.id === alert.segment_id)
    if (!segment) continue
    const midpoint = segment.coordinates[Math.floor(segment.coordinates.length / 2)]
    const campusLocation = campusLinked ? campusLocationForSegment(segment.id, 0.55) : null
    const id = `alert-${alert.id}`
    active.add(id)
    putLayerEntity(id, {
      show: layers.value.alerts,
      position: Cartesian3.fromDegrees(
        (campusLocation?.longitude ?? midpoint[0]) + ((index % 5) - 2) * (campusLinked ? 0.000015 : 0.00011),
        (campusLocation?.latitude ?? midpoint[1]) + (Math.floor(index / 5) % 5 - 2) * (campusLinked ? 0.000012 : 0.0001),
        campusLocation?.hasModelHeight ? campusLocation.height + 8 : 35
      ),
      properties: { segmentId: segment.id },
      point: {
        pixelSize: alert.level === 'critical' ? 11 : 8,
        color: Color.fromCssColorString(alert.level === 'critical' ? '#ff365f' : '#ffb547'),
        outlineColor: Color.WHITE, outlineWidth: 2,
        disableDepthTestDistance: Number.POSITIVE_INFINITY
      },
      label: {
        text: `${alert.event_type === 'fall' ? '跌倒' : alert.event_type === 'vital' ? '体征' : '聚集'} · ${segment.id}`,
        font: '11px sans-serif', fillColor: Color.WHITE,
        outlineColor: Color.fromCssColorString('#07131f'), outlineWidth: 3,
        style: LabelStyle.FILL_AND_OUTLINE, pixelOffset: new Cartesian2(0, -16),
        scaleByDistance: new NearFarScalar(700, 1, 6000, 0)
      }
    })
  }
  for (const [id, entity] of layerEntities) {
    if (!active.has(id)) { viewer.entities.remove(entity); layerEntities.delete(id) }
  }
  viewer.scene.requestRender()
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
        show: !nanlinSceneModeActive.value,
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
      entity.show = !nanlinSceneModeActive.value
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
    const campusLocation = nanlinSceneModeActive.value ? campusLocationForAthlete(athlete) : null
    const longitude = campusLocation?.longitude ?? athlete.longitude
    const latitude = campusLocation?.latitude ?? athlete.latitude
    const height = campusLocation?.hasModelHeight ? campusLocation.height + 3.2 : 12
    const visible = !nanlinSceneModeActive.value || Boolean(campusLocation)
    if (!entity) {
      entity = viewer.entities.add({
        id: `athlete-${athlete.id}`,
        show: visible,
        position: Cartesian3.fromDegrees(longitude, latitude, height),
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
      entity.show = visible
      entity.position = new ConstantProperty(Cartesian3.fromDegrees(longitude, latitude, height))
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
  for (const [index, drone] of drones.entries()) {
    let entity = droneEntities.get(drone.id)
    const selected = drone.id === selectedDrone.value?.id
    const campusLocation = nanlinSceneModeActive.value
      ? campusLocationForSegment(drone.target_segment_id, 0.45 + index * 0.1)
      : null
    const longitude = campusLocation?.longitude ?? drone.longitude
    const latitude = campusLocation?.latitude ?? drone.latitude
    const height = campusLocation?.hasModelHeight ? campusLocation.height + 48 + index * 8 : drone.altitude_m
    const visible = !nanlinSceneModeActive.value || Boolean(campusLocation)
    if (!entity) {
      entity = viewer.entities.add({
        id: `drone-${drone.id}`,
        show: visible,
        position: Cartesian3.fromDegrees(longitude, latitude, height),
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
      entity.show = visible
      entity.position = new ConstantProperty(Cartesian3.fromDegrees(longitude, latitude, height))
      entity.point.pixelSize = new ConstantProperty(selected ? 16 : 12)
      entity.point.color = new ConstantProperty(drone.status === 'dispatch' ? Color.fromCssColorString('#ff365f') : Color.fromCssColorString('#49bfff'))
      entity.point.outlineWidth = new ConstantProperty(selected ? 4 : 2)
      entity.label.text = new ConstantProperty(`◆ ${drone.name} · ${Math.round(drone.battery_percent)}%`)
    }
  }
}


function clearCampusCourseEntities() {
  for (const entity of nanlinCourseEntities) viewer?.entities.remove(entity)
  nanlinCourseEntities.length = 0
  selectedCampusFeature.value = null
}

function addCampusCourseEntities() {
  if (!viewer || nanlinCourseEntities.length) return
  const routeColors = ['#34d6c7', '#49bfff', '#f4d35e', '#ffad65', '#fb729b']
  for (const [index, segment] of campusRoute.value.segments.entries()) {
    const coordinates = segment.coordinates
    const linkedState = campusRoute.value.simulation_linked
      ? props.snapshot?.segments.find((item) => item.id === segment.id)
      : null
    const color = linkedState ? segmentRisk(linkedState).color : Color.fromCssColorString(routeColors[index % routeColors.length])
    const hasModelHeights = Array.isArray(segment.heights_m) && segment.heights_m.length === coordinates.length
    const positions = hasModelHeights
      ? Cartesian3.fromDegreesArrayHeights(coordinates.flatMap(([longitude, latitude], pointIndex) => [longitude, latitude, segment.heights_m[pointIndex] + 2]))
      : Cartesian3.fromDegreesArray(coordinates.flat())
    nanlinCourseEntities.push(viewer.entities.add({
      id: `nanlin-course-${segment.id}`,
      show: false,
      properties: { campusSegmentId: segment.id },
      polyline: {
        positions,
        clampToGround: !hasModelHeights,
        classificationType: ClassificationType.BOTH,
        width: 7,
        material: color
      }
    }))
    const midpointIndex = Math.floor(coordinates.length / 2)
    const midpoint = coordinates[midpointIndex]
    nanlinCourseEntities.push(viewer.entities.add({
      id: `nanlin-course-label-${segment.id}`,
      show: false,
      position: Cartesian3.fromDegrees(midpoint[0], midpoint[1], hasModelHeights ? segment.heights_m[midpointIndex] + 3 : 0),
      properties: { campusSegmentId: segment.id },
      label: {
        text: `${segment.id} ${segment.name}`,
        heightReference: hasModelHeights ? HeightReference.NONE : HeightReference.CLAMP_TO_GROUND,
        font: '700 13px sans-serif',
        fillColor: color,
        outlineColor: Color.fromCssColorString('#06111a'),
        outlineWidth: 5,
        style: LabelStyle.FILL_AND_OUTLINE,
        pixelOffset: new Cartesian2(0, -13),
        disableDepthTestDistance: Number.POSITIVE_INFINITY,
        scaleByDistance: new NearFarScalar(300, 1, 2600, 0.5)
      }
    }))
  }
  const siteColors = {
    start: '#fff4c0',
    medical: '#ff6688',
    water: '#58bfff',
    marshal: '#bd9cff',
    other: '#c8d9df'
  }
  for (const [index, site] of campusRoute.value.sites.entries()) {
    const [longitude, latitude] = site.coordinate
    const color = Color.fromCssColorString(siteColors[site.kind] ?? siteColors.other)
    const hasModelHeight = Number.isFinite(site.height_m)
    nanlinCourseEntities.push(viewer.entities.add({
      id: `nanlin-site-${index}`,
      show: false,
      position: Cartesian3.fromDegrees(longitude, latitude, hasModelHeight ? site.height_m + 4 : 0),
      properties: { campusSiteId: site.id },
      point: {
        heightReference: hasModelHeight ? HeightReference.NONE : HeightReference.CLAMP_TO_GROUND,
        pixelSize: site.kind === 'start' ? 18 : 13,
        color,
        outlineColor: Color.fromCssColorString('#06111a'),
        outlineWidth: 3,
        disableDepthTestDistance: Number.POSITIVE_INFINITY
      },
      label: {
        text: site.name,
        heightReference: hasModelHeight ? HeightReference.NONE : HeightReference.CLAMP_TO_GROUND,
        font: '700 12px sans-serif',
        fillColor: color,
        outlineColor: Color.fromCssColorString('#06111a'),
        outlineWidth: 5,
        style: LabelStyle.FILL_AND_OUTLINE,
        verticalOrigin: VerticalOrigin.BOTTOM,
        pixelOffset: new Cartesian2(0, -17),
        disableDepthTestDistance: Number.POSITIVE_INFINITY,
        scaleByDistance: new NearFarScalar(300, 1, 2500, 0.45)
      }
    }))
  }
}

function updateCampusCourseStyles() {
  if (!viewer || !campusRoute.value.simulation_linked) return
  const urgentIds = new Set(
    (props.snapshot?.alerts ?? [])
      .filter((alert) => alert.status === 'new' && alert.level === 'critical')
      .map((alert) => alert.segment_id)
  )
  for (const segment of campusRoute.value.segments) {
    const state = props.snapshot?.segments.find((item) => item.id === segment.id)
    if (!state) continue
    const urgent = urgentIds.has(segment.id)
    const selected = props.selectedSegmentId === segment.id
    const color = urgent ? Color.fromCssColorString('#ff365f') : segmentRisk(state).color
    const routeEntity = viewer.entities.getById(`nanlin-course-${segment.id}`)
    const labelEntity = viewer.entities.getById(`nanlin-course-label-${segment.id}`)
    if (routeEntity?.polyline) {
      routeEntity.polyline.width = new ConstantProperty(selected ? 12 : urgent ? 10 : 7)
      routeEntity.polyline.material = new PolylineGlowMaterialProperty({
        glowPower: urgent ? 0.42 : selected ? 0.3 : 0.16,
        color
      })
    }
    if (labelEntity?.label) {
      labelEntity.label.fillColor = new ConstantProperty(color)
      labelEntity.label.text = new ConstantProperty(`${segment.id} ${segment.name}`)
    }
  }
}

async function loadCampusRoute() {
  try {
    campusRoute.value = await platformApi.campusRoute()
    clearCampusCourseEntities()
    addCampusCourseEntities()
    setCampusCourseVisibility(nanlinSceneModeActive.value && nanlinSceneVisible.value && nanlinCourseVisible.value)
    renderSnapshot()
  } catch (error) {
    campusImportError.value = `无法读取已保存路线：${error.message}`
  }
}

async function importCampusFile(file, kind) {
  if (!file) return
  campusImportError.value = ''
  campusImportSuccess.value = ''
  if (!/\.(geojson|json)$/i.test(file.name)) {
    campusImportError.value = '请选择从 QGIS 导出的 .geojson 文件'
    return
  }
  if (kind === 'route' && campusRoute.value.segments.length && !window.confirm('新路线会替换当前已保存的校园路线，确定继续吗？')) return
  campusImportBusy.value = true
  try {
    campusRoute.value = await platformApi.importCampusGeoJson(file, kind)
    clearCampusCourseEntities()
    addCampusCourseEntities()
    setCampusCourseVisibility(nanlinSceneModeActive.value && nanlinSceneVisible.value && nanlinCourseVisible.value)
    renderSnapshot()
    campusImportSuccess.value = kind === 'route'
      ? `路线已保存：${campusRoute.value.segments.length} 段，约 ${campusRouteLength.value} km`
      : `保障点已保存：${campusRoute.value.sites.length} 个`
  } catch (error) {
    campusImportError.value = error.message
  } finally {
    campusImportBusy.value = false
    if (routeInput.value) routeInput.value.value = ''
    if (sitesInput.value) sitesInput.value.value = ''
  }
}

async function loadModels() {
  try {
    const result = await platformApi.models()
    availableModels.value = result.models ?? []
    const previous = window.localStorage.getItem('campus-model-id')
    if (previous && availableModels.value.some((item) => item.id === previous)) selectedModelId.value = previous
    else if (!availableModels.value.some((item) => item.id === selectedModelId.value)) {
      selectedModelId.value = availableModels.value[0]?.id ?? ''
    }
  } catch (error) {
    modelImportError.value = `无法读取模型列表：${error.message}`
  }
}

async function displayModel(modelId) {
  if (!modelId || modelUploadBusy.value) return
  if (!availableModels.value.some((item) => item.id === modelId)) {
    modelImportError.value = '这份模型尚未完成处理，不能切换显示'
    return
  }
  if (loadedModelId !== modelId && nanlinTileset && viewer && !viewer.isDestroyed()) {
    viewer.scene.primitives.remove(nanlinTileset)
    nanlinTileset = null
    loadedModelId = null
  }
  selectedModelId.value = modelId
  window.localStorage.setItem('campus-model-id', modelId)
  modelImportError.value = ''
  await focusCampusScene()
}

async function refreshModelJob() {
  if (!modelJob.value?.id) return
  try {
    const result = await platformApi.modelJob(modelJob.value.id)
    modelJob.value = result.job
    if (result.job.stage === 'ready') {
      window.localStorage.removeItem('campus-model-job')
      await loadModels()
      await displayModel(result.job.id)
    } else if (result.job.stage === 'error') {
      window.localStorage.removeItem('campus-model-job')
      modelImportError.value = result.job.message
    } else {
      jobPollTimer = window.setTimeout(refreshModelJob, 2000)
    }
  } catch (error) {
    window.localStorage.removeItem('campus-model-job')
    modelImportError.value = `无法读取处理状态：${error.message}`
  }
}

async function importModelZip(file) {
  if (!file) return
  modelImportError.value = ''
  if (!/\.zip$/i.test(file.name)) {
    modelImportError.value = '请选择包含完整 OSGB 或 3D Tiles 的 .zip 压缩包'
    return
  }
  if (file.size > 12 * 1024 ** 3) {
    modelImportError.value = '压缩包超过 12 GB 上限'
    return
  }
  if (file.size > 2 * 1024 ** 3 && !window.confirm(`这份模型包约 ${(file.size / 1024 ** 3).toFixed(1)} GB。上传、解压和转换可能耗时很久并占用大量磁盘空间。确认开始吗？`)) {
    if (modelZipInput.value) modelZipInput.value.value = ''
    return
  }
  modelUploadBusy.value = true
  modelUploadProgress.value = 0
  modelJob.value = null
  try {
    const result = await platformApi.importModel(file, (percent) => { modelUploadProgress.value = percent })
    modelJob.value = result.job
    window.localStorage.setItem('campus-model-job', result.job.id)
    modelUploadBusy.value = false
    await refreshModelJob()
  } catch (error) {
    modelImportError.value = error.message
  } finally {
    modelUploadBusy.value = false
    if (modelZipInput.value) modelZipInput.value.value = ''
  }
}

function setCampusCourseVisibility(visible) {
  for (const entity of nanlinCourseEntities) entity.show = visible
  if (!visible) selectedCampusFeature.value = null
  viewer?.scene.requestRender()
}

function toggleCampusCourse() {
  nanlinCourseVisible.value = !nanlinCourseVisible.value
  setCampusCourseVisibility(nanlinSceneModeActive.value && nanlinSceneVisible.value && nanlinCourseVisible.value)
}


function renderSnapshot() {
  if (!viewer || !props.snapshot) return
  renderSegments(props.snapshot.segments, props.snapshot.alerts)
  renderAthletes(props.snapshot.athletes)
  renderDrones(props.snapshot.drones)
  renderThematicLayers()
  updateCampusCourseStyles()
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

function focusCampusSegment(segmentId) {
  const segment = campusSegmentById(segmentId)
  if (!segment || !viewer) return
  const longitudes = segment.coordinates.map((coordinate) => coordinate[0])
  const latitudes = segment.coordinates.map((coordinate) => coordinate[1])
  viewer.camera.flyTo({
    destination: Rectangle.fromDegrees(
      Math.min(...longitudes) - 0.00045,
      Math.min(...latitudes) - 0.00045,
      Math.max(...longitudes) + 0.00045,
      Math.max(...latitudes) + 0.00045
    ),
    duration: 0.8
  })
}

function focusRaceCourse() {
  if (!viewer) return
  leaveCampusScene()
  viewer.camera.flyTo({
    destination: Rectangle.fromDegrees(114.343, 30.513, 114.387, 30.544),
    duration: 1.1
  })
}

function leaveCampusScene() {
  nanlinSceneModeActive.value = false
  nanlinSceneVisible.value = false
  if (nanlinTileset) nanlinTileset.show = false
  setCampusCourseVisibility(false)
  renderSnapshot()
}

async function focusCampusScene() {
  if (!viewer || nanlinSceneStatus.value === 'loading') return
  leaveCampusScene()
  nanlinSceneModeActive.value = true
  renderSnapshot()
  const model = selectedModel.value
  if (!nanlinTileset) {
    try {
      if (!model?.url) throw new Error('当前没有可用模型，请先导入完整的三维模型包')
      nanlinSceneStatus.value = 'loading'
      nanlinTileset = await Cesium3DTileset.fromUrl(model.url, {
        enableCollision: true,
        maximumScreenSpaceError: 32,
        dynamicScreenSpaceError: true,
        cacheBytes: 1024 * 1024 * 1024,
        maximumCacheOverflowBytes: 512 * 1024 * 1024,
        cullWithChildrenBounds: false
      })
      if (!viewer || viewer.isDestroyed()) return
      viewer.scene.primitives.add(nanlinTileset)
      nanlinTileset.show = false
      loadedModelId = model.id
      nanlinSceneStatus.value = 'ready'
    } catch (error) {
      console.error('三维模型加载失败', error)
      nanlinSceneStatus.value = 'error'
      modelImportError.value = `模型无法显示：${error.message}`
    }
  }
  if (!nanlinSceneModeActive.value) return
  nanlinSceneVisible.value = true
  if (nanlinTileset) nanlinTileset.show = true
  addCampusCourseEntities()
  setCampusCourseVisibility(nanlinCourseVisible.value)
  renderSnapshot()
  if (nanlinTileset) {
    await viewer.zoomTo(
      nanlinTileset,
      new HeadingPitchRange(0.15, -1.18, Math.max(500, nanlinTileset.boundingSphere.radius * 1.35))
    )
  } else {
    viewer.camera.flyTo({ destination: Rectangle.fromDegrees(118.805, 32.077, 118.820, 32.087), duration: 0.8 })
  }
  viewer.scene.requestRender()
  viewer.scene.screenSpaceCameraController.enableInputs = true
}

function toggleActiveScene() {
  if (nanlinSceneModeActive.value && nanlinTileset) {
    nanlinSceneVisible.value = !nanlinSceneVisible.value
    nanlinTileset.show = nanlinSceneVisible.value
    setCampusCourseVisibility(nanlinSceneVisible.value && nanlinCourseVisible.value)
  }
}

watch(() => props.snapshot, renderSnapshot, { deep: true })
watch(() => props.historicalAlerts, renderThematicLayers, { deep: true })
watch(layers, renderThematicLayers, { deep: true })
watch(() => props.selectedAthleteId, renderSnapshot)
watch(selectedDroneId, renderSnapshot)
watch(
  () => props.selectedSegmentId,
  (value, previous) => {
    renderSnapshot()
    if (value && value !== previous) {
      if (nanlinSceneModeActive.value && campusRoute.value.simulation_linked) focusCampusSegment(value)
      else if (!nanlinSceneModeActive.value) focusSegment(value)
    }
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
    const campusSiteId = picked?.id?.properties?.campusSiteId?.getValue()
    const campusSegmentId = picked?.id?.properties?.campusSegmentId?.getValue()
    const athleteId = picked?.id?.properties?.athleteId?.getValue()
    const droneId = picked?.id?.properties?.droneId?.getValue()
    const segmentId = picked?.id?.properties?.segmentId?.getValue()
    if (nanlinSceneModeActive.value && campusSiteId) {
      selectedCampusFeature.value = campusRoute.value.sites.find((site) => site.id === campusSiteId) ?? null
    } else if (nanlinSceneModeActive.value && campusSegmentId) {
      selectedCampusFeature.value = campusRoute.value.segments.find((segment) => segment.id === campusSegmentId) ?? null
      if (campusRoute.value.simulation_linked) emit('select-segment', campusSegmentId)
    } else if (droneId) {
      selectedDroneId.value = droneId
    } else if (athleteId) {
      emit('select-athlete', athleteId)
    } else if (segmentId) {
      emit('select-segment', segmentId)
    }
  }, ScreenSpaceEventType.LEFT_CLICK)
  renderSnapshot()
  await loadCampusRoute()
  await loadModels()
  const previousJob = window.localStorage.getItem('campus-model-job')
  if (previousJob) {
    modelJob.value = { id: previousJob, stage: 'checking', message: '正在读取上次的处理状态' }
    await refreshModelJob()
  }
  if (new URLSearchParams(window.location.search).get('scene') === 'nanlin') {
    await focusCampusScene()
  }
})

onBeforeUnmount(() => {
  if (jobPollTimer) window.clearTimeout(jobPollTimer)
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
      <span :class="nanlinSceneStatus">
        {{ nanlinSceneStatus === 'error' ? '三维模型不可用' : '场景切换' }}
      </span>
      <button @click="focusRaceCourse">赛事赛道</button>
      <button :disabled="nanlinSceneStatus === 'loading'" @click="focusCampusScene">
        {{ nanlinSceneStatus === 'loading' ? '三维模型加载中…' : nanlinSceneModeActive ? '重置实景视角' : '校园三维实景' }}
      </button>
      <button :disabled="!nanlinSceneModeActive || !nanlinTileset" @click="toggleActiveScene">
        {{ nanlinSceneVisible ? '隐藏模型' : '显示模型' }}
      </button>
      <button v-if="nanlinSceneModeActive" :disabled="!nanlinSceneVisible" @click="toggleCampusCourse">
        {{ nanlinCourseVisible ? '隐藏导入路线' : '显示导入路线' }}
      </button>
      <button v-if="nanlinSceneModeActive" class="campus-import-entry" @click="campusImportOpen = true; modelImportOpen = false">导入路线</button>
      <button class="model-import-entry" @click="modelImportOpen = true; campusImportOpen = false">导入三维模型{{ modelJob && !['ready', 'error'].includes(modelJob.stage) ? ' · 处理中' : '' }}</button>
    </div>
    <section class="layer-panel">
      <button class="layer-panel-toggle" type="button" @click="layerPanelOpen = !layerPanelOpen">专题图层 {{ layerPanelOpen ? '−' : '+' }}</button>
      <div v-if="layerPanelOpen" class="layer-panel-body">
        <template v-if="!nanlinSceneModeActive || campusRoute.simulation_linked">
          <label><input v-model="layers.crowd" type="checkbox"> 人群密度热力</label>
          <label><input v-model="layers.health" type="checkbox"> 健康风险热力</label>
          <label><input v-model="layers.uav" type="checkbox"> 无人机覆盖区</label>
          <label><input v-model="layers.alerts" type="checkbox"> 历史报警叠加</label>
          <small>{{ nanlinSceneModeActive ? '风险、覆盖与报警已按S1–S5投影到校园示范环线；数值与位置仍为模拟演示，不是实测结果。' : '赛段级风险热力、150 m 无人机圈与报警位置均为模拟示意；非实测密度、真实航拍范围或精确事发坐标。' }}</small>
        </template>
        <small v-else>这份导入路线未使用S1–S5编号，因此暂不能承载模拟风险与实体。</small>
      </div>
    </section>
    <div v-if="nanlinSceneModeActive" class="map-overlay real-scene-demo-badge">
      <b>{{ campusRoute.segments.length ? `校园导入路线 · 约 ${campusRouteLength} km` : '校园三维场景 · 待导入同伴绘制路线' }}</b>
      <span>{{ campusRoute.segments.length }} 个路线段 · {{ campusRoute.sites.length }} 个保障点 · {{ campusRoute.simulation_linked ? '已与S1–S5模拟数据建立空间映射' : '尚未与左侧模拟数据关联' }}</span>
    </div>
    <section v-if="nanlinSceneModeActive && nanlinCourseVisible" class="campus-plan-card">
      <div class="campus-plan-heading"><strong>校园路线接入</strong><span>待核查</span></div>
      <p v-if="campusRoute.segments.length">来源：{{ campusRoute.route_filename }}。{{ campusRoute.note }} 点选线段可同步选择左侧赛段。</p>
      <p v-else>旧截图拟合线已撤下。请让同伴在 QGIS 中沿道路绘制路线，导出 EPSG:4326 的 GeoJSON，再点上方“导入路线”。</p>
      <div v-if="campusRoute.sites.length" class="campus-plan-key">
        <span><i class="medical"></i>拟设医疗 {{ campusSiteCounts.medical }}</span>
        <span><i class="water"></i>拟设补给 {{ campusSiteCounts.water }}</span>
        <span><i class="marshal"></i>拟设观察 {{ campusSiteCounts.marshal }}</span>
      </div>
      <div v-if="selectedCampusFeature" class="campus-plan-selected">
        <b>{{ selectedCampusFeature.name }}</b>
        <span>{{ selectedCampusFeature.reason || selectedCampusFeature.task }}</span>
      </div>
      <small>导入成功不代表路线已经测量或验证；道路、封控与救护条件仍需现场核查。当前连接属于“模拟数据空间投影”，不是实测定位。</small>
    </section>
    <section v-if="campusImportOpen" class="campus-import-dialog" role="dialog" aria-modal="true" aria-label="导入校园路线">
      <div class="campus-import-heading"><strong>接入同伴绘制的校园路线</strong><button @click="campusImportOpen = false" aria-label="关闭">×</button></div>
      <p>路线和三维建筑模型是两种文件。这里导入 QGIS 绘制的 GeoJSON 线与点；原始 OSGB / 3D Tiles 模型不能通过这个小文件窗口上传。</p>
      <label class="campus-import-file">① 路线（必需）：LineString / MultiLineString
        <input ref="routeInput" type="file" accept=".geojson,.json" :disabled="campusImportBusy" @change="importCampusFile($event.target.files?.[0], 'route')">
      </label>
      <label class="campus-import-file">② 医疗、补给等点位（可选）：Point
        <input ref="sitesInput" type="file" accept=".geojson,.json" :disabled="campusImportBusy" @change="importCampusFile($event.target.files?.[0], 'sites')">
      </label>
      <small>导出坐标系选 WGS84 / EPSG:4326；路线属性可填 segment_id、name、task；点位属性可填 kind、name、note。文件保存在本机项目中，其他电脑需通过 Git 同步。</small>
      <p v-if="campusImportError" class="campus-import-error">{{ campusImportError }}</p>
      <p v-if="campusImportSuccess" class="campus-import-success">{{ campusImportSuccess }}</p>
    </section>
    <section v-if="modelImportOpen" class="campus-import-dialog model-import-dialog" role="dialog" aria-modal="true" aria-label="导入三维模型">
      <div class="campus-import-heading"><strong>接入三维实景模型</strong><button @click="modelImportOpen = false" aria-label="关闭">×</button></div>
      <p>这里接收完整的 <b>3D Tiles 或 OSGB 压缩包（.zip）</b>。3D Tiles 可直接校验接入；OSGB 会先在本机后台转换，不能选完文件立刻显示。</p>
      <div class="model-import-current">
        <span>当前显示</span><strong>{{ selectedModel?.name ?? '暂无模型' }}</strong>
      </div>
      <div v-if="availableModels.length" class="model-import-list">
        <span>已可使用的模型</span>
        <button v-for="model in availableModels" :key="model.id" :class="{ active: model.id === selectedModelId }" :disabled="nanlinSceneStatus === 'loading'" @click="displayModel(model.id)">
          <strong>{{ model.name }}</strong><small>{{ model.format }} · {{ model.id === selectedModelId ? '当前' : '点击切换' }}</small>
        </button>
      </div>
      <label class="campus-import-file">选择模型压缩包（最大 12 GB）
        <input ref="modelZipInput" type="file" accept=".zip,application/zip" :disabled="modelUploadBusy || (modelJob && !['ready', 'error'].includes(modelJob.stage))" @change="importModelZip($event.target.files?.[0])">
      </label>
      <div v-if="modelUploadBusy" class="model-import-progress"><strong>正在上传到本机：{{ modelUploadProgress }}%</strong><progress :value="modelUploadProgress" max="100"></progress><small>请保持网页和前后端运行，不要关闭窗口。</small></div>
      <div v-if="modelJob" class="model-import-progress"><strong>{{ modelJob.stage === 'ready' ? '处理完成' : modelJob.stage === 'error' ? '处理失败' : '后台处理中' }}</strong><span>{{ modelJob.message }}</span><progress v-if="modelJob.stage !== 'error'" :value="modelJob.progress || 0" max="100"></progress></div>
      <p v-if="modelImportError" class="campus-import-error">{{ modelImportError }}</p>
      <small>请压缩整个模型目录，保留内部层级与 metadata.xml / tileset.json 等文件。仅有一个 tileset.json 不够。原始 OSGB 转换依赖本机 3dtile 工具，可能占用数十 GB 空间；导入后仍须目视核查位置。模型文件只保存在这台电脑，不会自动上传 GitHub。</small>
    </section>
    <div v-if="selectedRisk && (!nanlinSceneModeActive || campusRoute.simulation_linked)" class="map-overlay map-risk-card" :class="selectedRisk.level">
      <span>当前赛段风险</span>
      <strong>{{ selectedRisk.label }}</strong>
      <b>{{ selectedRisk.percent }}%</b>
    </div>
    <section
      v-if="selectedDrone && !nanlinSceneModeActive"
      class="drone-monitor-card"
      :class="selectedDrone.status"
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
