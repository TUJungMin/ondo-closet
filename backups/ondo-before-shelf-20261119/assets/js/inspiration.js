(() => {
const panel=document.querySelector('.pinterest-panel');
const photos=[
 ['f8/70/3f/f8703fdea69f342e13c999b097ef45f4.jpg','브라운 카디건','https://www.pinterest.com/pin/422281209388500/'],
 ['ab/24/02/ab2402fc58249273697f6d9ec35704f2.jpg','울 블레이저','https://uk.pinterest.com/pin/927249010771235211/'],
 ['dd/ed/26/dded26ef520a86e5e389023f9407997e.jpg','데일리 카디건','https://www.pinterest.com/pin/21462535719575733/'],
 ['34/bd/87/34bd87918a4445254f8b814ed18c15df.jpg','베이지 니트 코디','https://www.pinterest.com/pin/409968372337296992/'],
 ['12/af/36/12af36081fb9cf6ea2da785640e5a990.jpg','체크 재킷 레이어드','https://www.pinterest.com/pin/422281208644025/']
];
panel.innerHTML='<div class="style-carousel-heading"><div><h2>내 스타일 참고 이미지</h2><p>마음에 드는 분위기를 찾아보세요.</p></div><button type="button" class="style-motion" aria-pressed="false">일시정지</button></div><div class="style-carousel"><div class="style-track"></div></div><p class="style-source">Pinterest에서 고른 코디 예시 · 카드를 누르면 출처가 열려요</p>';
const gender=get('gender'),age=get('ageGroup');
try{age.value=window.wardrobeStorage.getItem('wardrobe.ageGroup')||'';}catch{}
age.addEventListener('change',()=>{try{window.wardrobeStorage.setItem('wardrobe.ageGroup',age.value);}catch{}});
const track=panel.querySelector('.style-track');
function group(duplicate){const row=document.createElement('div');row.className='style-group';if(duplicate)row.setAttribute('aria-hidden','true');Array.from({length:3},()=>photos.filter((_,i)=>gender.value==='women'?i>=2:i<2)).flat().forEach(([path,title,link])=>{const card=document.createElement('a');card.className='style-photo-card';card.href=link;card.target='_blank';card.rel='noopener noreferrer';if(duplicate)card.tabIndex=-1;const image=document.createElement('img');image.src='https://i.pinimg.com/originals/'+path;image.alt=title+' 코디 참고 이미지';image.decoding='async';const caption=document.createElement('span');caption.textContent=title;card.append(image,caption);image.onerror=()=>{image.hidden=true;card.classList.add('image-unavailable');caption.textContent=title+' · Pinterest에서 보기 ↗';};row.append(card);});return row;}
function renderReferences(){track.replaceChildren(group(false),group(true));panel.querySelector('.style-carousel-heading p').textContent=(gender.value==='women'?'여성':'남성')+' 코디에서 마음에 드는 분위기를 찾아보세요.';}
gender.addEventListener('change',renderReferences);renderReferences();
const button=panel.querySelector('.style-motion');button.onclick=()=>{const paused=panel.classList.toggle('is-paused');button.textContent=paused?'재생':'일시정지';button.setAttribute('aria-pressed',String(paused));};
})();
