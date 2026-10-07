import {test} from 'node:test';
import assert from 'node:assert/strict';
import {binaryState,localChartPoint,pressureAxis,controlStateOption} from '../src/chart-behavior.mjs';
import {COMPRESSOR_HISTORY_SIGNALS,COMPRESSOR_SIGNALS} from '../src/detail-telemetry.mjs';
test('coordinates follow effective 90 percent scale and scroll offset',()=>{
  assert.deepEqual(localChartPoint({left:100,top:200,width:900,height:270},1000,300,550,335),[500,150]);
});
test('unknown state is not OFF and control graph is stepped',()=>{
  assert.equal(binaryState('On'),1);assert.equal(binaryState('Off'),0);assert.equal(binaryState('unknown'),null);
  const o=controlStateOption([{recorded_at:'2026-10-07T00:00:00',sv:'On',busy:null}]);
  assert.equal(o.series[0].step,'end');assert.equal(o.series[1].data[0][1],null);
  assert.equal(o.series[0].data[0][0],Date.parse('2026-10-06T17:00:00Z'));
  assert.equal(COMPRESSOR_HISTORY_SIGNALS.includes('sv'),true);
  assert.equal(COMPRESSOR_HISTORY_SIGNALS.includes('busy'),true);
  assert.equal(COMPRESSOR_SIGNALS.includes('sv'),false);
  const rows=[{recorded_at:'2026-10-07T00:00:00',sv:0,busy:1}];
  assert.equal(controlStateOption(rows),controlStateOption(rows),'unchanged polls must not redraw/reset zoom');
});
test('pressure signs preserved while zero is bottom of inverse axis',()=>{
  const o=pressureAxis([-80,-70,null]);assert.equal(o.max,0);assert.equal(o.inverse,true);assert.ok(o.min<-80);
});
