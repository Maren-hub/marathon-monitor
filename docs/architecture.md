# 平台架构说明

## 当前原型

```text
Python 模拟器
├─ 36 名运动员轨迹与心率
├─ 2 架无人机状态与任务
├─ 5 个赛段的聚集/健康风险
└─ 聚集、跌倒、体征异常事件
          │
          ▼
FastAPI 后端
├─ REST API
├─ WebSocket 实时推送
├─ 报警确认
└─ 监测任务自动切换
          │
          ▼
Vue + Cesium 前端
├─ 三维赛道
├─ 运动员与无人机位置
├─ 分段风险与监测任务
└─ 事件注入、报警和推演控制
```

## 后续真实系统

```text
手环/手机 ─MQTT─┐
                ├─ 数据接入服务 ─ PostgreSQL/PostGIS
无人机遥测 ────┤                       │
                │                       ├─ 风险计算服务
无人机视频 ─AI─┘                       ├─ 任务编排服务
                                        └─ 报警与救援调度
                                                 │
                                                 ▼
                                         Vue + Cesium 平台
```

## 已预留的扩展位置

- `backend/app/simulation.py`：将模拟数据逐步替换为真实数据源。
- `backend/app/main.py`：增加手环、无人机、AI事件和空间查询接口。
- `backend/app/schemas.py`：维护前后端统一的数据结构。
- `frontend/src/components/CesiumMap.vue`：加载真实3D Tiles和空间分析结果。
- `frontend/src/services/api.js`：对接新增后台接口。

## 建议的数据库表

进入第二阶段后，建议使用 PostgreSQL/PostGIS 添加：

- `race_tracks`：赛事和赛道中心线；
- `track_segments`：赛段几何、起止里程与静态风险；
- `athletes`：匿名运动员与设备编号；
- `wearable_readings`：位置、心率、步频和传感器质量；
- `drones`、`drone_telemetry`：无人机及其实时遥测；
- `detected_events`：AI或设备发现的异常事件；
- `segment_risk_snapshots`：各赛段的时序风险；
- `monitoring_tasks`：任务类型、优先级和执行资源；
- `alerts`：报警、确认与处置记录。

