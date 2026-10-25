// The DJ's cue template as the service stores it (service/onset_service/cue_template.py).
export type RoleSettings={enabled:boolean;memory:boolean;hot:boolean;pad:string|null};
export type CueTemplate={schema_version:number;drop_anchor?:'main_payoff'|'first_full_groove';bars_before_drop:{B:number;C:number};roles:Record<string,RoleSettings>};

export const PADS=['A','B','C','D','E','F','G','H'];
export const ROLE_ORDER=['A','B','C','D','E','F','G','L','I'];
export const ROLE_LABEL:Record<string,string>={A:'First beat',B:'Before the drop',C:'Before the drop',D:'Drop',E:'Breakdown',
  F:'Outro',G:'Second drop',L:'End loop',I:'Intro loop'};

/** What would stop the service accepting this template, in the DJ's words; empty when it is usable. */
export function templateProblems(t:CueTemplate):string[]{
  const problems:string[]=[];
  for(const role of ['B','C'] as const){const bars=t.bars_before_drop[role];
    if(!Number.isInteger(bars)||bars<1||bars>64)problems.push(`${role}: bars before the drop must be a whole number from 1 to 64`);}
  const hot=ROLE_ORDER.filter(r=>t.roles[r]?.enabled&&t.roles[r]?.hot);
  for(const role of hot)if(!t.roles[role].pad)problems.push(`${role}: choose a pad for its hot cue`);
  const pads=hot.map(r=>t.roles[r].pad).filter(Boolean) as string[];
  const shared=[...new Set(pads.filter((p,i)=>pads.indexOf(p)!==i))];
  for(const pad of shared)problems.push(`Pad ${pad} is used by ${hot.filter(r=>t.roles[r].pad===pad).join(' and ')}`);
  return problems;
}

/** The cue to focus after deciding `current`: the next one still open, wrapping round; null when none is. */
export function nextOpenCue(cues:{id:string;review:string}[],current:string){
  const open=(c:{review:string})=>c.review==='proposed'||c.review==='stale';
  const i=cues.findIndex(c=>c.id===current);
  const after=[...cues.slice(i+1),...cues.slice(0,Math.max(0,i))];
  return after.find(open)?.id??null;
}
