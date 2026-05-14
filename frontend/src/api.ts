// Typed client for POST /campaign.
//
// Types mirror `backend/app/models.py:CampaignResult` exactly. If the backend
// schema changes, update both. Kept hand-written (instead of generated) because
// the surface is small and the structure is the same thing the UI renders.

const API_BASE =
  (import.meta.env.VITE_API_BASE as string | undefined) ?? 'http://localhost:8000'

export type UsdRange = { low: number; high: number }

export type RankedPublisher = {
  publisher_id: string
  name: string
  rank: number
  fit_score: number
  rationale: string
}

export type ExcludedPublisher = {
  publisher_id: string
  name: string
  reason: string
}

export type Persona = {
  persona_id: string
  name: string
  selection_reasoning: string
}

export type Creative = {
  persona_id: string
  persona_name: string
  persona_reasoning: string
  headline: string
  body: string
  call_to_action: string
}

export type TargetingConfig = {
  age_range: string
  geos: string[]
  interests: string[]
}

export type PublisherAllocation = {
  publisher_id: string
  name: string
  percent: number
  suggested_daily_usd: UsdRange
}

export type BudgetConfig = {
  suggested_daily_usd: UsdRange
  suggested_flight_days: number
}

export type BidStrategy = {
  model: 'CPM' | 'CPC' | 'CPA'
  suggested_range_usd: UsdRange
  rationale: string
}

export type CampaignConfig = {
  targeting: TargetingConfig
  publisher_allocation: PublisherAllocation[]
  budget: BudgetConfig
  bid_strategy: BidStrategy
}

export type CampaignResult = {
  advertiser_brief: string
  ranked_publishers: RankedPublisher[]
  excluded_publishers: ExcludedPublisher[]
  selected_personas: Persona[]
  creatives: Creative[]
  campaign_config: CampaignConfig
}

export async function runCampaign(brief: string): Promise<CampaignResult> {
  const res = await fetch(`${API_BASE}/campaign`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ advertiser_brief: brief }),
  })
  if (!res.ok) {
    let detail = `HTTP ${res.status}`
    try {
      const body = (await res.json()) as { detail?: string }
      if (body?.detail) detail = body.detail
    } catch {
      // body wasn't JSON; keep the HTTP status
    }
    throw new Error(detail)
  }
  return (await res.json()) as CampaignResult
}
