import React,{useState} from 'react';
import type {Track} from './types';
import {Button,Card,Icon} from './ui';

/** What one rekordbox write changed, in words, from its manifest. */
export function restoreSummary(manifest:any,titleOf:(id:string)=>string|undefined){
  if(manifest.kind==='hot-slot-repair')
    return `Hot cue pad repair: ${manifest.moved||0} moved, ${manifest.dropped||0} removed`;
  const written:any[]=manifest.written||[];
  if(!written.length)return 'A playlist or comment write, with no cue changes';
  // Older manifests list bare track ids; newer ones list each track with the cues written.
  const titles=written.map(w=>titleOf(typeof w==='string'?w:w.track_id)||'An unmatched track');
  const counted=written.some(w=>Array.isArray(w?.cues)),cues=written.reduce((n,w)=>n+(w?.cues?.length||0),0);
  const named=titles.length>3?`${titles.slice(0,3).join(', ')} and ${titles.length-3} more`:titles.join(', ');
  return `Cues for ${named}${counted?` (${cues} cue${cues===1?'':'s'})`:''}`;
}
export const newestFirst=(manifests:any[])=>[...manifests].sort((a,b)=>String(b.created).localeCompare(String(a.created)));
const when=(iso:string)=>{const d=new Date(iso);return Number.isNaN(+d)?iso:d.toLocaleString(undefined,{dateStyle:'medium',timeStyle:'short'});};

/** rekordbox write history, with a preview and an explicit tick before a backup is put back. */
export function RekordboxHistory({tracks,run}:{tracks:Track[];run:(a:()=>Promise<any>,success?:string)=>Promise<any>}){
  const [manifests,setManifests]=useState<any[]>([]),[loaded,setLoaded]=useState(false),[chosen,setChosen]=useState<any>(null),[approved,setApproved]=useState(false);
  const titleOf=(id:string)=>tracks.find(t=>t.id===id)?.title;
  const load=()=>run(async()=>{const r=await window.onset.call('manifests');setManifests(newestFirst(r||[]));setLoaded(true);return r;});
  const close=()=>{setChosen(null);setApproved(false);};
  return <Card title="rekordbox write history" actions={<Button size="sm" icon="refresh" onClick={load}>{loaded?'Reload':'Load backups'}</Button>}>
    {manifests.map(m=><div className="list-row" key={m.id}>
      <span className="grow">{when(m.created)} <span className="dim">· {restoreSummary(m,titleOf)}</span></span>
      <Button size="sm" onClick={()=>{setChosen(m);setApproved(false);}}>Preview restore</Button>
    </div>)}
    {!manifests.length&&<p className="muted">{loaded?'OnSet has not written to rekordbox yet.':'Load backups to restore rekordbox to a state before an OnSet write.'}</p>}
    {chosen&&<div className="write-preview" role="dialog" aria-label="Confirm rekordbox restore">
      <h4>Put rekordbox back to before this write</h4>
      <p className="muted">{when(chosen.created)} · {restoreSummary(chosen,titleOf)}</p>
      <p className="warning"><Icon name="alert" size={14}/>This replaces rekordbox’s whole database with the copy saved just before that write. Everything changed in rekordbox since then is undone too, including your own cues, imports and playlists from after {when(chosen.created)}.</p>
      <p className="muted">Close rekordbox first; OnSet refuses while it runs. The current database is backed up before anything changes.</p>
      <div className="row" style={{marginTop:12}}>
        <label className="check grow"><input type="checkbox" checked={approved} onChange={e=>setApproved(e.target.checked)}/>Replace rekordbox’s database with the backup from {when(chosen.created)}</label>
        <Button size="sm" kind="ghost" onClick={close}>Cancel</Button>
        <Button size="sm" kind="danger" disabled={!approved} onClick={()=>run(async()=>{const r=await window.onset.call('restore',{id:chosen.id});close();return r;},'rekordbox restored; the previous database was backed up first')}>Restore</Button>
      </div>
    </div>}
  </Card>;
}
