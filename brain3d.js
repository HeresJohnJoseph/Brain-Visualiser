/* Headroom — shared real-3D brain scene (Three.js). No build step: ES module via CDN import map. */
import * as THREE from 'three';
import {mergeVertices} from 'three/addons/utils/BufferGeometryUtils.js';

(function(global){
  "use strict";

  function noise3(x,y,z){
    return (Math.sin(x*3.1+y*1.7)+Math.sin(y*2.6+z*3.3)+Math.sin(z*2.9+x*2.1)+Math.sin((x+y+z)*4.2))*0.25;
  }
  function fbm(x,y,z){
    let amp=1,freq=1,sum=0,norm=0;
    for(let i=0;i<4;i++){sum+=noise3(x*freq,y*freq,z*freq)*amp;norm+=amp;amp*=0.52;freq*=2.15;}
    return sum/norm;
  }
  // ridged noise: folds back on itself near zero-crossings, giving winding
  // gyrus/sulcus-like ridges instead of smooth rolling bumps
  function ridgedFbm(x,y,z){
    let amp=1,freq=1,sum=0,norm=0;
    for(let i=0;i<5;i++){
      const n=1-Math.abs(noise3(x*freq,y*freq,z*freq));
      sum+=n*n*amp; norm+=amp; amp*=0.55; freq*=2.05;
    }
    return sum/norm; // 0..1
  }

  function buildBrainGeometry(THREE, radius){
    let geo=new THREE.IcosahedronGeometry(radius,5);
    geo=mergeVertices(geo); // share vertices across faces so normals can blend smoothly
    const pos=geo.attributes.position;
    const colors=new Float32Array(pos.count*3);
    const warm=new THREE.Color('#ff8a4a'), pale=new THREE.Color('#e8c9a8'), cool=new THREE.Color('#7fa0c9');
    for(let i=0;i<pos.count;i++){
      const x=pos.getX(i),y=pos.getY(i),z=pos.getZ(i);
      const nx=x/radius, ny=y/radius, nz=z/radius;
      const r=ridgedFbm(nx*5.2,ny*5.2,nz*5.2);           // 0..1 fold ridges
      const groove=Math.exp(-(x*x)/0.018)*0.62;           // interhemispheric fissure
      let d=1+(r-0.52)*0.34-groove;
      d-=Math.max(0,(ny-0.55))*0.42;                      // flatten top slightly
      d-=Math.max(0,(-ny-0.6))*0.7;                       // pull in toward the stem
      pos.setXYZ(i,x*d,y*(d*0.9+0.1),z*d);
      const front=Math.max(0,nz);
      const col=pale.clone().lerp(warm,Math.min(1,r*0.85+front*0.3)).lerp(cool,Math.max(0,-ny*0.35));
      colors[i*3]=col.r;colors[i*3+1]=col.g;colors[i*3+2]=col.b;
    }
    geo.setAttribute('color',new THREE.BufferAttribute(colors,3));
    geo.computeVertexNormals();
    return geo;
  }

  function sphereFromNorm(nx,ny,r){
    const theta=(nx-0.5)*Math.PI*1.35;
    const phi=0.14*Math.PI+Math.min(0.98,Math.max(0.02,ny))*0.66*Math.PI;
    return {
      x:r*Math.sin(phi)*Math.sin(theta),
      y:r*Math.cos(phi),
      z:r*Math.sin(phi)*Math.cos(theta),
    };
  }

  function makeGlowTexture(THREE){
    const c=document.createElement('canvas');c.width=c.height=128;
    const cx=c.getContext('2d');
    const g=cx.createRadialGradient(64,64,0,64,64,64);
    g.addColorStop(0,'rgba(255,255,255,1)');g.addColorStop(0.35,'rgba(255,255,255,0.55)');g.addColorStop(1,'rgba(255,255,255,0)');
    cx.fillStyle=g;cx.fillRect(0,0,128,128);
    return new THREE.CanvasTexture(c);
  }

  function createBrainScene(canvas, opts){
    opts=opts||{};
    const renderer=new THREE.WebGLRenderer({canvas,antialias:true,alpha:true});
    renderer.setPixelRatio(Math.min(window.devicePixelRatio||1,2));
    renderer.outputColorSpace=THREE.SRGBColorSpace;
    renderer.toneMapping=THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure=1.15;

    const scene=new THREE.Scene();
    const camera=new THREE.PerspectiveCamera(38,1,0.1,50);
    camera.position.set(0,0,4.1);

    const group=new THREE.Group();
    scene.add(group);

    const RADIUS=1.35;
    const geo=buildBrainGeometry(THREE,RADIUS);
    const mat=new THREE.MeshStandardMaterial({vertexColors:true,roughness:0.5,metalness:0.08,emissive:new THREE.Color('#3a1204'),emissiveIntensity:0.35});
    const brain=new THREE.Mesh(geo,mat);
    group.add(brain);

    const glowTex=makeGlowTexture(THREE);
    const haloMat=new THREE.SpriteMaterial({map:glowTex,color:0xff7a3c,transparent:true,opacity:0.28,depthWrite:false,blending:THREE.AdditiveBlending});
    const halo=new THREE.Sprite(haloMat);
    halo.scale.set(RADIUS*3.4,RADIUS*3.4,1);
    halo.position.set(0,0,-0.2);
    group.add(halo);

    scene.add(new THREE.AmbientLight(0x2a3a5a,0.9));
    const warmLight=new THREE.PointLight(0xffb079,2.4,12,2);
    warmLight.position.set(2.6,2.1,3.2); scene.add(warmLight);
    const rimLight=new THREE.PointLight(0x6fa0ff,1.1,14,2);
    rimLight.position.set(-3,-1.6,-2.6); scene.add(rimLight);

    function resize(){
      const w=canvas.clientWidth||1,h=canvas.clientHeight||1;
      renderer.setSize(w,h,false);
      camera.aspect=w/h; camera.updateProjectionMatrix();
    }
    new ResizeObserver(resize).observe(canvas);
    resize();

    /* ---------- drag / idle rotation ---------- */
    let dragging=false, lastX=0, lastY=0, velY=0, rotX=-0.12, rotY=0.35, idleAllowed=true;
    canvas.addEventListener('pointerdown',e=>{dragging=true;lastX=e.clientX;lastY=e.clientY;canvas.setPointerCapture(e.pointerId);});
    canvas.addEventListener('pointermove',e=>{
      mouseNDC(e);
      if(!dragging)return;
      const dx=e.clientX-lastX, dy=e.clientY-lastY; lastX=e.clientX; lastY=e.clientY;
      velY=dx*0.006;
      rotY+=velY; rotX=Math.max(-0.9,Math.min(0.9,rotX+dy*0.006));
    });
    window.addEventListener('pointerup',()=>{dragging=false;});
    canvas.addEventListener('pointerleave',()=>{mouse.active=false;});

    const mouse={x:0,y:0,active:false};
    function mouseNDC(e){
      const r=canvas.getBoundingClientRect();
      mouse.x=((e.clientX-r.left)/r.width)*2-1;
      mouse.y=-((e.clientY-r.top)/r.height)*2+1;
      mouse.active=true;
    }
    canvas.addEventListener('mousemove',mouseNDC);
    canvas.addEventListener('mouseleave',()=>{mouse.active=false;});

    /* ---------- neurons ---------- */
    const neurons=new Map(); // id -> {mesh, glow, spec}
    const raycaster=new THREE.Raycaster();
    raycaster.params.Points={threshold:0.06};
    const pickMeshes=[];

    function neuronMaterial(hex){
      return new THREE.MeshBasicMaterial({color:hex});
    }
    function setNeurons(list){
      const seen=new Set();
      list.forEach(spec=>{
        seen.add(spec.id);
        let n=neurons.get(spec.id);
        const p=sphereFromNorm(spec.nx,spec.ny,RADIUS*1.035+ (spec.lift||0));
        if(!n){
          const core=new THREE.Mesh(new THREE.SphereGeometry(1,10,10),neuronMaterial(spec.color));
          const glow=new THREE.Sprite(new THREE.SpriteMaterial({map:glowTex,color:spec.color,transparent:true,opacity:0.55,depthWrite:false,blending:THREE.AdditiveBlending}));
          core.userData.id=spec.id; glow.userData.id=spec.id;
          group.add(core); group.add(glow);
          n={core,glow,spec};
          neurons.set(spec.id,n);
          pickMeshes.push(core);
        }
        n.core.position.set(p.x,p.y,p.z);
        n.glow.position.set(p.x,p.y,p.z);
        const r=spec.radius||0.045;
        n.core.scale.setScalar(r);
        n.glow.scale.setScalar(r*7);
        n.core.material.color.set(spec.color);
        n.glow.material.color.set(spec.color);
        n.core.material.opacity=spec.dim?0.35:1;
        n.core.material.transparent=!!spec.dim;
        n.glow.material.opacity=(spec.dim?0.18:0.55)*(spec.highlight?1.6:1);
        n.spec=spec;
      });
      [...neurons.keys()].forEach(id=>{
        if(!seen.has(id)){
          const n=neurons.get(id);
          group.remove(n.core); group.remove(n.glow);
          const idx=pickMeshes.indexOf(n.core); if(idx>=0)pickMeshes.splice(idx,1);
          neurons.delete(id);
        }
      });
    }

    function pick(){
      if(!mouse.active)return null;
      raycaster.setFromCamera(mouse,camera);
      const hits=raycaster.intersectObjects(pickMeshes);
      return hits.length?hits[0].object.userData.id:null;
    }

    function screenPos(id){
      const n=neurons.get(id); if(!n)return null;
      const v=n.core.position.clone();
      group.localToWorld(v);
      v.project(camera);
      const r=canvas.getBoundingClientRect();
      return {x:(v.x*0.5+0.5)*r.width, y:(-v.y*0.5+0.5)*r.height, behind:v.z>1};
    }

    /* ---------- hotspot ---------- */
    let hotspot=null;
    function setHotspot(nx,ny,hex){
      if(nx==null){if(hotspot){group.remove(hotspot);hotspot=null;}return;}
      const p=sphereFromNorm(nx,ny,RADIUS*1.06);
      if(!hotspot){
        hotspot=new THREE.Sprite(new THREE.SpriteMaterial({map:glowTex,color:hex,transparent:true,opacity:0.5,depthWrite:false,blending:THREE.AdditiveBlending}));
        group.add(hotspot);
      }
      hotspot.material.color.set(hex);
      hotspot.position.set(p.x,p.y,p.z);
    }

    /* ---------- aura (mental load) ---------- */
    function setAura(intensity){
      warmLight.intensity=2.0+intensity*2.4;
      mat.emissiveIntensity=0.25+intensity*0.5;
      haloMat.opacity=0.2+intensity*0.28;
    }

    /* ---------- edges (graph connections) ---------- */
    const edgeLines=[];
    function setEdges(list){
      edgeLines.forEach(l=>group.remove(l)); edgeLines.length=0;
      list.forEach(e=>{
        const a=neurons.get(e.a), b=neurons.get(e.b);
        if(!a||!b)return;
        const geo=new THREE.BufferGeometry().setFromPoints([a.core.position,b.core.position]);
        const mat2=new THREE.LineBasicMaterial({color:e.color||0xffffff,transparent:true,opacity:e.opacity!=null?e.opacity:0.25});
        const line=new THREE.Line(geo,mat2);
        line.userData.a=e.a; line.userData.b=e.b;
        group.add(line); edgeLines.push(line);
      });
    }
    function refreshEdgeGeometry(){
      edgeLines.forEach(line=>{
        const a=neurons.get(line.userData.a), b=neurons.get(line.userData.b);
        if(!a||!b)return;
        const p=line.geometry.attributes.position;
        p.setXYZ(0,a.core.position.x,a.core.position.y,a.core.position.z);
        p.setXYZ(1,b.core.position.x,b.core.position.y,b.core.position.z);
        p.needsUpdate=true;
      });
    }

    let hoveredId=null;
    const listeners={click:[],hover:[]};
    function on(evt,cb){listeners[evt].push(cb);}
    canvas.addEventListener('click',()=>{
      const id=pick(); listeners.click.forEach(cb=>cb(id));
    });

    const clock=new THREE.Clock();
    function frame(){
      const dt=Math.min(clock.getDelta(),0.05), t=clock.elapsedTime;
      if(!dragging&&idleAllowed) rotY+=dt*0.09;
      group.rotation.set(rotX,rotY,0);
      halo.material.rotation=t*0.05;
      neurons.forEach(n=>{
        const pulse=1+Math.sin(t*(n.spec.pulseSpeed||1.6)+ (n.spec.phase||0))*0.16*(n.spec.highlight?1.6:1);
        n.core.scale.setScalar((n.spec.radius||0.045)*pulse*(n.spec.highlight?1.35:1));
      });
      refreshEdgeGeometry();
      const hid=pick();
      if(hid!==hoveredId){hoveredId=hid;listeners.hover.forEach(cb=>cb(hid));}
      renderer.render(scene,camera);
      requestAnimationFrame(frame);
    }
    requestAnimationFrame(frame);

    return {setNeurons,setEdges,setHotspot,setAura,screenPos,pick,on,
      setIdle:v=>{idleAllowed=v;},
      addExtra:obj=>group.add(obj), group, THREE};
  }

  global.HeadroomBrain3D={createBrainScene, sphereFromNorm};
})(window);
