(() => {
const canvas=document.querySelector('#emission');if(!canvas)return;
const gl=canvas.getContext('webgl2',{antialias:false,alpha:false});
if(!gl){canvas.hidden=true;return;}
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

  float sat(float x){return clamp(x,0.,1.);}
  float sdCapsule(vec2 p,vec2 a,vec2 b,float r){
    vec2 pa=p-a,ba=b-a;
    float h=clamp(dot(pa,ba)/dot(ba,ba),0.,1.);
    return length(pa-ba*h)-r;
  }
  float sdCircle(vec2 p,float r){return length(p)-r;}
  float hash21(vec2 p){
    p=fract(p*vec2(123.34,456.21));
    p+=dot(p,p+45.32);
    return fract(p.x*p.y);
  }
  vec3 hsv2rgb(vec3 c){
    vec3 rgb=clamp(abs(mod(c.x*6.+vec3(0.,4.,2.),6.)-3.)-1.,0.,1.);
    rgb=rgb*rgb*(3.-2.*rgb);
    return c.z*mix(vec3(1.),rgb,c.y);
  }
  vec3 energyColor(vec2 p,float t,float lane){
    float h=fract(.91 + lane*.115 + p.x*.22 + t*uHueSpeed*.15
      + .035*sin(t*2.2+p.y*8.) + .018*sin(t*5.1-p.x*9.));
    h = .54 + .44 * (.5 + .5 * sin(h * 6.28318));
    return hsv2rgb(vec3(h,.88,1.15));
  }

  void main(){
    vec2 p=(vUv-.5)*vec2(uRes.x/uRes.y,1.0);
    p.y*=-1.0;

    vec3 c=vec3(.010,.014,.022);
    float vign=1.-.36*dot(p,p);
    c*=clamp(vign,.40,1.0);

    vec2 centers[4]=vec2[4](
      vec2(-.30,.14),vec2(.30,.14),vec2(-.30,-.14),vec2(.30,-.14)
    );

    for(int i=0;i<4;i++){
      float fi=float(i);
      vec2 q=p-centers[i];
      float e=uBands[i];
      float knob=uKnobs[i];

      vec2 a=vec2(-.105,0.),b=vec2(.105,0.);
      float r=.047;
      float d=sdCapsule(q,a,b,r);
      vec3 ec=energyColor(q,uTime,fi);

      float wide=exp(-max(d,0.)*14.0);
      float aura=exp(-max(d,0.)*31.0);
      c+=ec*(.10*wide+.19*aura)*e*uAtmos;

      vec2 rp=q;
      rp.y=(rp.y-.105)*2.8;
      float rd=sdCapsule(rp,a,b,r*1.05);
      float floorFall=exp(-abs(q.y-.108)*18.0);
      c+=ec*exp(-max(rd,0.)*18.0)*floorFall*e*uReflect*.24;

      float shell=1.-smoothstep(.0016,.0035,abs(d));
      vec3 shellCol=mix(vec3(.24,.27,.33),ec,sat(e*.95));
      c+=shellCol*shell*.46;

      float inside=1.-smoothstep(-.002,.001,d);
      float ribbon=.50+.50*sin(q.x*27.0-uTime*(2.6+fi*.31)+sin(q.y*34.+uTime)*.75);
      float plasma=inside*e*(.60+.40*ribbon);
      c+=ec*plasma*uEmission*.52;

      float hx=mix(-.10,.105,fract(uTime*(.14+.035*fi)+fi*.19));
      float hot=exp(-pow((q.x-hx)*12.,2.)-pow(q.y*21.,2.))*e;
      c+=ec*hot*uEmission*.72;

      float kx=mix(-.098,.098,knob);
      vec2 kp=q-vec2(kx,0.);
      float kd=sdCircle(kp,.0395);
      float km=1.-smoothstep(-.001,.001,kd);
      vec3 knobOff=vec3(.90,.91,.95);
      vec3 knobOn=vec3(.020,.024,.034);
      vec3 kc=mix(knobOff,knobOn,sat(knob*1.10));
      c=mix(c,kc,km);
      float rim=1.-smoothstep(.001,.0035,abs(kd));
      c+=mix(vec3(.58),ec,sat(e))*rim*.36;

      // Beat sparks become denser as the corresponding band gets hotter.
      float gate=smoothstep(.56,.94,e);
      for(int j=0;j<5;j++){
        float fj=float(j);
        float seed=hash21(vec2(fi*11.7+fj,19.7));
        float ang=6.28318*hash21(vec2(fi*3.1+fj,5.1));
        float rr=.058+.070*hash21(vec2(fi+fj,8.3));
        vec2 sp=vec2(cos(ang),sin(ang))*rr;
        sp.x+=mix(-.035,.035,seed);
        float sd=length(q-sp);
        float s=exp(-sd*720.0)*gate*(.35+.65*fract(uTime*2.4+seed));
        c+=energyColor(sp,uTime+fj*.09,fi)*s*1.7;
      }
    }

    outColor=vec4(c,1.);
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
    const w=Math.max(2,Math.floor(canvas.clientWidth*dpr));
    const h=Math.max(2,Math.floor(canvas.clientHeight*dpr));
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
      res:U(pScene,'uRes'),time:U(pScene,'uTime'),bands:U(pScene,'uBands'),knobs:U(pScene,'uKnobs'),
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
let audioCtx,analyser,data,source;
player?.addEventListener('play',async()=>{
  try{
    if(!audioCtx){audioCtx=new AudioContext();analyser=audioCtx.createAnalyser();analyser.fftSize=1024;data=new Uint8Array(analyser.frequencyBinCount);source=audioCtx.createMediaElementSource(player);source.connect(analyser);analyser.connect(audioCtx.destination);}
    await audioCtx.resume();
  }catch{document.querySelector('#visual-status').textContent='Ambiental';}
});
let paused=matchMedia('(prefers-reduced-motion: reduce)').matches;
const toggle=document.querySelector('#visual-toggle');
function label(){toggle.textContent=paused?'Activar movimiento':'Pausar movimiento';toggle.setAttribute('aria-pressed',String(!paused));}label();
toggle.addEventListener('click',()=>{paused=!paused;label();});
let previous=0;let lost=false;const started=performance.now();
canvas.addEventListener('webglcontextlost',e=>{e.preventDefault();lost=true;canvas.hidden=true;});
const bands=[.4,.6,.3,.7],knobs=[.3,.5,.2,.6];
function draw(ms){
 requestAnimationFrame(draw);
 if(lost||document.hidden||ms-previous<33||(paused&&previous))return;
 previous=ms;resize();const now=(ms-started)/1000;
 const active=analyser&&player&&!player.paused;
 if(active)analyser.getByteFrequencyData(data);
 for(let i=0;i<4;i++){
  let energy=.24+.52*Math.pow(.5+.5*Math.sin(now*(1.3+i*.37)+i),3);
  if(active){const ranges=[[1,8],[8,80],[80,350],[1,400]][i];let sum=0;for(let n=ranges[0];n<ranges[1];n++)sum+=data[n]||0;energy=sum/(ranges[1]-ranges[0])/180;}
  bands[i]=bands[i]*.8+Math.min(1,energy)*.2;knobs[i]=bands[i];
 }
 document.querySelector('#visual-status').textContent=active?'Siguiendo tu música':'Espectro ambiental';
 gl.bindTexture(gl.TEXTURE_2D,null);gl.bindFramebuffer(gl.FRAMEBUFFER,fbo);gl.viewport(0,0,rw,rh);gl.useProgram(pScene);
 gl.uniform2f(US.scene.res,rw,rh);gl.uniform1f(US.scene.time,now);gl.uniform4fv(US.scene.bands,bands);gl.uniform4fv(US.scene.knobs,knobs);
 gl.uniform1f(US.scene.reflect,params.reflect);gl.uniform1f(US.scene.hue,params.huespeed);gl.uniform1f(US.scene.emission,params.emission);gl.uniform1f(US.scene.atmos,params.atmos);gl.drawArrays(gl.TRIANGLES,0,3);
 gl.bindFramebuffer(gl.FRAMEBUFFER,null);gl.useProgram(pComp);gl.activeTexture(gl.TEXTURE0);gl.bindTexture(gl.TEXTURE_2D,tex);gl.uniform1i(US.comp.scene,0);gl.uniform2f(US.comp.res,rw,rh);gl.uniform1f(US.comp.bloom,params.bloom);gl.drawArrays(gl.TRIANGLES,0,3);
}
requestAnimationFrame(draw);
})();
