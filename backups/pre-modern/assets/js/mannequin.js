
try{
const THREE=await import('https://cdn.jsdelivr.net/npm/three@0.170.0/build/three.module.js');
const host=document.getElementById('studio3d');
const scene=new THREE.Scene();scene.background=new THREE.Color('#e8e7df');
const camera=new THREE.PerspectiveCamera(35,1,.1,100);camera.position.set(0,1.3,5.8);camera.lookAt(0,1.2,0);
const renderer=new THREE.WebGLRenderer({antialias:true});renderer.setPixelRatio(Math.min(devicePixelRatio,2));host.append(renderer.domElement);
scene.add(new THREE.HemisphereLight(0xffffff,0x777568,2.5));const light=new THREE.DirectionalLight(0xffffff,3);light.position.set(3,5,4);scene.add(light);
const body=new THREE.Group();scene.add(body);const garments={};
function mesh(geometry,color,x,y,z,sx=1,sy=1,sz=1){const obj=new THREE.Mesh(geometry,new THREE.MeshStandardMaterial({color,roughness:.8}));obj.position.set(x,y,z);obj.scale.set(sx,sy,sz);body.add(obj);return obj;}
const skin='#c69d82';mesh(new THREE.SphereGeometry(.17,48,40),skin,0,2.4,0,.9,1.3,.95);
mesh(new THREE.CylinderGeometry(.085,.09,.16,24),skin,0,2.13,0);
garments.top=[mesh(new THREE.CylinderGeometry(.31,.25,.67,32),skin,0,1.75,0,1,1,.65)];
for(const side of [-1,1]){
 const arm=mesh(new THREE.CapsuleGeometry(.085,.49,8,16),skin,side*.37,1.72,0);arm.rotation.z=side*.12;garments.top.push(arm);
 const leg=mesh(new THREE.CylinderGeometry(.115,.085,.94,24),skin,side*.145,.81,0);
 (garments.bottom??=[]).push(leg);
 (garments.shoes??=[]).push(mesh(new THREE.SphereGeometry(.13,24,16),skin,side*.145,.29,.08,1,.6,1.9));
}
garments.skirt=[mesh(new THREE.CylinderGeometry(.26,.43,.69,32),skin,0,1.12,0,1,1,.8)];garments.skirt[0].visible=false;
garments.outer=[mesh(new THREE.CylinderGeometry(.335,.29,.73,32,1,true),skin,0,1.74,0,1,1,.7)];garments.outer[0].visible=false;
for(const side of [-1,1]){
 mesh(new THREE.SphereGeometry(.024,24,16),'#ded4c8',side*.054,2.425,.145,1,.45,.3);
 mesh(new THREE.SphereGeometry(.008,16,12),'#4e453d',side*.054,2.425,.153,1,1,.4);
 mesh(new THREE.SphereGeometry(.03,24,16),skin,side*.15,2.39,0,.4,1,.6);
 mesh(new THREE.SphereGeometry(.06,24,20),skin,side*.4,1.35,0,.7,1.4,.5);
}
mesh(new THREE.SphereGeometry(.03,24,16),skin,0,2.37,.15,.6,1,.9);
mesh(new THREE.SphereGeometry(.035,24,16),'#976e62',0,2.32,.14,1,.17,.4);
mesh(new THREE.SphereGeometry(.17,48,32),'#46392e',0,2.49,-.035,.95,.8,.95);
renderer.toneMapping=THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure=1.1;
const fill=new THREE.DirectionalLight('#dde8ff',1.2);fill.position.set(-3,2,-3);scene.add(fill);
function updateBody(){
 const height=Number(document.getElementById('bodyHeight').value),weight=Number(document.getElementById('bodyWeight').value);
 if(height<130||height>220||weight<30||weight>200){document.getElementById('bodyStatus').textContent='키 130~220cm, 몸무게 30~200kg 범위로 입력하세요.';return;}
 const scale=height/170,width=Math.max(.7,Math.min(1.65,Math.sqrt(weight/65)/scale));
 body.scale.set(width,scale,width);
 camera.position.set(0,1.3*scale,5.8*Math.max(scale,1));camera.lookAt(0,1.2*scale,0);
 document.getElementById('bodyStatus').textContent=height+'cm · '+weight+'kg · 신체 비율을 근사한 3D 미리보기';
}
document.getElementById('bodyHeight').oninput=updateBody;
document.getElementById('bodyWeight').oninput=updateBody;
updateBody();
let down=false,last=0;
renderer.domElement.onpointerdown=event=>{down=true;last=event.clientX;renderer.domElement.setPointerCapture(event.pointerId);};
renderer.domElement.onpointermove=event=>{if(down){body.rotation.y+=(event.clientX-last)*.012;last=event.clientX;}};
renderer.domElement.onpointerup=()=>down=false;renderer.domElement.onpointercancel=()=>down=false;
window.addEventListener('wardrobe-outfit',event=>{
 Object.values(garments).flat().forEach(obj=>obj.material.color.set(skin));
 garments.outer[0].visible=false;garments.skirt[0].visible=false;garments.bottom.forEach(obj=>obj.visible=true);
 event.detail.forEach(item=>{(garments[item.type]||[]).forEach(obj=>{obj.visible=true;obj.material.color.set(item.color);});});
});
new ResizeObserver(()=>{const width=host.clientWidth,height=host.clientHeight;renderer.setSize(width,height);camera.aspect=width/height;camera.updateProjectionMatrix();}).observe(host);
renderer.setAnimationLoop(()=>renderer.render(scene,camera));
}catch(error){document.getElementById('studio3d').textContent='3D 뷰어를 불러오지 못했습니다. 인터넷 연결과 WebGL 지원을 확인해 주세요.';}
