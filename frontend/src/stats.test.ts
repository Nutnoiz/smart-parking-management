import {describe,expect,it} from 'vitest'
import {calculateZoneStats} from './stats'
import type {ParkingSpace} from './types'

function space(id:number,effective_status:ParkingSpace['effective_status']):ParkingSpace{
  return{id,space_code:`F1-A0${id}`,space_number:id,space_type:'STANDARD',occupancy_status:effective_status==='OCCUPIED'?'OCCUPIED':'AVAILABLE',operational_status:effective_status==='DISABLED'?'OUT_OF_SERVICE':'ACTIVE',effective_status,x_position:0,y_position:0,width:20,height:40,rotation:0,version:1,is_active:true,updated_at:'2026-10-05T00:00:00Z'}
}

describe('calculateZoneStats',()=>{
  it('excludes disabled spaces from occupancy rate capacity',()=>{
    const result=calculateZoneStats([space(1,'AVAILABLE'),space(2,'OCCUPIED'),space(3,'DISABLED')])
    expect(result).toEqual({total:3,available:1,occupied:1,disabled:1,occupancyRate:50})
  })
})

