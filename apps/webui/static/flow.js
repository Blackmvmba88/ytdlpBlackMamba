const notice=document.querySelector('#notice');
function message(text){if(notice)notice.textContent=text;}
async function queue(){const el=document.querySelector('#queue');if(!el||document.hidden)return;try{const r=await fetch('/jobs');if(r.ok)el.innerHTML=await r.text();}catch{}}
let collectionHTML='';
async function collection(){const el=document.querySelector('#saved-collection');if(!el||document.hidden)return;try{const r=await fetch('/collection');if(r.ok){const html=await r.text();if(html!==collectionHTML){el.innerHTML=html;collectionHTML=html;}}}catch{}}
queue();collection();setInterval(()=>{queue();collection();},3000);
document.querySelector('#search-form')?.addEventListener('submit',async e=>{e.preventDefault();const button=e.target.querySelector('button');button.disabled=true;message('Buscando en YouTube…');try{const r=await fetch('/search?q='+encodeURIComponent(e.target.q.value));if(!r.ok)throw Error();document.querySelector('#search-results').innerHTML=await r.text();message('');}catch{message('No se pudo buscar. Vuelve a intentar.');}finally{button.disabled=false;}});
document.addEventListener('submit',async e=>{if(!e.target.action.includes('/jobs'))return;e.preventDefault();const data=new FormData(e.target);if(e.submitter?.name)data.set(e.submitter.name,e.submitter.value);try{const r=await fetch(e.target.action,{method:'POST',body:data,headers:{'Accept':'application/json'}});if(!r.ok){const error=await r.json();throw Error(typeof error.detail==='string'?error.detail:'Revisa los datos.');}const result=await r.json();message(result.message||'Cola actualizada.');queue();collection();}catch(error){message(error.message);}});
document.querySelector('#open-folder')?.addEventListener('click',async()=>{try{const r=await fetch('/open_folder',{method:'POST'});if(!r.ok)throw Error();}catch{message('No se pudo abrir Finder. Tus archivos están en Descargas / MambaFlow.');}});

let localObjectURL;
const player=document.querySelector('#collection-player');
document.querySelector('#local-audio')?.addEventListener('change',async e=>{const file=e.target.files[0];if(!file)return;if(localObjectURL)URL.revokeObjectURL(localObjectURL);localObjectURL=URL.createObjectURL(file);player.dataset.mode='audio';player.src=localObjectURL;document.querySelector('#playing-title').textContent=file.name;try{await player.play();}catch{message('Pulsa reproducir para escuchar.');}});
const selected=new URLSearchParams(location.search).get('listen');
if(selected&&player){player.src='/media/'+selected.split('/').map(encodeURIComponent).join('/');document.querySelector('#playing-title').textContent=selected.split('/').pop();}

document.addEventListener('click',async event=>{
 const button=event.target.closest('[data-play-url]');if(!button)return;
 if(!player){location.href='/?listen='+encodeURIComponent(button.dataset.playUrl.slice('/media/'.length));return;}
 player.dataset.mode=button.dataset.playMode;player.src=button.dataset.playUrl;
 document.querySelector('#playing-title').textContent=button.dataset.playName;
 try{await player.play();player.scrollIntoView({block:'center',behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'auto':'smooth'});}catch{message('Pulsa reproducir. Si el navegador no admite este formato, abre el archivo desde Finder.');}
});
