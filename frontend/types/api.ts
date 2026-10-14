/**
 * Shared API types, mirroring the backend Pydantic schemas.
 *
 * These are hand-maintained rather than generated. If the API surface grows,
 * replace this file with `openapi-typescript` output from
 * `http://localhost:8000/openapi.json`.
 */

export type Role = 'admin' | 'buyer' | 'logistics' | 'quality'

export interface Company {
  code: string
  name: string
  currency: string
  locale: string
  default_language: string
  quality_check_required: boolean
  modules_enabled: string[]
}

export interface User {
  id: number
  username: string
  email: string | null
  full_name: string
  role: Role
  is_active: boolean
  companies: { code: string; name: string; currency: string }[]
}

export interface Token {
  access_token: string
  token_type: string
  expires_in: number
  user: User
  active_company: string
}

export interface PageMeta {
  total: number
  limit: number
  offset: number
}

export interface Page<T> {
  items: T[]
  meta: PageMeta
}

export interface Kpi {
  key: 'order_accuracy' | 'picks_per_hour' | 'dock_to_stock' | 'inventory_turnover'
  value: number | null
  unit: string | null
  delta: number | null
}

export interface DashboardSummary {
  company_code: string
  generated_at: string
  kpis: Kpi[]
  open_sales_orders: number
  open_purchase_orders: number
  orders_awaiting_quality: number
  pending_demand_lines: number
  items_below_minimum: number
  inventory_value: number
  routes_today: number
}

export interface Alert {
  severity: 'critical' | 'warning'
  code: string
  message: string
}

export interface StockLevel {
  item_id: number
  code: string
  description: string
  stock: number
  min_stock: number
}

export type SalesOrderStatus =
  | 'OPEN'
  | 'PICKING'
  | 'SHIPPED'
  | 'INVOICED'
  | 'CANCELLED'

export interface SalesOrderLine {
  id: number
  item_id: number
  item_code: string | null
  item_description: string | null
  quantity: number
  unit_price: number
  line_total: number
  qty_picked: number
  qty_shipped: number
}

export interface SalesOrder {
  id: number
  number: string
  customer_id: number
  customer_name: string | null
  order_date: string
  delivery_date: string | null
  status: SalesOrderStatus
  total: number
  notes: string | null
  lines: SalesOrderLine[]
}

export type PurchaseOrderStatus =
  | 'OPEN'
  | 'RECEIVED'
  | 'QC_PENDING'
  | 'QC_APPROVED'
  | 'REJECTED'
  | 'CLOSED'

export interface PurchaseOrderLine {
  id: number
  item_id: number
  item_code: string | null
  item_description: string | null
  quantity: number
  unit_cost: number
  line_total: number
  qty_received: number
  qc_status: 'PENDING' | 'PASSED' | 'FAILED'
}

export interface PurchaseOrder {
  id: number
  vendor_id: number
  vendor_name: string | null
  number: string
  order_date: string
  expected_date: string | null
  status: PurchaseOrderStatus
  total: number
  lines: PurchaseOrderLine[]
}

export interface Item {
  id: number
  code: string
  description: string
  unit: string
  unit_cost: number
  unit_price: number
  stock: number
  min_stock: number
  location: string
  category: string | null
  is_below_minimum: boolean
}

export interface Customer {
  id: number
  code: string
  name: string
  city: string | null
  country: string
}

export interface Vendor {
  id: number
  code: string
  name: string
  lead_time_days: number
  quality_rating: number
}

export interface DemandLine {
  id: number
  item_id: number
  item_code: string | null
  item_description: string | null
  required_date: string
  quantity_needed: number
  source: 'SALES_ORDER' | 'MIN_STOCK' | 'FORECAST'
  action: 'PENDING' | 'ORDERED' | 'IGNORED'
}

export interface Route {
  id: number
  code: string
  carrier: string
  date: string
  status: 'PLANNED' | 'IN_TRANSIT' | 'DELIVERED'
  stops: number
}

export interface ActivityEvent {
  id: number
  occurred_at: string
  actor_username: string
  entity: string
  entity_id: number | null
  action: string
  summary: string | null
  payload: Record<string, unknown> | null
}