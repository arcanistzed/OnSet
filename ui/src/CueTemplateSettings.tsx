import React,{useEffect,useState} from 'react';
import {Button,Card,Icon} from './ui';
import {roleColor} from './library';
import {PADS,ROLE_LABEL,ROLE_ORDER,templateProblems,type CueTemplate} from './cueTemplate';

const stamp=(v:any)=>typeof v==='number'?`${v.toFixed(3)} s`:'—';
const anchorName=(v:string)=>v==='main_payoff'?'main payoff':'first full groove';

function PayoffChoice({track,onSave}:{track:any;onSave:(id:string,event:any)=>void}){
  const [time,setTime]=useState(track.main_payoff.time==null?'':String(track.main_payoff.time));
  return <div className="row"><label>Main-payoff candidate (seconds) <input type="number" min="0" step="0.001"
    aria-label={`${track.title}: main-payoff candidate seconds`} value={time} onChange={e=>setTime(e.target.value)}/></label>
    <Button size="sm" disabled={!time||!Number.isFinite(+time)||+time<0} onClick={()=>onSave(track.track_id,{state:'present',time:+time})}>Use candidate</Button>
    <Button size="sm" kind="ghost" onClick={()=>onSave(track.track_id,{state:'unknown'})}>Clear selection</Button>
    <Button size="sm" kind="ghost" onClick={()=>onSave(track.track_id,{state:'absent'})}>No payoff</Button></div>;
}

/** The DJ's cue template: which roles OnSet proposes, where B and C sit, and how each is written. */
export function CueTemplateSettings({run}:{run:(a:()=>Promise<any>,success?:string)=>Promise<any>}){
  const [saved,setSaved]=useState<CueTemplate|null>(null),[draft,setDraft]=useState<CueTemplate|null>(null),[error,setError]=useState(''),[report,setReport]=useState<any>(null),[preview,setPreview]=useState<any>(null);
  useEffect(()=>{window.onset.call('cue-template').then((t:CueTemplate)=>{setSaved(t);setDraft(t);}).catch((e:any)=>setError(e.message));},[]);
  if(!draft)return <Card title="Cue template"><p className="muted">{error||'Loading the cue template…'}</p></Card>;
  const problems=templateProblems(draft),changed=JSON.stringify(draft)!==JSON.stringify(saved);
  const setRole=(role:string,patch:Partial<CueTemplate['roles'][string]>)=>setDraft(t=>t&&({...t,roles:{...t.roles,[role]:{...t.roles[role],...patch}}}));
  const setBars=(role:'B'|'C',value:string)=>setDraft(t=>t&&({...t,bars_before_drop:{...t.bars_before_drop,[role]:Math.floor(+value)}}));
  const save=()=>run(async()=>{const t=await window.onset.call('cue-template',{template:draft});setSaved(t);setDraft(t);setReport(null);setPreview(null);return t;},'Cue template saved');
  const inspect=()=>run(async()=>{const r=await window.onset.call('preview-cue-template',{});setPreview(r);setReport(null);return r;});
  const apply=()=>run(async()=>{const r=await window.onset.call('apply-cue-template',{preview_id:preview.id});setReport(r);setPreview(null);return r;},'Open cue proposals re-placed');
  const selectPayoff=(id:string,event:any)=>run(async()=>{
    await window.onset.call('edit',{id,changes:{main_payoff:event}});
    setPreview(null);const r=await window.onset.call('preview-cue-template',{});setPreview(r);return r;
  },'Main-payoff candidate saved; cues have not moved');
  return <Card title="Cue template" actions={<>
    <Button size="sm" kind="ghost" disabled={!changed} onClick={()=>{setDraft(saved);setReport(null);}}>Discard changes</Button>
    <Button size="sm" kind="primary" disabled={!changed||problems.length>0} onClick={save}>Save template</Button></>}>
    <p className="muted" style={{marginBottom:12}}>Which cues OnSet proposes for each track, and how approved ones are written to rekordbox. Changes shape proposals only: approved, rejected and hand-moved cues stay as you decided, and every write is still previewed.</p>
    <label>D and its B/C lead-ins <select aria-label="Drop cue anchor" value={draft.drop_anchor??'first_full_groove'}
      onChange={e=>{setDraft({...draft,schema_version:2,drop_anchor:e.target.value as CueTemplate['drop_anchor']});setPreview(null);}}>
      <option value="first_full_groove">First full groove (existing scheme)</option>
      <option value="main_payoff">Main payoff after the build</option></select></label>
    <p className="hint">Main payoff is a separate, unverified candidate. Choose its time in the preview below. When unknown or absent, this preset proposes no B/C/D; it never substitutes the first groove. E, G and loop positions keep their existing anchors. Existing decided cues retain their original meaning.</p>
    <div className="table-wrap"><table className="template-table">
      <thead><tr><th>Cue</th><th>Propose</th><th>Memory cue</th><th>Hot cue</th><th>Pad</th></tr></thead>
      <tbody>{ROLE_ORDER.map(role=>{const r=draft.roles[role];if(!r)return null;return <tr key={role} className={r.enabled?'':'dim'}>
        <td><span className="role-chip" style={{background:roleColor[role]||'#ccc'}}>{role}</span> {ROLE_LABEL[role]}
          {(role==='B'||role==='C')&&<label className="bars"><input type="number" min="1" max="64" step="1" aria-label={`${role}: bars before the drop`} value={draft.bars_before_drop[role]} onChange={e=>setBars(role,e.target.value)}/> bars before</label>}</td>
        <td><input type="checkbox" aria-label={`Propose ${role}`} checked={r.enabled} onChange={e=>setRole(role,{enabled:e.target.checked})}/></td>
        <td><input type="checkbox" aria-label={`Write ${role} as a memory cue`} disabled={!r.enabled} checked={r.memory} onChange={e=>setRole(role,{memory:e.target.checked})}/></td>
        <td><input type="checkbox" aria-label={`Write ${role} as a hot cue`} disabled={!r.enabled} checked={r.hot} onChange={e=>setRole(role,{hot:e.target.checked,pad:r.pad??PADS.find(p=>!ROLE_ORDER.some(o=>draft.roles[o]?.hot&&draft.roles[o]?.pad===p))??null})}/></td>
        <td><select aria-label={`Hot cue pad for ${role}`} disabled={!r.enabled||!r.hot} value={r.pad??''} onChange={e=>setRole(role,{pad:e.target.value||null})}>
          <option value="">—</option>{PADS.map(p=><option key={p} value={p}>{p}</option>)}</select></td>
      </tr>;})}</tbody>
    </table></div>
    {problems.map(p=><p className="warning" key={p}><Icon name="alert" size={14}/>{p}</p>)}
    <hr className="divider"/>
    <div className="row">
      <span className="muted grow">New analyses follow the saved template. Existing tracks keep their proposals until you re-place them.</span>
      <Button size="sm" disabled={changed} title={changed?'Save the template first':undefined} onClick={inspect}>Preview open proposals in every track</Button>
    </div>
    {preview&&!changed&&<div>
      <p>{preview.summary.tracks} tracks would change: {preview.summary.moved} updates, {preview.summary.added} additions, {preview.summary.removed} removals. {preview.summary.kept} decided or hand-moved cues stay.</p>
      {preview.details.map((t:any)=><details key={`${preview.id}-${t.track_id}`}><summary>{t.title} — first groove {stamp(t.first_full_groove.aligned_time)}; main payoff {stamp(t.main_payoff.aligned_time)} ({t.main_payoff.state})</summary>
        {draft.drop_anchor==='main_payoff'&&<><p className="hint">Selecting a candidate saves your choice without approving or moving cues. First-groove evidence stays separate.</p><PayoffChoice track={t} onSave={selectPayoff}/></>}
        {t.main_payoff.reason&&<p className="hint">{t.main_payoff.reason}</p>}
        {t.main_payoff.source&&<p className="hint">Main-payoff source: {t.main_payoff.source}; original candidate {stamp(t.main_payoff.original_time??t.main_payoff.time)}, aligned to {stamp(t.main_payoff.aligned_time)}. Unverified.</p>}
        <table><thead><tr><th>Cue</th><th>Action</th><th>Before</th><th>After</th></tr></thead><tbody>
          {t.changes.map((c:any)=><tr key={c.role}><td>{c.role}</td><td>{c.action}{c.action==='keep'&&c.anchor?` (${anchorName(c.anchor)})`:''}</td>
            <td>{c.before?.name} {stamp(c.before?.time)}{c.before?.end!=null?` → ${stamp(c.before.end)}`:''}</td>
            <td>{c.after?.name} {stamp(c.after?.time)}{c.after?.end!=null?` → ${stamp(c.after.end)}`:''}</td></tr>)}
        </tbody></table></details>)}
      <Button size="sm" disabled={!preview.summary.tracks} onClick={apply}>Apply these proposal changes</Button>
    </div>}
    {report&&<p className="hint" style={{marginTop:8}}>{report.tracks} track{report.tracks===1?'':'s'} updated: {report.moved} cue{report.moved===1?'':'s'} moved, {report.added} added, {report.removed} removed; {report.kept} decided or hand-moved cue{report.kept===1?'':'s'} left as they were.</p>}
    {error&&<p className="error-text">{error}</p>}
  </Card>;
}
