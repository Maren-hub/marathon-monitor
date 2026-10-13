<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { platformApi } from '../services/api'

const emit = defineEmits(['return-dashboard', 'return-home'])

const sourceModules = {
  wearable: {
    icon: '环', name: '手环体征数据', shortName: '手环数据', code: 'WEARABLE',
    description: '管理匿名运动员的距离、速度、心率、血氧和状态记录。',
    usage: '用于个体状态筛查、赛段体征统计和健康风险计算。',
    fields: [
      ['timestamp', '采集时间'], ['source_id', '设备编号'], ['athlete_id', '匿名运动员'], ['segment_id', '所属赛段'],
      ['distance_km', '距离/km'], ['speed_m_s', '速度/m·s⁻¹'], ['heart_rate_bpm', '心率/bpm'], ['spo2_pct', '血氧/%'],
      ['athlete_status', '运动状态'], ['data_quality', '数据质量'], ['data_status', '数据性质']
    ]
  },
  uav: {
    icon: '航', name: '无人机观测数据', shortName: '无人机数据', code: 'UAV',
    description: '管理无人机对赛段人数、观测面积、速度和异常目标的结构化观测。',
    usage: '用于计算人员密度、识别聚集趋势并提供疑似异常线索。',
    fields: [
      ['timestamp', '观测时间'], ['source_id', '无人机编号'], ['segment_id', '观测赛段'], ['person_count', '识别人数'],
      ['observed_area_m2', '观测面积/m²'], ['avg_speed_m_s', '平均速度/m·s⁻¹'], ['suspected_fall_count', '疑似跌倒'],
      ['abnormal_motion_count', '异常运动'], ['data_quality', '数据质量'], ['data_status', '数据性质']
    ]
  },
  environment: {
    icon: '境', name: '环境监测数据', shortName: '环境数据', code: 'ENVIRONMENT',
    description: '管理各赛段对应时间窗口的温度、湿度、风速和降雨量。',
    usage: '用于表达高温高湿等环境压力，并辅助解释赛事风险。',
    fields: [
      ['timestamp', '采集时间'], ['source_id', '环境站编号'], ['segment_id', '所属赛段'], ['temperature_c', '温度/℃'],
      ['humidity_pct', '湿度/%'], ['wind_speed_m_s', '风速/m·s⁻¹'], ['rainfall_mm', '降雨/mm'],
      ['data_quality', '数据质量'], ['data_status', '数据性质']
    ]
  },
  gis_segments: {
    icon: '段', name: '赛段GIS属性', shortName: '赛段GIS', code: 'GIS SEGMENT',
    description: '管理S1—S5的里程范围、道路宽度、坡度、弯道和救援通达条件。',
    usage: '用于把动态观测关联到稳定的赛段属性，并构造道路约束信号。',
    fields: [
      ['segment_id', '赛段编号'], ['start_km', '起点/km'], ['end_km', '终点/km'], ['road_width_m', '道路宽度/m'],
      ['mean_slope_pct', '平均坡度/%'], ['max_slope_pct', '最大坡度/%'], ['curve_level', '弯道等级'],
      ['emergency_access', '救援通达性'], ['nearest_medical_distance_km', '医疗点距离/km'], ['data_status', '数据性质']
    ]
  }
}

const navigation = [
  { key: 'overview', icon: '总', name: '数据总览', group: '总览' },
  ...Object.entries(sourceModules).map(([key, item], index) => ({ key, icon: item.icon, name: item.shortName, group: index === 0 ? '结构化观测' : '' })),
  { key: 'route', icon: '线', name: '路线与保障点', group: '空间资产' },
  { key: 'models', icon: '模', name: '三维实景模型', group: '' },
  { key: 'events', icon: '事', name: '事件记录', group: '业务成果' },
  { key: 'fusion', icon: '融', name: '赛段融合结果', group: '' }
]

const activeModule = ref('overview')
const dataViewMode = ref('simulation')
const loading = ref(true)
const refreshing = ref(false)
const pageError = ref('')
const refreshedAt = ref(null)
const status = ref(null)
const results = ref([])
const rules = ref(null)
const route = ref(null)
const models = ref([])
const snapshot = ref(null)
const sourceData = ref({})

const tableInput = ref(null)
const pendingExpectedKind = ref('')
const tableUploading = ref(false)
const tableDragging = ref('')
const defaultStatus = ref('模拟')
const tableReport = ref(null)
const tableFailure = ref(null)

const routeMessage = ref('')
const routeFailure = ref('')
const modelUploading = ref(false)
const modelUploadProgress = ref(0)
const modelJob = ref(null)
let modelPollTimer = null
let simulationPollTimer = null

const currentSource = computed(() => sourceModules[activeModule.value] ?? null)
const alerts = computed(() => (snapshot.value?.alerts ?? []).filter((item) => item.event_type !== 'system'))
const usableResults = computed(() => results.value.filter((item) => item.record_status === 'usable'))
const partialResults = computed(() => results.value.filter((item) => item.record_status !== 'usable'))

const athletesBySegment = computed(() => {
  const grouped = Object.fromEntries((snapshot.value?.segments ?? []).map((item) => [item.id, []]))
  for (const athlete of snapshot.value?.athletes ?? []) {
    if (!grouped[athlete.segment_id]) grouped[athlete.segment_id] = []
    grouped[athlete.segment_id].push(athlete)
  }
  return grouped
})

function segmentAverageSpeed(segmentId) {
  const athletes = athletesBySegment.value[segmentId] ?? []
  if (!athletes.length) return 0
  const total = athletes.reduce((sum, item) => sum + (item.pace_min_km > 0 ? 1000 / (item.pace_min_km * 60) : 0), 0)
  return Number((total / athletes.length).toFixed(2))
}

const simulationSourceData = computed(() => {
  const state = snapshot.value
  if (!state) return Object.fromEntries(Object.keys(sourceModules).map((key) => [key, { total: 0, returned: 0, records: [] }]))
  const timestamp = state.generated_at
  const wearable = state.athletes.map((item) => ({
    timestamp, source_id: `WRIST-${item.id}`, athlete_id: item.id, segment_id: item.segment_id,
    distance_km: item.distance_km, speed_m_s: Number((item.pace_min_km > 0 ? 1000 / (item.pace_min_km * 60) : 0).toFixed(2)),
    heart_rate_bpm: item.heart_rate, spo2_pct: item.blood_oxygen, athlete_status: item.status,
    data_quality: null, data_status: '模拟'
  }))
  const uav = state.drones.map((item) => {
    const athletes = athletesBySegment.value[item.target_segment_id] ?? []
    return {
      timestamp, source_id: item.id, segment_id: item.target_segment_id, person_count: athletes.length,
      observed_area_m2: null, avg_speed_m_s: segmentAverageSpeed(item.target_segment_id),
      suspected_fall_count: athletes.filter((athlete) => athlete.status === 'fallen').length,
      abnormal_motion_count: athletes.filter((athlete) => ['warning', 'fallen'].includes(athlete.status)).length,
      data_quality: null, data_status: '模拟'
    }
  })
  const environment = state.segments.map((item) => ({
    timestamp, source_id: 'SIM-WEATHER-01', segment_id: item.id,
    temperature_c: state.race.temperature_c, humidity_pct: state.race.humidity_percent,
    wind_speed_m_s: null, rainfall_mm: null, data_quality: null, data_status: '模拟'
  }))
  const gisSegments = state.segments.map((item) => ({
    segment_id: item.id, start_km: item.start_km, end_km: item.end_km,
    road_width_m: null, mean_slope_pct: null, max_slope_pct: null, curve_level: '待核实',
    emergency_access: '待核实', nearest_medical_distance_km: null, data_status: '模拟'
  }))
  const payload = (records) => ({ total: records.length, returned: Math.min(records.length, 200), records: records.slice(0, 200) })
  return { wearable: payload(wearable), uav: payload(uav), environment: payload(environment), gis_segments: payload(gisSegments) }
})

const currentSourcePayload = computed(() => dataViewMode.value === 'simulation'
  ? simulationSourceData.value[activeModule.value] ?? { total: 0, returned: 0, records: [] }
  : sourceData.value[activeModule.value] ?? { total: 0, returned: 0, records: [] })

const simulationUavTasks = computed(() => snapshot.value?.drones ?? [])
const simulationFusionResults = computed(() => (snapshot.value?.segments ?? []).map((item) => ({
  window_start: snapshot.value?.generated_at,
  segment_id: item.id,
  record_status: 'simulation',
  sample_athlete_count: item.athlete_count,
  uav_person_count: item.athlete_count,
  crowd_risk: item.crowd_risk,
  health_risk: item.health_risk,
  focus_label: item.focus_label,
  data_confidence: null
})))
const currentFusionResults = computed(() => dataViewMode.value === 'simulation' ? simulationFusionResults.value : results.value)
const currentStructuredCount = computed(() => dataViewMode.value === 'simulation'
  ? Object.values(simulationSourceData.value).reduce((sum, item) => sum + item.total, 0)
  : status.value?.total_records ?? 0)
const currentSourceCount = computed(() => dataViewMode.value === 'simulation'
  ? Object.values(simulationSourceData.value).filter((item) => item.total > 0).length
  : Object.values(status.value?.source_states ?? {}).filter((item) => item.available).length)

const overviewCards = computed(() => [
  ...Object.entries(sourceModules).map(([key, item]) => ({
    key, icon: item.icon, name: item.name, description: item.description,
    count: dataViewMode.value === 'simulation' ? simulationSourceData.value[key]?.total ?? 0 : status.value?.stored?.[key] ?? 0,
    status: dataViewMode.value === 'simulation'
      ? (simulationSourceData.value[key]?.total ? '比赛模拟' : '暂无记录')
      : (status.value?.source_states?.[key]?.available ? '已接入' : '待接入')
  })),
  { key: 'route', icon: '线', name: '路线与保障点', description: 'GeoJSON赛道、分段线和医疗/补给/观察点。', count: (route.value?.segments?.length ?? 0) + (route.value?.sites?.length ?? 0), status: route.value?.segments?.length ? '已配置' : '待配置' },
  { key: 'models', icon: '模', name: '三维实景模型', description: '用于赛事环境空间表达的3D Tiles模型。', count: models.value.length, status: models.value.length ? '可加载' : '待接入' },
  { key: 'events', icon: '事', name: '事件记录', description: '聚集、疑似跌倒和体征异常的响应记录。', count: alerts.value.length, status: alerts.value.length ? '有记录' : '暂无事件' },
  { key: 'fusion', icon: '融', name: '赛段融合结果', description: '赛段级人数、风险、监测重点和任务建议。', count: currentFusionResults.value.length, status: dataViewMode.value === 'simulation' ? '动态模拟结果' : (usableResults.value.length ? `${usableResults.value.length}项可计算` : '待补齐数据') }
])

const percent = (value) => value == null ? '—' : `${Math.round(value * 100)}%`
const missingLabel = (items) => items?.map((item) => sourceModules[item]?.shortName ?? item).join('、') || '无'
const formatDateTime = (value) => value ? new Date(value).toLocaleString('zh-CN', { hour12: false }) : '—'
const recordKey = (record, index) => `${record.timestamp ?? record.segment_id ?? 'row'}-${record.source_id ?? record.athlete_id ?? index}-${index}`

function formatCell(value, field) {
  if (value === null || value === undefined || value === '') return '—'
  if (field === 'timestamp') return formatDateTime(value)
  if (field === 'data_quality') return percent(value)
  const labels = { normal: '正常', warning: '关注', fallen: '疑似倒地', finished: '完赛' }
  return labels[value] ?? value
}

function navCount(key) {
  if (sourceModules[key]) return dataViewMode.value === 'simulation' ? simulationSourceData.value[key]?.total ?? 0 : status.value?.stored?.[key] ?? 0
  if (key === 'route') return (route.value?.segments?.length ?? 0) + (route.value?.sites?.length ?? 0)
  if (key === 'models') return models.value.length
  if (key === 'events') return alerts.value.length
  if (key === 'fusion') return currentFusionResults.value.length
  return currentStructuredCount.value
}

function selectModule(key) {
  activeModule.value = key
  tableReport.value = null
  tableFailure.value = null
  pageError.value = ''
}

async function refreshAll() {
  refreshing.value = true
  pageError.value = ''
  const requests = [
    ['status', platformApi.pipelineStatus()], ['results', platformApi.pipelineSegments()], ['rules', platformApi.pipelineRules()],
    ['route', platformApi.campusRoute()], ['models', platformApi.models()], ['snapshot', platformApi.snapshot()],
    ...Object.keys(sourceModules).map((key) => [`source:${key}`, platformApi.pipelineSourceRecords(key)])
  ]
  const settled = await Promise.allSettled(requests.map(([, request]) => request))
  settled.forEach((response, index) => {
    if (response.status !== 'fulfilled') return
    const key = requests[index][0]
    if (key === 'status') status.value = response.value
    else if (key === 'results') results.value = response.value
    else if (key === 'rules') rules.value = response.value
    else if (key === 'route') route.value = response.value
    else if (key === 'models') models.value = response.value.models ?? []
    else if (key === 'snapshot') snapshot.value = response.value
    else if (key.startsWith('source:')) sourceData.value[key.split(':')[1]] = response.value
  })
  const failures = settled.filter((item) => item.status === 'rejected')
  if (failures.length) pageError.value = `有${failures.length}项数据暂时无法读取，请确认后端已启动并刷新。`
  refreshedAt.value = new Date()
  loading.value = false
  refreshing.value = false
}

async function refreshSimulationSnapshot() {
  if (dataViewMode.value !== 'simulation') return
  try {
    snapshot.value = await platformApi.snapshot()
    refreshedAt.value = new Date()
  } catch {
    // 全量刷新会显示连接错误；轮询失败时保留最后一帧，避免页面闪烁。
  }
}

function openTablePicker(expectedKind = '') {
  if (tableUploading.value) return
  pendingExpectedKind.value = expectedKind
  tableInput.value?.click()
}

function onTableDrop(event, expectedKind = '') {
  tableDragging.value = ''
  uploadTable(event.dataTransfer?.files?.[0], expectedKind)
}

async function uploadTable(file, expectedKind = '') {
  if (!file) return
  tableReport.value = null
  tableFailure.value = null
  if (!/\.(xlsx|csv)$/i.test(file.name)) {
    tableFailure.value = { message: '请选择 .xlsx 或 .csv 文件；旧版 .xls 请先另存为 .xlsx', issues: [] }
    return
  }
  if (file.size > 6 * 1024 * 1024) {
    tableFailure.value = { message: '文件超过6 MB，请拆分后再导入', issues: [] }
    return
  }
  tableUploading.value = true
  try {
    tableReport.value = await platformApi.importSpreadsheet(file, defaultStatus.value, expectedKind)
    await refreshAll()
  } catch (error) {
    tableFailure.value = { message: error.message, issues: error.issues ?? [] }
  } finally {
    tableUploading.value = false
    pendingExpectedKind.value = ''
    if (tableInput.value) tableInput.value.value = ''
  }
}

async function clearSource(source) {
  const label = sourceModules[source]?.name ?? source
  if (!window.confirm(`确认只清空“${label}”吗？其他类型数据、路线和模型将保留。`)) return
  try {
    await platformApi.resetPipelineSource(source)
    await refreshAll()
  } catch (error) {
    pageError.value = `清空失败：${error.message}`
  }
}

async function clearPipelineData() {
  if (!window.confirm('确认清空四类结构化观测记录吗？路线、模型和模拟事件不会被删除。')) return
  try {
    await platformApi.resetPipeline()
    await refreshAll()
  } catch (error) {
    pageError.value = `清空失败：${error.message}`
  }
}

async function uploadGeoJson(event, kind) {
  const file = event.target.files?.[0]
  event.target.value = ''
  if (!file) return
  routeMessage.value = ''
  routeFailure.value = ''
  try {
    route.value = await platformApi.importCampusGeoJson(file, kind)
    routeMessage.value = kind === 'route' ? '赛道路线已导入并更新' : '保障点位已导入并更新'
  } catch (error) {
    routeFailure.value = error.message
  }
}

async function uploadModel(event) {
  const file = event.target.files?.[0]
  event.target.value = ''
  if (!file) return
  if (!/\.zip$/i.test(file.name)) {
    modelJob.value = { stage: 'error', message: '三维模型请选择 .zip 压缩包' }
    return
  }
  modelUploading.value = true
  modelUploadProgress.value = 0
  modelJob.value = { stage: 'uploading', message: '正在上传模型压缩包' }
  try {
    const response = await platformApi.importModel(file, (value) => { modelUploadProgress.value = value })
    modelJob.value = response.job
    pollModelJob(response.job.id)
  } catch (error) {
    modelUploading.value = false
    modelJob.value = { stage: 'error', message: error.message }
  }
}

async function pollModelJob(jobId) {
  window.clearTimeout(modelPollTimer)
  try {
    const response = await platformApi.modelJob(jobId)
    modelJob.value = response.job
    if (response.job.stage === 'ready') {
      modelUploading.value = false
      await refreshAll()
      return
    }
    if (response.job.stage === 'error') {
      modelUploading.value = false
      return
    }
    modelPollTimer = window.setTimeout(() => pollModelJob(jobId), 1800)
  } catch (error) {
    modelUploading.value = false
    modelJob.value = { stage: 'error', message: error.message }
  }
}

async function exportCurrentData() {
  try { await platformApi.exportResults(dataViewMode.value === 'simulation' ? 'simulation' : 'pipeline') }
  catch (error) { pageError.value = `导出失败：${error.message}` }
}

onMounted(() => {
  refreshAll()
  simulationPollTimer = window.setInterval(refreshSimulationSnapshot, 3000)
})
onBeforeUnmount(() => {
  window.clearTimeout(modelPollTimer)
  window.clearInterval(simulationPollTimer)
})
</script>

<template>
  <div class="data-management-page">
    <header class="data-management-header">
      <div class="data-management-brand">
        <div class="brand-mark">数</div>
        <div><span>DATA WORKSPACE</span><h1>赛事数据管理中心</h1><p>按数据类型独立接入、检查、查看与维护</p></div>
      </div>
      <div class="data-management-header-actions">
        <div class="data-source-switch" aria-label="数据视图切换">
          <button type="button" :class="{ active: dataViewMode === 'simulation' }" @click="dataViewMode = 'simulation'"><i></i>比赛模拟数据</button>
          <button type="button" :class="{ active: dataViewMode === 'external' }" @click="dataViewMode = 'external'"><i></i>外部接入数据</button>
        </div>
        <span class="data-refresh-time">更新 {{ refreshedAt?.toLocaleTimeString('zh-CN', { hour12: false }) ?? '—' }}</span>
        <button type="button" @click="refreshAll" :disabled="refreshing">{{ refreshing ? '刷新中…' : '刷新全部' }}</button>
        <button type="button" @click="emit('return-dashboard')">监控平台</button>
        <button type="button" class="quiet" @click="emit('return-home')">首页</button>
      </div>
    </header>

    <input ref="tableInput" type="file" accept=".xlsx,.csv" hidden @change="uploadTable($event.target.files?.[0], pendingExpectedKind)">

    <div class="data-workspace">
      <aside class="data-module-nav">
        <div class="data-nav-intro"><span>数据目录</span><strong>9 个独立模块</strong><small>不同类型分开管理，避免字段和用途混淆</small></div>
        <template v-for="item in navigation" :key="item.key">
          <p v-if="item.group" class="data-nav-group">{{ item.group }}</p>
          <button type="button" :class="{ active: activeModule === item.key }" @click="selectModule(item.key)">
            <i>{{ item.icon }}</i><span>{{ item.name }}</span><b>{{ navCount(item.key) }}</b>
          </button>
        </template>
        <div class="data-storage-note"><i></i><span><b>{{ dataViewMode === 'simulation' ? '当前：比赛模拟数据' : '外部数据：内存存储' }}</b><small>{{ dataViewMode === 'simulation' ? '与监控看板共用同一推演状态，每3秒同步一次。' : '后端重启后需重新导入；路线和模型文件会保留。' }}</small></span></div>
      </aside>

      <main class="data-module-content">
        <div v-if="pageError" class="data-page-banner">{{ pageError }}</div>
        <div v-if="activeModule === 'overview' || currentSource || activeModule === 'fusion'" class="data-view-notice" :class="dataViewMode">
          <b>{{ dataViewMode === 'simulation' ? '比赛演示数据' : '外部接入数据' }}</b>
          <span v-if="dataViewMode === 'simulation'">下列记录由平台模拟器生成，与监控看板使用同一数据源，用于大创比赛的功能验证与Demo展示，不代表真实赛事观测。</span>
          <span v-else>本视图管理通过 Excel、CSV 或接口导入的结构化记录；其与比赛模拟数据分开存放、分开标识。</span>
        </div>

        <section v-if="activeModule === 'overview'" class="data-module-view">
          <div class="data-module-title"><div><span>01 / DATA CATALOG</span><h2>数据资产总览</h2><p>每种数据拥有独立管理模块；这里仅汇总状态并提供入口。</p></div><div v-if="dataViewMode === 'external'" class="data-title-actions"><select v-model="defaultStatus"><option>模拟</option><option>公开</option><option>实测</option></select><button type="button" @click="openTablePicker('')">导入多工作表文件</button></div><div v-else class="data-title-actions"><button type="button" @click="emit('return-dashboard')">返回推演看板</button></div></div>
          <section class="data-summary-grid compact">
            <article><span>结构化记录</span><strong>{{ currentStructuredCount }}</strong><small>手环、无人机、环境、GIS</small></article>
            <article><span>数据类型</span><strong>{{ currentSourceCount }}/4</strong><small>{{ dataViewMode === 'simulation' ? '当前推演可查看来源' : '已导入数据来源' }}</small></article>
            <article><span>赛段结果</span><strong>{{ currentFusionResults.length }}</strong><small>{{ dataViewMode === 'simulation' ? '当前S1—S5动态状态' : '已形成的管道结果' }}</small></article>
            <article><span>空间资源</span><strong>{{ (route?.segments?.length ?? 0) + models.length }}</strong><small>赛段线与三维模型</small></article>
          </section>
          <div class="data-catalog-grid">
            <article v-for="item in overviewCards" :key="item.key" :class="{ ready: item.count > 0 }">
              <div class="catalog-icon">{{ item.icon }}</div><div class="catalog-body"><div><span>{{ item.status }}</span><b>{{ item.count }} 项</b></div><h3>{{ item.name }}</h3><p>{{ item.description }}</p><button type="button" @click="selectModule(item.key)">进入专门模块 <span>→</span></button></div>
            </article>
          </div>
          <div v-if="dataViewMode === 'external'" class="data-overview-import" :class="{ dragging: tableDragging === 'overview' }" @dragenter.prevent="tableDragging = 'overview'" @dragover.prevent="tableDragging = 'overview'" @dragleave.prevent="tableDragging = ''" @drop.prevent="onTableDrop($event, '')">
            <div><strong>一次导入多类数据</strong><span>适合包含“wearable / uav / environment / gis_segments”多个工作表的完整Excel。</span></div><button type="button" @click="openTablePicker('')">选择文件</button>
          </div>
          <div v-else class="data-overview-import simulation-summary"><div><strong>数据随模拟赛事动态更新</strong><span>在监控看板中启动推演、触发事件或重置后，这里的运动员、无人机、事件和赛段风险将同步变化。</span></div><button type="button" @click="refreshSimulationSnapshot">立即同步</button></div>
        </section>

        <section v-else-if="currentSource" class="data-module-view">
          <div class="data-module-title"><div><span>{{ currentSource.code }}</span><h2>{{ currentSource.name }}</h2><p>{{ currentSource.description }}</p></div><div v-if="dataViewMode === 'external'" class="data-title-actions"><a :href="`/api/pipeline/templates/${activeModule}.csv`" download>下载CSV模板</a><button type="button" class="danger" @click="clearSource(activeModule)">清空本类数据</button></div><div v-else class="data-title-actions"><button type="button" @click="refreshSimulationSnapshot">同步当前推演</button></div></div>
          <section class="source-module-metrics">
            <article><span>当前记录</span><strong>{{ currentSourcePayload.total }}</strong><small>最多预览最近200条</small></article>
            <article><span>数据状态</span><strong>{{ currentSourcePayload.total ? (dataViewMode === 'simulation' ? '正在模拟' : '已接入') : (dataViewMode === 'simulation' ? '等待推演' : '待接入') }}</strong><small>{{ currentSource.usage }}</small></article>
            <article><span>数据性质</span><strong>{{ dataViewMode === 'simulation' ? '模拟' : defaultStatus }}</strong><small>{{ dataViewMode === 'simulation' ? '原型系统自动生成' : '缺少data_status列时采用' }}</small></article>
          </section>
          <div v-if="dataViewMode === 'external'" class="source-module-grid">
            <article class="data-card source-upload-card">
              <div class="data-card-heading"><div><span>IMPORT</span><h3>导入{{ currentSource.shortName }}</h3></div><select v-model="defaultStatus"><option>模拟</option><option>公开</option><option>实测</option></select></div>
              <div class="data-upload-zone" :class="{ dragging: tableDragging === activeModule, uploading: tableUploading }" role="button" tabindex="0" @click="openTablePicker(activeModule)" @keydown.enter.prevent="openTablePicker(activeModule)" @dragenter.prevent="tableDragging = activeModule" @dragover.prevent="tableDragging = activeModule" @dragleave.prevent="tableDragging = ''" @drop.prevent="onTableDrop($event, activeModule)">
                <b>{{ tableUploading ? '正在校验并导入…' : `拖入${currentSource.shortName} Excel / CSV` }}</b><span>本入口只接受当前类型；上传错表会被拒绝，不会混入其他模块。</span>
              </div>
              <div v-if="tableFailure" class="data-import-result error"><strong>{{ tableFailure.message }}</strong><ul v-if="tableFailure.issues.length"><li v-for="(issue, index) in tableFailure.issues" :key="index">{{ issue }}</li></ul></div>
              <div v-else-if="tableReport" class="data-import-result success"><strong>{{ tableReport.filename }} 已导入</strong><span>本次接收 {{ tableReport.accepted[activeModule] ?? 0 }} 条 · 当前共 {{ tableReport.stored[activeModule] ?? 0 }} 条</span></div>
            </article>
            <article class="data-card source-field-card">
              <div class="data-card-heading"><div><span>SCHEMA</span><h3>字段与使用说明</h3></div><b>{{ currentSource.fields.length }}个字段</b></div>
              <div class="source-field-list"><span v-for="field in currentSource.fields" :key="field[0]"><code>{{ field[0] }}</code><b>{{ field[1] }}</b></span></div>
              <p>{{ currentSource.usage }}</p>
              <p class="source-warning">文件上传成功、记录通过校验和形成完整风险是三个不同阶段；缺失其他来源时，本类数据仍可查看，但只生成“部分数据”结果。</p>
            </article>
          </div>
          <article class="data-card source-record-card">
            <div class="data-card-heading"><div><span>RECORD PREVIEW</span><h3>{{ dataViewMode === 'simulation' ? '比赛模拟记录' : '已接入记录' }}</h3></div><b>{{ currentSourcePayload.returned ?? 0 }}/{{ currentSourcePayload.total ?? 0 }}</b></div>
            <p v-if="dataViewMode === 'simulation'" class="module-note">本表与监控看板共用当前推演快照。空值表示该项未在现有模拟器中设定，平台不会为了填满表格而虚构测量值。<span v-if="activeModule === 'uav'"> 其中人数为目标赛段的模拟运动员汇总，不是YOLO视频识别实测结果。</span><span v-if="activeModule === 'gis_segments'"> 道路宽度、坡度和医疗点距离等未核实字段继续留空。</span></p>
            <div v-if="!currentSourcePayload.records?.length" class="data-table-empty"><strong>暂无{{ currentSource.shortName }}</strong><span>{{ dataViewMode === 'simulation' ? '请确认后端已启动，再同步当前推演。' : '下载模板填写数据，或导入符合字段要求的Excel / CSV。' }}</span></div>
            <div v-else class="data-table-wrap source-record-table"><table><thead><tr><th v-for="field in currentSource.fields" :key="field[0]">{{ field[1] }}</th></tr></thead><tbody><tr v-for="(record, index) in currentSourcePayload.records" :key="recordKey(record, index)"><td v-for="field in currentSource.fields" :key="field[0]">{{ formatCell(record[field[0]], field[0]) }}</td></tr></tbody></table></div>
          </article>
          <article v-if="dataViewMode === 'simulation' && activeModule === 'uav'" class="data-card source-record-card">
            <div class="data-card-heading"><div><span>DEVICE TASK</span><h3>无人机设备与任务状态</h3></div><b>{{ simulationUavTasks.length }}架</b></div>
            <p class="module-note">上表是按目标赛段汇总的模拟观测记录；本表专门表示设备调度信息，两者不混为同一类数据。</p>
            <div class="data-table-wrap source-record-table"><table><thead><tr><th>设备</th><th>目标赛段</th><th>当前任务</th><th>镜头模式</th><th>飞行高度</th><th>电量</th><th>任务状态</th><th>预计到达</th></tr></thead><tbody><tr v-for="item in simulationUavTasks" :key="item.id"><td><b>{{ item.name }}（{{ item.id }}）</b></td><td>{{ item.target_segment_id }}</td><td>{{ item.task }}</td><td>{{ item.camera_mode }}</td><td>{{ item.altitude_m }} m</td><td>{{ Math.round(item.battery_percent) }}%</td><td>{{ item.status === 'dispatch' ? '任务响应' : '自主巡航' }}</td><td>{{ item.eta_seconds ? `${item.eta_seconds}秒` : '已抵达' }}</td></tr></tbody></table></div>
          </article>
        </section>

        <section v-else-if="activeModule === 'route'" class="data-module-view">
          <div class="data-module-title"><div><span>SPATIAL / GEOJSON</span><h2>路线与保障点管理</h2><p>赛道分段线和医疗、补给、观察点分别导入、分别检查。</p></div><div class="data-title-actions"><label>导入赛道GeoJSON<input type="file" accept=".geojson,.json" hidden @change="uploadGeoJson($event, 'route')"></label><label>导入保障点GeoJSON<input type="file" accept=".geojson,.json" hidden @change="uploadGeoJson($event, 'sites')"></label></div></div>
          <div v-if="routeMessage" class="spatial-message success">{{ routeMessage }}</div><div v-if="routeFailure" class="spatial-message error">{{ routeFailure }}</div>
          <section class="source-module-metrics"><article><span>路线长度</span><strong>{{ route?.route_length_km ?? 0 }} km</strong><small>{{ route?.route_filename ?? '尚未导入' }}</small></article><article><span>赛段数量</span><strong>{{ route?.segments?.length ?? 0 }}</strong><small>{{ route?.simulation_linked ? '已按S1—S5承载模拟数据' : '尚未完成S1—S5关联' }}</small></article><article><span>保障点</span><strong>{{ route?.sites?.length ?? 0 }}</strong><small>{{ route?.sites_filename ?? '尚未导入' }}</small></article></section>
          <article class="data-card"><div class="data-card-heading"><div><span>ROUTE SEGMENTS</span><h3>赛道分段线</h3></div><b>{{ route?.status ?? '—' }}</b></div><p class="module-note">{{ route?.note }}</p><div v-if="!route?.segments?.length" class="data-table-empty"><strong>暂无路线</strong><span>请从QGIS导出EPSG:4326的GeoJSON线要素。</span></div><div v-else class="data-table-wrap"><table><thead><tr><th>赛段</th><th>名称</th><th>任务说明</th><th>节点数</th><th>高度信息</th></tr></thead><tbody><tr v-for="item in route.segments" :key="item.id"><td><b>{{ item.id }}</b></td><td>{{ item.name }}</td><td>{{ item.task }}</td><td>{{ item.coordinates?.length ?? 0 }}</td><td>{{ item.heights_m ? '含模型高度' : '二维经纬度' }}</td></tr></tbody></table></div></article>
          <article class="data-card"><div class="data-card-heading"><div><span>SUPPORT SITES</span><h3>赛事保障点</h3></div><b>{{ route?.sites?.length ?? 0 }}个点位</b></div><div v-if="!route?.sites?.length" class="data-table-empty"><strong>暂无保障点</strong><span>可单独导入医疗点、补给点、观察点和起终点。</span></div><div v-else class="data-table-wrap"><table><thead><tr><th>编号</th><th>类型</th><th>名称</th><th>设置说明</th><th>坐标</th></tr></thead><tbody><tr v-for="item in route.sites" :key="item.id"><td><b>{{ item.id }}</b></td><td>{{ item.kind }}</td><td>{{ item.name }}</td><td>{{ item.reason }}</td><td>{{ item.coordinate?.join(', ') }}</td></tr></tbody></table></div></article>
        </section>

        <section v-else-if="activeModule === 'models'" class="data-module-view">
          <div class="data-module-title"><div><span>SPATIAL / 3D TILES</span><h2>三维实景模型管理</h2><p>模型文件与赛事观测数据分开管理；模型负责空间表达，不直接生成风险。</p></div><div class="data-title-actions"><label :class="{ disabled: modelUploading }">{{ modelUploading ? '处理中…' : '导入模型ZIP' }}<input type="file" accept=".zip" hidden :disabled="modelUploading" @change="uploadModel"></label></div></div>
          <div class="model-catalog-grid"><article v-for="item in models" :key="item.id" class="data-card model-catalog-card"><div class="model-preview-mark">3D</div><div><span>{{ item.format }}</span><h3>{{ item.name }}</h3><p>来源：{{ item.source }}</p><small>{{ item.created_at ? formatDateTime(item.created_at) : '项目内置模型' }}</small></div><b>可加载</b></article><article v-if="!models.length" class="data-card data-table-empty"><strong>暂无可用模型</strong><span>导入包含完整tileset.json及瓦片文件的ZIP。</span></article></div>
          <div v-if="modelJob" class="model-job-status" :class="modelJob.stage"><div><strong>{{ modelJob.message }}</strong><span>{{ modelJob.stage === 'uploading' ? modelUploadProgress : modelJob.progress ?? 0 }}%</span></div><progress max="100" :value="modelJob.stage === 'uploading' ? modelUploadProgress : modelJob.progress ?? 0"></progress></div>
          <article class="data-card model-rule-card"><div class="data-card-heading"><div><span>IMPORT RULES</span><h3>模型包要求</h3></div></div><div><span><b>3D Tiles</b>ZIP中必须同时包含tileset.json和其引用的全部瓦片。</span><span><b>OSGB</b>需要metadata.xml、Data目录及全部OSGB文件，并依赖本机转换工具。</span><span><b>坐标核查</b>加载成功后仍需检查模型、路线和点位是否处于同一空间位置。</span></div></article>
        </section>

        <section v-else-if="activeModule === 'events'" class="data-module-view">
          <div class="data-module-title"><div><span>BUSINESS / EVENTS</span><h2>事件记录管理</h2><p>集中查看模拟赛事中聚集、疑似跌倒和体征异常的发现与处置状态。</p></div><div class="data-title-actions"><button type="button" @click="emit('return-dashboard')">进入事件处置</button></div></div>
          <section class="source-module-metrics"><article><span>事件总数</span><strong>{{ alerts.length }}</strong><small>不含系统启动提示</small></article><article><span>处理中</span><strong>{{ alerts.filter((item) => item.status !== 'resolved').length }}</strong><small>需要继续确认或处置</small></article><article><span>已完成</span><strong>{{ alerts.filter((item) => item.status === 'resolved').length }}</strong><small>平台状态已更新</small></article></section>
          <article class="data-card"><div class="data-card-heading"><div><span>EVENT LOG</span><h3>事件明细</h3></div><b>模拟业务记录</b></div><div v-if="!alerts.length" class="data-table-empty"><strong>暂无赛事事件</strong><span>在监控平台触发聚集、跌倒或体征异常后，这里会形成记录。</span></div><div v-else class="data-table-wrap"><table><thead><tr><th>发生时间</th><th>类型</th><th>事件名称</th><th>赛段</th><th>等级</th><th>处置状态</th><th>责任单位</th><th>响应时间</th></tr></thead><tbody><tr v-for="item in alerts" :key="item.id"><td>{{ item.timestamp ?? item.time }}</td><td>{{ item.event_type }}</td><td><b>{{ item.title }}</b></td><td>{{ item.segment_id }}</td><td>{{ item.level }}</td><td>{{ item.status }}</td><td>{{ item.responsible_unit ?? '—' }}</td><td>{{ item.response_seconds == null ? '—' : `${item.response_seconds}秒` }}</td></tr></tbody></table></div></article>
        </section>

        <section v-else-if="activeModule === 'fusion'" class="data-module-view">
          <div class="data-module-title"><div><span>BUSINESS / FUSION RESULT</span><h2>赛段融合结果管理</h2><p>{{ dataViewMode === 'simulation' ? '查看当前模拟赛事中S1—S5的人数、聚集风险、健康风险和监测重点。' : '查看四类外部数据在同一赛段、同一60秒窗口内形成的风险和任务建议。' }}</p></div><div class="data-title-actions"><button type="button" @click="exportCurrentData">导出当前成果</button><button v-if="dataViewMode === 'external'" type="button" class="danger" @click="clearPipelineData">清空四类记录</button></div></div>
          <section class="source-module-metrics"><article><span>{{ dataViewMode === 'simulation' ? '当前赛段' : '结果窗口' }}</span><strong>{{ currentFusionResults.length }}</strong><small>{{ dataViewMode === 'simulation' ? '与推演看板同步' : (rules?.version ?? 'prototype-v0.1') }}</small></article><article><span>{{ dataViewMode === 'simulation' ? '在线运动员' : '完整结果' }}</span><strong>{{ dataViewMode === 'simulation' ? (snapshot?.stats?.online_athletes ?? 0) : usableResults.length }}</strong><small>{{ dataViewMode === 'simulation' ? '匿名模拟对象' : '四类来源齐全' }}</small></article><article><span>{{ dataViewMode === 'simulation' ? '未处置事件' : '部分结果' }}</span><strong>{{ dataViewMode === 'simulation' ? (snapshot?.stats?.open_alerts ?? 0) : partialResults.length }}</strong><small>{{ dataViewMode === 'simulation' ? '聚集、跌倒或体征异常' : '明确保留缺失项' }}</small></article></section>
          <article class="data-card"><div class="data-card-heading"><div><span>SEGMENT RESULT</span><h3>{{ dataViewMode === 'simulation' ? '比赛模拟赛段结果' : '外部数据融合结果' }}</h3></div><b>{{ dataViewMode === 'simulation' ? '当前推演快照' : `${status?.time_window_seconds ?? 60}秒窗口` }}</b></div><p v-if="dataViewMode === 'simulation'" class="module-note">风险值为0—1之间的原型规则值，用于驱动监测重点切换，不是事故概率或医学诊断结果。</p><div v-if="loading" class="data-table-empty">正在读取数据状态…</div><div v-else-if="!currentFusionResults.length" class="data-table-empty"><strong>尚无赛段结果</strong><span>{{ dataViewMode === 'simulation' ? '请确认后端模拟器已启动。' : '先到四类结构化数据模块导入记录；来源不完整时也会显示部分结果。' }}</span></div><div v-else class="data-table-wrap"><table><thead><tr><th>生成时间</th><th>赛段</th><th>数据状态</th><th>运动员人数</th><th>{{ dataViewMode === 'simulation' ? '模拟汇总人数' : '无人机观测人数' }}</th><th>聚集风险</th><th>健康风险</th><th>监测重点</th><th>数据置信度</th></tr></thead><tbody><tr v-for="item in currentFusionResults" :key="`${item.window_start}-${item.segment_id}`"><td>{{ formatDateTime(item.window_start) }}</td><td><b>{{ item.segment_id }}</b></td><td><span class="record-status" :class="item.record_status">{{ item.record_status === 'simulation' ? '比赛模拟' : (item.record_status === 'usable' ? '可计算' : `缺少${missingLabel(item.missing_sources)}`) }}</span></td><td>{{ item.sample_athlete_count }}</td><td>{{ item.uav_person_count ?? '—' }}</td><td class="crowd-cell">{{ percent(item.crowd_risk) }}</td><td class="health-cell">{{ percent(item.health_risk) }}</td><td>{{ item.focus_label || '待补齐数据' }}</td><td>{{ dataViewMode === 'simulation' ? '—' : percent(item.data_confidence) }}</td></tr></tbody></table></div></article>
        </section>

        <div v-if="tableFailure && !currentSource" class="data-import-result floating error"><strong>{{ tableFailure.message }}</strong><ul v-if="tableFailure.issues.length"><li v-for="(issue, index) in tableFailure.issues" :key="index">{{ issue }}</li></ul></div>
        <div v-else-if="tableReport && !currentSource" class="data-import-result floating success"><strong>{{ tableReport.filename }} 已导入</strong><span>{{ Object.entries(tableReport.accepted).map(([key, count]) => `${sourceModules[key]?.shortName ?? key} ${count}条`).join(' · ') }}</span></div>
      </main>
    </div>
  </div>
</template>
