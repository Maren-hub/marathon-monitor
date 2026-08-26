<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import AlertPanel from './components/AlertPanel.vue'
import CesiumMap from './components/CesiumMap.vue'
import ControlBar from './components/ControlBar.vue'
import HeaderBar from './components/HeaderBar.vue'
import PipelinePanel from './components/PipelinePanel.vue'
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
const dataMode = ref('simulation')
const pipelineResults = ref([])
const pipelineError = ref('')
const pipelineUpdatedAt = ref(null)
let pipelineTimer = null

const latestPipelineResults = computed(() => {
  const latest = new Map()
  for (const result of pipelineResults.value) {
    if (result.record_status === 'usable') latest.set(result.segment_id, result)
  }
  return Array.from(latest.values())
})

const latestPipelineBySegment = computed(() => new Map(latestPipelineResults.value.map((item) => [item.segment_id, item])))
const pipelineAvailable = computed(() => latestPipelineResults.value.length > 0)

const displaySnapshot = computed(() => {
  if (!snapshot.value || dataMode.value !== 'pipeline') return snapshot.value
  const pipelineBySegment = latestPipelineBySegment.value
  return {
    ...snapshot.value,
    segments: snapshot.value.segments.map((segment) => {
      const result = pipelineBySegment.get(segment.id)
      if (!result) return { ...segment, data_source: 'simulation-fallback' }
      return {
        ...segment,
        athlete_count: result.uav_person_count ?? segment.athlete_count,
        crowd_risk: result.crowd_risk,
        health_risk: result.health_risk,
        focus: result.focus,
        focus_label: result.focus_label,
        monitoring_tasks: result.monitoring_tasks,
        recommended_units: result.recommended_units,
        data_confidence: result.data_confidence,
        rule_version: result.rule_version,
        data_source: 'pipeline'
      }
    })
  }
})

const selectedSegment = computed(() => displaySnapshot.value?.segments.find((item) => item.id === selectedSegmentId.value) ?? null)
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

async function refreshPipeline({ silent = false } = {}) {
  try {
    pipelineResults.value = await platformApi.pipelineSegments()
    pipelineUpdatedAt.value = new Date()
    pipelineError.value = ''
    if (!silent) showToast(`已读取${latestPipelineResults.value.length}个赛段的接入数据`)
  } catch (error) {
    pipelineError.value = `自动数据管道暂时不可用：${error.message}`
    if (!silent) showToast(pipelineError.value)
  }
}

async function changeDataMode(mode) {
  if (mode === 'pipeline') await refreshPipeline({ silent: true })
  dataMode.value = mode
  showToast(mode === 'pipeline' ? '已切换到自动接入数据' : '已切换到模拟推演数据')
}

function pipelineTimeLabel() {
  return pipelineUpdatedAt.value?.toLocaleTimeString('zh-CN', { hour12: false }) ?? '尚未刷新'
}

onMounted(async () => {
  await refreshPipeline({ silent: true })
  pipelineTimer = window.setInterval(() => {
    if (dataMode.value === 'pipeline') refreshPipeline({ silent: true })
  }, 3000)
})

onBeforeUnmount(() => window.clearInterval(pipelineTimer))

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
    <HeaderBar
      :snapshot="displaySnapshot"
      :connection-status="connectionStatus"
      :data-mode="dataMode"
      :pipeline-available="pipelineAvailable"
      @open-review="reviewOpen = true"
      @change-data-mode="changeDataMode"
    />

    <div v-if="errorMessage || pipelineError" class="error-banner">{{ pipelineError || errorMessage }}</div>

    <main v-if="displaySnapshot" class="dashboard-grid">
      <SegmentPanel
        :segments="displaySnapshot.segments"
        :selected-id="selectedSegmentId"
        @select="selectedSegmentId = $event"
      />
      <CesiumMap
        :snapshot="displaySnapshot"
        :selected-segment-id="selectedSegmentId"
        :selected-athlete-id="selectedAthleteId"
        @select-segment="selectedSegmentId = $event"
        @select-athlete="selectedAthleteId = $event"
      />
      <aside class="right-stack">
        <StrategyPanel :segment="selectedSegment" />
        <PipelinePanel
          v-if="dataMode === 'pipeline'"
          :results="latestPipelineResults"
          :selected-segment-id="selectedSegmentId"
          @select="selectedSegmentId = $event"
        />
        <AlertPanel
          v-else
          :alerts="snapshot.alerts"
          @locate="selectedSegmentId = $event"
          @action="handleAlertAction"
        />
      </aside>
      <div v-if="dataMode === 'pipeline'" class="control-bar pipeline-data-bar">
        <div class="selected-context">
          <span>当前数据来源</span>
          <strong>多源数据自动处理管道</strong>
          <small>{{ latestPipelineResults.length }}个赛段已接入 · 每3秒自动刷新</small>
        </div>
        <div class="pipeline-bar-status">
          <span>最近读取</span>
          <strong>{{ pipelineTimeLabel() }}</strong>
          <small>规则版本 prototype-v0.1</small>
        </div>
        <button @click="refreshPipeline()">立即刷新数据</button>
      </div>
      <ControlBar
        v-else
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

    <ReviewPanel v-if="reviewOpen && displaySnapshot?.review" :snapshot="displaySnapshot" @close="reviewOpen = false" />
  </div>
</template>
