import { sourceTime } from './history-browser.mjs';
export const PRESSURE_COLORS = Object.freeze({hp_1st:'#2563eb',lp_1st:'#60a5fa',hp_2nd:'#c65d10',lp_2nd:'#f5a54a'});

export function binaryState(value) {
  if (value === null || value === undefined || value === '') return null;
  const text=String(value).trim().toLowerCase();
  if (['on','true','1'].includes(text)) return 1;
  if (['off','false','0'].includes(text)) return 0;
  return null;
}

export function localChartPoint(rect,width,height,clientX,clientY) {
  if (!rect.width || !rect.height) return null;
  return [(clientX-rect.left)*width/rect.width,(clientY-rect.top)*height/rect.height];
}

// zrender's canvas fallback uses physical CSS coordinates under ancestor zoom.
// Supply its documented normalized event fields before renderer listeners run.
export function bindChartCoordinates(node,chart) {
  const events=['mousemove','mousedown','mouseup','click','dblclick','contextmenu','wheel','mousewheel','pointermove','pointerdown','pointerup','touchstart','touchmove','touchend'];
  const handler=event=>{
    const point=event.touches?.[0] || event.changedTouches?.[0] || event;
    const xy=localChartPoint(node.getBoundingClientRect(),chart.getWidth(),chart.getHeight(),point.clientX,point.clientY);
    if (xy) { event.zrX=xy[0];event.zrY=xy[1]; }
  };
  events.forEach(type=>node.addEventListener(type,handler,{capture:true,passive:true}));
  return ()=>events.forEach(type=>node.removeEventListener(type,handler,true));
}

export function pressureAxis(values) {
  const data=values.filter(v=>v!==null && v!==undefined).map(Number).filter(Number.isFinite);
  const low=Math.min(-100,...data),high=Math.max(0,...data),pad=Math.max(5,(high-low)*.04);
  return {type:'value',name:'Estimated pressure (kPa)',inverse:true,min:Math.floor((low-pad)/5)*5,max:high>0?Math.ceil((high+pad)/5)*5:0};
}

const stateChartCache = new WeakMap();
export function controlStateOption(rows) {
  if(stateChartCache.has(rows))return stateChartCache.get(rows);
  const names=['SV','Busy'];
  const option = {
    animation:false,color:['#8b5cf6','#0891b2'],
    tooltip:{trigger:'axis',confine:true,axisPointer:{type:'line'},formatter:params=>[new Date(params[0]?.value?.[0]).toLocaleString('en-GB',{timeZone:'Asia/Bangkok'}),...params.map(p=>`${p.seriesName}: ${p.value?.[1]??'—'}`)].join('<br/>')},
    legend:{top:0,textStyle:{color:'#98a6af'}},grid:[{left:65,right:35,top:42,height:'28%'},{left:65,right:35,top:'53%',height:'28%'}],
    axisPointer:{link:[{xAxisIndex:'all'}]},
    xAxis:[{type:'time',gridIndex:0,axisLabel:{show:false}},{type:'time',gridIndex:1,axisLabel:{hideOverlap:true,color:'#98a6af'}}],
    yAxis:names.map((name,i)=>({type:'value',name,gridIndex:i,min:0,max:1,interval:1,nameTextStyle:{color:'#98a6af'},axisLabel:{color:'#98a6af'},splitLine:{lineStyle:{color:'#293034'}}})),
    dataZoom:[{type:'inside',xAxisIndex:[0,1]},{type:'slider',xAxisIndex:[0,1],bottom:8,height:18}],
    series:names.map((name,i)=>({name,type:'line',step:'end',showSymbol:false,connectNulls:false,xAxisIndex:i,yAxisIndex:i,
      data:rows.map(row=>[sourceTime(row.recorded_at),binaryState(row[name.toLowerCase()])]),lineStyle:{width:2.3}}))
  };
  stateChartCache.set(rows,option);
  return option;
}
