// 历史草案，仅存档，不再由平台加载。路线应由 GIS 同伴绘制并通过 GeoJSON 导入。
// 原校园候选线位使用 WGS84；第三项是旧模型表面高程（米）。
// 根据同伴在模型俯视截图上手绘的路线，于模型中逐点目视拟合，不是实测道路中心线。
// 这些高程仅适配当前模型的放置方式；更换模型或实地核线后需重新校准。
export const nanlinCourse = {
  status: '候选方案·待现场核实',
  source: '同伴手绘路线截图 + 校园倾斜摄影模型目视拟合',
  route: [
    [118.8138126, 32.0844876, -149.01], // 北侧林缘，拟设起终点
    [118.8144405, 32.0842824, -154.85],
    [118.8149484, 32.0837388, -148.00],
    [118.8156407, 32.0833695, -148.00],
    [118.8162200, 32.0829990, -151.86],
    [118.8166026, 32.0823082, -150.00], // 东侧弯道
    [118.8168719, 32.0816939, -150.00],
    [118.8169139, 32.0810961, -155.26],
    [118.8165495, 32.0805529, -154.03],
    [118.8161457, 32.0802350, -153.31],
    [118.8155954, 32.0801753, -154.73],
    [118.8148971, 32.0804191, -158.10],
    [118.8141084, 32.0805968, -159.21],
    [118.8132937, 32.0806747, -160.86], // 南侧道路
    [118.8126924, 32.0806290, -161.65],
    [118.8120419, 32.0802654, -163.07], // 体育场南侧转弯
    [118.8117364, 32.0804848, -162.00],
    [118.8112390, 32.0811787, -163.35],
    [118.8101119, 32.0818060, -165.05],
    [118.8090693, 32.0823845, -164.29], // 体育馆西侧外缘道路
    [118.8091116, 32.0830720, -163.72],
    [118.8093822, 32.0835345, -160.00],
    [118.8098567, 32.0837538, -161.44],
    [118.8104651, 32.0841258, -163.29],
    [118.8117723, 32.0836823, -161.48],
    [118.8121022, 32.0836921, -152.10],
    [118.8123758, 32.0842034, -151.86],
    [118.8128361, 32.0845851, -150.00],
    [118.8134300, 32.0845769, -146.82],
    [118.8138126, 32.0844876, -149.01]
  ],
  segments: [
    { id: 'C1', name: '北侧林缘段', from: 0, to: 5, task: '起跑聚集、通行秩序' },
    { id: 'C2', name: '东侧弯道段', from: 5, to: 10, task: '转弯减速、道路边界' },
    { id: 'C3', name: '南侧道路段', from: 10, to: 16, task: '人流交汇、补给秩序' },
    { id: 'C4', name: '体育馆西侧段', from: 16, to: 23, task: '路口冲突、个体体征' },
    { id: 'C5', name: '北侧回程段', from: 23, to: 29, task: '疲劳风险、终点汇集' }
  ],
  sites: [
    { id: 'start', kind: 'start', name: '拟设起终点', routeIndex: 0, reason: '位于北侧道路；集结空间、道路通行和校方许可待现场核实。' },
    { id: 'medical-1', kind: 'medical', name: '拟设医疗点 M1', routeIndex: 28, reason: '服务起终点人群；救护车进出条件与校方场地许可待核实。' },
    { id: 'medical-2', kind: 'medical', name: '拟设医疗点 M2', routeIndex: 9, reason: '覆盖东南侧弯道与南侧道路；救护通道待核实。' },
    { id: 'medical-3', kind: 'medical', name: '拟设医疗点 M3', routeIndex: 19, reason: '覆盖体育馆西侧回程；驻点位置与救护资源待核实。' },
    { id: 'water-1', kind: 'water', name: '拟设补给点 W1', routeIndex: 7, reason: '分散前段人流；布置空间和垃圾回收位置待核实。' },
    { id: 'water-2', kind: 'water', name: '拟设补给点 W2', routeIndex: 16, reason: '照顾后程体力变化；不能妨碍校园正常通行。' },
    { id: 'marshal-1', kind: 'marshal', name: '拟设观察点 V1', routeIndex: 6, reason: '关注东侧弯道转弯冲突，志愿者站位待核实。' },
    { id: 'marshal-2', kind: 'marshal', name: '拟设观察点 V2', routeIndex: 26, reason: '关注回程与终点汇集，现场视线待核实。' }
  ]
}

export function routeLengthKm(coordinates = []) {
  const radiusKm = 6371.0088
  let length = 0
  for (let index = 1; index < coordinates.length; index += 1) {
    const [longitude1, latitude1] = coordinates[index - 1]
    const [longitude2, latitude2] = coordinates[index]
    const dLatitude = (latitude2 - latitude1) * Math.PI / 180
    const dLongitude = (longitude2 - longitude1) * Math.PI / 180
    const a = Math.sin(dLatitude / 2) ** 2
      + Math.cos(latitude1 * Math.PI / 180) * Math.cos(latitude2 * Math.PI / 180)
      * Math.sin(dLongitude / 2) ** 2
    length += 2 * radiusKm * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a))
  }
  return length
}
