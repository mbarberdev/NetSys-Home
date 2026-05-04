export type Action = 'block' | 'isolate' | 'guest_network' | 'schedule_block'

export interface Device {
  id: number
  name: string
  type: string
  mac: string
  ip?: string | null
}

export interface Policy {
  id: number
  type: string
  rule: string
  device_id: number
  action: string
  created_at: string
}

export interface Classification {
  predicted_action: Action
  confidence: number | null
  model: string | null
}

export interface IntentResponse extends Policy {
  enforced: boolean
  classification?: Classification
}

export interface ClassifyResponse extends Classification {
  text: string
}

export interface AppStatus {
  openwrt: 'connected' | 'disconnected' | string
  version: string | null
  hostname: string | null
  model: string | null
  app_version: string
  classifier: string
}

export const ACTION_LABELS: Record<Action, string> = {
  block: 'Block device',
  isolate: 'Isolate device',
  guest_network: 'Create guest network',
  schedule_block: 'Schedule block',
}

export const ACTION_DESCRIPTIONS: Record<Action, string> = {
  block: 'Cut all internet access for the selected device.',
  isolate: 'Keep internet access but block LAN peer-to-peer traffic.',
  guest_network: 'Spin up an isolated 10.10.10.0/24 SSID for visitors.',
  schedule_block: 'Block the device every day after the chosen time, restore at 06:00.',
}
