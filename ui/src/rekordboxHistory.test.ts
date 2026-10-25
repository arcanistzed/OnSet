import {describe,it,expect} from 'vitest';
import {restoreSummary,newestFirst} from './RekordboxHistory';

const titles:Record<string,string>={a:'Losing It',b:'Stop It',c:'La Danza',d:'Lock In'};
const titleOf=(id:string)=>titles[id];
const cue={InMsec:1};

describe('rekordbox write history',()=>{
 it('names the tracks and cues a write changed',()=>{
  expect(restoreSummary({written:[{track_id:'a',cues:[cue,cue]}]},titleOf)).toBe('Cues for Losing It (2 cues)');
  expect(restoreSummary({written:['a','b','c','d'].map(track_id=>({track_id,cues:[cue]}))},titleOf)).toBe('Cues for Losing It, Stop It, La Danza and 1 more (4 cues)');
 });
 it('reads older manifests that list bare track ids',()=>{
  expect(restoreSummary({written:['b']},titleOf)).toBe('Cues for Stop It');
 });
 it('describes pad repairs by what moved, not as zero tracks written',()=>{
  expect(restoreSummary({kind:'hot-slot-repair',written:[],moved:9,dropped:3},titleOf)).toBe('Hot cue pad repair: 9 moved, 3 removed');
 });
 it('says when a write changed no cues',()=>{
  expect(restoreSummary({written:[]},titleOf)).toBe('A playlist or comment write, with no cue changes');
 });
 it('lists the newest write first',()=>{
  expect(newestFirst([{created:'2026-10-22T10:41'},{created:'2026-10-22T18:40'}]).map(m=>m.created)).toEqual(['2026-10-22T18:40','2026-10-22T10:41']);
 });
});
