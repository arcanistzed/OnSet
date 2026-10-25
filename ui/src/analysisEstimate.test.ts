import {describe,it,expect} from 'vitest';
import {analysisEstimate,needsDeep,duration,CONFIRM_ANALYSIS_AT} from './library';

const done={state:'complete'},failed={state:'failed'};
const tracks=[
 {id:'a',analysis_state:'complete',analysis:{deep:{models:{demucs:done,beat_this:done}}}},
 {id:'b',analysis_state:'partial',analysis:{deep:{models:{demucs:done,beat_this:failed}}}},
 {id:'c',analysis_state:'pending',analysis:null},
];

describe('analysis job estimates',()=>{
 it('counts a track as needing deep analysis when a model is missing or failed',()=>{
  expect(needsDeep(tracks[0])).toBe(false);
  expect(needsDeep(tracks[1])).toBe(true);
  expect(needsDeep(tracks[2])).toBe(true);
 });
 it('estimates time and disk, and lists the tracks that still need it',()=>{
  const deep=analysisEstimate(tracks,['a','b','c'],true);
  expect(deep).toMatchObject({count:3,pending:['b','c'],minutes:63,diskGb:.3});
  const light=analysisEstimate(tracks,['a','b','c'],false);
  expect(light).toMatchObject({count:3,pending:['b','c'],minutes:3,diskGb:0});
 });
 it('ignores ids that are no longer in the library',()=>{
  expect(analysisEstimate(tracks,['a','gone'],true).count).toBe(1);
 });
 it('says durations the way a DJ would',()=>{
  expect(duration(3)).toBe('about 3 min');
  expect(duration(63)).toBe('about 1.1 hours');
  expect(duration(160*21)).toBe('about 56 hours');
 });
 it('asks before jobs of more than a handful of tracks',()=>{expect(CONFIRM_ANALYSIS_AT).toBe(5);});
});
