<script setup>
import { computed, ref, watch } from 'vue'
import AlertPanel from './components/AlertPanel.vue'
import CesiumMap from './components/CesiumMap.vue'
import ControlBar from './components/ControlBar.vue'
import HeaderBar from './components/HeaderBar.vue'
import ReviewPanel from './components/ReviewPanel.vue'
import SegmentPanel from './components/SegmentPanel.vue'
import StrategyPanel from './components/StrategyPanel.vue'
import { usePlatform } from './composables/usePlatform'
import { platformApi } from './services/api'

const { snapshot, connectionStatus, errorMessage, refresh } = usePlatform()
const selectedSegmentId = ref('S1')
const selectedAthleteId = ref('')
const lastDemoSegmentId = ref('')
const busy = ref(false)
const toast = ref('')
const reviewOpen = ref(false)

const selectedSegment = computed(() => snapshot.value?.segments.find((item) => item.id === selectedSegmentId.value) ?? null)
const isRunning = computed(() => snapshot.value?.race.status === 'running')

watch(snapshot, (value) => {
  if (value && !value.segments.some((item) => item.id === selectedSegmentId.value)) {
    selectedSegmentId.value = value.segments[0]?.id ?? ''
  }
})

watch(
  () => snapshot.value?.demo?.current_segment_id,
  (segmentId) => {
    if (segmentId && segmentId !== lastDemoSegmentId.value) {
      lastDemoSegmentId.value = segmentId
      selectedSegmentId.value = segmentId
    }
  }
)

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
    showToast({
      start: '推演已继续',
      pause: '推演已暂停',
      reset: '模拟数据已重置',
      auto_start: '自动赛事演示已开始'
    }[action])
  } catch (error) {
    showToast(`操作失败：${error.message}`)
  } finally {
    busy.value = false
  }
}

async function handleAlertAction({ alertId, action }) {
  try {
    await platformApi.alertAction(alertId, action)
    await refresh()
    const labels = {
      acknowledge: '报警信息已确认',
      uav_review: '已派遣无人机近距复核',
      medical_dispatch: '已派遣医疗救援组',
      staff_dispatch: '已派遣现场保障人员',
      resolve: '事件处置已完成'
    }
    showToast(labels[action] ?? '处置状态已更新')
  } catch (error) {
    showToast(`操作失败：${error.message}`)
  }
}
</script>

<template>
  <div class="app-shell">
    <HeaderBar :snapshot="snapshot" :connection-status="connectionStatus" @open-review="reviewOpen = true" />

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
        :selected-athlete-id="selectedAthleteId"
        @select-segment="selectedSegmentId = $event"
        @select-athlete="selectedAthleteId = $event"
      />
      <aside class="right-stack">
        <StrategyPanel :segment="selectedSegment" />
        <AlertPanel
          :alerts="snapshot.alerts"
          @locate="selectedSegmentId = $event"
          @action="handleAlertAction"
        />
      </aside>
      <ControlBar
        :selected-segment="selectedSegment"
        :running="isRunning"
        :busy="busy"
        :demo="snapshot.demo"
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

    <ReviewPanel v-if="reviewOpen && snapshot?.review" :snapshot="snapshot" @close="reviewOpen = false" />
  </div>
</template>
