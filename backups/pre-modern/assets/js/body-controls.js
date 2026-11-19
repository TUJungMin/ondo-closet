
const bodyControls=document.createElement('div');bodyControls.className='body-controls';
bodyControls.innerHTML='<label>키 (cm)<input id="bodyHeight" type="number" min="130" max="220" value="170"></label><label>몸무게 (kg)<input id="bodyWeight" type="number" min="30" max="200" value="65"></label><p id="bodyStatus">키·몸무게를 기반으로 한 대략적인 체형입니다.</p>';
document.getElementById('studio3d').before(bodyControls);
