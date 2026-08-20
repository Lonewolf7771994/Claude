const fs=require('fs');
const bars=fs.readFileSync('gld.csv','utf8').trim().split('\n').map(l=>{
  const [d,o,h,lo,c,v]=l.split(','); return {d,o:+o,h:+h,l:+lo,c:+c,v:+v};
});
const N=bars.length, last=bars[N-1], px=last.c;
const tr=bars.map((r,i)=>i===0?r.h-r.l:Math.max(r.h-r.l,Math.abs(r.h-bars[i-1].c),Math.abs(r.l-bars[i-1].c)));
const ATR=new Array(N).fill(null); let a=tr.slice(1,15).reduce((x,y)=>x+y,0)/14; ATR[14]=a;
for(let i=15;i<N;i++){a=(a*13+tr[i])/14;ATR[i]=a;}
const atrNow=ATR[N-1];

const K=5, HALF=0.30, CLUSTER=0.55, MAXDIST=15;

// 1. pivots -> fixed-width candidate zones, so width can never run away
const piv=[];
for(let i=K;i<N-K;i++){
  let isH=true,isL=true;
  for(let j=i-K;j<=i+K;j++){ if(j===i)continue;
    if(bars[j].h>=bars[i].h) isH=false;
    if(bars[j].l<=bars[i].l) isL=false; }
  if(isH) piv.push({i,kind:'supply',c:bars[i].h,d:bars[i].d});
  if(isL) piv.push({i,kind:'demand',c:bars[i].l,d:bars[i].d});
}

// 2. cluster pivots whose centres sit within CLUSTER x ATR of the running mean
function cluster(list){
  const out=[]; list.sort((x,y)=>x.c-y.c);
  for(const p of list){
    const g=out[out.length-1];
    if(g && Math.abs(p.c-g.mean) <= CLUSTER*atrNow){
      g.members.push(p); g.mean=g.members.reduce((s,m)=>s+m.c,0)/g.members.length;
    } else out.push({kind:p.kind,mean:p.c,members:[p]});
  }
  return out;
}
let groups=[...cluster(piv.filter(p=>p.kind==='supply')),...cluster(piv.filter(p=>p.kind==='demand'))];

// 3. bounded band around the cluster centre, then measure how price treated it
const zones=groups.map(g=>{
  const centre=g.mean, lo=centre-HALF*atrNow, hi=centre+HALF*atrNow;
  const from=Math.min(...g.members.map(m=>m.i));
  const lastIdx=Math.max(...g.members.map(m=>m.i));
  let touches=0,lastTouch=null;
  for(let i=from+1;i<N;i++) if(bars[i].h>=lo && bars[i].l<=hi){touches++;lastTouch=bars[i].d;}
  return {kind:g.kind,lo,hi,centre,from,lastIdx,pivots:g.members.length,touches,lastTouch,
    formed:bars[from].d,
    score:g.members.length*3 + Math.min(touches,12)*0.5 + (lastIdx/N)*5};
});

// 4. keep what is actually tradeable from here
const near=zones.filter(z=>Math.abs((z.centre/px-1)*100)<=MAXDIST);
const above=near.filter(z=>z.lo>px).sort((x,y)=>y.score-x.score).slice(0,3);
const below=near.filter(z=>z.hi<px).sort((x,y)=>y.score-x.score).slice(0,3);
const inside=near.filter(z=>z.lo<=px&&z.hi>=px).sort((x,y)=>y.score-x.score).slice(0,1);

// 5. final overlap pass so no two drawn bands collide
let keep=[...above,...inside,...below].sort((x,y)=>x.lo-y.lo);
const merged=[];
for(const z of keep){
  const p=merged[merged.length-1];
  if(p && z.lo<=p.hi){ p.hi=Math.max(p.hi,z.hi); p.pivots+=z.pivots;
    p.touches=Math.max(p.touches,z.touches); p.from=Math.min(p.from,z.from);
    p.formed=p.from===z.from?z.formed:p.formed;
    p.lastTouch=[p.lastTouch,z.lastTouch].filter(Boolean).sort().pop();
  } else merged.push({...z});
}
const out=merged.map(z=>{
  const mid=(z.lo+z.hi)/2;
  return {type: z.lo>px?'supply':z.hi<px?'demand':'active',
    lo:+z.lo.toFixed(2), hi:+z.hi.toFixed(2), mid:+mid.toFixed(2),
    width:+(z.hi-z.lo).toFixed(2), widthAtr:+((z.hi-z.lo)/atrNow).toFixed(2),
    formed:z.formed, pivots:z.pivots, touches:z.touches,
    lastTouch:z.lastTouch, fresh:z.touches===0,
    distPct:+(((mid/px)-1)*100).toFixed(2)};
}).sort((x,y)=>y.mid-x.mid);
fs.writeFileSync('zones.json',JSON.stringify(out));
console.log('price',px,'| ATR14',atrNow.toFixed(2),'| band width',(2*HALF*atrNow).toFixed(2),'| zones',out.length,'\n');
console.log('type     range                width  xATR  formed      swings touch  last touch  dist');
out.forEach(z=>console.log(
  z.type.padEnd(8), (z.lo.toFixed(2)+' – '+z.hi.toFixed(2)).padEnd(20),
  z.width.toFixed(2).padStart(5), String(z.widthAtr).padStart(5),' '+z.formed,
  String(z.pivots).padStart(6), String(z.touches).padStart(6),
  ' '+String(z.lastTouch||'never').padEnd(11), (z.distPct>0?'+':'')+z.distPct+'%'));
