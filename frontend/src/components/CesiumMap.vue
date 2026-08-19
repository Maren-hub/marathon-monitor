<script setup>
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import {
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
  selectedSegmentId: { type: String, default: '' }
})

const emit = defineEmits(['select-segment'])
const container = ref(null)
let viewer = null
let clickHandler = null
const segmentEntities = new Map()
const athleteEntities = new Map()
const droneEntities = new Map()

function segmentColor(segment) {
  const dominantRisk = Math.max(segment.crowd_risk, segment.health_risk)
  if (dominantRisk >= 0.78) return Color.fromCssColorString('#ff4d6d')
  if (segment.focus === 'crowd') return Color.fromCssColorString('#ffb547')
  if (segment.focus === 'health') return Color.fromCssColorString('#ff6b8a')
  return Color.fromCssColorString('#34d6c7')
}

function athleteColor(status) {
  if (status === 'fallen') return Color.fromCssColorString('#ff365f')
  if (status === 'warning') return Color.fromCssColorString('#ffb547')
  if (status === 'finished') return Color.fromCssColorString('#708196')
  return Color.fromCssColorString('#f3f7fb')
}

function renderSegments(segments) {
  for (const segment of segments) {
    const flatCoordinates = segment.coordinates.flat()
    const midpoint = segment.coordinates[Math.floor(segment.coordinates.length / 2)]
    const color = segmentColor(segment)
    const selected = segment.id === props.selectedSegmentId
    let entity = segmentEntities.get(segment.id)
    if (!entity) {
      entity = viewer.entities.add({
        id: `segment-${segment.id}`,
        position: Cartesian3.fromDegrees(midpoint[0], midpoint[1], 35),
        properties: { segmentId: segment.id },
        polyline: {
          positions: Cartesian3.fromDegreesArray(flatCoordinates),
          clampToGround: true,
          width: selected ? 12 : 7,
          material: new PolylineGlowMaterialProperty({ glowPower: 0.18, color })
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
      entity.polyline.width = new ConstantProperty(selected ? 12 : 7)
      entity.polyline.material = new PolylineGlowMaterialProperty({ glowPower: selected ? 0.28 : 0.16, color })
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
    if (!entity) {
      entity = viewer.entities.add({
        id: `athlete-${athlete.id}`,
        position: Cartesian3.fromDegrees(athlete.longitude, athlete.latitude, 12),
        point: {
          pixelSize: abnormal ? 11 : 5,
          color: athleteColor(athlete.status),
          outlineColor: Color.fromCssColorString('#07131f'),
          outlineWidth: 2,
          disableDepthTestDistance: Number.POSITIVE_INFINITY
        },
        label: {
          text: abnormal ? `${athlete.bib} · ${athlete.heart_rate} bpm` : '',
          show: abnormal,
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
      entity.point.pixelSize = new ConstantProperty(abnormal ? 11 : 5)
      entity.label.show = new ConstantProperty(abnormal)
      entity.label.text = new ConstantProperty(abnormal ? `${athlete.bib} · ${athlete.heart_rate} bpm` : '')
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
    if (!entity) {
      entity = viewer.entities.add({
        id: `drone-${drone.id}`,
        position: Cartesian3.fromDegrees(drone.longitude, drone.latitude, drone.altitude_m),
        point: {
          pixelSize: 12,
          color: Color.fromCssColorString('#49bfff'),
          outlineColor: Color.WHITE,
          outlineWidth: 2,
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
      entity.label.text = new ConstantProperty(`◆ ${drone.name} · ${Math.round(drone.battery_percent)}%`)
    }
  }
}

function renderSnapshot() {
  if (!viewer || !props.snapshot) return
  renderSegments(props.snapshot.segments)
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
    const segmentId = picked?.id?.properties?.segmentId?.getValue()
    if (segmentId) emit('select-segment', segmentId)
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
    <div class="map-overlay legend">
      <span><i class="crowd"></i>聚集优先</span>
      <span><i class="health"></i>健康优先</span>
      <span><i class="balanced"></i>综合监测</span>
      <span><i class="critical"></i>高风险</span>
    </div>
  </div>
</template>
