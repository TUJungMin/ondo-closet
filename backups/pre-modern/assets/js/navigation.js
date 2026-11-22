
(() => {
const main=document.querySelector('main');main.id='outfitPage';main.setAttribute('role','tabpanel');
const closetPage=document.createElement('section');closetPage.id='closetPage';closetPage.className='closet-page';closetPage.hidden=true;closetPage.setAttribute('role','tabpanel');main.after(closetPage);
const closet=document.querySelector('.wardrobe');closetPage.append(closet);
const tabs=document.createElement('nav');tabs.className='app-tabs';tabs.setAttribute('role','tablist');tabs.setAttribute('aria-label','온도옷장 메뉴');
tabs.innerHTML='<button id="outfitTab" role="tab" aria-controls="outfitPage" aria-selected="true">오늘의 코디</button><button id="closetTab" role="tab" aria-controls="closetPage" aria-selected="false">내 옷장</button>';
document.querySelector('header').after(tabs);main.setAttribute('aria-labelledby','outfitTab');closetPage.setAttribute('aria-labelledby','closetTab');
function switchTab(showCloset){main.hidden=showCloset;closetPage.hidden=!showCloset;get('outfitTab').setAttribute('aria-selected',!showCloset);get('closetTab').setAttribute('aria-selected',showCloset);}
get('outfitTab').onclick=()=>switchTab(false);get('closetTab').onclick=()=>switchTab(true);
const recommendation=document.createElement('section');recommendation.className='owned-outfit';
recommendation.innerHTML='<h2>내 옷으로 오늘의 코디</h2><p class="muted">옷장에 등록한 옷에서 날씨와 장소에 맞는 조합을 골라드려요.</p><div id="ownedPicks" class="owned-grid"></div>';
document.querySelector('.weather').after(recommendation);
const styleLabel=get('preferredStyle').parentElement;recommendation.append(styleLabel,get('buildOutfit'),get('outfitStatus'));
const go=document.createElement('button');go.textContent='옷장에 옷 추가하기';go.onclick=()=>switchTab(true);recommendation.append(go);
const filters=document.createElement('div');filters.className='closet-filters';
const categories=['전체','상의','바지','스커트','겉옷','신발'];let category='전체';
const count=document.createElement('p');count.className='muted';
const empty=document.createElement('p');empty.className='closet-empty';
get('closetGrid').before(filters,count);get('closetGrid').after(empty);
categories.forEach(name=>{const button=document.createElement('button');button.textContent=name;button.setAttribute('aria-pressed',name===category);button.onclick=()=>{category=name;filter();};filters.append(button);});
function filter(){
 const cards=[...get('closetGrid').children];let visible=0;
 cards.forEach(card=>{const matches=category==='전체'||card.querySelector('small')?.textContent===category;card.hidden=!matches;if(matches)visible++;});
 [...filters.children].forEach(button=>button.setAttribute('aria-pressed',button.textContent===category));
 count.textContent='내 옷 '+cards.length+'벌 · '+category+' '+visible+'벌';
 empty.hidden=visible>0;empty.textContent=cards.length?'이 분류에 등록된 옷이 없습니다.':'아직 옷장이 비어 있어요. 사진을 올려 첫 번째 옷을 등록해 보세요.';
}
new MutationObserver(filter).observe(get('closetGrid'),{childList:true});filter();
const preview=document.createElement('img');preview.className='photo-preview';preview.hidden=true;preview.alt='등록할 옷 사진 미리보기';get('garmentPhoto').after(preview);
let previewUrl;
get('garmentPhoto').addEventListener('change',()=>{if(previewUrl)URL.revokeObjectURL(previewUrl);const file=get('garmentPhoto').files[0];preview.hidden=!file;if(file){previewUrl=URL.createObjectURL(file);preview.src=previewUrl;}});
get('garmentForm').addEventListener('reset',()=>{preview.hidden=true;if(previewUrl)URL.revokeObjectURL(previewUrl);});
window.addEventListener('wardrobe-outfit',event=>{
 const output=get('ownedPicks');output.replaceChildren();
 event.detail.forEach(item=>{const card=document.createElement('div'),image=document.createElement('img'),label=document.createElement('p');image.src=item.photo;image.alt=item.name;label.textContent=item.name;card.append(image,label);output.append(card);});
});
const closetRecommend=document.createElement('button');closetRecommend.className='primary';closetRecommend.textContent='이 옷장으로 코디 추천받기';
closetRecommend.onclick=()=>{switchTab(false);get('buildOutfit').click();recommendation.scrollIntoView({behavior:'smooth',block:'start'});};
get('closetGrid').after(closetRecommend);
})();
