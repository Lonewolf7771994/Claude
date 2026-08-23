const fs=require('fs');
const load=f=>fs.readFileSync(f,'utf8').trim().split('\n').map(l=>{
  const [t,o,h,lo,c]=l.split(','); return {t,o:+o,h:+h,l:+lo,c:+c};});

const ema=(a,p)=>{const k=2/(p+1);let pr=null;return a.map((x,i)=>{if(i<p-1)return null;
  if(i===p-1){pr=a.slice(0,p).reduce((s,y)=>s+y,0)/p;return pr;}pr=x*k+pr*(1-k);return pr;});};
function rsi(a,p=14){const o=new Array(a.length).fill(null);if(a.length<=p)return o;
  let g=0,l=0;for(let i=1;i<=p;i++){const d=a[i]-a[i-1];d>=0?g+=d:l-=d;}g/=p;l/=p;
  o[p]=l===0?100:100-100/(1+g/l);
  for(let i=p+1;i<a.length;i++){const d=a[i]-a[i-1];g=(g*(p-1)+Math.max(d,0))/p;l=(l*(p-1)+Math.max(-d,0))/p;
    o[i]=l===0?100:100-100/(1+g/l);}return o;}
function atrSeries(b,p=14){const tr=b.map((r,i)=>i===0?r.h-r.l:Math.max(r.h-r.l,Math.abs(r.h-b[i-1].c),Math.abs(r.l-b[i-1].c)));
  const o=new Array(b.length).fill(null);if(b.length<=p)return o;
  let a=tr.slice(1,p+1).reduce((x,y)=>x+y,0)/p;o[p]=a;
  for(let i=p+1;i<b.length;i++){a=(a*(p-1)+tr[i])/p;o[i]=a;}return o;}

function enrich(bars){
  const c=bars.map(b=>b.c);
  const e9=ema(c,9), e21=ema(c,21), R=rsi(c,14), A=atrSeries(bars,14);
  const r2=(v,d)=>v==null?null:+v.toFixed(d);
  const dp = bars[0].c>1000?2:2;
  return bars.map((b,i)=>[b.t,b.o,b.h,b.l,b.c,r2(e9[i],dp),r2(e21[i],dp),r2(R[i],1)]);
}

// zones from the 4h structure
function zones(bars,px){
  const N=bars.length, A=atrSeries(bars,14);
  const atr=A[N-1]||(bars[N-1].c*0.01);
  const K=2, HALF=0.30, CLUSTER=0.60, MAXDIST=15;
  const piv=[];
  for(let i=K;i<N-K;i++){
    let isH=true,isL=true;
    for(let j=i-K;j<=i+K;j++){ if(j===i)continue;
      if(bars[j].h>=bars[i].h) isH=false;
      if(bars[j].l<=bars[i].l) isL=false; }
    if(isH) piv.push({i,kind:'supply',c:bars[i].h});
    if(isL) piv.push({i,kind:'demand',c:bars[i].l});
  }
  const cluster=list=>{const out=[];list.sort((x,y)=>x.c-y.c);
    for(const p of list){const g=out[out.length-1];
      if(g&&Math.abs(p.c-g.mean)<=CLUSTER*atr){g.members.push(p);g.mean=g.members.reduce((s,m)=>s+m.c,0)/g.members.length;}
      else out.push({kind:p.kind,mean:p.c,members:[p]});}
    return out;};
  const groups=[...cluster(piv.filter(p=>p.kind==='supply')),...cluster(piv.filter(p=>p.kind==='demand'))];
  let zs=groups.map(g=>{
    const lo=g.mean-HALF*atr, hi=g.mean+HALF*atr;
    const from=Math.min(...g.members.map(m=>m.i)), lastIdx=Math.max(...g.members.map(m=>m.i));
    let touches=0; for(let i=from+1;i<N;i++) if(bars[i].h>=lo&&bars[i].l<=hi) touches++;
    return {lo,hi,centre:g.mean,from,pivots:g.members.length,touches,formed:bars[from].t,
      score:g.members.length*3+Math.min(touches,12)*0.5+(lastIdx/N)*5};
  }).filter(z=>Math.abs((z.centre/px-1)*100)<=MAXDIST);
  const above=zs.filter(z=>z.lo>px).sort((a,b)=>b.score-a.score).slice(0,4);
  const below=zs.filter(z=>z.hi<px).sort((a,b)=>b.score-a.score).slice(0,4);
  const inside=zs.filter(z=>z.lo<=px&&z.hi>=px).sort((a,b)=>b.score-a.score).slice(0,1);
  let keep=[...above,...inside,...below].sort((a,b)=>a.lo-b.lo);
  const m=[];
  for(const z of keep){const p=m[m.length-1];
    if(p&&z.lo<=p.hi){p.hi=Math.max(p.hi,z.hi);p.pivots+=z.pivots;p.touches=Math.max(p.touches,z.touches);}
    else m.push({...z});}
  return {atr:+atr.toFixed(2), zones:m.map(z=>({
    type:z.lo>px?'supply':z.hi<px?'demand':'active',
    lo:+z.lo.toFixed(2),hi:+z.hi.toFixed(2),
    pivots:z.pivots,touches:z.touches,fresh:z.touches===0,
    distPct:+((((z.lo+z.hi)/2/px)-1)*100).toFixed(2)})).sort((a,b)=>b.lo-a.lo)};
}

const out={};
for(const [key,name,sym,quote,px24h] of [
  ['PAXG','Pax Gold','PAXG_USD',{last:4593.31,chg:0.0199,high:4618.14,low:4500.43,bid:4593.32,ask:4593.33,vol:536.37,volUsd:2447469.10},null],
  ['BTC','Bitcoin','BTC_USD',{last:78091.89,chg:0.0560,high:79518.33,low:73890.48,bid:78094.34,ask:78094.35,vol:9893.8991,volUsd:760966680.09},null]]){
  const f=key.toLowerCase();
  const m15=load(f+'-15m.csv'), h4=load(f+'-4h.csv');
  const px=m15[m15.length-1].c;
  const z=zones(h4,px);
  out[key]={name,sym,quote,px,
    tf:{'15m':enrich(m15),'4h':enrich(h4)},
    atr4h:z.atr, zones:z.zones,
    chg4h:+((px/h4[h4.length-1].o-1)*100).toFixed(2),
    winHigh:Math.max(...h4.map(b=>b.h)), winLow:Math.min(...h4.map(b=>b.l))};
}
fs.writeFileSync('live.json',JSON.stringify(out));
for(const k in out){const o=out[k];
  console.log('\n=== '+k+'  last '+o.px+'  | 4h ATR '+o.atr4h+' | 8d range '+o.winLow+'–'+o.winHigh);
  console.log('type     range                       tests  swings  dist');
  o.zones.forEach(z=>console.log(' ',z.type.padEnd(7),
    (z.lo.toLocaleString()+' – '+z.hi.toLocaleString()).padEnd(26),
    String(z.touches).padStart(5),String(z.pivots).padStart(7),
    ' '+(z.distPct>0?'+':'')+z.distPct+'%'+(z.fresh?'  UNTESTED':'')));
}
console.log('\nbytes',fs.statSync('live.json').size);
