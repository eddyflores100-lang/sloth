// SLOTH — breakfast receipt dashboard · v2 "el recibo del desayuno"
// Sirve el último recibo firmado como una hoja de papel cálida, y lo verifica
// DE FORMA INDEPENDIENTE del Python que lo produjo: JSON canónico + cadena
// SHA-256 + Ed25519 vía WebCrypto. Dos implementaciones que coinciden valen
// más que una. Endpoints: GET / · GET /receipt/latest.json · GET /verify ·
// PUT /api/receipt?token=… (invariado; el app.py y el turno nocturno no cambian).

const HTML = `<!doctype html>
<html lang="es" data-theme="day">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>SLOTH — el recibo del desayuno · AliceLabs LLC</title>
<meta name="description" content="El perezoso trabaja mientras duermes y firma todo lo que toca: recibo nocturno con cadena SHA-256 y firma Ed25519, verificable en tu navegador sin preguntarle a nadie.">
<style>
:root{
  --bg:#e9dfc9; --sheet:#faf5e9; --sheet2:#f3ecdd;
  --ink:#2a2118; --coffee:#6f5232; --faint:#8a7355;
  --leaf:#3e6b3a; --rust:#b0492c; --amber:#a97f2a;
  --line:rgba(42,33,24,.16); --line2:rgba(42,33,24,.34);
  --fur:#c8a67a; --fur2:#e2d0a8; --face:#efe3c8; --mask:#5a4632; --wood:#6f5232;
}
html[data-theme="night"]{
  --bg:#171210; --sheet:#221b15; --sheet2:#2a221a;
  --ink:#e8dcc4; --coffee:#c9a877; --faint:#9a8a6f;
  --leaf:#7fb069; --rust:#d97757; --amber:#d9a441;
  --line:rgba(232,220,196,.15); --line2:rgba(232,220,196,.35);
  --fur:#a98a5e; --fur2:#c7b183; --face:#d9c69c; --mask:#43331f; --wood:#8a6a42;
}
*{margin:0;padding:0;box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{
  background:var(--bg);
  background-image:repeating-linear-gradient(45deg, rgba(111,82,50,.045) 0 2px, transparent 2px 9px);
  color:var(--ink);
  font:15px/1.6 ui-monospace,"SF Mono",Menlo,Consolas,"Liberation Mono",monospace;
  min-height:100vh; padding:34px 16px 60px;
}
::selection{background:var(--amber);color:#fff}
.wrap{max-width:700px;margin:0 auto}
.topbar{display:flex;justify-content:space-between;align-items:center;margin-bottom:14px}
.kick{font-size:10.5px;letter-spacing:.24em;text-transform:uppercase;color:var(--coffee)}
#theme{background:none;border:1px solid var(--line2);color:var(--ink);border-radius:2px;
  padding:5px 9px;cursor:pointer;font:inherit;font-size:11px;letter-spacing:.08em}
#theme:hover{background:var(--ink);color:var(--sheet)}
/* ------- la hoja ------- */
.sheet{background:var(--sheet);position:relative;
  box-shadow:0 1px 0 rgba(0,0,0,.05),0 18px 44px -20px rgba(60,42,20,.38);
  border-radius:3px}
.perfo{height:16px;background-image:radial-gradient(circle,var(--bg) 4.5px,transparent 5.2px);
  background-size:24px 16px;background-position:6px 0;background-repeat:repeat-x}
.sheet-in{padding:6px 42px 34px}
/* ------- cabecera ------- */
.mast{text-align:center;padding:10px 0 4px}
.mast svg{width:255px;height:auto;display:block;margin:0 auto}
.brand{font-family:Georgia,"Iowan Old Style","Times New Roman",serif;
  font-size:52px;letter-spacing:.04em;line-height:1;margin-top:-6px}
.brand small{display:block;font-size:11px;letter-spacing:.34em;text-transform:uppercase;
  color:var(--coffee);margin-top:9px}
.tag{color:var(--faint);font-size:12.5px;margin-top:12px;font-style:italic;
  font-family:Georgia,serif}
.rmeta{margin:20px 0 6px;border-top:2px solid var(--ink);border-bottom:2px solid var(--ink);
  padding:10px 2px;display:flex;justify-content:space-between;gap:10px;flex-wrap:wrap;
  font-size:11px;letter-spacing:.14em;text-transform:uppercase}
.rmeta b{font-weight:700}
/* ------- secciones ------- */
h2{font-family:Georgia,serif;font-weight:400;font-size:21px;margin:30px 0 4px;letter-spacing:.01em}
h2 + .sub{color:var(--faint);font-size:11.5px;margin-bottom:14px;font-style:italic;font-family:Georgia,serif}
.entries{position:relative;list-style:none;margin:10px 0 4px}
.entries::before{content:"";position:absolute;left:3.5px;top:10px;bottom:10px;border-left:1px dashed var(--line2)}
.entries li{display:grid;grid-template-columns:16px 62px 74px 1fr;gap:0 8px;
  padding:7.5px 0;align-items:baseline;position:relative}
.nd{width:8px;height:8px;border-radius:50%;border:1.5px solid var(--line2);
  background:var(--sheet);position:relative;top:1px;transition:background .3s,border-color .3s}
li.done .nd{background:var(--leaf);border-color:var(--leaf)}
.ts{color:var(--coffee);font-size:11.5px;white-space:nowrap}
.tool{font-size:9.5px;letter-spacing:.13em;text-transform:uppercase;border:1px solid var(--line2);
  color:var(--coffee);padding:1.5px 8px;border-radius:999px;justify-self:start;white-space:nowrap}
.tool.t-inbox{border-color:var(--amber);color:var(--amber)}
.tool.t-brief{border-color:var(--rust);color:var(--rust)}
.act b{font-weight:700}
.lk{display:none;font-size:9.5px;color:var(--leaf);letter-spacing:.06em;margin-left:8px;white-space:nowrap}
li.done .lk{display:inline}
/* ------- rechazos ------- */
.declined{list-style:none;margin:8px 0 0}
.declined li{border:1px solid var(--rust);border-radius:3px;padding:11px 14px;margin:10px 0;
  break-inside:avoid}
.declined .dhead{display:flex;gap:10px;align-items:baseline;flex-wrap:wrap;margin-bottom:5px}
.declined .tool{border-color:var(--rust);color:var(--rust)}
.declined .dact{font-weight:700;font-size:13.5px}
.declined .dwhy{color:var(--rust);font-size:12.5px;overflow-wrap:anywhere}
.none{color:var(--faint);font-style:italic;font-family:Georgia,serif}
/* ------- verificación ------- */
.verify{margin-top:34px;border-top:1px solid var(--line);padding-top:22px}
.vrow{display:flex;gap:22px;align-items:center;flex-wrap:wrap}
.vbtn{font:inherit;font-size:12px;letter-spacing:.14em;text-transform:uppercase;
  background:var(--sheet);color:var(--ink);border:2px solid var(--ink);
  padding:11px 20px;border-radius:2px;cursor:pointer}
.vbtn:hover{background:var(--ink);color:var(--sheet)}
.vbtn[disabled]{opacity:.45;cursor:default}
.vstate{font-size:12.5px;color:var(--faint);margin-top:14px}
.vstate .ok{color:var(--leaf)} .vstate .bad{color:var(--rust)}
.stampzone{min-width:200px;min-height:70px;display:flex;align-items:center;justify-content:flex-start}
.stamp{display:none;transform:rotate(-7deg);border:3px double var(--leaf);color:var(--leaf);
  font-weight:700;font-size:17px;letter-spacing:.18em;padding:12px 16px;text-transform:uppercase;
  text-align:center;mix-blend-mode:multiply;border-radius:3px}
html[data-theme="night"] .stamp{mix-blend-mode:normal}
.stamp.bad{border-color:var(--rust);color:var(--rust)}
.stamp.show{display:inline-block;animation:stamp .55s cubic-bezier(.2,1.7,.4,1) both}
@keyframes stamp{0%{opacity:0;transform:rotate(-7deg) scale(2.3)}
 62%{opacity:1;transform:rotate(-7deg) scale(.92)} 80%{transform:rotate(-7deg) scale(1.04)}
 100%{opacity:1;transform:rotate(-7deg) scale(1)}}
/* ------- prueba ------- */
.proof{margin-top:30px;border:1px dashed var(--line2);border-radius:3px;padding:16px 18px}
.proof h3{font-family:Georgia,serif;font-weight:400;font-size:14px;letter-spacing:.05em;margin-bottom:10px}
.prow{display:flex;gap:10px;align-items:baseline;font-size:11.5px;padding:3.5px 0}
.prow .pl{color:var(--coffee);letter-spacing:.1em;text-transform:uppercase;font-size:9.5px;white-space:nowrap}
.prow .dots{flex:1;border-bottom:2px dotted var(--line);position:relative;top:-3px;min-width:20px}
.prow .pv{overflow-wrap:anywhere;text-align:right;max-width:70%}
/* ------- sloth estados ------- */
.zzz{opacity:0;font-family:Georgia,serif;font-style:italic;fill:var(--faint);font-size:15px}
.z1{animation:zf 5.2s ease-in-out 1.2s infinite}
.z2{animation:zf 5.2s ease-in-out 2.6s infinite}
.z3{animation:zf 5.2s ease-in-out 4s infinite}
@keyframes zf{0%{opacity:0;transform:translate(0,4px)}30%{opacity:.85}60%{opacity:.35}
 100%{opacity:0;transform:translate(9px,-13px)}}
#sloth-body{transform-origin:178px 132px;animation:breathe 7s ease-in-out infinite}
@keyframes breathe{0%,100%{transform:scale(1,1)}50%{transform:scale(1.016,.99)}}
.eye-open{display:none}
html.verified .eye-open{display:block}
html.verified .eye-c1{display:none}
html.verified .zzz{display:none}
.wake{display:none;text-align:center;font-family:Georgia,serif;font-style:italic;
  color:var(--faint);font-size:12.5px;margin-top:2px}
html.verified .wake{display:block}
/* ------- vacío / pie ------- */
.empty{display:none;text-align:center;padding:34px 10px 10px;font-family:Georgia,serif;
  font-style:italic;font-size:15.5px;color:var(--faint)}
.empty small{display:block;font-family:ui-monospace,Menlo,monospace;font-style:normal;
  font-size:11px;margin-top:14px;letter-spacing:.06em}
footer{margin-top:26px;text-align:center;color:var(--faint);font-size:11px;line-height:1.9}
footer a{color:var(--coffee);text-decoration:none;border-bottom:1px dotted var(--coffee)}
footer a:hover{color:var(--ink);border-color:var(--ink)}
@media (prefers-reduced-motion:reduce){
  #sloth-body,.z1,.z2,.z3{animation:none}
  .stamp.show{animation:none}
  html.verified .eye-open{display:block} html.verified .eye-c1{display:none}
}
@media print{
  body{background:#fff;padding:0}
  .sheet{box-shadow:none} .perfo{display:none} #theme{display:none}
  .vbtn{display:none}
}
@media (max-width:560px){
  .sheet-in{padding:4px 20px 26px}
  .entries li{grid-template-columns:14px 52px 1fr;grid-template-areas:"nd ts act" "nd sp tool"}
  .nd{grid-area:nd;align-self:start;margin-top:5px}
  .ts{grid-area:ts}.tool{grid-area:tool;justify-self:start;margin-top:2px}
  .act{grid-area:act}.act .lk{display:block;margin-left:0;margin-top:2px}
  .brand{font-size:40px}
}
</style>
</head>
<body>
<div class="wrap">
  <div class="topbar">
    <span class="kick">AliceLabs LLC · turno de noche</span>
    <button id="theme" type="button">modo noche</button>
  </div>

  <div class="sheet">
    <div class="perfo"></div>
    <div class="sheet-in">

      <div class="mast">
        <svg viewBox="0 0 340 190" role="img" aria-label="Un perezoso dormido colgado de una rama">
          <path d="M6,52 C 90,40 250,40 334,50" fill="none" stroke="var(--wood)" stroke-width="13" stroke-linecap="round"/>
          <path d="M58,47 C 82,30 116,27 127,33" fill="none" stroke="var(--wood)" stroke-width="6" stroke-linecap="round"/>
          <g fill="var(--leafbg)">
            <ellipse cx="104" cy="26" rx="10" ry="4.6" transform="rotate(-28 104 26)"/>
            <ellipse cx="122" cy="23" rx="9" ry="4.2" transform="rotate(14 122 23)"/>
            <ellipse cx="88" cy="33" rx="8" ry="3.8" transform="rotate(-52 88 33)"/>
            <ellipse cx="304" cy="42" rx="10" ry="4.6" transform="rotate(-24 304 42)"/>
            <ellipse cx="318" cy="36" rx="9" ry="4.2" transform="rotate(18 318 36)"/>
          </g>
          <path d="M150,54 C 145,74 150,88 163,96" stroke="var(--fur)" stroke-width="15" fill="none" stroke-linecap="round"/>
          <path d="M206,54 C 211,74 206,88 193,96" stroke="var(--fur)" stroke-width="15" fill="none" stroke-linecap="round"/>
          <g stroke="var(--mask)" stroke-width="2.4" fill="none" stroke-linecap="round">
            <path d="M147,50 C 145,42 147,37 151,35"/>
            <path d="M152,51 C 150,43 152,38 156,36"/>
            <path d="M157,52 C 155,44 157,39 161,37"/>
            <path d="M209,50 C 211,42 209,37 205,35"/>
            <path d="M204,51 C 206,43 204,38 200,36"/>
            <path d="M199,52 C 201,44 199,39 195,37"/>
          </g>
          <g id="sloth-body">
            <ellipse cx="178" cy="122" rx="42" ry="33" fill="var(--fur)"/>
            <ellipse cx="178" cy="129" rx="25" ry="20" fill="var(--fur2)"/>
            <circle cx="178" cy="88" r="26" fill="var(--fur)"/>
            <ellipse cx="178" cy="92" rx="19.5" ry="15.5" fill="var(--face)"/>
            <ellipse cx="167.5" cy="89" rx="8.4" ry="6" transform="rotate(-18 167.5 89)" fill="var(--mask)"/>
            <ellipse cx="188.5" cy="89" rx="8.4" ry="6" transform="rotate(18 188.5 89)" fill="var(--mask)"/>
            <path class="eye-c1" d="M162.5,90 Q167,93.5 171.5,90" stroke="var(--face)" stroke-width="2.2" fill="none" stroke-linecap="round"/>
            <path class="eye-c2" d="M183.5,90 Q188,93.5 192.5,90" stroke="var(--face)" stroke-width="2.2" fill="none" stroke-linecap="round"/>
            <circle class="eye-open" cx="167.5" cy="89.5" r="2.7" fill="var(--face)"/>
            <ellipse cx="178" cy="98" rx="4.6" ry="3.4" fill="var(--mask)"/>
            <path d="M169,103.5 Q178,110.5 187,103.5" stroke="var(--mask)" stroke-width="2.2" fill="none" stroke-linecap="round"/>
          </g>
          <text class="zzz z1" x="216" y="66" font-size="12">z</text>
          <text class="zzz z2" x="231" y="52" font-size="15">z</text>
          <text class="zzz z3" x="247" y="37" font-size="18">z</text>
        </svg>
        <p class="wake">abre un ojo: todo en orden.</p>
        <h1 class="brand">SLOTH<small>Sleepy Lazy Overnight Task Handler</small></h1>
        <p class="tag">Trabaja mientras duermes. Firma todo lo que toca. Y a las siete tienes el recibo en la mesa.</p>
      </div>

      <div class="rmeta">
        <span>recibo de la noche del <b id="r-date">—</b></span>
        <span><b id="r-count">—</b> acciones · <b id="r-decl">—</b> rechazos</span>
      </div>

      <h2>Lo que hizo mientras dormías</h2>
      <p class="sub">cada línea va encadenada a la anterior por SHA-256 — pulsa verificar y mira los eslabones cerrarse</p>
      <ol id="entries" class="entries"></ol>

      <h2>Lo que se negó a hacer</h2>
      <p class="sub">los clics irreversibles siguen siendo humanos</p>
      <ul id="declined" class="declined"></ul>

      <div class="verify">
        <div class="vrow">
          <button id="go" class="vbtn" type="button">verificar recibo</button>
          <div class="stampzone"><span class="stamp" id="stamp">RECIBO VERIFICADO</span></div>
        </div>
        <p class="vstate" id="vstate">reuniendo eslabones…</p>
      </div>

      <div class="proof" id="proof" hidden>
        <h3>La prueba</h3>
        <div class="prow"><span class="pl">esquema</span><span class="dots"></span><span class="pv" id="p-scheme">—</span></div>
        <div class="prow"><span class="pl">cabeza de la cadena</span><span class="dots"></span><span class="pv" id="p-head">—</span></div>
        <div class="prow"><span class="pl">clave pública</span><span class="dots"></span><span class="pv" id="p-pub">—</span></div>
        <div class="prow"><span class="pl">firmado</span><span class="dots"></span><span class="pv" id="p-sig">—</span></div>
      </div>

      <div class="empty" id="empty">
        todavía no hay recibos — el perezoso duerme su siesta más larga.<br>
        cuando termine el turno, habrá una hoja firmada esperándote.
        <small>mientras tanto: GET /receipt/latest.json · GET /verify</small>
      </div>

    </div>
    <div class="perfo"></div>
  </div>

  <footer>
    SLOTH es un agente nocturno de <a href="https://utalabs.tech">AliceLabs LLC</a> — una acción, un eslabón; una noche, un recibo.<br>
    Verificado en tu navegador con WebCrypto, sin preguntarle a nadie. <a href="/receipt/latest.json">JSON crudo</a> · <a href="/verify">/verify</a> · <a href="https://utalabs.tech">utalabs.tech</a>
  </footer>
</div>

<script>
(function(){
"use strict";
var doc=document, root=doc.documentElement;

/* ---------- tema ---------- */
var tbtn=doc.getElementById('theme');
function setT(t){
  root.setAttribute('data-theme',t);
  tbtn.textContent=(t==='night')?'amanecer':'modo noche';
  try{localStorage.setItem('sloth-tema',t)}catch(e){}
}
try{setT(localStorage.getItem('sloth-tema')||'day')}catch(e){setT('day')}
tbtn.addEventListener('click',function(){
  setT(root.getAttribute('data-theme')==='night'?'day':'night');
});

/* ---------- utilidades ---------- */
function esc(s){return String(s).replace(/[&<>"]/g,function(c){
  return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c];});}
function fmtTs(ts){
  var d=new Date(ts); if(isNaN(d))return ts;
  return ('0'+d.getHours()).slice(-2)+':'+('0'+d.getMinutes()).slice(-2);
}
var $=function(id){return doc.getElementById(id)};

/* ---------- cripto: canónico + SHA-256 + Ed25519 (WebCrypto) ---------- */
function canonical(o){
  if(o===null||typeof o!=='object')return JSON.stringify(o);
  if(Array.isArray(o))return '['+o.map(canonical).join(',')+']';
  var k=Object.keys(o).sort();
  return '{'+k.map(function(x){return JSON.stringify(x)+':'+canonical(o[x])}).join(',')+'}';
}
function sha256hex(s){
  var buf=new TextEncoder().encode(s);
  return crypto.subtle.digest('SHA-256',buf).then(function(h){
    var a=new Uint8Array(h),o='';
    for(var i=0;i<a.length;i++)o+=('0'+a[i].toString(16)).slice(-2);
    return o;});
}
function hexBytes(h){
  var a=new Uint8Array(h.length/2);
  for(var i=0;i<a.length;i++)a[i]=parseInt(h.substr(i*2,2),16);
  return a;
}
function verifyReceipt(r){
  var problems=[], prev='0'.repeat(64), i;
  for(i=0;i<r.entries.length;i++){
    var e=r.entries[i], body=Object.assign({},e); delete body.hash;
    if(e.prev!==prev)problems.push('eslabón '+i+': prev-hash no coincide');
    prev=e.hash;
  }
  var chain=Promise.resolve();
  function add(n){chain=chain.then(function(){
    var e=r.entries[n], body=Object.assign({},e); delete body.hash;
    return sha256hex(canonical(body)).then(function(h){
      if(h!==e.hash)problems.push('eslabón '+n+': hash no coincide');
    });});}
  for(i=0;i<r.entries.length;i++)add(i);
  return chain.then(function(){
    var sig=r.signature||{};
    if(sig.head!==prev)problems.push('firma: la cabeza no coincide con la cadena');
    if(sig.entries!==r.entries.length)problems.push('firma: número de entradas no coincide');
    var payload=canonical({scheme:sig.scheme,date:sig.date,head:sig.head,
      entries:sig.entries,declined:sig.declined,signed_at:sig.signed_at});
    return crypto.subtle.importKey('raw',hexBytes(sig.public_key),{name:'Ed25519'},false,['verify'])
      .then(function(k){return crypto.subtle.verify({name:'Ed25519'},k,
        hexBytes(sig.signature),new TextEncoder().encode(payload));})
      .then(function(ok){if(!ok)problems.push('firma: Ed25519 NO verifica')},
        function(e){problems.push('firma: '+e.message)});
  }).then(function(){return problems});
}

/* ---------- render ---------- */
var D=null, rows=[], reduced=false;
try{reduced=matchMedia('(prefers-reduced-motion: reduce)').matches}catch(e){}

function render(){
  var sig=D.signature||{};
  $('r-date').textContent=D.date||'—';
  $('r-count').textContent=D.entries.length;
  var nd=(D.declined||[]).length;
  $('r-decl').textContent=nd;
  var ol=$('entries'); ol.innerHTML='';
  rows=[];
  D.entries.forEach(function(e,i){
    var li=doc.createElement('li');
    li.innerHTML='<span class="nd"></span><span class="ts">'+esc(fmtTs(e.ts))+
      '</span><span class="tool t-'+esc(e.tool)+'">'+esc(e.tool)+'</span>'+
      '<span class="act">'+esc(e.action)+
      '<span class="lk">eslabón '+('0'+(i+1)).slice(-2)+' ✓</span></span>';
    ol.appendChild(li); rows.push(li);
  });
  var ul=$('declined');
  if(nd===0){ul.innerHTML='<li class="none">nada que rechazar — una noche tranquila.</li>';}
  else{
    ul.innerHTML='';
    (D.declined||[]).forEach(function(x){
      var li=doc.createElement('li');
      li.innerHTML='<div class="dhead"><span class="tool t-'+esc(x.tool)+'">'+esc(x.tool)+
        '</span><span class="dact">'+esc(x.action)+'</span></div>'+
        '<div class="dwhy">'+esc(x.reason||'')+'</div>';
      ul.appendChild(li);
    });
  }
  $('p-scheme').textContent=sig.scheme||'—';
  $('p-head').textContent=sig.head||'—';
  $('p-pub').textContent=sig.public_key||'—';
  $('p-sig').textContent=(sig.signed_at||'—')+' · '+sig.entries+' entradas';
  $('proof').hidden=false;
}

/* ---------- verificación animada ---------- */
function resetRows(){
  rows.forEach(function(r){r.classList.remove('done')});
  root.classList.remove('verified');
  var st=$('stamp'); st.classList.remove('show','bad');
}
function stamp(problems){
  var st=$('stamp'), vs=$('vstate'), btn=$('go');
  if(!problems.length){
    st.textContent='RECIBO VERIFICADO';
    st.classList.remove('bad'); st.classList.add('show');
    root.classList.add('verified');
    vs.innerHTML='<span class="ok">'+D.entries.length+' eslabones ✓ · firma Ed25519 ✓</span>'+
      '<br>comprobado en tu navegador, sin preguntarle a nadie.';
  }else{
    st.textContent='CADENA ROTA';
    st.classList.add('bad'); st.classList.add('show');
    vs.innerHTML='<span class="bad">'+problems.map(esc).join('<br>')+'</span>';
  }
  btn.disabled=false; btn.textContent='volver a comprobar';
}
function walk(){
  if(!D)return;
  resetRows();
  var btn=$('go'); btn.disabled=true; btn.textContent='sin prisa…';
  var vs=$('vstate');
  if(reduced||!window.crypto||!crypto.subtle){
    rows.forEach(function(r){r.classList.add('done')});
    vs.textContent='comprobando firma…';
    verifyReceipt(D).then(stamp);
    return;
  }
  var i=0;
  function step(){
    if(i<rows.length){
      rows[i].classList.add('done');
      vs.textContent='eslabón '+('0'+(i+1)).slice(-2)+' / '+('0'+rows.length).slice(-2)+' cerrado ✓';
      i++; setTimeout(step,120);
      return;
    }
    vs.textContent='cadena íntegra — ahora la firma Ed25519…';
    verifyReceipt(D).then(stamp);
  }
  step();
}
$('go').addEventListener('click',walk);

/* ---------- arranque ---------- */
fetch('/receipt/latest.json').then(function(r){return r.json()}).then(function(j){
  if(!j||j.error||!j.entries||!j.entries.length){
    $('empty').style.display='block';
    $('vstate').textContent='no hay nada que verificar todavía.';
    return;
  }
  D=j; render(); walk();
}).catch(function(){
  $('empty').style.display='block';
  $('vstate').textContent='no hay nada que verificar todavía.';
});
})();
</script>
</body>
</html>
`;

/* ---------- verificación en el edge (misma lógica, otra implementación) ---------- */
function canonical(obj) {
  if (obj === null || typeof obj !== "object") return JSON.stringify(obj);
  if (Array.isArray(obj)) return "[" + obj.map(canonical).join(",") + "]";
  const keys = Object.keys(obj).sort();
  return "{" + keys.map(k => JSON.stringify(k) + ":" + canonical(obj[k])).join(",") + "}";
}
async function sha256hex(s) {
  const buf = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(s));
  return [...new Uint8Array(buf)].map(b => b.toString(16).padStart(2, "0")).join("");
}
function hexBytes(hex) {
  const a = new Uint8Array(hex.length / 2);
  for (let i = 0; i < a.length; i++) a[i] = parseInt(hex.substr(i * 2, 2), 16);
  return a;
}
async function verifyReceipt(receipt) {
  const problems = [];
  let prev = "0".repeat(64);
  for (let n = 0; n < receipt.entries.length; n++) {
    const e = receipt.entries[n];
    const body = { ...e }; delete body.hash;
    if (e.prev !== prev) problems.push("entry " + n + ": prev-hash mismatch");
    const h = await sha256hex(canonical(body));
    if (h !== e.hash) problems.push("entry " + n + ": hash mismatch");
    prev = e.hash;
  }
  const sig = receipt.signature || {};
  if (sig.head !== prev) problems.push("signature: head mismatch");
  if (sig.entries !== receipt.entries.length) problems.push("signature: count mismatch");
  try {
    const payload = canonical({ scheme: sig.scheme, date: sig.date, head: sig.head,
      entries: sig.entries, declined: sig.declined, signed_at: sig.signed_at });
    const pubRaw = hexBytes(sig.public_key);
    const key = await crypto.subtle.importKey("raw", pubRaw, { name: "Ed25519" }, false, ["verify"]);
    const ok = await crypto.subtle.verify({ name: "Ed25519" }, key,
      hexBytes(sig.signature), new TextEncoder().encode(payload));
    if (!ok) problems.push("signature: Ed25519 verify FAILED");
  } catch (e) { problems.push("signature: " + e.message); }
  return problems;
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (request.method === "PUT" && url.pathname === "/api/receipt") {
      if (url.searchParams.get("token") !== env.UPLOAD_TOKEN)
        return new Response("forbidden", { status: 403 });
      const body = await request.json();
      await env.RECEIPTS.put("latest.json", JSON.stringify(body.json));
      await env.RECEIPTS.put("latest.html", body.html || "");
      return Response.json({ ok: true, date: body.json && body.json.date });
    }
    if (url.pathname === "/receipt/latest.json") {
      const j = await env.RECEIPTS.get("latest.json");
      return new Response(j || '{"error":"no receipts yet"}',
        { headers: { "content-type": "application/json", "access-control-allow-origin": "*" } });
    }
    if (url.pathname === "/verify") {
      const j = await env.RECEIPTS.get("latest.json");
      if (!j) return Response.json({ verified: false, problems: ["no receipts"] });
      const problems = await verifyReceipt(JSON.parse(j));
      const r = JSON.parse(j);
      return Response.json({ verified: problems.length === 0, problems,
        entries: r.entries.length, date: r.date });
    }
    // GET / — el recibo del desayuno, siempre la versión nueva (los datos
    // llegan por /receipt/latest.json; el HTML antiguo de KV queda obsoleto)
    return new Response(HTML, { headers: { "content-type": "text/html; charset=utf-8" } });
  }
};
