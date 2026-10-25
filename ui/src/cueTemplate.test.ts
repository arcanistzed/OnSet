import {describe,it,expect} from 'vitest';
import {templateProblems,nextOpenCue,type CueTemplate} from './cueTemplate';

const role=(pad:string|null,hot=true,enabled=true)=>({enabled,memory:true,hot,pad});
const template=():CueTemplate=>({schema_version:1,bars_before_drop:{B:32,C:16},
  roles:{A:role('A'),B:role('B'),C:role('C'),D:role('D'),E:role('E'),F:role('F'),G:role('G'),L:role('H'),I:role(null,false)}});

describe('cue template',()=>{
 it('accepts the default scheme',()=>{expect(templateProblems(template())).toEqual([]);});
 it('names roles that share a pad',()=>{
  const t=template();t.roles.D.pad='B';
  expect(templateProblems(t)).toEqual(['Pad B is used by B and D']);
 });
 it('ignores pads of disabled or memory-only roles',()=>{
  const t=template();t.roles.D={...t.roles.D,pad:'B',hot:false};expect(templateProblems(t)).toEqual([]);
  t.roles.D={...t.roles.D,hot:true,enabled:false};expect(templateProblems(t)).toEqual([]);
 });
 it('needs a pad for every hot cue and sensible bar counts',()=>{
  const t=template();t.roles.I.hot=true;t.bars_before_drop.B=0;
  expect(templateProblems(t)).toEqual(['B: bars before the drop must be a whole number from 1 to 64','I: choose a pad for its hot cue']);
 });
});

describe('fast cue review',()=>{
 const cues=[{id:'a',review:'approved'},{id:'b',review:'proposed'},{id:'c',review:'rejected'},{id:'d',review:'stale'}];
 it('moves on to the next open cue',()=>{expect(nextOpenCue(cues,'b')).toBe('d');});
 it('wraps round to an earlier open cue',()=>{expect(nextOpenCue(cues,'d')).toBe('b');});
 it('says when nothing is left open',()=>{expect(nextOpenCue([{id:'a',review:'approved'}],'a')).toBeNull();});
});
