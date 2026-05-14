import { useState } from 'react'
import {
  runCampaign,
  type CampaignResult,
  type Creative,
  type ExcludedPublisher,
  type Persona,
  type RankedPublisher,
  type CampaignConfig,
  type PublisherAllocation,
  type UsdRange,
} from './api'
import './App.css'

const EXAMPLES: string[] = [
  'We sell premium dog food for senior dogs, targeting owners who care about joint health and longevity. Grain-free, vet-formulated, subscription-based.',
  'A sustainable activewear brand for women. Made from recycled ocean plastic. Price point sits between Lululemon and Girlfriend Collective.',
  'Technical outerwear for serious backcountry skiers. Our shells are what patrollers wear. Starts at $650, goes up from there.',
  'Refillable, concentrated cleaning products. Skip the single-use plastic bottles. Works as well as the big brands.',
]

function App() {
  const [brief, setBrief] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<CampaignResult | null>(null)

  const canRun = brief.trim().length >= 3 && !loading

  async function handleRun() {
    if (!canRun) return
    setLoading(true)
    setError(null)
    try {
      const data = await runCampaign(brief.trim())
      setResult(data)
    } catch (e) {
      setResult(null)
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="app">
      <header className="app-header">
        <h1>Ad placement prototype</h1>
        <p className="subtitle">
          One sentence in. Ranked publishers, target personas, ad creatives, and a campaign
          config out.
        </p>
      </header>

      <section className="input-card">
        <label htmlFor="brief" className="label">
          Advertiser brief
        </label>
        <textarea
          id="brief"
          className="brief"
          placeholder="e.g. We make small-batch soy candles, hand-poured in Vermont. No synthetic fragrances. Mostly bought as gifts."
          value={brief}
          onChange={(e) => setBrief(e.target.value)}
          rows={4}
          disabled={loading}
        />
        <div className="input-row">
          <div className="examples">
            <span className="examples-label">Try:</span>
            {EXAMPLES.map((ex, i) => (
              <button
                key={i}
                type="button"
                className="example-chip"
                onClick={() => setBrief(ex)}
                disabled={loading}
                title={ex}
              >
                Example {i + 1}
              </button>
            ))}
          </div>
          <button
            type="button"
            className="run"
            onClick={handleRun}
            disabled={!canRun}
          >
            {loading ? 'Planning…' : 'Run'}
          </button>
        </div>
        {error && <div className="error">Error: {error}</div>}
        {loading && (
          <div className="hint">
            Calling the planner, then the copywriter. Usually 10–25 seconds.
          </div>
        )}
      </section>

      {result && <Results result={result} />}

      {!result && !loading && (
        <section className="empty">
          <p>Write a one-liner above and hit Run.</p>
        </section>
      )}
    </div>
  )
}

function Results({ result }: { result: CampaignResult }) {
  return (
    <div className="results">
      <PublishersSection
        ranked={result.ranked_publishers}
        excluded={result.excluded_publishers}
      />
      <PersonasSection personas={result.selected_personas} />
      <CreativesSection creatives={result.creatives} />
      <ConfigSection config={result.campaign_config} />
    </div>
  )
}

function PublishersSection({
  ranked,
  excluded,
}: {
  ranked: RankedPublisher[]
  excluded: ExcludedPublisher[]
}) {
  const sorted = [...ranked].sort((a, b) => a.rank - b.rank)
  return (
    <section className="card">
      <h2>Publishers</h2>
      <p className="card-sub">Ranked by fit, with the planner's rationale.</p>
      <ol className="publisher-list">
        {sorted.map((p) => (
          <li key={p.publisher_id} className="publisher">
            <div className="publisher-head">
              <span className="rank">#{p.rank}</span>
              <span className="pub-name">{p.name}</span>
              <span className="fit" title="Fit score (0.0 – 1.0)">
                fit {p.fit_score.toFixed(2)}
              </span>
              <span className="pub-id">{p.publisher_id}</span>
            </div>
            <p className="rationale">{p.rationale}</p>
          </li>
        ))}
      </ol>

      {excluded.length > 0 && (
        <details className="excluded" open>
          <summary>
            Considered &amp; excluded ({excluded.length})
          </summary>
          <ul className="excluded-list">
            {excluded.map((p) => (
              <li key={p.publisher_id}>
                <span className="pub-name">{p.name}</span>
                <span className="pub-id">{p.publisher_id}</span>
                <span className="reason">— {p.reason}</span>
              </li>
            ))}
          </ul>
        </details>
      )}
    </section>
  )
}

function PersonasSection({ personas }: { personas: Persona[] }) {
  return (
    <section className="card">
      <h2>Personas</h2>
      <p className="card-sub">
        {personas.length} personas the planner chose, with the reason for each.
      </p>
      <ul className="persona-list">
        {personas.map((p) => (
          <li key={p.persona_id} className="persona">
            <div className="persona-head">
              <span className="persona-name">{p.name}</span>
              <span className="persona-id">{p.persona_id}</span>
            </div>
            <p className="reasoning">{p.selection_reasoning}</p>
          </li>
        ))}
      </ul>
    </section>
  )
}

function CreativesSection({ creatives }: { creatives: Creative[] }) {
  return (
    <section className="card">
      <h2>Creatives</h2>
      <p className="card-sub">One ad variant per persona.</p>
      <div className="creative-grid">
        {creatives.map((c, i) => (
          <article key={`${c.persona_id}-${i}`} className="creative">
            <header className="creative-head">
              <span className="creative-persona">For {c.persona_name}</span>
              <span className="persona-id">{c.persona_id}</span>
            </header>
            <p className="creative-reason">{c.persona_reasoning}</p>
            <h3 className="headline">{c.headline}</h3>
            <p className="body">{c.body}</p>
            {c.call_to_action && (
              <div className="cta-row">
                <span className="cta">{c.call_to_action}</span>
              </div>
            )}
          </article>
        ))}
      </div>
    </section>
  )
}

function fmtMoneyRange(r: UsdRange): string {
  return `$${Math.round(r.low).toLocaleString()} – $${Math.round(r.high).toLocaleString()}`
}

function ConfigSection({ config }: { config: CampaignConfig }) {
  const sortedAllocs: PublisherAllocation[] = [...config.publisher_allocation].sort(
    (a, b) => b.percent - a.percent,
  )
  return (
    <section className="card">
      <h2>Campaign config</h2>
      <p className="card-sub">
        The minimum shape a downstream order-creation system would need.
      </p>

      <div className="config-grid">
        <div className="config-block">
          <h3>Targeting</h3>
          <dl className="kv">
            <dt>Age</dt>
            <dd>{config.targeting.age_range}</dd>
            <dt>Geos</dt>
            <dd>
              {config.targeting.geos.length > 0
                ? config.targeting.geos.join(', ')
                : '—'}
            </dd>
            <dt>Interests</dt>
            <dd className="tags">
              {config.targeting.interests.map((t) => (
                <span key={t} className="tag">
                  {t}
                </span>
              ))}
            </dd>
          </dl>
        </div>

        <div className="config-block">
          <h3>Budget</h3>
          <dl className="kv">
            <dt>Daily</dt>
            <dd>{fmtMoneyRange(config.budget.suggested_daily_usd)}</dd>
            <dt>Flight</dt>
            <dd>{config.budget.suggested_flight_days} days</dd>
          </dl>
        </div>

        <div className="config-block">
          <h3>Bid strategy</h3>
          <dl className="kv">
            <dt>Model</dt>
            <dd>
              <span className="badge">{config.bid_strategy.model}</span>
            </dd>
            <dt>Range</dt>
            <dd>{fmtMoneyRange(config.bid_strategy.suggested_range_usd)}</dd>
            <dt>Why</dt>
            <dd className="rationale-cell">{config.bid_strategy.rationale}</dd>
          </dl>
        </div>
      </div>

      <div className="config-block config-block-wide">
        <h3>Publisher allocation</h3>
        <table className="alloc-table">
          <thead>
            <tr>
              <th>Publisher</th>
              <th>Share</th>
              <th>Daily budget</th>
            </tr>
          </thead>
          <tbody>
            {sortedAllocs.map((a) => (
              <tr key={a.publisher_id}>
                <td>
                  <span className="pub-name">{a.name}</span>
                  <span className="pub-id">{a.publisher_id}</span>
                </td>
                <td className="share-cell">
                  <div className="share-bar">
                    <div
                      className="share-bar-fill"
                      style={{ width: `${Math.min(100, a.percent * 100)}%` }}
                    />
                  </div>
                  <span className="share-pct">{(a.percent * 100).toFixed(0)}%</span>
                </td>
                <td>{fmtMoneyRange(a.suggested_daily_usd)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <details className="raw-json">
        <summary>Raw JSON</summary>
        <pre>{JSON.stringify(config, null, 2)}</pre>
      </details>
    </section>
  )
}

export default App
