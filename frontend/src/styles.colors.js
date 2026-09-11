// 与 dataviz 参考色板一致的分类色固定顺序(已通过相邻对 CVD 校验)
export const seriesColors = [
  '#2a78d6', '#eb6834', '#1baf7a', '#eda100',
  '#e87ba4', '#008300', '#4a3aa7', '#e34948',
]
export const seriesColor = (i) => seriesColors[i % seriesColors.length]
