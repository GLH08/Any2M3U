export interface SourceOut {
  id: number
  name: string
  type: 'local' | 'webdav'
  config: any
  group_by_dir: boolean
  refresh_cron: string | null
  enabled: boolean
  last_scan_at: string | null
  last_scan_status: string | null
  last_error: string | null
  created_at: string
}

export interface RuleOut {
  id: number
  source_id: number
  name: string
  include_exts: string | null
  exclude_keywords: string | null
  include_paths: string | null
  group_title: string
  tpl: string
  logo_dir: string
  enabled: boolean
  created_at: string
}
