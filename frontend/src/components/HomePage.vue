<script setup>
defineProps({
  connectionStatus: { type: String, default: 'connecting' }
})

const emit = defineEmits(['enter-dashboard', 'open-help', 'open-data'])

function scrollToSection(id) {
  document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}
</script>

<template>
  <div class="home-page">
    <header class="home-nav">
      <button class="home-logo" type="button" aria-label="返回首页顶部" @click="scrollToSection('home-top')">
        <span class="logo-symbol"><i></i><i></i><i></i></span>
        <span><strong>智跑慧巡</strong><small>MARATHON INTELLIGENCE</small></span>
      </button>
      <nav aria-label="首页导航">
        <button type="button" @click="scrollToSection('overview')">项目概览</button>
        <button type="button" @click="scrollToSection('capabilities')">系统能力</button>
        <button type="button" @click="emit('open-data')">数据管理</button>
        <button type="button" @click="emit('open-help')">帮助中心</button>
      </nav>
      <button class="nav-enter" type="button" @click="emit('enter-dashboard')">进入监控平台 <span aria-hidden="true">↗</span></button>
    </header>

    <main>
      <section id="home-top" class="home-hero" aria-labelledby="home-title">
        <div class="hero-image" role="img" aria-label="城市马拉松跑者、无人机与赛道的概念插画"></div>
        <div class="hero-shade" aria-hidden="true"></div>
        <div class="hero-grid" aria-hidden="true"></div>
        <div class="hero-content">
          <div class="hero-kicker"><span class="kicker-line"></span> MARATHON INTELLIGENCE</div>
          <h1 id="home-title">智跑<span>慧巡</span></h1>
          <p class="hero-lead">马拉松赛事智能监测平台</p>
          <p class="hero-brief">空地协同 <i></i> 分段监测 <i></i> 风险响应</p>
          <div class="hero-actions">
            <button class="primary-action" type="button" @click="emit('enter-dashboard')">进入监控平台 <span aria-hidden="true">↗</span></button>
          </div>
        </div>
        <div class="hero-footnote"><span class="status-dot" :class="connectionStatus"></span> 概念插画 · 模拟赛事演示</div>
        <button class="hero-scroll" type="button" @click="scrollToSection('overview')">了解项目 <span aria-hidden="true">↓</span></button>
      </section>

      <section id="overview" class="home-section overview-section">
        <div class="section-heading"><span>01 / PROJECT OVERVIEW</span><h2>从“看见赛道”到“知道先看哪里”</h2><p>平台的重点不是叠加更多画面，而是把赛道位置、风险变化与巡查任务联系起来。</p></div>
        <div class="logic-chain" aria-label="平台工作链路">
          <div><b>01</b><strong>多源感知</strong><span>赛段位置、模拟无人机与穿戴数据</span></div>
          <div><b>02</b><strong>时空融合</strong><span>统一到赛段与时间，形成态势快照</span></div>
          <div><b>03</b><strong>动态研判</strong><span>比较聚集风险与健康风险</span></div>
          <div><b>04</b><strong>任务响应</strong><span>推荐巡查、复核和现场处置</span></div>
          <div><b>05</b><strong>赛事复盘</strong><span>记录报警、响应与处置过程</span></div>
        </div>
      </section>

      <section id="capabilities" class="home-section capabilities-section">
        <div class="section-heading"><span>02 / SYSTEM CAPABILITIES</span><h2>围绕赛事全过程构建的原型能力</h2><p>按目前已经实现的功能展示，尚未接入的真实硬件与识别模型不写成既有成果。</p></div>
        <div class="capability-grid">
          <article><span class="capability-icon">◇</span><small>01 / 空间底座</small><h3>三维赛道态势</h3><p>Cesium 展示赛段、运动员、无人机与风险分级；校园倾斜摄影模型可单独切换查看。</p><b>已实现 · 实景模型已接入</b></article>
          <article><span class="capability-icon">≋</span><small>02 / 数据处理</small><h3>多源数据处理管道</h3><p>后端原型可接收统一格式的数据，完成赛段融合、规则型风险计算和任务建议。</p><b>已实现 · 当前以样例数据验证</b></article>
          <article><span class="capability-icon">◎</span><small>03 / 任务策略</small><h3>分赛段监测重点</h3><p>前程关注拥挤与通行，后程增加个体安全关注；权重随模拟赛况变化，供后续实验验证。</p><b>已实现 · 原型规则</b></article>
          <article><span class="capability-icon">↗</span><small>04 / 应急闭环</small><h3>发现—调度—处置—复盘</h3><p>演示聚集、跌倒和体征异常事件，以及无人机复核、现场响应和赛事复盘。</p><b>已实现 · 模拟推演</b></article>
        </div>
      </section>

      <section id="scenes" class="home-section scenes-section">
        <div class="section-heading"><span>03 / APPLICATION SCENES</span><h2>两种场景，各自承担不同验证任务</h2><p>把“平台流程已跑通”与“真实校园空间已接入”分开展示，成果边界更清楚。</p></div>
        <div class="scene-grid">
          <article class="scene-card simulation-scene"><div class="scene-top"><span>SCENE A</span><b>可交互演示</b></div><h3>长距离赛事模拟赛道</h3><p>五段式逻辑赛道展示人员流动、风险变化、无人机任务与事件处置。路线和运动员体征为模拟数据，用于验证系统流程。</p><button type="button" @click="emit('enter-dashboard')">进入模拟推演 <span aria-hidden="true">→</span></button></article>
          <article class="scene-card campus-scene"><div class="scene-top"><span>SCENE B</span><b>真实空间底座</b></div><h3>校园三维实景</h3><p>已接入 16 个倾斜摄影分块，可在平台地图中查看校园建筑与场地。校园赛事路线已用于模拟展示，后续仍需完成现场核查。</p><button type="button" @click="emit('enter-dashboard')">进入平台查看 <span aria-hidden="true">→</span></button></article>
        </div>
        <div class="next-step"><strong>下一步验证重点</strong><span>核实校园具体赛道与监测点 → 与三维模型配准 → 完善比赛模拟数据 → 对动态任务策略开展演示验证</span></div>
      </section>
      <section id="architecture" class="home-section architecture-section">
        <div class="section-heading"><span>04 / SYSTEM ARCHITECTURE</span><h2>智跑慧巡怎样把数据变成行动</h2><p>这是目前原型的实际技术链路；真实硬件和识别模型仍是后续接入对象。</p></div>
        <div class="architecture-flow" aria-label="系统架构图">
          <div><small>01 / 数据来源</small><strong>模拟赛事 / 标准化接入样例</strong><span>运动员、赛段、无人机、报警与校园三维模型</span></div><i aria-hidden="true">→</i>
          <div><small>02 / Python · FastAPI</small><strong>融合、风险与任务建议</strong><span>统一接口 · 规则计算 · 历史记录 · 结果导出</span></div><i aria-hidden="true">→</i>
          <div><small>03 / Vue · Cesium · ECharts</small><strong>三维监控与统计分析</strong><span>赛段态势 · 专题图层 · 事件处置 · 趋势图表</span></div><i aria-hidden="true">→</i>
          <div><small>04 / 赛事人员</small><strong>查看、确认与复盘</strong><span>任务调度建议、人工处置与成果留存</span></div>
        </div>
        <div class="architecture-docs"><strong>技术文档</strong><a href="/api/technical-docs/architecture" download>总体架构 ↗</a><a href="/api/technical-docs/pipeline" download>数据处理管道 ↗</a><a href="/api/technical-docs/campus-route" download>校园路线接入 ↗</a><button type="button" @click="emit('open-help')">查看操作指南与参数说明 →</button></div>
      </section>
    </main>

    <footer class="home-footer"><span>智跑慧巡 · 大创项目原型</span><span>真实三维场景与模拟赛事数据已明确区分</span><button type="button" @click="scrollToSection('home-top')">返回顶部 ↑</button></footer>
  </div>
</template>

<style scoped>
.architecture-section { background: #071a28; }.architecture-flow { display: flex; align-items: stretch; gap: 10px; }.architecture-flow > div { flex: 1; min-width: 0; display: grid; align-content: start; gap: 13px; min-height: 190px; padding: 22px; border: 1px solid rgba(108,206,215,.28); border-radius: 12px; background: linear-gradient(155deg,#103447,#0a2433); }.architecture-flow small { color: #69dace; font-size: 10px; }.architecture-flow strong { font-size: 17px; line-height: 1.4; }.architecture-flow span { color: #93b0bf; font-size: 12px; line-height: 1.6; }.architecture-flow > i { align-self: center; color: #5ddacb; font-style: normal; font-size: 25px; }.architecture-docs { display: flex; align-items: center; gap: 15px; flex-wrap: wrap; margin-top: 20px; color: #b6d0d7; font-size: 12px; }.architecture-docs a { padding: 8px 11px; border: 1px solid #2e6574; border-radius: 7px; color: #8de9e0; text-decoration: none; }.architecture-docs button { padding: 9px 12px; border: 0; color: #071e29; border-radius: 7px; background: #70e2d6; }.architecture-docs a:hover { border-color: #81efe2; }
@media (max-width: 1100px) { .architecture-flow { flex-wrap: wrap; }.architecture-flow > div { flex: 1 1 42%; }.architecture-flow > i { display: none; } } @media (max-width: 650px) { .architecture-flow > div { flex-basis: 100%; } }
.home-page { height: 100%; overflow-y: auto; overflow-x: hidden; color: #edf8fb; background: #06111a; scroll-behavior: smooth; }
.home-page button { cursor: pointer; }
.home-nav { height: 78px; position: relative; z-index: 10; display: flex; align-items: center; justify-content: space-between; gap: 28px; padding: 0 clamp(24px, 5vw, 88px); border-bottom: 1px solid rgba(117, 181, 202, .16); background: #071524; }
.home-logo { display: flex; align-items: center; gap: 13px; padding: 0; border: 0; color: #f0fbff; background: transparent; text-align: left; }
.logo-symbol { position: relative; width: 42px; height: 42px; display: block; border: 1px solid rgba(90, 224, 215, .6); border-radius: 12px; background: linear-gradient(145deg, #102f3d, #071824); }
.logo-symbol::after { content: ''; position: absolute; left: 10px; top: 9px; width: 18px; height: 18px; border: 2px solid #79ead9; border-left-color: transparent; border-radius: 50%; transform: rotate(-35deg); }
.logo-symbol i { position: absolute; width: 5px; height: 5px; border-radius: 50%; background: #7eecdf; box-shadow: 0 0 8px #54d9d6; }
.logo-symbol i:nth-child(1) { left: 8px; top: 24px; }.logo-symbol i:nth-child(2) { left: 23px; top: 8px; }.logo-symbol i:nth-child(3) { left: 26px; top: 27px; }
.home-logo strong { display: block; font-size: 17px; letter-spacing: .035em; }.home-logo small { display: block; margin-top: 3px; color: #75a5b3; font-size: 9px; letter-spacing: .2em; }
.home-nav nav { display: flex; align-items: center; gap: clamp(18px, 3vw, 44px); }.home-nav nav button { border: 0; color: #acc3cc; background: transparent; font-size: 13px; }.home-nav nav button:hover { color: #77ecdf; }
.nav-enter { padding: 10px 18px; border: 1px solid rgba(111, 231, 224, .45); border-radius: 7px; color: #a9f5ea; background: rgba(61, 190, 194, .08); white-space: nowrap; font-size: 12px; }.nav-enter:hover { background: rgba(61, 190, 194, .2); }.nav-enter span { margin-left: 9px; }
.home-hero { min-height: min(800px, calc(100vh - 78px)); position: relative; isolation: isolate; display: grid; grid-template-columns: minmax(390px, .92fr) minmax(530px, 1.08fr); align-items: center; gap: 15px; padding: 66px clamp(24px, 6vw, 105px) 80px; overflow: hidden; background: radial-gradient(circle at 76% 40%, #103954 0%, #0b263a 30%, #071827 65%, #06121d 100%); }
.hero-glow { position: absolute; inset: 0; z-index: -1; background: radial-gradient(ellipse at 72% 72%, rgba(33, 155, 175, .16), transparent 42%), linear-gradient(90deg, rgba(2, 11, 20, .55), transparent 72%); }
.hero-grid { position: absolute; inset: 0; z-index: -1; opacity: .35; background-image: linear-gradient(rgba(83, 154, 177, .09) 1px, transparent 1px), linear-gradient(90deg, rgba(83, 154, 177, .09) 1px, transparent 1px); background-size: 58px 58px; mask-image: linear-gradient(90deg, transparent 10%, #000 90%); }
.hero-content { position: relative; z-index: 2; padding-bottom: 18px; }.hero-kicker { display: flex; align-items: center; gap: 12px; margin-bottom: 32px; color: #7ce1d8; font-size: 12px; letter-spacing: .18em; }.kicker-line { width: 34px; height: 1px; background: #55d4cb; }
.hero-content h1 { margin: 0; font-size: clamp(38px, 3.8vw, 68px); line-height: 1.24; letter-spacing: -.045em; font-weight: 780; white-space: nowrap; }.hero-content h1 em { color: #7aebde; font-style: normal; text-shadow: 0 0 38px rgba(67, 220, 204, .2); }
.hero-lead { margin: 26px 0 16px; font-size: clamp(17px, 1.5vw, 23px); color: #d7e9ee; letter-spacing: .02em; }.hero-description { max-width: 570px; margin: 0; color: #9bb7c4; font-size: 14px; line-height: 1.9; }
.hero-actions { display: flex; gap: 12px; margin-top: 35px; }.hero-actions button { min-width: 150px; padding: 14px 22px; border-radius: 7px; font-size: 13px; font-weight: 700; }.primary-action { border: 1px solid #58dacc; color: #06252c; background: linear-gradient(110deg, #79ecdf, #42bde4); box-shadow: 0 11px 34px rgba(26, 192, 198, .18); }.primary-action:hover { filter: brightness(1.1); transform: translateY(-1px); }.secondary-action { border: 1px solid rgba(169, 204, 215, .38); color: #d3e9ee; background: rgba(12, 37, 52, .65); }.secondary-action:hover { border-color: #75dcd6; }.hero-actions span { margin-left: 15px; }
.hero-footnote { display: flex; align-items: center; gap: 9px; margin-top: 33px; color: #789aaa; font-size: 11px; }.status-dot { width: 7px; height: 7px; border-radius: 50%; background: #d5a753; }.status-dot.online { background: #51dccb; box-shadow: 0 0 13px #51dccb; }.footnote-divider { width: 1px; height: 12px; margin: 0 7px; background: #42616f; }
.hero-visual { position: relative; height: min(620px, 65vh); min-height: 480px; border: 1px solid rgba(122, 214, 228, .22); border-radius: 20px; background: radial-gradient(circle at 59% 38%, #153c4c 0%, #0a2638 46%, #081c2d 77%); box-shadow: 0 30px 90px rgba(0, 0, 0, .35), inset 0 0 95px rgba(45, 154, 177, .1); overflow: hidden; }
.hero-visual::before { content: ''; position: absolute; inset: 0; opacity: .22; background-image: linear-gradient(rgba(106, 184, 195, .18) 1px, transparent 1px), linear-gradient(90deg, rgba(106, 184, 195, .18) 1px, transparent 1px); background-size: 30px 30px; }.hero-visual::after { content: ''; position: absolute; inset: 12px; border: 1px solid rgba(99, 181, 197, .08); border-radius: 13px; pointer-events: none; }
.course-graphic { position: absolute; inset: 0; width: 100%; height: 100%; }.visual-caption { position: absolute; z-index: 2; left: 24px; top: 23px; display: grid; gap: 4px; }.visual-caption span,.visual-coordinate { color: #70aebf; font-size: 9px; letter-spacing: .19em; }.visual-caption strong { font-size: 15px; }.visual-coordinate { position: absolute; z-index: 2; top: 28px; right: 25px; }
.visual-panel { position: absolute; z-index: 2; width: 179px; padding: 13px 14px; border: 1px solid rgba(127, 205, 218, .25); border-radius: 10px; background: rgba(5, 21, 34, .9); backdrop-filter: blur(10px); box-shadow: 0 13px 28px rgba(0,0,0,.25); }.visual-panel small { display: block; color: #8caebb; font-size: 10px; }.visual-panel strong { display: block; margin: 5px 0 10px; font-size: 13px; }.visual-panel span { display: block; color: #6da4b2; font-size: 9px; }.visual-panel i { display: inline-block; width: 5px; height: 5px; margin-right: 4px; border-radius: 50%; background: #f3bd67; }.panel-crowd { top: 20%; right: 5%; }.panel-health { bottom: 18%; left: 6%; }.panel-health i { background: #f5849d; }
.visual-bottom { position: absolute; z-index: 2; right: 24px; bottom: 24px; display: flex; gap: 18px; padding: 9px 12px; border: 1px solid rgba(89, 157, 181, .18); border-radius: 6px; background: rgba(5, 22, 34, .8); }.visual-bottom span { color: #a4c3cb; font-size: 10px; white-space: nowrap; }.visual-bottom i { display: inline-block; width: 5px; height: 5px; margin-right: 4px; border-radius: 50%; background: #61d6d0; }.visual-disclaimer { position: absolute; left: 23px; bottom: 25px; z-index: 2; color: #7594a2; font-size: 9px; }
.home-section { padding: 100px clamp(24px, 6vw, 105px); scroll-margin-top: 18px; }.section-heading { max-width: 850px; margin-bottom: 36px; }.section-heading > span { color: #65d9d5; font-size: 11px; font-weight: 700; letter-spacing: .22em; }.section-heading h2 { margin: 16px 0 12px; font-size: clamp(28px, 2.7vw, 42px); line-height: 1.25; letter-spacing: -.03em; }.section-heading p { margin: 0; color: #8faab8; font-size: 14px; line-height: 1.8; }
.overview-section { background: #091c2b; }.logic-chain { display: grid; grid-template-columns: repeat(5, 1fr); gap: 12px; }.logic-chain > div { min-height: 150px; position: relative; padding: 24px 20px; border: 1px solid rgba(112, 183, 203, .18); border-radius: 11px; background: linear-gradient(155deg, rgba(31, 73, 89, .45), rgba(9, 32, 46, .8)); }.logic-chain > div:not(:last-child)::after { content: '→'; position: absolute; right: -12px; top: 45%; z-index: 2; color: #4fa7b5; background: #091c2b; }.logic-chain b { display: block; margin-bottom: 16px; color: #6de0d6; font-size: 12px; }.logic-chain strong { display: block; margin-bottom: 8px; font-size: 17px; }.logic-chain span { color: #8ba7b4; font-size: 11px; line-height: 1.6; }
.capabilities-section { background: #071725; }.capability-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 16px; }.capability-grid article { min-height: 290px; position: relative; display: flex; flex-direction: column; padding: 25px; border: 1px solid rgba(112, 183, 203, .18); border-radius: 12px; background: #0d2737; }.capability-grid article:hover { border-color: rgba(91, 211, 210, .52); transform: translateY(-2px); }.capability-icon { width: 43px; height: 43px; display: grid; place-items: center; margin-bottom: 28px; border: 1px solid rgba(91, 214, 208, .4); border-radius: 9px; color: #70e5d9; font-size: 25px; }.capability-grid small { color: #66b2be; font-size: 10px; letter-spacing: .1em; }.capability-grid h3 { margin: 8px 0 10px; font-size: 18px; }.capability-grid p { margin: 0 0 22px; color: #8eacb8; font-size: 12px; line-height: 1.8; }.capability-grid b { margin-top: auto; color: #66d7c7; font-size: 10px; font-weight: 600; }
.scenes-section { background: linear-gradient(160deg, #0b2030, #071723); }.scene-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 18px; }.scene-card { min-height: 305px; padding: 28px 30px; border: 1px solid rgba(116, 190, 210, .22); border-radius: 13px; background: radial-gradient(circle at 92% 10%, rgba(77, 187, 194, .13), transparent 42%), #0c293a; }.campus-scene { background: radial-gradient(circle at 92% 10%, rgba(90, 131, 204, .16), transparent 42%), #0b2539; }.scene-top { display: flex; align-items: center; justify-content: space-between; }.scene-top span { color: #69bdc7; font-size: 11px; letter-spacing: .16em; }.scene-top b { padding: 6px 9px; border: 1px solid rgba(89, 211, 206, .33); border-radius: 20px; color: #7bddce; font-size: 10px; font-weight: 500; }.scene-card h3 { margin: 50px 0 13px; font-size: 25px; }.scene-card p { max-width: 530px; min-height: 70px; margin: 0; color: #a2b9c4; font-size: 13px; line-height: 1.8; }.scene-card button { margin-top: 25px; padding: 0; border: 0; color: #79e4d9; background: transparent; font-size: 13px; font-weight: 700; }.scene-card button span { margin-left: 10px; }.scene-card button:hover { color: #fff; }.next-step { display: flex; gap: 23px; align-items: center; margin-top: 20px; padding: 19px 22px; border-left: 3px solid #65d9cd; background: rgba(93, 177, 181, .08); }.next-step strong { color: #a2e9e2; white-space: nowrap; font-size: 12px; }.next-step span { color: #a0b8c1; font-size: 12px; line-height: 1.6; }
.home-footer { display: flex; justify-content: space-between; align-items: center; gap: 18px; padding: 26px clamp(24px, 6vw, 105px); border-top: 1px solid rgba(112, 183, 203, .16); color: #789aa8; background: #06121d; font-size: 11px; }.home-footer button { border: 0; color: #8bdcd6; background: transparent; font-size: 11px; }
@media (max-width: 1150px) { .home-hero { grid-template-columns: 1fr; padding-top: 90px; }.hero-content { max-width: 790px; }.hero-visual { width: 100%; max-width: 840px; height: 560px; }.logic-chain { grid-template-columns: repeat(3, 1fr); }.logic-chain > div::after { display: none; }.capability-grid { grid-template-columns: repeat(2, 1fr); } }
@media (max-width: 720px) { .home-nav { height: 68px; padding: 0 17px; }.home-nav nav { display: none; }.home-logo strong { font-size: 12px; }.home-logo small { font-size: 7px; }.logo-symbol { width: 35px; height: 35px; flex: 0 0 35px; }.nav-enter { padding: 8px 9px; font-size: 10px; }.home-hero { min-height: auto; padding: 67px 20px 60px; grid-template-columns: minmax(0, 1fr); }.hero-kicker { margin-bottom: 22px; font-size: 9px; }.hero-content h1 { font-size: clamp(33px, 7vw, 52px); white-space: normal; }.hero-lead { font-size: 16px; }.hero-description { font-size: 12px; }.hero-actions { flex-wrap: wrap; }.hero-actions button { min-width: 140px; padding: 12px 14px; }.hero-footnote { flex-wrap: wrap; line-height: 1.6; }.hero-visual { min-height: 350px; height: 420px; }.visual-caption { top: 18px; left: 17px; }.visual-coordinate { display: none; }.visual-panel { width: 145px; padding: 10px; }.visual-panel strong { font-size: 10px; }.visual-panel small,.visual-panel span { font-size: 8px; }.panel-crowd { right: 4%; top: 18%; }.panel-health { left: 4%; bottom: 19%; }.visual-bottom { left: 12px; right: 12px; bottom: 12px; justify-content: space-between; gap: 5px; }.visual-bottom span { font-size: 8px; }.visual-disclaimer { left: 14px; bottom: 52px; font-size: 8px; }.home-section { padding: 68px 20px; }.logic-chain { grid-template-columns: 1fr; gap: 9px; }.logic-chain > div { min-height: 100px; padding: 17px 19px; }.logic-chain b { margin-bottom: 7px; }.capability-grid,.scene-grid { grid-template-columns: 1fr; }.capability-grid article { min-height: 230px; }.scene-card { min-height: 260px; padding: 22px; }.scene-card h3 { margin-top: 35px; font-size: 20px; }.scene-card p { min-height: 0; }.next-step { display: block; }.next-step span { display: block; margin-top: 8px; }.home-footer { flex-wrap: wrap; padding: 25px 20px; line-height: 1.6; } }
@media (prefers-reduced-motion: reduce) { .home-page { scroll-behavior: auto; } * { transition: none !important; } }

/* 首页封面：让赛事插画成为主视觉，保持与监控平台一致的深蓝、青色界面语言。 */
.home-page { position: relative; }
.home-nav { position: absolute; inset: 0 0 auto; width: 100%; border-bottom-color: rgba(216, 246, 248, .18); background: linear-gradient(180deg, rgba(3, 14, 24, .84), rgba(3, 14, 24, .28)); }
.home-hero { display: flex; align-items: center; min-height: 650px; height: 100svh; padding: 118px clamp(24px, 6vw, 105px) 126px; background: #06111a; }
.hero-image, .hero-shade { position: absolute; inset: 0; pointer-events: none; }
.hero-image { z-index: 0; background: url('/images/marathon-hero.png') center center / cover no-repeat; }
.hero-shade { z-index: 1; background: linear-gradient(90deg, rgba(3, 15, 27, .94) 0%, rgba(5, 18, 31, .85) 24%, rgba(6, 22, 35, .45) 52%, rgba(6, 19, 30, .08) 82%), linear-gradient(0deg, rgba(3, 15, 26, .67), transparent 29%, transparent 75%, rgba(3, 15, 26, .2)); }
.hero-grid { z-index: 2; opacity: .27; background-size: 65px 65px; mask-image: linear-gradient(90deg, #000 0%, transparent 65%); pointer-events: none; }
.hero-content { z-index: 3; max-width: 650px; padding: 0; }
.hero-kicker { margin-bottom: 24px; color: #8ee9df; font-size: 11px; font-weight: 700; letter-spacing: .24em; }
.kicker-line { width: 31px; background: #77e9de; }
.hero-content h1 { margin: 0; color: #f2fbfc; font-size: clamp(56px, 6.2vw, 100px); line-height: 1.07; font-weight: 800; letter-spacing: .06em; white-space: nowrap; text-shadow: 0 8px 35px rgba(0, 0, 0, .35); }
.hero-content h1 span { color: #70e4d8; }
.hero-lead { margin: 22px 0 0; color: #f0f8f8; font-size: clamp(19px, 1.8vw, 29px); font-weight: 600; letter-spacing: .1em; text-shadow: 0 3px 14px rgba(0,0,0,.45); }
.hero-brief { display: flex; align-items: center; gap: 14px; margin: 18px 0 0; color: #c3dde0; font-size: 13px; letter-spacing: .09em; }
.hero-brief i { width: 3px; height: 3px; border-radius: 50%; background: #86dcd8; }
.hero-actions { margin-top: 42px; }
.hero-actions button { min-width: 195px; padding: 15px 26px; font-size: 14px; }
.primary-action { border-radius: 8px; background: linear-gradient(110deg, #8cf2e5, #43c5e2); box-shadow: 0 14px 38px rgba(7, 44, 53, .28); }
.hero-footnote { position: absolute; z-index: 3; left: clamp(24px, 6vw, 105px); bottom: 31px; margin: 0; color: #d2e6e7; font-size: 11px; letter-spacing: .05em; }
.hero-scroll { position: absolute; z-index: 3; right: clamp(24px, 6vw, 105px); bottom: 25px; display: flex; align-items: center; gap: 12px; padding: 6px 0; border: 0; color: #e0eeee; background: transparent; font-size: 11px; letter-spacing: .08em; }
.hero-scroll span { font-size: 16px; }
.hero-scroll:hover { color: #87e9dc; }

@media (max-width: 1150px) {
  .home-hero { display: flex; padding-top: 112px; }
  .hero-content { max-width: 620px; }
}
@media (max-width: 720px) {
  .home-nav { height: 68px; }
  .home-hero { height: 100svh; min-height: 620px; padding: 112px 24px 110px; }
  .hero-image { background-position: 54% center; }
  .hero-shade { background: linear-gradient(90deg, rgba(3, 15, 27, .91), rgba(4, 17, 29, .62) 70%, rgba(5, 19, 30, .33)), linear-gradient(0deg, rgba(3, 15, 26, .73), transparent 36%); }
  .hero-kicker { margin-bottom: 18px; font-size: 9px; }
  .hero-content h1 { font-size: clamp(50px, 13vw, 72px); letter-spacing: .03em; }
  .hero-lead { margin-top: 19px; font-size: 18px; letter-spacing: .04em; }
  .hero-brief { flex-wrap: wrap; gap: 9px; font-size: 10px; }
  .hero-actions { margin-top: 31px; }
  .hero-actions button { min-width: 177px; }
  .hero-footnote { left: 24px; bottom: 25px; font-size: 10px; }
  .hero-scroll { display: none; }
}
</style>
