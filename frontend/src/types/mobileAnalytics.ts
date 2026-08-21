export interface MobileZone {
  zoneId: string
  name: string
  revenue: number
  utilization: number
}

export interface MobileSession {
  id: string
  seatName: string
  zoneName: string
  memberName?: string
  startTime: string
  duration: number
  status: 'IN_USE' | 'PAUSED'
}

export interface MobileShiftSummary {
  revenue: number
  sessions: number
  avgDuration: number
}

export interface MobileAnalytics {
  revenueToday: number
  activeSessions: number
  shiftSummary: MobileShiftSummary
  topZones: MobileZone[]
  activeSessionsList: MobileSession[]
}
