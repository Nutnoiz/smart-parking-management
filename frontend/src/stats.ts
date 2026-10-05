import type {ParkingSpace} from './types'

export function calculateZoneStats(spaces:ParkingSpace[]){
  const total=spaces.length
  const available=spaces.filter(space=>space.effective_status==='AVAILABLE').length
  const occupied=spaces.filter(space=>space.effective_status==='OCCUPIED').length
  const disabled=spaces.filter(space=>space.effective_status==='DISABLED').length
  const occupancyRate=Math.round(occupied/Math.max(1,total-disabled)*100)
  return{total,available,occupied,disabled,occupancyRate}
}

