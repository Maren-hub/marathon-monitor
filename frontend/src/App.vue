<script setup>
import { computed, ref, watch } from 'vue'
import AlertPanel from './components/AlertPanel.vue'
import CesiumMap from './components/CesiumMap.vue'
import ControlBar from './components/ControlBar.vue'
import HeaderBar from './components/HeaderBar.vue'
import SegmentPanel from './components/SegmentPanel.vue'
import { usePlatform } from './composables/usePlatform'
import { platformApi } from './services/api'

const { snapshot, connectionStatus, errorMessage, refresh } = usePlatform()
const selectedSegmentId = ref('S1')
const busy = ref(false)
const toast = ref('')

const selectedSegment = computed(() => snapshot.value?.segments.find((item) => item.id === selectedSegmentId.value) ?? null)
const isRunning = computed(() => snapshot.value?.race.status === 'running')

watch(snapshot, (value) => {
  if (value && !value.segments.some((item) => item.id === selectedSegmentId.value)) {
    selectedSegmentId.value = value.segments[0]?.id ?? ''
  }
})

function showToast(message) {
  toast.value = message
  window.setTimeout(() => {
    if (toast.value === message) toast.value = ''
  }, 2600)
}

async function injectEvent(type) {
  if (!selectedSegmentId.value) return
  busy.value = true
  try {
    await platformApi.injectEvent(type, selectedSegmentId.value)
    await refresh()
    const labels = { crowd: '聚集事件', fall: '跌倒事件', vital: '体征异常' }
    showToast(`已在${selectedSegment.value?.name ?? '当前赛段'}注入${labels[type]}`)
  } catch (error) {
    showToast(`操作失败：${error.message}`)
  } finally {
    busy.value = false
  }
}

async function controlSimulation(action) {
  busy.value = true
  try {
    snapshot.value = await platformApi.control(action)
    showToast({ start: '推演已继续', pause: '推演已暂停', reset: '模拟数据已重置' }[action])
  } catch (error) {
    showToast(`操作失败：${error.message}`)
  } finally {
    busy.value = false
  }
}

async function acknowledge(alertId) {
  try {
    await platformApi.acknowledge(alertId)
    await refresh()
    showToast('报警已确认处置')
  } catch (error) {
    showToast(`操作失败：${error.message}`)
  }
}
</script>

<template>
  <div class="app-shell">
    <HeaderBar :snapshot="snapshot" :connection-status="connectionStatus" />

    <div v-if="errorMessage" class="error-banner">{{ errorMessage }}</div>

    <main v-if="snapshot" class="dashboard-grid">
      <SegmentPanel
        :segments="snapshot.segments"
        :selected-id="selectedSegmentId"
        @select="selectedSegmentId = $event"
      />
      <CesiumMap
        :snapshot="snapshot"
        :selected-segment-id="selectedSegmentId"
        @select-segment="selectedSegmentId = $event"
      />
      <AlertPanel
        :alerts="snapshot.alerts"
        @locate="selectedSegmentId = $event"
        @acknowledge="acknowledge"
      />
      <ControlBar
        :selected-segment="selectedSegment"
        :running="isRunning"
        :busy="busy"
        @inject="injectEvent"
        @control="controlSimulation"
      />
    </main>

    <div v-else class="loading-screen">
      <div class="loading-ring"></div>
      <strong>正在连接马拉松数字孪生系统</strong>
      <span>加载赛道、运动员与无人机状态…</span>
    </div>

    <Transition name="toast">
      <div v-if="toast" class="toast-message">{{ toast }}</div>
    </Transition>
  </div>
</template>

