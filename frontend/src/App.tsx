import {FormEvent,useCallback,useEffect,useMemo,useRef,useState} from 'react'
import {
  Activity,BarChart3,Building2,Car,ChevronRight,Clock3,History,Layers3,
  LogOut,Map,Menu,Monitor,Move,ParkingCircle,Save,Search,Settings2,ShieldCheck,Undo2,Wifi,X,
} from 'lucide-react'
import {api,token,wsUrl} from './api'
import {calculateZoneStats} from './stats'
import type {DashboardSummary,FloorMap,FloorSummary,ParkingEvent,ParkingSpace,ParkingZone,Status} from './types'

const emptySummary:DashboardSummary={building_code:'PA',building_name:'Parking Building A',total:0,available:0,occupied:0,disabled:0,occupancy_rate:0,floors:[]}
type View='overview'|'map'|'available'|'events'|'monitor'

function useData<T>(path:string,initial:T,revision=0){
  const [data,setData]=useState<T>(initial)
  const [error,setError]=useState('')
  const load=useCallback(()=>api<T>(path).then(value=>{setData(value);setError('')}).catch(error=>setError(error.message)),[path])
  useEffect(()=>{void load()},[load,revision])
  return{data,error,load,setData}
}

function Login({onLogin}:{onLogin:()=>void}){
  const [username,setUsername]=useState('admin')
  const [password,setPassword]=useState('')
  const [error,setError]=useState('')
  const [busy,setBusy]=useState(false)
  async function submit(event:FormEvent){
    event.preventDefault();setBusy(true);setError('')
    try{
      const result=await api<{access_token:string;display_name:string;role:string}>('/auth/login',{method:'POST',body:JSON.stringify({username,password})})
      localStorage.setItem('parking_token',result.access_token)
      localStorage.setItem('parking_user',result.display_name)
      localStorage.setItem('parking_role',result.role)
      onLogin()
    }catch(error){setError((error as Error).message)}finally{setBusy(false)}
  }
  return <main className="login-page">
    <section className="login-visual">
      <div className="login-mark"><ParkingCircle size={30}/><span>SMART PARKING</span></div>
      <div className="login-copy"><p>BUILDING OPERATIONS</p><h1>เห็นทุกช่องจอด<br/>จากหน้าจอเดียว</h1><span>Digital twin สำหรับอาคารจอดรถ 4 ชั้น พร้อมข้อมูลสถานะแบบเรียลไทม์</span></div>
      <div className="login-map" aria-hidden="true">{Array.from({length:36},(_,i)=><i className={i%5===0?'occupied':''} key={i}/>)}</div>
    </section>
    <form className="login-card" onSubmit={submit}>
      <p className="eyebrow">SECURE OPERATOR ACCESS</p><h2>เข้าสู่ระบบควบคุม</h2><p>ใช้บัญชีเจ้าหน้าที่เพื่อดูและเปลี่ยนสถานะช่องจอด</p>
      <label><span>ชื่อผู้ใช้</span><input value={username} onChange={e=>setUsername(e.target.value)} autoComplete="username"/></label>
      <label><span>รหัสผ่าน</span><input type="password" value={password} onChange={e=>setPassword(e.target.value)} autoComplete="current-password"/></label>
      {error&&<div className="error-box">{error}</div>}
      <button className="primary-button" disabled={busy}>{busy?'กำลังเข้าสู่ระบบ...':'เข้าสู่ระบบ'}</button>
    </form>
  </main>
}

function Metric({label,value,detail,tone,icon:Icon}:{label:string;value:string|number;detail:string;tone:string;icon:typeof Car}){
  return <article className={`metric-card ${tone}`}><div><span>{label}</span><strong>{value}</strong><small>{detail}</small></div><i><Icon size={22}/></i></article>
}

function Sidebar({view,setView,open,setOpen,onLogout}:{view:View;setView:(v:View)=>void;open:boolean;setOpen:(v:boolean)=>void;onLogout:()=>void}){
  const items:[View,string,typeof BarChart3][]=[['overview','ภาพรวม',BarChart3],['map','แผนผังช่องจอด',Map],['monitor','จอสรุปแต่ละชั้น',Monitor],['available','ค้นหาช่องว่าง',Search],['events','ประวัติสถานะ',History]]
  return <aside className={open?'sidebar open':'sidebar'}>
    <div className="brand"><span><ParkingCircle size={24}/></span><div>SMART<b>PARKING</b></div><button onClick={()=>setOpen(false)} aria-label="ปิดเมนู"><X/></button></div>
    <p className="nav-label">PARKING CONTROL</p>
    <nav>{items.map(([key,label,Icon])=><button className={view===key?'active':''} onClick={()=>{setView(key);setOpen(false)}} key={key}><Icon size={18}/><span>{label}</span><ChevronRight size={15}/></button>)}</nav>
    <div className="building-state"><span><i/>ระบบออนไลน์</span><b>Parking Building A</b><small>4 Floors · 704 Spaces</small></div>
    <button className="logout" onClick={onLogout}><LogOut size={17}/> ออกจากระบบ</button>
  </aside>
}

function FloorSelector({floors,selected,onSelect}:{floors:FloorSummary[];selected:number;onSelect:(id:number)=>void}){
  return <div className="floor-selector">{floors.map(floor=><button className={floor.id===selected?'selected':''} onClick={()=>onSelect(floor.id)} key={floor.id}><span>{floor.floor_code}</span><b>{floor.available}</b><small>ช่องว่าง</small><i style={{width:`${100-floor.occupancy_rate}%`}}/></button>)}</div>
}

function statusLabel(status:Status){return{AVAILABLE:'ว่าง',OCCUPIED:'มีรถจอด',DISABLED:'ปิดใช้งาน',UNKNOWN:'ไม่ทราบสถานะ'}[status]}

function ParkingMapView({floor,selected,onSelect,editable=false,onMove}:{floor:FloorMap|null;selected:ParkingSpace|null;onSelect:(space:ParkingSpace)=>void;editable?:boolean;onMove?:(space:ParkingSpace,x:number,y:number)=>void}){
  const drag=useRef<{space:ParkingSpace;dx:number;dy:number}|null>(null)
  if(!floor)return <div className="map-loading">กำลังโหลดแผนผัง...</div>
  const [, , viewWidth, viewHeight]=floor.view_box.split(/\s+/).map(Number)
  function svgPoint(event:React.PointerEvent<SVGElement>){const svg=event.currentTarget.ownerSVGElement||event.currentTarget as SVGSVGElement;const point=svg.createSVGPoint();point.x=event.clientX;point.y=event.clientY;const matrix=svg.getScreenCTM();return matrix?point.matrixTransform(matrix.inverse()):point}
  function move(event:React.PointerEvent<SVGSVGElement>){if(!editable||!drag.current||!onMove)return;const point=svgPoint(event);const {space,dx,dy}=drag.current;onMove(space,Math.max(18,Math.min(viewWidth-18-space.width,point.x-dx)),Math.max(18,Math.min(viewHeight-18-space.height,point.y-dy)))}
  return <div className={`parking-canvas ${editable?'editing':''}`}>
    <svg viewBox={floor.view_box} role="img" aria-label={`แผนผัง ${floor.floor_name}`} onPointerMove={move} onPointerUp={()=>{drag.current=null}} onPointerCancel={()=>{drag.current=null}}>
      <defs>
        <pattern id="grid" width="28" height="28" patternUnits="userSpaceOnUse"><path d="M 28 0 L 0 0 0 28" fill="none" stroke="#1b493f" strokeWidth=".5"/></pattern>
        <marker id="arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="#6ebba5"/></marker>
      </defs>
      <rect width="1740" height="700" rx="22" fill="#0b2924"/>
      <rect x="12" y="12" width="1716" height="676" rx="16" fill="url(#grid)" stroke="#2a6254" strokeWidth="2"/>
      <g className="map-structure">
        <rect x="34" y="44" width="1672" height="74" rx="10"/>
        <rect x="34" y="584" width="1672" height="74" rx="10"/>
        <rect x="45" y="232" width="330" height="202" rx="13"/>
        <rect x="545" y="232" width="600" height="202" rx="13"/>
        <rect x="1320" y="232" width="330" height="202" rx="13"/>
      </g>
      <g className="lane-arrows" markerEnd="url(#arrow)">
        <path d="M 1650 170 H 950"/><path d="M 790 170 H 90"/>
        <path d="M 1650 520 H 1688 Q 1715 520 1715 493 V 197 Q 1715 170 1688 170 H 1650"/>
        <path d="M 90 520 H 790"/><path d="M 950 520 H 1650"/>
      </g>
      {floor.floor_code==='F1'&&<g className="map-gates">
        <g className="map-gate exit"><rect x="36" y="126" width="145" height="30" rx="7"/><text x="108" y="146">ทางออก · EXIT</text></g>
        <g className="map-gate entrance"><rect x="36" y="538" width="145" height="30" rx="7"/><text x="108" y="558">ทางเข้า · ENTRY</text></g>
      </g>}
      <g className="map-labels">
        <text x="870" y="35">ZONE D · NORTH DECK</text><text x="870" y="682">ZONE E · SOUTH DECK</text>
        <text x="210" y="222">ZONE A</text><text x="845" y="222">ZONE B</text><text x="1485" y="222">ZONE C</text>
        <text className="lane-label" x="870" y="174">ONE WAY · DRIVE LANE</text><text className="lane-label" x="870" y="524">ONE WAY · DRIVE LANE</text>
      </g>
      <g className="ramp up"><rect x="395" y="232" width="130" height="202" rx="13"/><path d="M 433 363 V 326 C 433 287 487 287 487 326 V 350 M 478 338 L 487 350 L 496 338"/><text x="460" y="410">ทางขึ้น · UP</text></g>
      <g className="ramp down"><rect x="1165" y="232" width="130" height="202" rx="13"/><path d="M 1203 363 V 326 C 1203 287 1257 287 1257 326 V 350 M 1248 338 L 1257 350 L 1266 338"/><text x="1230" y="410">ทางลง · DOWN</text></g>
      {floor.zones.flatMap(zone=>zone.spaces.map(space=><g className={`parking-space ${space.effective_status.toLowerCase()} ${selected?.id===space.id?'selected':''}`} transform={`rotate(${space.rotation} ${space.x_position+space.width/2} ${space.y_position+space.height/2})`} onClick={()=>onSelect(space)} onPointerDown={event=>{if(!editable)return;event.currentTarget.setPointerCapture(event.pointerId);const point=svgPoint(event);drag.current={space,dx:point.x-space.x_position,dy:point.y-space.y_position};onSelect(space)}} tabIndex={0} role="button" aria-label={`${space.space_code} ${statusLabel(space.effective_status)}`} onKeyDown={event=>{if(event.key==='Enter'||event.key===' ')onSelect(space)}} key={space.id}>
        <rect x={space.x_position} y={space.y_position} width={space.width} height={space.height} rx="3"><title>{space.space_code} · {statusLabel(space.effective_status)}</title></rect>
        <text x={space.x_position+space.width/2} y={space.y_position+space.height/2} dominantBaseline="central">{space.space_number}</text>
      </g>))}
    </svg>
    <div className="map-legend"><span><i className="available"/>ว่าง</span><span><i className="occupied"/>มีรถจอด</span><span><i className="disabled"/>ปิดใช้งาน</span><span><i className="unknown"/>ไม่ทราบสถานะ</span></div>
  </div>
}

function SpacePanel({space,zone,onUpdate,onClose,busy}:{space:ParkingSpace;zone?:ParkingZone;onUpdate:(changes:Partial<ParkingSpace>)=>void;onClose:()=>void;busy:boolean}){
  return <aside className="space-panel">
    <header><div><p className="eyebrow">PARKING SPACE</p><h3>{space.space_code}</h3></div><button onClick={onClose}><X/></button></header>
    <div className={`space-status ${space.effective_status.toLowerCase()}`}><i/><span>{statusLabel(space.effective_status)}</span><small>{space.operational_status==='ACTIVE'?'พร้อมใช้งาน':'ระงับการใช้งาน'}</small></div>
    <dl><div><dt>ชั้น / โซน</dt><dd>{space.space_code.split('-')[0]} · Zone {zone?.zone_code}</dd></div><div><dt>ประเภท</dt><dd>{space.space_type}</dd></div><div><dt>แหล่งข้อมูล</dt><dd>MANUAL</dd></div><div><dt>อัปเดตล่าสุด</dt><dd>{new Date(space.updated_at).toLocaleString('th-TH')}</dd></div></dl>
    <div className="status-actions">
      <p>เปลี่ยนสถานะการจอด</p>
      <button disabled={busy||space.occupancy_status==='AVAILABLE'} onClick={()=>onUpdate({occupancy_status:'AVAILABLE'})}><i className="available"/>ตั้งเป็นว่าง</button>
      <button disabled={busy||space.occupancy_status==='OCCUPIED'} onClick={()=>onUpdate({occupancy_status:'OCCUPIED'})}><i className="occupied"/>มีรถจอด</button>
      <button disabled={busy} onClick={()=>onUpdate({operational_status:space.operational_status==='ACTIVE'?'OUT_OF_SERVICE':'ACTIVE'})}><i className="disabled"/>{space.operational_status==='ACTIVE'?'ปิดใช้งานช่อง':'เปิดใช้งานช่อง'}</button>
    </div>
  </aside>
}

function ZoneCards({zones}:{zones:ParkingZone[]}){
  return <div className="zone-cards">{zones.map(zone=>{const stats=calculateZoneStats(zone.spaces);return <article key={zone.id}><header><span>ZONE {zone.zone_code}</span><b>{stats.available}<small> ว่าง</small></b></header><div className="zone-progress"><i style={{width:`${stats.occupancyRate}%`}}/></div><footer><span>{stats.total} ช่อง</span><span>{stats.occupied} ใช้งาน</span><strong>{stats.occupancyRate}%</strong></footer></article>})}</div>
}

function FloorMonitor({floor,floors,selectedFloor,onSelect,onExit}:{floor:FloorMap|null;floors:FloorSummary[];selectedFloor:number;onSelect:(id:number)=>void;onExit:()=>void}){
  const zones=(floor?.zones||[]).map(zone=>({zone,stats:calculateZoneStats(zone.spaces)}))
  const available=zones.reduce((sum,item)=>sum+item.stats.available,0)
  const total=zones.reduce((sum,item)=>sum+item.stats.total,0)
  return <main className="monitor-board">
    <header className="monitor-header">
      <div><p className="eyebrow">SMART PARKING · LIVE FLOOR DISPLAY</p><h1>{floor?.floor_name||'กำลังโหลดข้อมูลชั้น...'}</h1><p>จำนวนช่องว่างแยกตามโซน · อัปเดตสถานะอัตโนมัติ</p></div>
      <div className="monitor-tools"><span className="monitor-live"><i/> LIVE</span><button onClick={onExit}><X size={18}/> กลับหน้าควบคุม</button></div>
    </header>
    <nav className="monitor-floor-tabs" aria-label="เลือกชั้น">{floors.map(item=><button className={item.id===selectedFloor?'selected':''} onClick={()=>onSelect(item.id)} key={item.id}><span>{item.floor_code}</span><small>{item.floor_name}</small></button>)}</nav>
    <section className="monitor-total"><div><span>ช่องว่างทั้งหมด · {floor?.floor_name||'ชั้น'}</span><small>รวมทุกโซน</small></div><strong>{available}</strong><b>/ {total} ช่อง</b></section>
    <section className="monitor-zones" aria-label="จำนวนช่องว่างแยกตามโซน">
      {zones.map(({zone,stats})=><article className="monitor-zone" key={zone.id}>
        <header><span>ZONE</span><b>{zone.zone_code}</b></header>
        <div className="monitor-open-count">{stats.available}</div>
        <p>ช่องว่าง</p>
        <div className="monitor-capacity"><span>จากทั้งหมด</span><b>{stats.total}</b><span>ช่อง</span></div>
        <div className="monitor-availability"><i style={{width:`${stats.available/Math.max(1,stats.total)*100}%`}}/></div>
        <small>{stats.occupied} ใช้งาน · {stats.disabled} ปิดปรับปรุง</small>
      </article>)}
      {!floor&&<div className="monitor-loading">กำลังโหลดสถานะช่องจอด...</div>}
    </section>
    <footer className="monitor-footer"><span><i/> ข้อมูลสดจากระบบจัดการช่องจอด</span><span>SMART PARKING · {floor?.floor_code||'—'}</span></footer>
  </main>
}

function AvailableView({floor,selectSpace}:{floor:FloorMap|null;selectSpace:(space:ParkingSpace)=>void}){
  const [query,setQuery]=useState('')
  const [zone,setZone]=useState('ALL')
  const spaces=useMemo(()=>floor?.zones.flatMap(item=>item.spaces.map(space=>({space,zone:item.zone_code})))||[],[floor])
  const filtered=spaces.filter(item=>item.space.effective_status==='AVAILABLE'&&(zone==='ALL'||item.zone===zone)&&item.space.space_code.toLowerCase().includes(query.toLowerCase()))
  return <section className="content-page"><div className="section-head"><div><p className="eyebrow">AVAILABLE SPACE FINDER</p><h2>ค้นหาช่องจอดที่ว่าง</h2><p>เลือกผลลัพธ์เพื่อไฮไลต์ตำแหน่งบนแผนผัง</p></div><span className="result-count">{filtered.length} ช่อง</span></div><div className="filters"><label><Search size={17}/><input placeholder="ค้นหา เช่น F3-A04" value={query} onChange={e=>setQuery(e.target.value)}/></label><select value={zone} onChange={e=>setZone(e.target.value)}><option value="ALL">ทุกโซน</option>{['A','B','C','D','E'].map(x=><option value={x} key={x}>Zone {x}</option>)}</select></div><div className="available-grid">{filtered.map(({space,zone})=><button onClick={()=>selectSpace(space)} key={space.id}><span><i/>{space.space_code}</span><small>Zone {zone} · {space.space_type}</small><ChevronRight size={16}/></button>)}</div></section>
}

function EventsView({events}:{events:ParkingEvent[]}){
  return <section className="content-page"><div className="section-head"><div><p className="eyebrow">TRACEABILITY</p><h2>ประวัติการเปลี่ยนสถานะ</h2><p>ตรวจสอบช่อง เวลา แหล่งข้อมูล และสถานะก่อนหลัง</p></div><History/></div><div className="event-table"><div className="table-head"><span>เวลา</span><span>ช่องจอด</span><span>การเปลี่ยนแปลง</span><span>แหล่งข้อมูล</span></div>{events.map(event=><article key={event.id}><time>{new Date(event.event_at).toLocaleString('th-TH')}</time><b>{event.space_code}</b><span><i className={event.old_status.toLowerCase()}/>{event.old_status}<ChevronRight size={13}/><i className={event.new_status.toLowerCase()}/>{event.new_status}</span><small>{event.event_source}</small></article>)}{!events.length&&<div className="empty-state">ยังไม่มีประวัติการเปลี่ยนสถานะ</div>}</div></section>
}

function Dashboard(){
  const [view,setView]=useState<View>('overview')
  const [menuOpen,setMenuOpen]=useState(false)
  const [floorId,setFloorId]=useState(0)
  const [selected,setSelected]=useState<ParkingSpace|null>(null)
  const [busy,setBusy]=useState(false)
  const [revision,setRevision]=useState(0)
  const {data:summary,error:summaryError,load:loadSummary}=useData('/dashboard/summary',emptySummary,revision)
  const effectiveFloor=floorId||summary.floors[0]?.id||0
  const {data:floor,error:floorError,load:loadFloor}=useData<FloorMap|null>(effectiveFloor?`/floors/${effectiveFloor}/map`:'/floors/0/map',null,revision)
  const {data:events,load:loadEvents}=useData<ParkingEvent[]>('/events?limit=40',[],revision)
  useEffect(()=>{if(!floorId&&summary.floors.length)setFloorId(summary.floors[0].id)},[summary.floors,floorId])
  useEffect(()=>{
    let socket:WebSocket|undefined
    let retry:number|undefined
    const connect=()=>{socket=new WebSocket(wsUrl());socket.onmessage=()=>setRevision(value=>value+1);socket.onclose=()=>{retry=window.setTimeout(connect,2500)}}
    connect();return()=>{if(retry)clearTimeout(retry);socket?.close()}
  },[])
  const zone=selected?floor?.zones.find(zone=>zone.spaces.some(space=>space.id===selected.id)):undefined
  async function updateSpace(changes:Partial<ParkingSpace>){
    if(!selected)return
    setBusy(true)
    try{
      const next=await api<ParkingSpace>(`/spaces/${selected.id}/status`,{method:'POST',body:JSON.stringify({occupancy_status:changes.occupancy_status,operational_status:changes.operational_status,version:selected.version})})
      setSelected(next);await Promise.all([loadFloor(),loadSummary(),loadEvents()])
    }catch(error){alert((error as Error).message);await loadFloor()}finally{setBusy(false)}
  }
  function chooseSpace(space:ParkingSpace){setSelected(space);if(view==='available')setView('map')}
  if(view==='monitor')return <FloorMonitor floor={floor} floors={summary.floors} selectedFloor={effectiveFloor} onSelect={id=>{setFloorId(id);setSelected(null)}} onExit={()=>setView('overview')}/>
  return <div className="app-shell">
    <Sidebar view={view} setView={setView} open={menuOpen} setOpen={setMenuOpen} onLogout={()=>{localStorage.removeItem('parking_token');location.reload()}}/>
    <main className="main-area">
      <header className="topbar"><button className="menu-button" onClick={()=>setMenuOpen(true)}><Menu/></button><div><h1>Smart Parking</h1><p>Parking operations · digital twin control</p></div><div className="top-status"><span><Wifi size={15}/> LIVE</span><div className="avatar">AD</div></div></header>
      <div className="workspace">
        {(summaryError||floorError)&&<div className="error-box">{summaryError||floorError}</div>}
        {view==='events'?<EventsView events={events}/>:view==='available'?<><FloorSelector floors={summary.floors} selected={effectiveFloor} onSelect={id=>{setFloorId(id);setSelected(null)}}/><AvailableView floor={floor} selectSpace={chooseSpace}/></>:<>
          <div className="page-title"><div><p className="eyebrow">OPERATIONS OVERVIEW</p><h2>{view==='overview'?'สถานะอาคารจอดรถ':'แผนผังช่องจอดแบบเรียลไทม์'}</h2><p>ภาพรวม {summary.building_name} · อัปเดตสถานะจากช่องจอดจริง</p></div><span className="mode-pill"><ShieldCheck size={15}/> MANUAL MODE</span></div>
          {view==='overview'&&<><div className="metrics-grid"><Metric label="ช่องจอดทั้งหมด" value={summary.total.toLocaleString()} detail="4 ชั้น · 5 โซนต่อชั้น" tone="teal" icon={ParkingCircle}/><Metric label="พร้อมใช้งาน" value={summary.available.toLocaleString()} detail={`${Math.round(summary.available/Math.max(1,summary.total)*100)}% ของพื้นที่ทั้งหมด`} tone="green" icon={Car}/><Metric label="มีรถจอด" value={summary.occupied.toLocaleString()} detail={`Occupancy ${summary.occupancy_rate}%`} tone="amber" icon={Activity}/><Metric label="ปิดใช้งาน" value={summary.disabled.toLocaleString()} detail="ไม่นับเป็นช่องว่าง" tone="gray" icon={Settings2}/></div><div className="operation-strip"><div><span>สถานะระบบ</span><b><i/> Online</b></div><div><span>อาคาร</span><b>1</b></div><div><span>จำนวนชั้น</span><b>4</b></div><div><span>จำนวนโซน</span><b>20</b></div><div><span>Event Source</span><b>MANUAL</b></div></div></>}
          <FloorSelector floors={summary.floors} selected={effectiveFloor} onSelect={id=>{setFloorId(id);setSelected(null)}}/>
          <section className="digital-twin"><header><div><p className="eyebrow">PARKING DIGITAL TWIN</p><h3>{floor?.floor_name||'Floor'} · Live Parking Map</h3><span>คลิกช่องจอดเพื่อดูรายละเอียดและเปลี่ยนสถานะ</span></div><div className="live-badge"><i/> LIVE <b>{floor?.zones.flatMap(z=>z.spaces).filter(s=>s.effective_status==='OCCUPIED').length||0} OCCUPIED</b></div></header><div className="map-layout"><ParkingMapView floor={floor} selected={selected} onSelect={setSelected}/>{selected&&<SpacePanel space={selected} zone={zone} onUpdate={updateSpace} onClose={()=>setSelected(null)} busy={busy}/>}</div></section>
          <ZoneCards zones={floor?.zones||[]}/>
          {view==='overview'&&<section className="activity-panel"><div><p className="eyebrow">RECENT ACTIVITY</p><h3>รายการเปลี่ยนสถานะล่าสุด</h3></div><div>{events.slice(0,5).map(event=><article key={event.id}><i className={event.new_status.toLowerCase()}/><span><b>{event.space_code}</b><small>{event.old_status} → {event.new_status}</small></span><time><Clock3 size={13}/>{new Date(event.event_at).toLocaleTimeString('th-TH',{hour:'2-digit',minute:'2-digit'})}</time></article>)}{!events.length&&<p className="empty-state">ยังไม่มีรายการเปลี่ยนสถานะ</p>}</div></section>}
        </>}
      </div>
    </main>
  </div>
}

export default function App(){
  const [authenticated,setAuthenticated]=useState(Boolean(token()))
  useEffect(()=>{const expired=()=>setAuthenticated(false);window.addEventListener('parking-auth-expired',expired);return()=>window.removeEventListener('parking-auth-expired',expired)},[])
  return authenticated?<Dashboard/>:<Login onLogin={()=>setAuthenticated(true)}/>
}
