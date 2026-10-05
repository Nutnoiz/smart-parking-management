const base=import.meta.env.VITE_API_URL||'/api'

export function token(){return localStorage.getItem('parking_token')||''}

export async function api<T>(path:string,init:RequestInit={}):Promise<T>{
  const response=await fetch(`${base}${path}`,{
    ...init,
    headers:{'Content-Type':'application/json',...(token()?{Authorization:`Bearer ${token()}`} :{}),...(init.headers||{})},
  })
  if(response.status===401){localStorage.removeItem('parking_token');window.dispatchEvent(new Event('parking-auth-expired'))}
  if(!response.ok){const payload=await response.json().catch(()=>({detail:'ไม่สามารถเชื่อมต่อระบบได้'}));throw new Error(payload.detail||'Request failed')}
  return response.json()
}

export function wsUrl(){
  const explicit=import.meta.env.VITE_WS_URL
  if(explicit)return `${explicit}?token=${encodeURIComponent(token())}`
  const protocol=location.protocol==='https:'?'wss:':'ws:'
  return `${protocol}//${location.host}/api/ws?token=${encodeURIComponent(token())}`
}

