(() => {
const form=get('garmentForm'),input=get('garmentPhoto'),label=input.closest('label');
label.classList.add('upload-photo');input.accept='image/jpeg,image/png,image/webp';
[...label.childNodes].filter(n=>n.nodeType===3).forEach(n=>n.remove());
input.setAttribute('aria-label','옷 사진 추가 또는 교체');
const intro=document.createElement('div');intro.className='upload-intro';intro.innerHTML='<span class="upload-icon" aria-hidden="true">＋</span><strong class="upload-heading">여기에 옷 사진을 놓아주세요</strong><span class="upload-help">사진을 끌어다 놓거나 이 박스를 눌러 추가하세요</span><span class="upload-format">JPG · PNG · WebP · 최대 15MB / 한 번에 한 벌씩</span>';
label.prepend(intro);
const status=document.createElement('p');status.className='upload-file-status';status.setAttribute('role','status');label.after(status);
const details=document.createElement('div');details.className='upload-details';
const title=document.createElement('h3');title.textContent='02  옷에 대해 알려주세요';details.append(title);
[...form.children].filter(n=>n!==label&&n!==status).forEach(n=>details.append(n));form.append(details);
const submit=details.querySelector('button.primary');submit.textContent='내 옷장에 추가하기';
const steps=document.createElement('h3');steps.className='upload-section-title';steps.textContent='01  사진 한 장으로 시작해요';label.before(steps);
let dragDepth=0;
const valid=file=>file&&['image/jpeg','image/png','image/webp'].includes(file.type)&&file.size<=15*1024*1024;
function message(){const file=input.files[0];label.classList.toggle('has-photo',!!file);intro.querySelector('strong').textContent=file?'사진을 바꾸려면 누르거나 끌어다 놓으세요':'여기에 옷 사진을 놓아주세요';status.textContent=file?file.name+' · 아래에서 옷 정보를 확인해 주세요.':'';}
input.addEventListener('change',()=>{if(input.files[0]&&!valid(input.files[0])){input.value='';const preview=label.querySelector('.photo-preview');if(preview)preview.hidden=true;message();status.textContent='15MB 이하의 JPG, PNG, WebP 사진을 선택해 주세요.';return;}message();});
label.addEventListener('dragenter',event=>{event.preventDefault();dragDepth++;label.classList.add('drag-over');});
label.addEventListener('dragover',event=>{event.preventDefault();event.dataTransfer.dropEffect='copy';});
label.addEventListener('dragleave',event=>{event.preventDefault();if(--dragDepth<=0)label.classList.remove('drag-over');});
label.addEventListener('drop',event=>{event.preventDefault();dragDepth=0;label.classList.remove('drag-over');const files=event.dataTransfer.files;if(files.length!==1){status.textContent='사진은 한 장씩 추가해 주세요.';return;}if(!valid(files[0])){status.textContent='15MB 이하의 JPG, PNG, WebP 사진을 선택해 주세요.';return;}input.files=files;input.dispatchEvent(new Event('change',{bubbles:true}));});
form.addEventListener('reset',()=>{label.classList.remove('has-photo');intro.querySelector('strong').textContent='여기에 옷 사진을 놓아주세요';status.textContent='';});
const hint=document.createElement('p');hint.className='note';hint.textContent='밝은 곳에서 옷 한 벌이 전체적으로 보이게 촬영해 주세요. 등록한 사진은 나중에 교체하거나 회전할 수 있어요.';form.after(hint);
})();
