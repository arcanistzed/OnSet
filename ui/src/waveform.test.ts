import {describe,it,expect} from 'vitest';
import {isDrag,DRAG_THRESHOLD_PX} from './library';

describe('waveform click versus drag',()=>{
 it('treats a press released in place as a click',()=>{
  expect(isDrag(100,100)).toBe(false);
  expect(isDrag(100,100+DRAG_THRESHOLD_PX-1)).toBe(false);
  expect(isDrag(100,100-(DRAG_THRESHOLD_PX-1))).toBe(false);
 });
 it('treats travel past the threshold either way as a drag',()=>{
  expect(isDrag(100,100+DRAG_THRESHOLD_PX)).toBe(true);
  expect(isDrag(100,60)).toBe(true);
 });
});
