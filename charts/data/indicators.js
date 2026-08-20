const fs = require('fs');
const rows = fs.readFileSync('gld.csv','utf8').trim().split('\n').map(l=>{
  const [date,o,h,lo,c,v] = l.split(',');
  return {date, o:+o, h:+h, l:+lo, c:+c, v:+v};
});
const close = rows.map(r=>r.c);
const N = rows.length;

const sma = (arr,p) => arr.map((_,i)=> i<p-1 ? null : arr.slice(i-p+1,i+1).reduce((a,b)=>a+b,0)/p);
const ema = (arr,p) => { const k=2/(p+1); let prev=null; return arr.map((x,i)=>{ if(i<p-1) return null;
  if(i===p-1){ prev=arr.slice(0,p).reduce((a,b)=>a+b,0)/p; return prev; }
  prev = x*k + prev*(1-k); return prev; }); };

// Wilder RSI(14)
function rsi(arr,p=14){
  const out=new Array(arr.length).fill(null);
  let ag=0,al=0;
  for(let i=1;i<=p;i++){ const d=arr[i]-arr[i-1]; if(d>=0) ag+=d; else al-=d; }
  ag/=p; al/=p;
  out[p] = al===0?100:100-100/(1+ag/al);
  for(let i=p+1;i<arr.length;i++){
    const d=arr[i]-arr[i-1]; const g=d>0?d:0, l=d<0?-d:0;
    ag=(ag*(p-1)+g)/p; al=(al*(p-1)+l)/p;
    out[i]= al===0?100:100-100/(1+ag/al);
  }
  return out;
}
// Wilder ATR
function atr(rows,p=14){
  const tr=rows.map((r,i)=> i===0 ? r.h-r.l : Math.max(r.h-r.l, Math.abs(r.h-rows[i-1].c), Math.abs(r.l-rows[i-1].c)));
  const out=new Array(rows.length).fill(null);
  let a=tr.slice(1,p+1).reduce((x,y)=>x+y,0)/p; out[p]=a;
  for(let i=p+1;i<rows.length;i++){ a=(a*(p-1)+tr[i])/p; out[i]=a; }
  return out;
}
const sma20=sma(close,20), sma50=sma(close,50), sma200=sma(close,200);
const ema12=ema(close,12), ema26=ema(close,26), ema20=ema(close,20);
const macdLine = close.map((_,i)=> (ema12[i]!=null&&ema26[i]!=null)? ema12[i]-ema26[i] : null);
const mvals = macdLine.filter(v=>v!=null);
const sigOnly = ema(mvals,9);
const firstM = macdLine.findIndex(v=>v!=null);
const signal = new Array(N).fill(null);
sigOnly.forEach((v,i)=>{ if(v!=null) signal[firstM+i]=v; });
const hist = macdLine.map((v,i)=> (v!=null&&signal[i]!=null)? v-signal[i] : null);
const rsi14 = rsi(close,14);
const atr14 = atr(rows,14), atr20 = atr(rows,20);
// Bollinger 20,2
const bbU=[],bbL=[];
for(let i=0;i<N;i++){
  if(i<19){bbU.push(null);bbL.push(null);continue;}
  const w=close.slice(i-19,i+1), m=sma20[i];
  const sd=Math.sqrt(w.reduce((a,x)=>a+(x-m)*(x-m),0)/19);
  bbU.push(m+2*sd); bbL.push(m-2*sd);
}
const r2=v=>v==null?null:Math.round(v*100)/100;
const out = rows.map((r,i)=>({
  d:r.date,o:r.o,h:r.h,l:r.l,c:r.c,v:r.v,
  s20:r2(sma20[i]), s50:r2(sma50[i]), s200:r2(sma200[i]),
  bu:r2(bbU[i]), bl:r2(bbL[i]),
  r:r2(rsi14[i]), mh:r2(hist[i]), ml:r2(macdLine[i]), ms:r2(signal[i])
}));
fs.writeFileSync('series.json', JSON.stringify(out));

const i = N-1, j = N-2;
console.log('=== computed @', rows[i].date, '(last bar) ===');
console.log('close', rows[i].c, 'sma20', r2(sma20[i]), 'sma50', r2(sma50[i]), 'sma200', r2(sma200[i]));
console.log('ema20', r2(ema20[i]), 'bbU', r2(bbU[i]), 'bbL', r2(bbL[i]));
console.log('rsi14', r2(rsi14[i]), 'macd', r2(macdLine[i]), 'sig', r2(signal[i]), 'hist', r2(hist[i]));
console.log('atr14', r2(atr14[i]), 'atr20', r2(atr20[i]));
console.log('=== computed @', rows[j].date, '(prior bar, to match provider snapshot) ===');
console.log('sma20', r2(sma20[j]), 'sma50', r2(sma50[j]), 'sma200', r2(sma200[j]), 'ema20', r2(ema20[j]));
console.log('bbU', r2(bbU[j]), 'bbL', r2(bbL[j]), 'rsi14', r2(rsi14[j]));
console.log('macd', r2(macdLine[j]), 'sig', r2(signal[j]), 'hist', r2(hist[j]), 'atr20', r2(atr20[j]));
console.log('=== PROVIDER SNAPSHOT ===');
console.log('rsi 66.96 sma20 387.88 sma50 381.56 sma200 412.95 ema20 392.63 bbU 418.16 bbL 357.60 macd 7.6273 sig 5.0091 hist 2.6181 atr20 7.34');
const hi=Math.max(...rows.map(r=>r.h)), lo=Math.min(...rows.map(r=>r.l));
console.log('range high', hi, 'low', lo, 'bars', N);

// ---- structural facts ----
const above200 = rows.map((r,i)=> sma200[i]!=null && r.c>sma200[i]);
let streak=0; for(let k=N-1;k>=0 && above200[k];k--) streak++;
let lastBelow=null; for(let k=N-1-streak;k>=0;k--){ if(sma200[k]!=null){ lastBelow=rows[k].date; break; } }
// prior stretch above 200
let prevAbove=null;
for(let k=N-1-streak;k>=0;k--){ if(above200[k]){ prevAbove=rows[k].date; break; } }
// cross events sma50 vs sma200
const crosses=[];
for(let k=1;k<N;k++){
  if(sma50[k]==null||sma200[k]==null||sma50[k-1]==null||sma200[k-1]==null) continue;
  const p=sma50[k-1]-sma200[k-1], c=sma50[k]-sma200[k];
  if(p<=0&&c>0) crosses.push([rows[k].date,'golden']);
  if(p>=0&&c<0) crosses.push([rows[k].date,'death']);
}
const peak=rows.reduce((a,r)=>r.h>a.h?r:a);
const trough=rows.slice(rows.indexOf(peak)).reduce((a,r)=>r.l<a.l?r:a);
const last=rows[N-1];
console.log('\n=== STRUCTURE ===');
console.log('consecutive closes above SMA200:', streak, '| first of streak:', rows[N-streak].date);
console.log('prior close above SMA200 before streak:', prevAbove);
console.log('50/200 crosses:', JSON.stringify(crosses));
console.log('peak', peak.date, peak.h, '| post-peak trough', trough.date, trough.l);
console.log('drawdown from peak high:', ((last.c/peak.h-1)*100).toFixed(1)+'%');
console.log('rally off trough:', ((last.c/trough.l-1)*100).toFixed(1)+'%');
console.log('last close', last.c, 'prev close', rows[N-2].c, 'chg', (last.c-rows[N-2].c).toFixed(2), ((last.c/rows[N-2].c-1)*100).toFixed(2)+'%');
console.log('bb (sample sd) last:', r2(bbU[N-1]), r2(bbL[N-1]), '| @prior', r2(bbU[N-2]), r2(bbL[N-2]));
const bbpct = (last.c-bbL[N-1])/(bbU[N-1]-bbL[N-1])*100;
console.log('bb %B:', bbpct.toFixed(1));
console.log('ATR14 as % of price:', (atr14[N-1]/last.c*100).toFixed(2)+'%');
console.log('vol feed break: last big-volume bar', rows.filter(r=>r.v>1e6).slice(-1)[0].date);
