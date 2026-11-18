(() => {
const shell=document.createElement('div');shell.className='entry-shell';document.body.append(shell);
const profile={gender:'',height:170,styles:[],tops:[],bottoms:[],outers:[],colors:[]};
let step=0,starting=false;
const pages=[
 {key:'gender',title:'어떤 코디를 보고 싶나요?',help:'원하는 코디 기준을 선택해 주세요. 키는 선택 입력이며 실제 핏을 예측하지는 않습니다.',single:true,options:[['men','남성 코디'],['women','여성 코디']]},
 {key:'styles',title:'마음에 드는 스타일을 골라주세요',help:'평소 입고 싶은 분위기를 여러 개 선택할 수 있어요.',options:[['minimal','미니멀','단정하고 간결하게'],['casual','캐주얼','편안한 일상 코디'],['formal','포멀','출근과 격식 있는 자리'],['sport','스포티','활동하기 편하게']]},
 {key:'tops',title:'자주 입는 상의는 어떤 건가요?',help:'옷장을 모두 등록하지 않아도 괜찮아요. 자주 손이 가는 종류부터 알려주세요.',options:['반팔 티셔츠','긴팔 티셔츠','셔츠','블라우스','니트','맨투맨','후드티','폴로 셔츠']},
 {key:'bottoms',title:'하의도 골라볼까요?',help:'편하게 입는 바지와 스커트를 여러 개 선택해 주세요.',options:['데님','슬랙스','면바지','조거 팬츠','와이드 팬츠','반바지','미디스커트','롱스커트']},
 {key:'outers',title:'즐겨 입는 겉옷은 무엇인가요?',help:'간절기와 추운 날 자주 챙기는 옷을 골라주세요.',options:['카디건','블레이저','트렌치코트','울 코트','바람막이','데님 재킷','가죽 재킷','패딩','겉옷을 잘 안 입어요']},
 {key:'colors',title:'어떤 색감이 편한가요?',help:'좋아하는 색을 여러 개 선택해 주세요. 이 정보는 체험 요약에 표시됩니다.',options:['블랙·화이트','베이지·브라운','그레이·네이비','파스텔','채도 낮은 색','선명한 포인트 컬러']},
 {key:'summary',title:'이제 나만의 옷장을 시작해 볼까요?',help:'사진을 등록하면 보유한 옷 중에서 조합을 추천해 드려요.'}
];
function element(tag,text){const node=document.createElement(tag);if(text)node.textContent=text;return node;}
function entry(){
 shell.replaceChildren();shell.append(element('div','온도옷장.'));shell.firstChild.className='entry-brand';
 shell.append(element('h1','오늘 입을 옷, 함께 골라볼까요?'),element('p','내 옷으로 만드는 날씨 맞춤 코디. 원하는 방식으로 시작하세요.'));
 const options=element('div');options.className='entry-options';
 const login=element('button');login.className='entry-option';login.innerHTML='<strong>로그인</strong><span>기존 옷장으로 시작하기</span><small>현재는 서버 인증 없는 체험 로그인입니다.</small>';login.onclick=()=>loginView();
 const guest=element('button');guest.className='entry-option guest';guest.innerHTML='<strong>게스트로 시작</strong><span>간단한 취향 질문 후 바로 체험해요.<br>새로고침하거나 나가면 체험 데이터가 사라져요.</span>';guest.onclick=()=>{step=0;draw();};
 options.append(login,guest);shell.append(options);
}
function loginView(){
 shell.innerHTML='<div class="entry-brand">온도옷장.</div><div class="onboard-box"><h2>체험 로그인</h2><p>현재 기기의 기존 옷장을 불러옵니다. 실제 회원 인증과 계정별 저장은 백엔드 연결 후 제공됩니다.</p><div class="onboard-actions"><button id="entryBack">뒤로</button><button class="primary" id="demoLogin">체험 로그인으로 들어가기</button></div></div>';
 document.getElementById('entryBack').onclick=entry;document.getElementById('demoLogin').onclick=()=>start(false);
}
function draw(){
 const page=pages[step];shell.innerHTML='<div class="entry-brand">온도옷장.</div>';
 const box=element('div');box.className='onboard-box';
 box.append(element('small',(step+1)+' / '+pages.length+' · 나의 취향 알아보기'));
 const progress=element('div');progress.className='onboard-progress';pages.forEach((_,i)=>{const bar=element('i');if(i<=step)bar.className='filled';progress.append(bar);});box.append(progress,element('h2',page.title),element('p',page.help));
 if(page.options){
  const choices=element('div');choices.className='choice-grid';
  page.options.forEach(option=>{
   const [value,label,description]=Array.isArray(option)?option:[option,option];
   const button=element('button',label);button.type='button';
   const chosen=page.single?profile[page.key]===value:profile[page.key].includes(value);button.setAttribute('aria-pressed',chosen);
   if(description)button.append(element('small',description));
   button.onclick=()=>{if(page.single)profile[page.key]=value;else profile[page.key]=chosen?profile[page.key].filter(item=>item!==value):[...profile[page.key],value];draw();};
   choices.append(button);
  });box.append(choices);
 }
 if(step===0){
  const label=element('label','키 (cm, 선택)');label.className='onboard-field';const input=element('input');input.type='number';input.min='100';input.max='230';input.value=profile.height??'';input.oninput=()=>profile.height=input.value===''?null:Number(input.value);label.append(input);box.append(label);
 }
 if(page.key==='summary'){
  const summary=element('div');summary.className='profile-summary';
  const styleNames=pages[1].options.filter(([key])=>profile.styles.includes(key)).map(([,label])=>label);
  [profile.gender==='women'?'여성 코디':'남성 코디',profile.height?profile.height+'cm':'키 미입력',styleNames.join(' · '),...['tops','bottoms','outers','colors'].map(key=>profile[key].join(' · ')||'선택 안 함')].forEach(text=>summary.append(element('div',text)));
  box.append(summary,element('p','취향과 업로드 사진은 이번 체험 중에만 사용됩니다. 스타일 선택은 추천에 반영되고, 자주 입는 옷·색감은 등록 참고용으로 표시됩니다.'));
 }
 const error=element('p');error.className='entry-error';error.setAttribute('role','status');box.append(error);
 const actions=element('div');actions.className='onboard-actions';
 const back=element('button',step?'이전':'처음으로');back.onclick=()=>{if(step){step--;draw();}else entry();};
 const next=element('button',step===pages.length-1?'내 옷장 시작하기':'다음');next.className='primary';
 next.onclick=()=>{
  if(step===0&&(!profile.gender||(profile.height!==null&&(!Number.isFinite(profile.height)||profile.height<100||profile.height>230)))){error.textContent='코디 기준을 선택하고 키를 100~230cm 범위로 입력해 주세요.';return;}
  if(step===1&&!profile.styles.length){error.textContent='원하는 스타일을 한 개 이상 선택해 주세요.';return;}
  if(step===pages.length-1){start(true);return;}step++;draw();
 };
 actions.append(back,next);box.append(actions);shell.append(box);
}
async function start(guest){
 if(starting)return;starting=true;window.guestMode=guest;window.guestProfile=guest?structuredClone(profile):null;
 if(!guest)window.wardrobeStorage=localStorage;
 try{
  for(const placeholder of document.querySelectorAll('[data-app-script]')){
   const src=placeholder.dataset.appScript;
   if(src.endsWith('/mannequin.js'))continue;
   await new Promise((resolve,reject)=>{const script=document.createElement('script');script.src=src;script.onload=resolve;script.onerror=reject;document.body.append(script);});
  }
  shell.remove();document.body.classList.remove('entry-mode');
  const banner=element('div');banner.className='session-banner';
  banner.append(element('span',guest?'게스트 체험 · 사진과 기록은 새로고침 시 초기화됩니다.':'체험 로그인 · 이 브라우저에 저장됩니다. 계정 인증 미연결'));
  const exit=element('button','처음으로');exit.onclick=()=>{if(!guest||confirm('게스트 체험 데이터를 지우고 처음으로 돌아갈까요?'))location.reload();};banner.append(exit);document.querySelector('header').after(banner);
  if(guest){
   const gender=document.getElementById('gender');gender.value=profile.gender;gender.dispatchEvent(new Event('change'));
   document.getElementById('preferredStyle').value=profile.styles[0]||'';
   const summary=element('div');summary.className='personal-settings';summary.append(element('h3','내가 고른 취향'));
   summary.append(element('p',[...profile.tops,...profile.bottoms,...profile.outers,...profile.colors].join(' · ')||'사진을 등록하며 취향을 더 알려주세요.'));
   document.getElementById('garmentForm').before(summary);
   document.getElementById('closetTab').click();
  }
 }catch{shell.append(element('p','화면을 불러오지 못했습니다. 새로고침 후 다시 시도해 주세요.'));}
}
entry();
})();
