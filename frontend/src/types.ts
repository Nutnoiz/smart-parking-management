export type Status='AVAILABLE'|'OCCUPIED'|'UNKNOWN'|'DISABLED'

export interface FloorSummary{
  id:number
  floor_code:string
  floor_name:string
  floor_number:number
  total:number
  available:number
  occupied:number
  disabled:number
  occupancy_rate:number
}

export interface DashboardSummary{
  building_code:string
  building_name:string
  total:number
  available:number
  occupied:number
  disabled:number
  occupancy_rate:number
  floors:FloorSummary[]
}

export interface ParkingSpace{
  id:number
  space_code:string
  space_number:number
  space_type:string
  occupancy_status:'AVAILABLE'|'OCCUPIED'|'UNKNOWN'
  operational_status:'ACTIVE'|'OUT_OF_SERVICE'
  effective_status:Status
  x_position:number
  y_position:number
  width:number
  height:number
  rotation:number
  version:number
  is_active:boolean
  updated_at:string
}

export interface ParkingZone{
  id:number
  zone_code:string
  zone_name:string
  spaces:ParkingSpace[]
}

export interface FloorMap{
  id:number
  floor_code:string
  floor_name:string
  view_box:string
  zones:ParkingZone[]
}

export interface ParkingEvent{
  id:number
  space_code:string
  old_status:Status
  new_status:Status
  event_source:string
  event_at:string
  note?:string
}

