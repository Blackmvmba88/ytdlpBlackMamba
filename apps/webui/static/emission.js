(() => {
const canvas=document.querySelector('#emission');if(!canvas)return;
const gl=canvas.getContext('webgl2',{antialias:false,alpha:false});
if(!gl){canvas.hidden=true;document.querySelector("#mic-toggle").disabled=true;document.querySelector("#mic-message").textContent="El visualizador requiere WebGL para reaccionar al micrófono.";return;}
const extFloat=gl.getExtension('EXT_color_buffer_float');
  const vs=`#version 300 es
  precision highp float;
  const vec2 P[3]=vec2[3](vec2(-1.,-1.),vec2(3.,-1.),vec2(-1.,3.));
  out vec2 vUv;
  void main(){gl_Position=vec4(P[gl_VertexID],0.,1.);vUv=.5*(gl_Position.xy+1.);}
  `;

  const fsScene=`#version 300 es
  precision highp float;
  in vec2 vUv;
  out vec4 outColor;
  uniform vec2 uRes;
  uniform float uTime,uEmission,uAtmos,uReflect,uHueSpeed;
  uniform vec4 uBands,uKnobs;
  uniform float uSpectrum[48];
  vec3 palette(float x){
    return mix(vec3(.18,.48,1.),vec3(1.,.12,.55),.5+.5*sin(x*4.5+uTime*.12));
  }
  void main(){
    vec2 uv=vUv;
    vec3 col=vec3(.013,.010,.030);
    float energy=dot(uBands,vec4(.25));
    energy=energy/(.72+energy);
    // Broad drifting ribbons: light surrounds the content rather than becoming a control.
    for(int i=0;i<3;i++){
      float fi=float(i);
      float center=.43+.22*sin(uv.x*3.6+uTime*.16+fi*1.7);
      float dist=abs(uv.y-center);
      float cloud=exp(-dist*dist/(.017+energy*.008));
      float edge=pow(abs(uv.x-.5)*2.,1.3);
      col+=palette(uv.x+fi*.5)*cloud*(.055+.10*energy)*(.3+edge);
    }
    // 48 frequency columns; reflection and bloom inherit the reference's light treatment.
    float slot=clamp(floor(uv.x*48.),0.,47.);
    int idx=int(slot);
    float level=uSpectrum[idx];
    float compressed=level/(.62+level);
    float height=.018+compressed*.16;
    float x=abs(fract(uv.x*48.)-.5);
    float width=1.-smoothstep(.20,.38,x);
    float baseline=.13;
    float bar=step(baseline,uv.y)*(1.-smoothstep(height,height+.005,uv.y-baseline))*width;
    float segments=.45+.55*smoothstep(.12,.22,fract((uv.y-baseline)*105.));
    vec3 tint=palette(uv.x*1.6);
    col+=tint*bar*segments*(.16+compressed*.48);
    float glow=exp(-pow((uv.y-baseline-height*.5)/(.03+height*.65),2.));
    col+=tint*glow*(.014+compressed*.035);
    float reflected=step(uv.y,baseline)*exp(-(baseline-uv.y)*28.)*width*step(baseline-uv.y,height*.5);
    col+=tint*reflected*compressed*.08;
    col+=palette(uv.x)*exp(-abs(uv.y-baseline)*350.)*.055;
    outColor=vec4(col,1.);
  }`;

  const fsComposite=`#version 300 es
  precision highp float;
  in vec2 vUv;
  out vec4 outColor;
  uniform sampler2D uScene;
  uniform vec2 uRes;
  uniform float uBloom;
  vec3 aces(vec3 x){
    float a=2.51,b=.03,c=2.43,d=.59,e=.14;
    return clamp((x*(a*x+b))/(x*(c*x+d)+e),0.,1.);
  }
  vec3 sampleBloom(vec2 uv){
    vec2 px=1.0/uRes;
    vec3 s=vec3(0.);float w=0.;
    float R[5]=float[5](2.,5.,11.,22.,38.);
    float W[5]=float[5](.24,.22,.19,.15,.10);
    for(int i=0;i<5;i++){
      vec2 o=px*R[i];float k=W[i];
      s+=texture(uScene,uv+vec2( o.x,0)).rgb*k;
      s+=texture(uScene,uv+vec2(-o.x,0)).rgb*k;
      s+=texture(uScene,uv+vec2(0, o.y)).rgb*k;
      s+=texture(uScene,uv+vec2(0,-o.y)).rgb*k;
      s+=texture(uScene,uv+vec2( o.x, o.y)).rgb*k*.72;
      s+=texture(uScene,uv+vec2(-o.x, o.y)).rgb*k*.72;
      s+=texture(uScene,uv+vec2( o.x,-o.y)).rgb*k*.72;
      s+=texture(uScene,uv+vec2(-o.x,-o.y)).rgb*k*.72;
      w+=k*(4.+4.*.72);
    }
    return s/max(w,.001);
  }
  void main(){
    vec3 base=texture(uScene,vUv).rgb;
    vec3 b=sampleBloom(vUv);
    vec3 bright=max(b-vec3(.13),vec3(0.));
    vec3 hdr=base+bright*uBloom*2.30;
    hdr+=pow(max(base-vec3(.53),vec3(0.)),vec3(1.7))*.19;
    vec3 mapped=aces(hdr*1.04);
    mapped=pow(mapped,vec3(1./2.2));
    outColor=vec4(mapped,1.);
  }`;

  function compile(type,src){
    const sh=gl.createShader(type);gl.shaderSource(sh,src);gl.compileShader(sh);
    if(!gl.getShaderParameter(sh,gl.COMPILE_STATUS))throw new Error(gl.getShaderInfoLog(sh));
    return sh;
  }
  function program(vsSrc,fsSrc){
    const p=gl.createProgram();
    gl.attachShader(p,compile(gl.VERTEX_SHADER,vsSrc));
    gl.attachShader(p,compile(gl.FRAGMENT_SHADER,fsSrc));
    gl.linkProgram(p);
    if(!gl.getProgramParameter(p,gl.LINK_STATUS))throw new Error(gl.getProgramInfoLog(p));
    return p;
  }

  const pScene=program(vs,fsScene),pComp=program(vs,fsComposite);
  const vao=gl.createVertexArray();gl.bindVertexArray(vao);

  const tex=gl.createTexture();gl.bindTexture(gl.TEXTURE_2D,tex);
  gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MIN_FILTER,gl.LINEAR);
  gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MAG_FILTER,gl.LINEAR);
  gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_S,gl.CLAMP_TO_EDGE);
  gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_T,gl.CLAMP_TO_EDGE);

  const fbo=gl.createFramebuffer();gl.bindFramebuffer(gl.FRAMEBUFFER,fbo);
  gl.framebufferTexture2D(gl.FRAMEBUFFER,gl.COLOR_ATTACHMENT0,gl.TEXTURE_2D,tex,0);

  let rw=0,rh=0;
  function resize(){
    const dpr=Math.min(devicePixelRatio||1,1.25);
    const w=Math.max(2,Math.min(1600,Math.floor(canvas.clientWidth*dpr)));
    const h=Math.max(2,Math.min(1200,Math.floor(canvas.clientHeight*dpr)));
    if(w===rw&&h===rh)return;
    rw=w;rh=h;canvas.width=w;canvas.height=h;
    gl.bindTexture(gl.TEXTURE_2D,tex);
    const internal=extFloat?gl.RGBA16F:gl.RGBA8;
    const type=extFloat?gl.HALF_FLOAT:gl.UNSIGNED_BYTE;
    gl.texImage2D(gl.TEXTURE_2D,0,internal,w,h,0,gl.RGBA,type,null);
  }

  const U=(p,n)=>gl.getUniformLocation(p,n);
  const US={
    scene:{
      res:U(pScene,'uRes'),time:U(pScene,'uTime'),bands:U(pScene,'uBands'),knobs:U(pScene,'uKnobs'),spectrum:U(pScene,'uSpectrum'),
      reflect:U(pScene,'uReflect'),hue:U(pScene,'uHueSpeed'),emission:U(pScene,'uEmission'),atmos:U(pScene,'uAtmos')
    },
    comp:{res:U(pComp,'uRes'),bloom:U(pComp,'uBloom'),scene:U(pComp,'uScene')}
  };

  const params={
    emission:3.10,bloom:2.35,atmos:1.20,reflect:1.10,sensitivity:1.85,audioSmooth:.72,
    damping:.68,frequency:21,huespeed:.68
  };
  document.querySelectorAll('[data-emission] input').forEach(inp=>{
    const out=inp.parentElement.querySelector('output');
    const sync=()=>{params[inp.id]=+inp.value;out.textContent=(+inp.value).toFixed(2)};
    inp.addEventListener('input',sync);sync();
  });


const player=document.querySelector('#collection-player');
let audioCtx,analyser,source,micAnalyser,micSource,micStream;
const data=new Uint8Array(512);
const micButton=document.querySelector('#mic-toggle');
const micMessage=document.querySelector('#mic-message');
let micPending=false,leaving=false;
async function ensureAudio(){
  if(!audioCtx)audioCtx=new AudioContext();
  if(audioCtx.state==='suspended')await audioCtx.resume();
}
function updateStatus(){
 document.querySelector('#visual-status').textContent=micStream?'Vúmetro · micrófono en vivo':analyser&&player&&!player.paused?'Vúmetro · siguiendo tu música':'Ambiente · sin audio';
}
function stopMic(){
 const stream=micStream;micStream=null;
 if(micSource){micSource.disconnect();micSource=null;}
 if(micAnalyser){micAnalyser.disconnect();micAnalyser=null;}
 if(stream)stream.getTracks().forEach(track=>track.stop());
 micButton.textContent='Activar micrófono';micButton.setAttribute('aria-pressed','false');updateStatus();
}
player?.addEventListener('play',async()=>{
 try{
  await ensureAudio();
  if(!source){analyser=audioCtx.createAnalyser();analyser.fftSize=1024;source=audioCtx.createMediaElementSource(player);source.connect(analyser);analyser.connect(audioCtx.destination);}
  updateStatus();
 }catch{micMessage.textContent='No se pudo activar el análisis del reproductor.';}
});
player?.addEventListener('pause',updateStatus);
if(!navigator.mediaDevices?.getUserMedia){micButton.disabled=true;micMessage.textContent='Este navegador no permite acceder al micrófono aquí.';}
async function startMic(){
 if(micPending)return;
 if(micStream){stopMic();micMessage.textContent='Micrófono apagado.';return;}
 micPending=true;micButton.disabled=true;micMessage.textContent='Autoriza el micrófono en el aviso del navegador.';
 try{
  await ensureAudio();
  const stream=await navigator.mediaDevices.getUserMedia({audio:{echoCancellation:false,noiseSuppression:false,autoGainControl:false},video:false});
  if(leaving){stream.getTracks().forEach(track=>track.stop());return;}
  micStream=stream;micAnalyser=audioCtx.createAnalyser();micAnalyser.fftSize=1024;micAnalyser.smoothingTimeConstant=.65;
  micSource=audioCtx.createMediaStreamSource(stream);micSource.connect(micAnalyser);
  // Analysis only: the microphone is never connected to the speakers.
  stream.getAudioTracks().forEach(track=>track.addEventListener('ended',()=>{stopMic();micMessage.textContent='El micrófono se desconectó.';}));
  micButton.textContent='Apagar micrófono';micButton.setAttribute('aria-pressed','true');
  micMessage.textContent='Micrófono activo · análisis local, sin grabar ni reproducir tu voz.';updateStatus();
 }catch(error){
  stopMic();
  micMessage.textContent=error.name==='NotAllowedError'?'Permiso denegado. Habilita el micrófono en los permisos del navegador y vuelve a intentar.':error.name==='NotFoundError'?'No se encontró un micrófono conectado.':'No se pudo abrir el micrófono. Revisa que esté disponible y vuelve a intentar.';
 }finally{micPending=false;micButton.disabled=false;}
}
micButton.addEventListener('click',()=>{ if(micStream) stopMic(); else startMic(); });
addEventListener('pagehide',()=>{leaving=true;stopMic();});
addEventListener('pageshow',()=>{leaving=false;});
// Preferred mode: ask once on startup. The browser may still require a permission gesture.
if(!micButton.disabled && localStorage.getItem('mambaflow-mic') !== 'off'){
  startMic();
}
let paused=matchMedia('(prefers-reduced-motion: reduce)').matches;
const toggle=document.querySelector('#visual-toggle');
function label(){toggle.textContent=paused?'Activar movimiento':'Pausar movimiento';toggle.setAttribute('aria-pressed',String(!paused));}label();
toggle.addEventListener('click',()=>{paused=!paused;label();});
let previous=0;let lost=false;const started=performance.now();
canvas.addEventListener('webglcontextlost',e=>{e.preventDefault();lost=true;canvas.hidden=true;stopMic();});
const bands=[.4,.6,.3,.7],knobs=[.3,.5,.2,.6];
const spectrum=new Float32Array(48);
function draw(ms){
 requestAnimationFrame(draw);
 if(lost||document.hidden||ms-previous<33||(paused&&previous))return;
 previous=ms;resize();const now=(ms-started)/1000;
 const activeAnalyser=micStream?micAnalyser:(player&&!player.paused?analyser:null);
 const active=!!activeAnalyser;
 if(active)activeAnalyser.getByteFrequencyData(data);
 for(let i=0;i<4;i++){
  let energy=.24+.52*Math.pow(.5+.5*Math.sin(now*(1.3+i*.37)+i),3);
  if(active){const ranges=[[1,8],[8,80],[80,350],[1,400]][i];let sum=0;for(let n=ranges[0];n<ranges[1];n++)sum+=data[n]||0;energy=sum/(ranges[1]-ranges[0])/180;}
  bands[i]=bands[i]*.8+Math.min(1,energy)*.2;knobs[i]=bands[i];
 }
 for(let i=0;i<48;i++){
   let value=.08+.24*Math.pow(.5+.5*Math.sin(now*.8+i*.32),3);
   if(active){
     const low=Math.floor(Math.pow(i/48,2)*data.length);
     const high=Math.max(low+1,Math.floor(Math.pow((i+1)/48,2)*data.length));
     let sum=0;for(let k=low;k<high;k++)sum+=data[k]||0;
     value=Math.min(1,sum/(high-low)/200);
   }
   spectrum[i]=spectrum[i]*.72+value*.28;
 }
 updateStatus();
 gl.bindTexture(gl.TEXTURE_2D,null);gl.bindFramebuffer(gl.FRAMEBUFFER,fbo);gl.viewport(0,0,rw,rh);gl.useProgram(pScene);
 gl.uniform2f(US.scene.res,rw,rh);gl.uniform1f(US.scene.time,now);gl.uniform4fv(US.scene.bands,bands);gl.uniform4fv(US.scene.knobs,knobs);gl.uniform1fv(US.scene.spectrum,spectrum);
 gl.uniform1f(US.scene.reflect,params.reflect);gl.uniform1f(US.scene.hue,params.huespeed);gl.uniform1f(US.scene.emission,params.emission);gl.uniform1f(US.scene.atmos,params.atmos);gl.drawArrays(gl.TRIANGLES,0,3);
 gl.bindFramebuffer(gl.FRAMEBUFFER,null);gl.useProgram(pComp);gl.activeTexture(gl.TEXTURE0);gl.bindTexture(gl.TEXTURE_2D,tex);gl.uniform1i(US.comp.scene,0);gl.uniform2f(US.comp.res,rw,rh);gl.uniform1f(US.comp.bloom,params.bloom);gl.drawArrays(gl.TRIANGLES,0,3);
}
requestAnimationFrame(draw);
})();
