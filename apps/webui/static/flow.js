const notice=document.querySelector('#notice');
function message(text){if(notice)notice.textContent=text;}
async function queue(){const el=document.querySelector('#queue');if(!el||document.hidden)return;try{const r=await fetch('/jobs');if(r.ok)el.innerHTML=await r.text();}catch{}}
queue();setInterval(queue,3000);
document.querySelector('#search-form')?.addEventListener('submit',async e=>{e.preventDefault();const button=e.target.querySelector('button');button.disabled=true;message('Buscando en YouTube…');try{const r=await fetch('/search?q='+encodeURIComponent(e.target.q.value));if(!r.ok)throw Error();document.querySelector('#search-results').innerHTML=await r.text();message('');}catch{message('No se pudo buscar. Vuelve a intentar.');}finally{button.disabled=false;}});
document.addEventListener('submit',async e=>{if(!e.target.action.includes('/jobs'))return;e.preventDefault();const data=new FormData(e.target);if(e.submitter?.name)data.set(e.submitter.name,e.submitter.value);try{const r=await fetch(e.target.action,{method:'POST',body:data});if(!r.ok){const error=await r.json();throw Error(typeof error.detail==='string'?error.detail:'Revisa los datos.');}message('Cola actualizada.');queue();}catch(error){message(error.message);}});
document.querySelector('#open-folder')?.addEventListener('click',async()=>{try{const r=await fetch('/open_folder',{method:'POST'});if(!r.ok)throw Error();}catch{message('No se pudo abrir Finder. Tus archivos están en Descargas / MambaFlow.');}});

let localObjectURL;
const player=document.querySelector('#collection-player');
document.querySelector('#local-audio')?.addEventListener('change',async e=>{const file=e.target.files[0];if(!file)return;if(localObjectURL)URL.revokeObjectURL(localObjectURL);localObjectURL=URL.createObjectURL(file);player.src=localObjectURL;document.querySelector('#playing-title').textContent=file.name;try{await player.play();}catch{message('Pulsa reproducir para escuchar.');}});
const selected=new URLSearchParams(location.search).get('listen');
if(selected&&player){player.src='/media/'+selected.split('/').map(encodeURIComponent).join('/');document.querySelector('#playing-title').textContent=selected.split('/').pop();}
