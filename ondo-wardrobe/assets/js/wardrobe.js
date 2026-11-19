
(() => {
const section=document.createElement('section');section.className='wardrobe';
section.innerHTML='<h2>내 옷장</h2><p class="muted">옷 한 벌씩 촬영하거나 사진을 선택하고, 종류와 특성을 등록하세요.</p><form id="garmentForm" class="wardrobe-form"><label>옷 사진<input id="garmentPhoto" type="file" accept="image/*" required></label><label>이름<input id="garmentName" maxlength="60" placeholder="아이보리 니트" required></label><label>종류<select id="garmentType"><option value="top">상의</option><option value="bottom">바지</option><option value="skirt">스커트</option><option value="outer">겉옷</option><option value="shoes">신발</option></select></label><label>색상<input id="garmentColor" type="color" value="#d9d1bd"></label><label>보온성<select id="garmentWarm"><option value="light">얇음</option><option value="medium">보통</option><option value="warm">따뜻함</option></select></label><label>스타일<select id="garmentStyle"><option value="minimal">미니멀</option><option value="casual">캐주얼</option><option value="formal">포멀</option><option value="sport">스포티</option></select></label><label><input id="garmentWater" type="checkbox" style="width:auto"> 방수 소재</label><label><input id="garmentGrip" type="checkbox" style="width:auto"> 미끄럼 방지 밑창</label><button class="primary">옷장에 등록</button></form><p id="closetStatus" role="status"></p><div class="integration"><strong>Pinterest 스타일 · 계정 미연결</strong><p class="note">저장 핀 자동 가져오기는 Pinterest 앱 인증 연결이 필요합니다. 현재는 선호 스타일을 직접 선택해 추천에 반영할 수 있습니다.</p><label>선호 스타일<select id="preferredStyle"><option value="">장소에 맞춰 선택</option><option value="minimal">미니멀</option><option value="casual">캐주얼</option><option value="formal">포멀</option><option value="sport">스포티</option></select></label></div><button id="buildOutfit" class="primary">내 옷으로 코디 만들기</button><p id="outfitStatus" role="status"></p><div id="closetGrid" class="wardrobe-grid"></div>';
document.querySelector('.mannequin-panel').before(section);
const studio=document.createElement('div');studio.id='studio3d';studio.className='studio3d';studio.setAttribute('aria-label','회전 가능한 3D 코디 마네킹');
document.querySelector('.mannequin-panel').append(studio);
const note=document.createElement('p');note.className='studio-note';note.textContent='드래그로 회전 · 3D 의상은 등록한 종류와 색상을 표현합니다. 사진의 실제 핏·무늬 재현은 아직 지원하지 않습니다.';
studio.after(note);get('outfitCaption').textContent='내 옷으로 코디를 만들면 선택한 의상 색상이 반영됩니다.';
let closet=[],selected=[];
const dbPromise=window.guestMode?Promise.resolve(null):new Promise((resolve,reject)=>{const request=indexedDB.open('weather-wardrobe',1);request.onupgradeneeded=()=>request.result.createObjectStore('clothes',{keyPath:'id'});request.onsuccess=()=>resolve(request.result);request.onerror=()=>reject(request.error);});
async function transaction(mode,operation){if(window.guestMode)return window.guestStore('clothes',operation);const db=await dbPromise;return new Promise((resolve,reject)=>{const tx=db.transaction('clothes',mode);const req=operation(tx.objectStore('clothes'));tx.oncomplete=()=>resolve(req.result);tx.onerror=()=>reject(tx.error);tx.onabort=()=>reject(tx.error);});}
async function updateItem(item,changes){
 const updated={...item,...changes};
 try{await transaction('readwrite',store=>store.put(updated));Object.assign(item,updated);paint();}
 catch{get('closetStatus').textContent='옷 상태를 저장하지 못했습니다.';}
}
function paint(){
 const grid=get('closetGrid');grid.replaceChildren();

 closet.forEach(item=>{
  const card=document.createElement('article');card.className='garment'+(selected.includes(item.id)?' selected':'');
  const image=document.createElement('img');image.src=item.photo;image.alt=item.name;
  const name=document.createElement('strong');name.textContent=item.name;
  const label=document.createElement('small');label.textContent={top:'상의',bottom:'바지',skirt:'스커트',outer:'겉옷',shoes:'신발'}[item.type];
  const remove=document.createElement('button');remove.textContent='삭제';remove.onclick=async()=>{try{await transaction('readwrite',store=>store.delete(item.id));closet=closet.filter(row=>row.id!==item.id);selected=[];paint();window.dispatchEvent(new CustomEvent('wardrobe-outfit',{detail:[]}));}catch{get('closetStatus').textContent='삭제하지 못했습니다.';}};
 const edit=document.createElement('button');edit.textContent='사진·정보 수정';edit.onclick=()=>editGarment(item);
 card.append(image,name,label,edit,remove);grid.append(card);
 });
}
function editGarment(item){
 const dialog=document.createElement('dialog');dialog.className='garment-editor';
 dialog.innerHTML='<form><h2>사진·정보 수정</h2><img class="edit-preview" alt="수정할 옷 사진"><label>사진 교체<input name="photo" type="file" accept="image/jpeg,image/png,image/webp"></label><button type="button" class="rotate">사진 90° 회전</button><label>이름<input name="name" required maxlength="60"></label><label>종류<select name="type"><option value="top">상의</option><option value="bottom">바지</option><option value="skirt">스커트</option><option value="outer">겉옷</option><option value="shoes">신발</option></select></label><label>색상<input name="color" type="color"></label><label>보온성<select name="warm"><option value="light">얇음</option><option value="medium">보통</option><option value="warm">따뜻함</option></select></label><label>스타일<select name="style"><option value="minimal">미니멀</option><option value="casual">캐주얼</option><option value="formal">포멀</option><option value="sport">스포티</option></select></label><p role="status"></p><div class="editor-actions"><button type="button" class="cancel">취소</button><button class="primary">변경 저장</button></div></form>';
 const form=dialog.querySelector('form'),preview=dialog.querySelector('img'),status=dialog.querySelector('[role=status]');
 let photo=item.photo,busy=false;
 preview.src=photo;
 ['name','type','color','warm','style'].forEach(key=>form.elements[key].value=item[key]);
 form.elements.photo.onchange=async()=>{
  const file=form.elements.photo.files[0];if(!file)return;
  if(file.size>15000000){status.textContent='15MB 이하 이미지를 선택하세요.';return;}
  busy=true;
  try{
   photo=await new Promise((resolve,reject)=>{
    const reader=new FileReader();reader.onerror=reject;reader.onload=()=>{
     const image=new Image();image.onerror=reject;image.onload=()=>{
      const scale=Math.min(1,700/Math.max(image.width,image.height)),canvas=document.createElement('canvas');
      canvas.width=Math.round(image.width*scale);canvas.height=Math.round(image.height*scale);
      canvas.getContext('2d').drawImage(image,0,0,canvas.width,canvas.height);resolve(canvas.toDataURL('image/jpeg',.85));
     };image.src=reader.result;
    };reader.readAsDataURL(file);
   });preview.src=photo;status.textContent='사진이 준비됐어요. 저장하면 반영됩니다.';
  }catch{status.textContent='사진을 읽지 못했습니다. JPG·PNG·WebP 파일을 선택하세요.';}
  finally{busy=false;}
 };
 dialog.querySelector('.rotate').onclick=async()=>{
  if(busy)return;busy=true;
  try{
   const image=new Image();image.src=photo;await image.decode();
   const canvas=document.createElement('canvas');canvas.width=image.height;canvas.height=image.width;
   const context=canvas.getContext('2d');context.translate(canvas.width/2,canvas.height/2);context.rotate(Math.PI/2);context.drawImage(image,-image.width/2,-image.height/2);
   photo=canvas.toDataURL('image/jpeg',.9);preview.src=photo;
  }catch{status.textContent='사진 회전에 실패했습니다.';}finally{busy=false;}
 };
 form.onsubmit=async event=>{
  event.preventDefault();if(busy)return;
  const name=form.elements.name.value.trim();if(!name){status.textContent='옷 이름을 입력하세요.';return;}
  const updated={...item,name,photo};
  ['type','color','warm','style'].forEach(key=>updated[key]=form.elements[key].value);
  busy=true;
  try{await transaction('readwrite',store=>store.put(updated));Object.assign(item,updated);paint();if(selected.includes(item.id))recommend();dialog.close();}
  catch{status.textContent='저장에 실패했습니다. 다시 시도해 주세요.';}finally{busy=false;}
 };
 dialog.querySelector('.cancel').onclick=()=>dialog.close();
 dialog.onclose=()=>dialog.remove();document.body.append(dialog);dialog.showModal();
}
get('garmentForm').onsubmit=async event=>{
 event.preventDefault();const file=get('garmentPhoto').files[0];if(!file)return;
 if(file.size>15000000){get('closetStatus').textContent='15MB 이하 사진을 선택하세요.';return;}
 try{
  const photo=await new Promise((resolve,reject)=>{const reader=new FileReader();reader.onload=()=>{const img=new Image();img.onload=()=>{const scale=Math.min(1,700/Math.max(img.width,img.height)),canvas=document.createElement('canvas');canvas.width=img.width*scale;canvas.height=img.height*scale;canvas.getContext('2d').drawImage(img,0,0,canvas.width,canvas.height);resolve(canvas.toDataURL('image/jpeg',.8));};img.onerror=reject;img.src=reader.result;};reader.onerror=reject;reader.readAsDataURL(file);});
  const item={id:crypto.randomUUID(),name:get('garmentName').value.trim(),photo,type:get('garmentType').value,color:get('garmentColor').value,warm:get('garmentWarm').value,style:get('garmentStyle').value,water:get('garmentWater').checked,grip:get('garmentGrip').checked};
  if(!item.name)return;
  await transaction('readwrite',store=>store.put(item));closet.push(item);paint();get('garmentForm').reset();get('closetStatus').textContent=window.guestMode?'이번 체험의 옷장에 추가했습니다. 새로고침하면 초기화됩니다.':'이 브라우저의 옷장에 저장했습니다.';
 }catch{get('closetStatus').textContent='사진을 저장하지 못했습니다. 이미지 형식과 브라우저 저장 공간을 확인하세요.';}
};
function recommend(){
 const preference=get('preferredStyle').value||({office:'minimal',cafe:'casual',outdoor:'sport',formal:'formal'}[place]);
 const raw=Math.min(weather.low,weather.feel);
 const warmth=raw+Number(get('sensitivity').value);
 const target=warmth<12?'warm':warmth<20?'medium':'light';
 const types=['top','bottom','shoes'];if(warmth<19)types.push('outer');
 const picks=[],missing=[];
 const pool=closet;
 function score(item){return ((item.style===preference||window.guestProfile?.styles?.includes(item.style))?3:0)+(item.warm===target?2:0);}
 types.forEach(type=>{
  let options=pool.filter(item=>item.type===type||(type==='bottom'&&item.type==='skirt'));
  if(type==='shoes'&&weather.condition!=='dry')options=options.filter(item=>item.water&&(weather.condition!=='snow'||item.grip));
  options.sort((a,b)=>score(b)-score(a));
  const pick=options[0];
  if(pick)picks.push(pick);else missing.push({top:'상의',bottom:'하의',shoes:weather.condition==='dry'?'신발':'날씨에 맞는 방수·접지 신발',outer:'겉옷'}[type]);
 });
 selected=picks.map(item=>item.id);paint();
 get('outfitStatus').textContent=(picks.length?'선택한 옷 · '+picks.map(item=>item.name).join(' + '):'옷 사진을 등록하면 코디를 추천해 드려요.')+(missing.length?' / 더 필요한 항목 · '+missing.join(', '):'');
 window.dispatchEvent(new CustomEvent('wardrobe-outfit',{detail:picks}));

}
get('buildOutfit').onclick=recommend;
get('preferredStyle').onchange=()=>{if(selected.length)recommend();};
transaction('readonly',store=>store.getAll()).then(rows=>{closet=rows;paint();}).catch(()=>get('closetStatus').textContent='브라우저에서 옷장 저장 기능을 사용할 수 없습니다.');
})();