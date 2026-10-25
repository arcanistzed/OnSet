import {describe,expect,it} from 'vitest';
import {issueCounts,orderRows,readinessParams,ReadinessRow} from './readiness';

const fix={action:'review-cues',label:'Review cue D'};
const rows:ReadinessRow[]=[
  {track_id:'a',title:'A',artist:null,status:'ready',issues:[{code:'not-written',severity:'info',message:'',fix}]},
  {track_id:'b',title:'B',artist:null,status:'check',issues:[{code:'no-key',severity:'warning',message:'',fix:{action:'edit',label:'Set the key'}},{code:'drop-unapproved',severity:'warning',message:'',fix}]},
  {track_id:'c',title:'C',artist:null,status:'blocked',issues:[{code:'drop-unapproved',severity:'warning',message:'',fix},{code:'missing-file',severity:'blocker',message:'',fix:{action:'relocate',label:'Locate the audio file'}}]},
  {track_id:'d',title:'D',artist:null,status:'check',issues:[]},
];

describe('gig readiness',()=>{
  it('sends the chosen scope and only asks for checksums when wanted',()=>{
    expect(readinessParams({kind:'selection',ids:['a']},false)).toEqual({track_ids:['a']});
    expect(readinessParams({kind:'playlist',name:'Friday'},true)).toEqual({verify_audio:true,playlist:'Friday'});
    expect(readinessParams({kind:'set',id:'s1'},false)).toEqual({set_id:'s1'});
  });
  it('lists blocked tracks first and keeps the set order within a status',()=>{
    const ordered=orderRows(rows);
    expect(ordered.map(r=>r.track_id)).toEqual(['c','b','d','a']);
    expect(ordered[0].issues.map(i=>i.code)).toEqual(['missing-file','drop-unapproved']);
  });
  it('counts the kinds of problem, leaving out information',()=>{
    expect(issueCounts(rows).map(c=>[c.code,c.count])).toEqual([['drop-unapproved',2],['missing-file',1],['no-key',1]]);
  });
});
