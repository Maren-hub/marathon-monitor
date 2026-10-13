<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import AlertPanel from './components/AlertPanel.vue'
import AnalyticsPanel from './components/AnalyticsPanel.vue'
import CesiumMap from './components/CesiumMap.vue'
import ControlBar from './components/ControlBar.vue'
import DataManagementPage from './components/DataManagementPage.vue'
import HeaderBar from './components/HeaderBar.vue'
import HelpCenter from './components/HelpCenter.vue'
import HomePage from './components/HomePage.vue'
import PipelinePanel from './components/PipelinePanel.vue'
import ReviewPanel from './components/ReviewPanel.vue'
import SegmentPanel from './components/SegmentPanel.vue'
import StrategyPanel from './components/StrategyPanel.vue'
import UavReviewPage from './components/UavReviewPage.vue'
import { usePlatform } from './composables/usePlatform'
import { platformApi } from './services/api'

const { snapshot, connectionStatus, errorMessage, refresh } = usePlatform()

function viewFromHash() {
  const view = window.location.hash.replace('#', '')
  return ['dashboard', 'help', 'uav-review', 'data'].includes(view) ? view : 'home'
}

const activeView = ref(viewFromHash())
const selectedSegmentId = ref('S1')
const selectedAthleteId = ref('')
const lastDemoSegmentId = ref('')
const busy = ref(false)
const toast = ref('')
const reviewOpen = ref(false)
const uavReviewAlert = ref(null)
const analyticsOpen = ref(false)
const analytics = ref(null)
const dataMode = ref('simulation')
const pipelineResults = ref([])
const pipelineError = ref('')
const pipelineUpdatedAt = ref(null)
let pipelineTimer = null
let analyticsTimer = null

function syncViewWithUrl() {
  activeView.value = viewFromHash()
}

function changeView(view) {
  if (view !== 'dashboard') { reviewOpen.value = false; analyticsOpen.value = false }
  activeView.value = view
  window.location.hash = view
}

const latestPipelineAll = computed(() => {
  const latest = new Map()
  for (const result of pipelineResults.value) {
    latest.set(result.segment_id, result)
  }
  return Array.from(latest.values())
})

const latestPipelineResults = computed(() => latestPipelineAll.value.filter((item) => item.record_status === 'usable'))

const latestPipelineBySegment = computed(() => new Map(latestPipelineResults.value.map((item) => [item.segment_id, item])))
const pipelineAvailable = computed(() => latestPipelineAll.value.length > 0)

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

async function onSpreadsheetImported(report) {
  await refreshPipeline({ silent: true })
  showToast(`表格已导入；${report.usable_segments.length}个赛段可计算风险`)
}

async function changeDataMode(mode) {
  if (mode === 'pipeline') await refreshPipeline({ silent: true })
  dataMode.value = mode
  showToast(mode === 'pipeline' ? '已切换到自动接入数据' : '已切换到模拟推演数据')
}

function pipelineTimeLabel() {
  return pipelineUpdatedAt.value?.toLocaleTimeString('zh-CN', { hour12: false }) ?? '尚未刷新'
}

async function refreshAnalytics() {
  try { analytics.value = await platformApi.analytics() } catch (error) { console.warn('统计历史暂不可用', error) }
}

async function openAnalytics() {
  await refreshAnalytics()
  analyticsOpen.value = true
}

async function exportResults() {
  try {
    await platformApi.exportResults(dataMode.value)
    showToast('成果包已下载：含 CSV、JSON 与 HTML 快照报告')
  } catch (error) { showToast(`导出失败：${error.message}`) }
}

onMounted(async () => {
  window.addEventListener('hashchange', syncViewWithUrl)
  await refreshPipeline({ silent: true })
  await refreshAnalytics()
  pipelineTimer = window.setInterval(() => {
    if (dataMode.value === 'pipeline') refreshPipeline({ silent: true })
  }, 3000)
  analyticsTimer = window.setInterval(() => {
    if (activeView.value === 'dashboard') refreshAnalytics()
  }, 5000)
})

onBeforeUnmount(() => {
  window.clearInterval(pipelineTimer)
  window.clearInterval(analyticsTimer)
  window.removeEventListener('hashchange', syncViewWithUrl)
})

async function injectEvent(type) {
  if (!selectedSegmentId.value) return
  busy.value = true
  try {
    await platformApi.injectEvent(type, selectedSegmentId.value)
    await refresh()
    await refreshAnalytics()
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
    await refreshAnalytics()
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
    const reviewedAlert = action === 'uav_review' ? snapshot.value?.alerts.find((item) => item.id === alertId) : null
    await platformApi.alertAction(alertId, action)
    await refresh()
    await refreshAnalytics()
    const labels = {
      acknowledge: '报警信息已确认',
      uav_review: '已派遣无人机近距复核',
      medical_dispatch: '已派遣医疗救援组',
      staff_dispatch: '已派遣现场保障人员',
      resolve: '事件处置已完成'
    }
    showToast(labels[action] ?? '处置状态已更新')
    if (action === 'uav_review') {
      uavReviewAlert.value = reviewedAlert ?? null
      changeView('uav-review')
    }
  } catch (error) {
    showToast(`操作失败：${error.message}`)
  }
}
</script>

<template>
  <HomePage v-if="activeView === 'home'" :connection-status="connectionStatus" @enter-dashboard="changeView('dashboard')" @open-help="changeView('help')" @open-data="changeView('data')" />
  <HelpCenter v-else-if="activeView === 'help'" @return-home="changeView('home')" @enter-dashboard="changeView('dashboard')" />
  <UavReviewPage v-else-if="activeView === 'uav-review'" :alert="uavReviewAlert" @return-dashboard="changeView('dashboard')" />
  <DataManagementPage v-else-if="activeView === 'data'" @return-dashboard="changeView('dashboard')" @return-home="changeView('home')" />
  <div v-else class="app-shell">
    <HeaderBar
      :snapshot="displaySnapshot"
      :connection-status="connectionStatus"
      :data-mode="dataMode"
      :pipeline-available="pipelineAvailable"
      @open-review="reviewOpen = true"
      @open-analytics="openAnalytics"
      @open-help="changeView('help')"
      @open-data="changeView('data')"
      @export-results="exportResults"
      @change-data-mode="changeDataMode"
      @return-home="changeView('home')"
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
        :historical-alerts="analytics?.alerts ?? []"
        :selected-segment-id="selectedSegmentId"
        :selected-athlete-id="selectedAthleteId"
        @select-segment="selectedSegmentId = $event"
        @select-athlete="selectedAthleteId = $event"
      />
      <aside class="right-stack">
        <StrategyPanel :segment="selectedSegment" />
        <PipelinePanel
          v-if="dataMode === 'pipeline'"
          :results="latestPipelineAll"
          :selected-segment-id="selectedSegmentId"
          @select="selectedSegmentId = $event"
          @imported="onSpreadsheetImported"
        />
        <AlertPanel
          v-else
          :alerts="snapshot.alerts"
          @locate="selectedSegmentId = $event"
          @action="handleAlertAction"
          @open-uav-review="uavReviewAlert = null; changeView('uav-review')"
        />
      </aside>
      <div v-if="dataMode === 'pipeline'" class="control-bar pipeline-data-bar">
        <div class="selected-context">
          <span>当前数据来源</span>
          <strong>多源数据自动处理管道</strong>
          <small>{{ latestPipelineResults.length }}个赛段数据完整 · {{ latestPipelineAll.length - latestPipelineResults.length }}个待补齐 · 每3秒刷新</small>
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
    <AnalyticsPanel v-if="analyticsOpen && displaySnapshot" :snapshot="displaySnapshot" :analytics="analytics" :data-mode="dataMode" @close="analyticsOpen = false" />
  </div>
</template>
