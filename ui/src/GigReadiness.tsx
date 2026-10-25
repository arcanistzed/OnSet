import React,{useEffect,useState} from 'react';
import {Button,Field,Pill,Segmented} from './ui';
import {issueCounts,orderRows,readinessParams,ReadinessRow,ReadinessScope} from './readiness';

const statusPill={blocked:['bad','Not ready'],check:['warn','Check'],ready:['good','Ready']} as const;
const severityPill={blocker:'bad',warning:'warn',info:'info'} as const;

/** Read-only pre-gig check of the checked tracks, a rekordbox playlist or a saved set. It only
 * reports; each finding opens the track where the fix is made. */
export function GigReadiness({marked,playlists,run,onOpen,onClose}:{marked:string[];playlists:string[];run:(fn:()=>Promise<any>,done?:string)=>Promise<any>;onOpen:(trackId:string)=>void;onClose:()=>void}){
  const [kind,setKind]=useState<'selection'|'playlist'|'set'>(marked.length?'selection':'playlist');
  const [playlist,setPlaylist]=useState(playlists[0]||''),[sets,setSets]=useState<any[]>([]),[setId,setSetId]=useState('');
  const [verify,setVerify]=useState(false),[result,setResult]=useState<any>(null);
  useEffect(()=>{window.onset.call('sets').then((s:any[])=>{const live=(s||[]).filter(p=>!p.stale);setSets(live);setSetId(id=>id||live[0]?.id||'');}).catch(()=>setSets([]));},[]);
  const scope:ReadinessScope|null=kind==='selection'?(marked.length?{kind,ids:marked}:null):kind==='playlist'?(playlist?{kind,name:playlist}:null):(setId?{kind,id:setId}:null);
  function check(){if(scope)run(async()=>{const r=await window.onset.call('gig-readiness',readinessParams(scope,verify));setResult(r);return r;});}
  const rows:ReadinessRow[]=result?orderRows(result.tracks):[];
  const counts=issueCounts(rows);
  return <div className="write-preview" role="region" aria-label="Gig readiness check">
    <div className="row"><h4 className="grow">Gig readiness</h4><Button kind="ghost" size="sm" onClick={onClose}>Close</Button></div>
    <p className="muted">Checks files, grids against rekordbox, the first-beat and drop cues, stale approvals, key and BPM. It changes nothing; open a track to fix it.</p>
    <div className="row">
      <Segmented label="Check" value={kind} onChange={v=>{setKind(v as any);setResult(null);}} options={[{id:'selection',label:`Checked tracks (${marked.length})`},{id:'playlist',label:'rekordbox playlist'},{id:'set',label:'Saved set'}]}/>
      {kind==='playlist'&&<Field label="Playlist" hint={playlists.length?undefined:'Read rekordbox to load playlists'}><select value={playlist} onChange={e=>{setPlaylist(e.target.value);setResult(null);}}>{playlists.map(n=><option key={n} value={n}>{n}</option>)}</select></Field>}
      {kind==='set'&&<Field label="Set" hint={sets.length?undefined:'No current saved sets'}><select value={setId} onChange={e=>{setSetId(e.target.value);setResult(null);}}>{sets.map(s=><option key={s.id} value={s.id}>{s.name||`${s.track_ids.length} tracks · ${s.id.slice(0,8)}`}</option>)}</select></Field>}
      <label className="row"><input type="checkbox" checked={verify} onChange={e=>setVerify(e.target.checked)}/> Verify audio checksums (slower)</label>
      <Button kind="primary" size="sm" disabled={!scope} onClick={check}>Check</Button>
    </div>
    {result&&<>
      <p><b>{result.summary.ready}</b> ready · <b>{result.summary.check}</b> to check · <b>{result.summary.blocked}</b> not ready, of {result.summary.total}</p>
      {counts.length>0&&<p className="muted">{counts.map(c=>`${c.message}: ${c.count}`).join(' · ')}</p>}
      <table className="table"><tbody>{rows.map(row=><tr key={row.track_id}>
        <td><Pill state={statusPill[row.status][0]}>{statusPill[row.status][1]}</Pill></td>
        <td><button className="track-cell" onClick={()=>onOpen(row.track_id)}><strong>{row.title||row.track_id}</strong><small>{row.artist||''}</small></button></td>
        <td>{row.issues.length?<ul className="stack">{row.issues.map(i=><li key={i.code} className="row"><Pill state={severityPill[i.severity]}>{i.severity}</Pill><span className="grow">{i.message}</span><Button size="sm" kind="ghost" onClick={()=>onOpen(row.track_id)}>{i.fix.label}</Button></li>)}</ul>:<span className="muted">Nothing to fix</span>}</td>
      </tr>)}</tbody></table>
    </>}
  </div>;
}
