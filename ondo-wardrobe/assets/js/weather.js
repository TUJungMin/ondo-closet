
const get=id=>document.getElementById(id);
let weather={low:11,high:22,feel:17,condition:'dry',probability:null,label:'직접 입력 예시 · 간절기',change:null};
let place='office',request=0;
const looks={
 office:{title:'단정하게, 편안하게.',description:'출근과 미팅에는 차분한 뉴트럴 조합.',colors:['#e8e1d3','#394956','#8c8171'],names:'아이보리 · 네이비 · 토프',top:'셔츠 또는 파인 니트',bottom:'스트레이트 슬랙스',accessory:'간결한 토트백'},
 cafe:{title:'부드러운 색으로 기분 전환.',description:'카페와 데이트에는 밝은 베이스와 은은한 포인트.',colors:['#eee3d3','#a9b69c','#765146'],names:'크림 · 세이지 · 코코아',top:'니트 또는 코튼 셔츠',bottom:'데님 또는 롱스커트',accessory:'브라운 크로스백'},
 outdoor:{title:'가볍게 나가고, 편하게 걷기.',description:'야외에서는 움직임이 편한 소재와 레이어드.',colors:['#c4c9ae','#515b43','#e2d6bb'],names:'라이트 카키 · 올리브 · 샌드',top:'통기성 좋은 티셔츠',bottom:'활동하기 편한 팬츠',accessory:'가벼운 백팩'},
 formal:{title:'차분한 톤으로 정돈된 인상.',description:'격식 있는 자리에는 톤을 좁힌 조합.',colors:['#353c44','#d6d2c9','#706f72'],names:'차콜 · 오프화이트 · 그레이',top:'단색 셔츠 또는 블라우스',bottom:'테일러드 팬츠 또는 미디스커트',accessory:'장식이 적은 가방'}
};
function render(){
 const w=weather,t=Math.min(w.feel,w.low)+Number(get('sensitivity').value),gap=w.high-w.low;
 get('weatherLabel').textContent=w.label;get('temperature').textContent=Math.round(w.feel)+'°';
 get('conditionLabel').textContent='체감 기온 · '+({dry:'비·눈 예보 없음',rain:'비 대비',snow:'눈 대비'}[w.condition]);
 get('weatherIcon').textContent={dry:'☀',rain:'☂',snow:'❄'}[w.condition];
 get('range').textContent=w.low+'° / '+w.high+'°';get('gap').textContent=gap.toFixed(1).replace('.0','')+'°';
 get('rainChance').textContent=w.probability===null?'미입력':w.probability+'%';
 get('weatherAdvice').textContent=(gap>=10?'일교차가 커요. 벗어서 들고 다닐 수 있는 겉옷을 챙기세요.':'하루 중 가장 쌀쌀한 시간에 맞춰 옷을 골라보세요.')+(w.change!==null&&Math.abs(w.change)>=5?' 어제보다 최고 기온이 '+Math.abs(w.change).toFixed(1)+'° '+(w.change<0?'낮아요.':'높아요.'):'');
 const outer=t<5?'보온 아우터를 입으세요':t<12?'도톰한 겉옷을 챙기세요':t<19?'가벼운 겉옷을 챙기세요':'가벼운 옷차림도 좋아요';
 get('outerTitle').textContent=outer;
 get('outerText').textContent=t<5?'패딩이나 두꺼운 코트에 니트를 겹쳐 입어보세요.':t<12?'재킷이나 코트에 얇은 이너를 겹쳐 입으면 실내에서 조절하기 편해요.':t<19?'카디건이나 가벼운 재킷을 추천해요. 낮에는 벗고 아침저녁에 걸치세요.':'통기성 좋은 상의를 고르세요. 냉방이 강한 실내에서는 얇은 셔츠를 덧입어도 좋아요.';
 get('shoeTitle').textContent=w.condition==='snow'?'접지력 있는 방수 부츠':w.condition==='rain'?'물에 강한 신발을 선택하세요':place==='outdoor'?'쿠션 있는 워킹화':place==='formal'?'단정한 로퍼 또는 낮은 구두':'편안한 스니커즈 또는 로퍼';
 get('shoeText').textContent=w.condition==='snow'?'보온 안감과 미끄럼 방지 밑창을 확인하세요. 얼어 있는 길에서는 보폭을 줄이세요.':w.condition==='rain'?'방수 신발이나 레인부츠를 고르고 젖은 바닥에서의 접지력을 확인하세요.':'오래 걷는다면 발에 맞는 사이즈와 안정적인 밑창을 우선하세요.';
 get('avoidShoes').textContent=w.condition==='snow'?'피할 신발 · 매끈한 밑창, 높은 굽, 발이 노출되는 신발':w.condition==='rain'?'피할 신발 · 방수 처리 없는 스웨이드, 물이 스며드는 캔버스':'';
  const female=get('gender').value==='women';
 const look={...looks[place]};
 if(female){
  look.top=place==='formal'?'단색 블라우스':place==='office'?'셔츠 또는 파인 니트':place==='cafe'?'라운드 니트 또는 블라우스':'통기성 좋은 티셔츠';
  look.bottom=place==='cafe'?'미디스커트':place==='formal'?'테일러드 팬츠':'스트레이트 팬츠';
 }else{
  look.top=place==='formal'?'단색 드레스 셔츠':place==='office'?'옥스퍼드 셔츠 또는 니트':place==='cafe'?'니트 또는 캐주얼 셔츠':'통기성 좋은 티셔츠';
  look.bottom=place==='cafe'?'스트레이트 데님':place==='outdoor'?'활동하기 편한 팬츠':'테일러드 슬랙스';
 }
 const figure=get('mannequin');
 figure.classList.toggle('skirt',female&&place==='cafe');
 figure.classList.toggle('with-outer',t<19);
 figure.classList.toggle('boots',w.condition==='snow'||w.condition==='rain');
 figure.style.setProperty('--outfit-top',look.colors[0]);
 figure.style.setProperty('--outfit-bottom',look.colors[1]);
 figure.style.setProperty('--outfit-outer',look.colors[2]);
 get('outfitCaption').textContent=(female?'여성':'남성')+' 코디 · '+look.top+' + '+look.bottom+(t<19?' + 겉옷':'');get('lookTitle').textContent=look.title;get('lookDescription').textContent=look.description;get('colorNames').textContent=look.names;
 get('swatches').replaceChildren();look.colors.forEach((color,index)=>{const swatch=document.createElement('div');swatch.className='swatch';swatch.style.background=color;swatch.setAttribute('aria-label',look.names.split(' · ')[index]);get('swatches').append(swatch);});
 get('lookList').replaceChildren();[['상의',w.high>=27?'통기성 좋은 얇은 상의':look.top],['하의',look.bottom],['가방·소품',look.accessory+(w.condition==='rain'?' · 우산':'')]].forEach(([label,text])=>{const p=document.createElement('p'),small=document.createElement('small');small.textContent=label;p.append(small,document.createTextNode(text));get('lookList').append(p);});
}
get('places').querySelectorAll('button').forEach(button=>button.onclick=()=>{place=button.dataset.place;get('places').querySelectorAll('button').forEach(item=>item.setAttribute('aria-pressed',item===button));render();});
get('sensitivity').onchange=render;get('gender').onchange=render;
get('manual').onsubmit=event=>{event.preventDefault();if(Number(get('low').value)>Number(get('high').value)){get('status').textContent='최저 기온은 최고 기온 이하로 입력해 주세요.';return;}request++;weather={low:Number(get('low').value),high:Number(get('high').value),feel:Number(get('feel').value),condition:get('condition').value,probability:null,label:'직접 입력한 날씨',change:null};get('status').textContent='입력한 날씨로 추천하고 있어요.';get('fetchWeather').disabled=false;render();};
get('city').onchange=()=>{request++;get('fetchWeather').disabled=false;get('status').textContent='도시를 변경했어요. 날씨 가져오기를 눌러 주세요.';};
get('fetchWeather').onclick=async()=>{
 const id=++request;get('fetchWeather').disabled=true;get('status').textContent='최신 예보를 불러오는 중…';
 const [latitude,longitude]=get('city').value.split(','),city=get('city').selectedOptions[0].textContent;
 try{
  const params=new URLSearchParams({latitude,longitude,current:'apparent_temperature',daily:'temperature_2m_max,temperature_2m_min,precipitation_probability_max,rain_sum,snowfall_sum',timezone:'Asia/Seoul',past_days:'1',forecast_days:'1'});
  const response=await fetch('https://api.open-meteo.com/v1/forecast?'+params,{signal:AbortSignal.timeout(12000)});if(!response.ok)throw Error();
  const data=await response.json();if(id!==request)return;
  const index=data.daily.time.indexOf(data.current.time.slice(0,10));if(index<0)throw Error();
  const low=data.daily.temperature_2m_min[index],high=data.daily.temperature_2m_max[index],feel=data.current.apparent_temperature;
  if(![low,high,feel].every(Number.isFinite))throw Error();
  const probability=data.daily.precipitation_probability_max[index],snow=data.daily.snowfall_sum[index],rain=data.daily.rain_sum[index];
  weather={low,high,feel,probability,condition:snow>0?'snow':rain>0||probability>=40?'rain':'dry',label:city+' · '+data.current.time.replace('T',' ')+' 예보',change:index>0?high-data.daily.temperature_2m_max[index-1]:null};
  get('status').textContent='예보를 반영했어요. 비·눈은 오늘 하루 예보 기준입니다.';render();
 }catch{if(id===request)get('status').textContent='예보 연결에 실패했어요. 현재 추천은 이전 입력 기준입니다. 직접 입력으로 이용해 주세요.';}
 finally{if(id===request)get('fetchWeather').disabled=false;}
};
render();
