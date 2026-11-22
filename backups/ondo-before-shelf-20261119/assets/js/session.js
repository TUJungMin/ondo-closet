window.guestMode=true;
const sessionValues=new Map();
window.wardrobeStorage={
 getItem:key=>sessionValues.get(key)??null,
 setItem:(key,value)=>sessionValues.set(key,String(value)),
 removeItem:key=>sessionValues.delete(key)
};
const guestCollections=new Map();
window.guestStore=async(name,operation)=>{
 if(!guestCollections.has(name))guestCollections.set(name,new Map());
 const data=guestCollections.get(name);
 const result=operation({
  getAll:()=>({result:[...data.values()].map(value=>structuredClone(value))}),
  put:value=>{data.set(value.id,structuredClone(value));return {result:value.id};},
  delete:id=>{data.delete(id);return {result:undefined};}
 });
 return result.result;
};
