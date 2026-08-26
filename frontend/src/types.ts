export type Money = string;

export interface DashboardSummary {
  total_spend: Money;
  total_orders: number;
  average_order_value: Money;
  supplier_count: number;
  category_count: number;
  business_unit_count: number;
}

export interface SupplierAnalytics {
  supplier_id: string;
  supplier_name: string;
  country: string;
  spend: Money;
  share_percent: Money;
  transaction_count: number;
  average_order_value: Money;
  total_quantity: Money;
  rank: number;
}

export interface CategoryAnalytics {
  category_id: number;
  category_name: string;
  spend: Money;
  share_percent: Money;
  transaction_count: number;
  average_order_value: Money;
  supplier_count: number;
}

export interface BusinessUnitAnalytics {
  business_unit_id: number;
  business_unit_name: string;
  spend: Money;
  share_percent: Money;
  transaction_count: number;
}

export interface MonthlyAnalytics {
  month: string;
  spend: Money;
  transaction_count: number;
  average_order_value: Money;
  growth_percent: Money | null;
}

export interface SupplierConcentration {
  total_spend: Money;
  supplier_count: number;
  top_5_spend: Money;
  top_5_concentration_percent: Money;
  top_10_spend: Money;
  top_10_concentration_percent: Money;
}

export interface ContractAnalytics {
  total_spend: Money;
  total_orders: number;
  on_contract_spend: Money;
  off_contract_spend: Money;
  on_contract_percent: Money;
  off_contract_percent: Money;
  on_contract_order_count: number;
  off_contract_order_count: number;
}

export interface SupplierRecord {
  supplier_id: string;
  supplier_name: string;
  country: string;
}

export interface CategoryRecord {
  category_id: number;
  category_name: string;
  item_count: number;
  total_spend: Money;
}

export interface BusinessUnitRecord {
  business_unit_id: number;
  business_unit_name: string;
  transaction_count: number;
  total_spend: Money;
}

export interface Paginated<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export type OpportunityType =
  | "PRICE_OPTIMIZATION"
  | "CONTRACT_LEAKAGE"
  | "SUPPLIER_CONSOLIDATION"
  | "SUPPLIER_PERFORMANCE";

export interface Opportunity {
  opportunity_id: number;
  opportunity_type: OpportunityType;
  item_id: number;
  item_name: string;
  category_id: number;
  category_name: string;
  supplier_id: string | null;
  supplier_name: string | null;
  actual_price: Money | null;
  benchmark_price: Money | null;
  price_variance_percent: Money | null;
  quantity: Money | null;
  estimated_savings: Money;
  review_spend: Money;
  confidence_score: Money;
  priority_score: Money;
  priority_level: "CRITICAL" | "HIGH" | "MEDIUM" | "LOW";
  status: string;
  supporting_metrics: Record<string, unknown>;
  created_at: string;
}

export interface OpportunitySummary {
  active_opportunity_count: number;
  estimated_price_optimization_savings: Money;
  review_spend: Money;
  critical_count: number;
  high_priority_count: number;
  price_optimization_count: number;
  contract_leakage_count: number;
  supplier_consolidation_count: number;
  supplier_performance_count: number;
  savings_note: string;
}

export interface Recommendation {
  recommendation_id: number;
  opportunity_id: number;
  opportunity_type: OpportunityType;
  item_name: string;
  supplier_name: string | null;
  title: string;
  summary: string;
  reasoning: string;
  recommended_action: string;
  estimated_impact: Money;
  risks: string | null;
  next_steps: string[];
  confidence_score: Money;
  model_name: string;
  prompt_version: string;
  created_at: string;
}

