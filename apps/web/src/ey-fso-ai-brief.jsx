import { useState } from "react";
import {
  BookOpen,
  Share2,
  FlaskConical,
  Eye,
  ChevronRight,
  Star,
  ExternalLink,
  ArrowRight,
  Filter,
  Activity,
  Code2,
  TrendingUp,
  Database,
  Layers,
  Sparkles,
  Inbox,
  Search,
  FileCode,
  CheckCircle,
  Users,
  Building2,
} from "lucide-react";
import pipelineData from "../../../data/output.json";

/* ------------------------------------------------------------------ */
/*  Mock data — week 18 / 2026                                         */
/* ------------------------------------------------------------------ */

const ACTION_ITEMS = pipelineData.actionItems ?? [
  {
    priority: "READ",
    title: "Hierarchical Reasoning for Multi-Asset Portfolio Optimization",
    source: "Stanford AI Lab × JPM Asset Mgmt",
    sourceMeta: "arXiv 2604.18432 · 38 pp",
    date: "Apr 29",
    why:
      "First production-grade benchmark showing tree-search reasoning beats traditional RL on multi-period rebalancing. Direct relevance to discretionary mandates and the robo-advisory book.",
    tags: ["WAM", "Capital Markets"],
    score: 87,
    fsoRelevant: true,
  },
  {
    priority: "EXPERIMENT",
    title: "Claude Sonnet 4.6 ships native tool-graph orchestration",
    source: "Anthropic Engineering",
    sourceMeta: "Release notes · API GA",
    date: "May 1",
    why:
      "Removes most LangGraph / LlamaIndex glue for typical agent workflows. Drop-in replacement could cut our pipeline LOC by ~40% and eliminate a class of orchestration bugs.",
    tags: ["All Verticals"],
    score: 92,
    fsoRelevant: true,
  },
  {
    priority: "SHARE",
    title: "Generative AI in Wealth Management — 2026 State of the Industry",
    source: "BCG · Financial Services Insights",
    sourceMeta: "62 pp report",
    date: "Apr 27",
    why:
      "Useful client-facing material. 73% of UHNW advisors now use AI assistants for prep; competitive pressure on tier-2 RIAs is intensifying. Solid third-party validation slide.",
    tags: ["WAM"],
    score: 78,
    fsoRelevant: true,
  },
  {
    priority: "WATCH",
    title: "Test-time-compute scaling laws for actuarial reserving",
    source: "Lemonade Research × Caltech",
    sourceMeta: "Working paper · pre-print",
    date: "May 2",
    why:
      "Early signal that o-series-style reasoning models materially improve loss-triangle projections. Worth monitoring for the Insurance practice; not yet production-ready.",
    tags: ["Insurance"],
    score: 69,
    fsoRelevant: true,
  },
];

const REPOS = pipelineData.repos ?? [
  {
    name: "anthropics/claude-agent-sdk",
    stars: "18.4k",
    delta: "+1,247",
    desc: "Build agents with Claude — TS + Python",
    url: "https://github.com/anthropics/claude-agent-sdk",
    language: "Python",
    bullets: [
      "Provides SDK primitives for building Claude-powered agents.",
      "Includes tool-use patterns for TypeScript and Python apps.",
      "Useful when teams need a compact agent runtime to inspect.",
    ],
  },
  {
    name: "modal-labs/modal-llm-stack",
    stars: "9.8k",
    delta: "+612",
    desc: "Reference patterns for serverless inference",
    url: "https://github.com/modal-labs/modal-llm-stack",
    language: "Python",
    bullets: [
      "Shows deployment patterns for serverless LLM workloads.",
      "Covers inference-oriented application structure.",
      "Helpful for teams comparing hosted GPU execution options.",
    ],
  },
  {
    name: "observerlabs/finbench-2026",
    stars: "4.3k",
    delta: "+488",
    desc: "Open evals — 10-K, MD&A, earnings calls",
    url: "https://github.com/observerlabs/finbench-2026",
    language: "Python",
    bullets: [
      "Focuses on finance-domain model evaluation tasks.",
      "Includes benchmark patterns for filings and earnings material.",
      "Relevant for FSO teams designing model risk tests.",
    ],
  },
  {
    name: "deepmind/jax-agents",
    stars: "7.2k",
    delta: "+401",
    desc: "Multi-agent RL primitives in JAX",
    url: "https://github.com/deepmind/jax-agents",
    language: "JAX",
    bullets: [
      "Provides JAX primitives for multi-agent experiments.",
      "Useful for simulation and reinforcement-learning workflows.",
      "Worth watching for agent evaluation research patterns.",
    ],
  },
  {
    name: "meta-llama/llama-cookbook",
    stars: "31.2k",
    delta: "+287",
    desc: "Recipes for fine-tuning Llama 4",
    url: "https://github.com/meta-llama/llama-cookbook",
    language: "Python",
    bullets: [
      "Collects practical recipes for Llama model usage.",
      "Covers fine-tuning, inference, and app-building workflows.",
      "Good reference material for open-model experimentation.",
    ],
  },
];

const MODELS = pipelineData.models ?? [
  {
    name: "Claude Sonnet 4.6",
    org: "Anthropic",
    date: "May 1",
    note: "Native tool-graph · +12pp SWE-bench",
    tag: "API",
  },
  {
    name: "Llama 4 405B Instruct",
    org: "Meta",
    date: "Apr 30",
    note: "Open weights · 256k context window",
    tag: "OPEN",
  },
  {
    name: "GPT-5.5 Turbo",
    org: "OpenAI",
    date: "Apr 28",
    note: "API-only · reasoning_effort param",
    tag: "API",
  },
];

const TOOLS_SERVICES = pipelineData.toolsServices ?? [
  {
    name: "Claude Code",
    org: "Anthropic",
    date: "May 2",
    note: "Terminal-native AI coding agent with multi-file editing & git integration",
    tag: "CLI",
  },
  {
    name: "Codex",
    org: "OpenAI",
    date: "May 1",
    note: "Cloud-based coding agent — async task execution in sandboxed environments",
    tag: "CLOUD",
  },
  {
    name: "GitHub Copilot Agent Mode",
    org: "Microsoft",
    date: "Apr 29",
    note: "Autonomous multi-step coding within VS Code — terminal & file access",
    tag: "IDE",
  },
  {
    name: "Meta AI Studio",
    org: "Meta",
    date: "Apr 28",
    note: "Custom AI character builder with Llama 4 backbone — API & web",
    tag: "PLATFORM",
  },
  {
    name: "Azure AI Agent Service",
    org: "Microsoft",
    date: "Apr 26",
    note: "Managed agent orchestration — tool use, memory, multi-turn on Azure",
    tag: "CLOUD",
  },
  {
    name: "Google Jules",
    org: "Google",
    date: "Apr 25",
    note: "Async AI coding agent for GitHub — background PR generation",
    tag: "CLOUD",
  },
];

const PAPERS = pipelineData.papers ?? [
  {
    title: "Hierarchical Reasoning for Multi-Asset Portfolio Optimization",
    authors: "K. Tanaka, M. Rodriguez, F. Esposito, et al.",
    org: "Stanford AI Lab · JPM Asset Mgmt",
    date: "Apr 29, 2026",
    hasCode: true,
    stars: 312,
    score: 87,
    verticals: ["WAM", "Capital Markets"],
    fsoRelevant: true,
    abstract:
      "We introduce HR-PO, a hierarchical tree-search method for multi-period portfolio optimization that decouples strategic asset allocation from tactical rebalancing. On a 10-year backtest across 47 mandates, HR-PO outperforms Markowitz mean-variance by 142 bps annualized while respecting transaction-cost and drawdown constraints. Ablations show the hierarchy — not the search budget — drives most of the gain.",
    takeaways: [
      "Tree-search reasoning outperforms traditional RL on multi-period rebalancing by 142 bps annualized",
      "Hierarchy structure matters more than compute budget for portfolio optimization",
      "Directly applicable to discretionary mandates and robo-advisory workflows",
      "Production-grade benchmark validated on 47 real mandates over 10 years",
    ],
    relevance: { wam: "Critical", cm: "High", ins: "Low", risk: "Medium" },
  },
  {
    title: "Claim Triage with Sparse Mixture-of-Experts: A Production Deployment",
    authors: "S. Chen, A. Patel, R. Voss",
    org: "Lemonade Research",
    date: "Apr 25, 2026",
    hasCode: true,
    stars: 89,
    score: 71,
    verticals: ["Insurance"],
    fsoRelevant: true,
    abstract:
      "We deploy a 32-expert sparse MoE for first-notice-of-loss triage across auto, home, and pet lines. Latency is equivalent to a 7B dense baseline while matching a 70B model on triage accuracy; live A/B shows an 18% reduction in cycle time and a 4.2% lift in fraud catch-rate. We discuss serving infrastructure, expert sharding, and failover paths under bursty inbound load.",
    takeaways: [
      "32-expert sparse MoE achieves 70B-model accuracy at 7B-model latency",
      "18% reduction in claims cycle time in live A/B testing",
      "4.2% improvement in fraud detection catch-rate",
      "Covers auto, home, and pet insurance lines with single architecture",
      "Details on expert sharding and failover for production deployment",
    ],
    relevance: { wam: "Low", cm: "Low", ins: "Critical", risk: "Medium" },
  },
  {
    title: "Causal Stress Testing in Financial Networks via Agent Simulation",
    authors: "L. Wang, P. Mehta, D. Friedman",
    org: "Imperial College · Bank of England",
    date: "Apr 22, 2026",
    hasCode: false,
    stars: 0,
    score: 79,
    verticals: ["Risk", "Capital Markets"],
    fsoRelevant: true,
    abstract:
      "An agent-based framework for systemic-risk analysis that combines structural causal models with LLM-driven counterparty behavior. We demonstrate scenarios — a stablecoin run, a 75 bps rates shock — where agentic feedback amplifies losses 2-3× versus VaR-style monte-carlo baselines. The framework is calibrated to Q4-2025 EBA stress data.",
    takeaways: [
      "Agent-based models show 2-3× loss amplification vs traditional VaR in stress scenarios",
      "Combines structural causal models with LLM-driven counterparty behavior",
      "Tested on stablecoin run and 75bps rates shock scenarios",
      "Calibrated to real EBA Q4-2025 stress test data",
      "Directly relevant for regulatory stress testing and systemic risk assessment",
    ],
    relevance: { wam: "Medium", cm: "High", ins: "Medium", risk: "Critical" },
  },
  {
    title: "Long-Context Retrieval for Earnings-Call Analysis at Scale",
    authors: "J. Kim, F. Oduya, et al.",
    org: "Bloomberg AI",
    date: "Apr 18, 2026",
    hasCode: true,
    stars: 156,
    score: 64,
    verticals: ["Capital Markets"],
    fsoRelevant: true,
    abstract:
      "Compares 1M-token-context models against state-of-the-art RAG pipelines on a 12-year corpus of S&P 500 earnings calls. Long-context wins on multi-quarter narrative tracking; RAG retains a clear edge on factoid retrieval and per-query cost. We propose a hybrid router that delivers 92% of long-context quality at 23% of the cost.",
    takeaways: [
      "Hybrid router achieves 92% of long-context quality at 23% of the cost",
      "Long-context models superior for multi-quarter narrative tracking",
      "RAG still wins on factoid retrieval and per-query cost efficiency",
      "Tested on 12-year S&P 500 earnings call corpus",
    ],
    relevance: { wam: "High", cm: "Critical", ins: "Low", risk: "Low" },
  },
];

const BLOGS = pipelineData.blogs ?? [
  {
    source: "Netflix Tech Blog",
    title: "Operating 1,400 production agents — lessons from year one",
    tag: "INFRA",
    date: "Apr 30",
    fsoRelevant: false,
    takeaways: [
      "Failure isolation via agent sandboxing reduced cascading failures by 73%",
      "Standardized observability layer across all 1,400 agents critical for debugging",
      "Auto-scaling based on reasoning-token consumption, not request count",
      "Agent versioning and canary deployments prevent regressions at scale",
    ],
  },
  {
    source: "Uber Engineering",
    title: "Petabyte-scale RL fine-tuning on heterogeneous fleets",
    tag: "RL SYSTEMS",
    date: "Apr 28",
    fsoRelevant: false,
    takeaways: [
      "Custom data pipeline handles 2.3PB of driving telemetry for RL training",
      "Heterogeneous GPU fleet utilization improved 40% with dynamic scheduling",
      "Checkpoint recovery under 90s enables aggressive experimentation",
      "Applicable to any large-scale RL fine-tuning on mixed infrastructure",
    ],
  },
  {
    source: "SemiAnalysis",
    title: "Test-time compute economics — Q1 2026 update",
    tag: "ECONOMICS",
    date: "Apr 26",
    fsoRelevant: true,
    takeaways: [
      "Cost per reasoning token dropped 62% YoY — now viable for production loops",
      "Optimal compute allocation: 70% inference, 30% verification for financial tasks",
      "Break-even point for test-time scaling is ~$0.002/token at current volumes",
      "Financial services among top 3 verticals driving reasoning-model demand",
    ],
  },
  {
    source: "The Pragmatic Engineer",
    title: "Inside Anthropic's eval infrastructure",
    tag: "EVAL",
    date: "Apr 22",
    fsoRelevant: false,
    takeaways: [
      "Eval-driven development: every prod change gated by 2,000+ automated evals",
      "Human-in-the-loop calibration weekly to prevent eval drift",
      "Separate eval clusters prevent resource contention with training",
      "Lessons transferable to enterprise AI teams building internal eval suites",
    ],
  },
  {
    source: "McKinsey Digital",
    title: "AI-first operating models in wholesale banking — what's working",
    tag: "COMPETITOR",
    date: "Apr 29",
    fsoRelevant: true,
    isCompetitor: true,
    takeaways: [
      "Top-quartile banks achieve 35% FTE savings in middle-office via AI agents",
      "McKinsey's AI delivery framework emphasizes domain-specific fine-tuning",
      "Client adoption accelerating: 60% of tier-1 banks have AI in production",
      "Key gap: most firms lack unified AI governance across business lines",
      "McKinsey recommends 'AI factory' model with centralized platform teams",
    ],
  },
  {
    source: "Accenture Technology",
    title: "Scaling generative AI in capital markets — from POC to production",
    tag: "COMPETITOR",
    date: "Apr 25",
    fsoRelevant: true,
    isCompetitor: true,
    takeaways: [
      "Accenture reports 4x acceleration in trade lifecycle processing via LLMs",
      "Regulatory compliance automation reduces review cycles from weeks to hours",
      "Platform approach: shared foundation models with domain adapters per desk",
      "Key learning: data quality gates are the #1 blocker for production AI",
    ],
  },
];

const SOCIAL_POSTS = pipelineData.socialPosts ?? [
  {
    platform: "linkedin",
    author: "Andrej Karpathy",
    handle: "karpathy",
    verified: true,
    role: "AI Researcher, ex-Tesla/OpenAI",
    date: "May 3",
    content: "The shift from 'prompt engineering' to 'agent engineering' is real. The best teams I see are building evaluation harnesses before building agents. Test-driven agent development is the unlock.",
    engagement: { likes: 12400, comments: 843, reposts: 2100 },
    relatedTopics: ["Agent Engineering", "Evaluation"],
    fsoRelevant: false,
    linkedContent: { type: "blog", title: "Inside Anthropic's eval infrastructure" },
  },
  {
    platform: "twitter",
    author: "Jim Fan",
    handle: "@DrJimFan",
    verified: true,
    role: "Sr. Research Scientist, NVIDIA",
    date: "May 2",
    content: "Tree-search reasoning for portfolio optimization is a sleeper hit. The Stanford/JPM paper shows hierarchy > compute for multi-period planning. This pattern will generalize far beyond finance.",
    engagement: { likes: 4200, comments: 312, reposts: 890 },
    relatedTopics: ["Reasoning", "Portfolio Optimization"],
    fsoRelevant: true,
    linkedContent: { type: "paper", title: "Hierarchical Reasoning for Multi-Asset Portfolio Optimization" },
  },
  {
    platform: "linkedin",
    author: "Cassie Kozyrkov",
    handle: "kozyrkov",
    verified: true,
    role: "CEO, Data Scientific | ex-Google Chief Decision Scientist",
    date: "May 1",
    content: "Production AI in financial services is less about model capability and more about governance rails. The firms winning are those who invested in eval + monitoring infrastructure 18 months ago.",
    engagement: { likes: 8900, comments: 567, reposts: 1400 },
    relatedTopics: ["AI Governance", "Financial Services", "Production AI"],
    fsoRelevant: true,
    linkedContent: null,
  },
  {
    platform: "twitter",
    author: "Shreya Shankar",
    handle: "@sh_reya",
    verified: true,
    role: "PhD @ UC Berkeley, AI Systems",
    date: "May 2",
    content: "The hybrid RAG + long-context router from Bloomberg AI is clever. 92% quality at 23% cost is exactly the kind of engineering that matters for real deployments. Paper of the week for me.",
    engagement: { likes: 2800, comments: 189, reposts: 456 },
    relatedTopics: ["RAG", "Long Context", "Cost Optimization"],
    fsoRelevant: true,
    linkedContent: { type: "paper", title: "Long-Context Retrieval for Earnings-Call Analysis at Scale" },
  },
  {
    platform: "linkedin",
    author: "Andrew Ng",
    handle: "andrewyng",
    verified: true,
    role: "Founder, DeepLearning.AI | Landing AI",
    date: "Apr 30",
    content: "Agentic workflows are transforming enterprise AI. The key insight: agents that can self-verify and escalate uncertain decisions outperform those optimized purely for accuracy. This is especially true in regulated industries like finance and healthcare.",
    engagement: { likes: 34200, comments: 2100, reposts: 5600 },
    relatedTopics: ["Agentic AI", "Enterprise AI", "Regulated Industries"],
    fsoRelevant: true,
    linkedContent: { type: "blog", title: "Operating 1,400 production agents — lessons from year one" },
  },
  {
    platform: "twitter",
    author: "Harrison Chase",
    handle: "@hwchase17",
    verified: true,
    role: "CEO, LangChain",
    date: "May 1",
    content: "Claude Sonnet 4.6's native tool-graph orchestration is a paradigm shift. It handles 80% of what frameworks like ours do — out of the box. The future of agent infra is at the model layer.",
    engagement: { likes: 6100, comments: 534, reposts: 1200 },
    relatedTopics: ["Tool Orchestration", "Agent Frameworks", "Claude"],
    fsoRelevant: false,
    linkedContent: null,
  },
  {
    platform: "linkedin",
    author: "Matt Turck",
    handle: "mattturck",
    verified: true,
    role: "Managing Director, FirstMark Capital",
    date: "Apr 29",
    content: "Watching consulting firms race to build AI practices. McKinsey's AI-first operating model report is aggressive — 35% FTE savings in banking middle-office. Accenture countering with trade lifecycle automation claims. The real winners will be those who ship, not those who publish reports.",
    engagement: { likes: 5400, comments: 389, reposts: 780 },
    relatedTopics: ["Consulting", "AI Strategy", "Financial Services"],
    fsoRelevant: true,
    isCompetitor: true,
    linkedContent: { type: "blog", title: "AI-first operating models in wholesale banking — what's working" },
  },
];

/* ------------------------------------------------------------------ */
/*  Style maps                                                         */
/* ------------------------------------------------------------------ */

const PRIORITY = {
  READ:       { hex: "#fb923c", bgRgba: "rgba(251,146,60,0.10)", borderRgba: "rgba(251,146,60,0.40)", icon: BookOpen },
  EXPERIMENT: { hex: "#a78bfa", bgRgba: "rgba(167,139,250,0.10)", borderRgba: "rgba(167,139,250,0.40)", icon: FlaskConical },
  SHARE:      { hex: "#34d399", bgRgba: "rgba(52,211,153,0.10)",  borderRgba: "rgba(52,211,153,0.40)",  icon: Share2 },
  WATCH:      { hex: "#f87171", bgRgba: "rgba(248,113,113,0.10)", borderRgba: "rgba(248,113,113,0.40)", icon: Eye },
};

const RELEVANCE = {
  Critical: { dot: "#fbbf24", text: "#fcd34d" },
  High:     { dot: "rgba(251,191,36,0.55)", text: "#fde68a" },
  Medium:   { dot: "#64748b", text: "#cbd5e1" },
  Low:      { dot: "#334155", text: "#64748b" },
};

const FSO_GOLD = "#fbbf24";

/* ------------------------------------------------------------------ */
/*  Atoms                                                              */
/* ------------------------------------------------------------------ */

function CircularScore({ score, size = 44 }) {
  const r = 16;
  const c = 2 * Math.PI * r;
  const offset = c - (score / 100) * c;
  return (
    <div className="relative shrink-0" style={{ width: size, height: size }}>
      <svg
        viewBox="0 0 40 40"
        style={{ width: size, height: size, transform: "rotate(-90deg)" }}
      >
        <circle cx="20" cy="20" r={r} stroke="#1c1f3f" strokeWidth="3" fill="none" />
        <circle
          cx="20"
          cy="20"
          r={r}
          stroke={FSO_GOLD}
          strokeWidth="3"
          fill="none"
          strokeDasharray={c}
          strokeDashoffset={offset}
          strokeLinecap="round"
        />
      </svg>
      <div
        className="absolute inset-0 flex items-center justify-center ai-mono"
        style={{
          fontSize: Math.round(size * 0.26),
          color: FSO_GOLD,
          letterSpacing: "0.02em",
        }}
      >
        {score}
      </div>
    </div>
  );
}

function PriorityChip({ kind }) {
  const p = PRIORITY[kind];
  const Icon = p.icon;
  return (
    <span
      className="inline-flex items-center gap-1.5"
      style={{ color: p.hex }}
    >
      <Icon size={12} strokeWidth={2.5} />
      <span
        className="ai-mono"
        style={{
          fontSize: 10,
          letterSpacing: "0.18em",
          fontWeight: 600,
        }}
      >
        {kind}
      </span>
    </span>
  );
}

function SectionHeader({ title, sub }) {
  return (
    <div
      className="flex items-baseline justify-between mb-4 pb-2 border-b"
      style={{ borderColor: "#1c1f3f" }}
    >
      <h2
        className="ai-mono text-slate-200"
        style={{ fontSize: 12, letterSpacing: "0.22em" }}
      >
        {title}
      </h2>
      {sub && (
        <div
          className="ai-mono"
          style={{
            fontSize: 10,
            letterSpacing: "0.18em",
            color: "#475569",
            textTransform: "uppercase",
          }}
        >
          {sub}
        </div>
      )}
    </div>
  );
}

function Tag({ children }) {
  return (
    <span
      className="ai-mono px-2 py-0.5 border"
      style={{
        fontSize: 10,
        letterSpacing: "0.12em",
        color: "#94a3b8",
        backgroundColor: "rgba(30,41,59,0.5)",
        borderColor: "rgba(51,65,85,0.6)",
      }}
    >
      {children}
    </span>
  );
}

function TakeawayList({ takeaways }) {
  return (
    <div className="mt-3 mb-1">
      <div
        className="ai-mono mb-2"
        style={{ fontSize: 9, letterSpacing: "0.18em", color: "#475569" }}
      >
        KEY TAKEAWAYS
      </div>
      <ul className="space-y-1.5">
        {takeaways.map((t, i) => (
          <li key={i} className="flex items-start gap-2">
            <ChevronRight size={10} className="shrink-0 mt-1" style={{ color: FSO_GOLD }} />
            <span style={{ fontSize: 12, color: "#94a3b8", lineHeight: 1.5 }}>{t}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Tab 1 — Weekly Briefing                                            */
/* ------------------------------------------------------------------ */

function ActionCard({ item }) {
  const p = PRIORITY[item.priority];
  return (
    <div
      className="group relative border transition-colors"
      style={{ backgroundColor: "#0e1130", borderColor: "#1c1f3f" }}
      onMouseEnter={(e) => (e.currentTarget.style.borderColor = "#2a2e58")}
      onMouseLeave={(e) => (e.currentTarget.style.borderColor = "#1c1f3f")}
    >
      <div
        className="absolute left-0 top-0 bottom-0"
        style={{ width: 3, backgroundColor: p.hex }}
      />
      <div className="pl-6 pr-5 py-5">
        <div className="flex items-start justify-between gap-4 mb-3">
          <PriorityChip kind={item.priority} />
          <div className="flex items-center gap-3">
            <span
              className="ai-mono"
              style={{ fontSize: 11, color: "#64748b" }}
            >
              {item.date}
            </span>
            <CircularScore score={item.score} size={38} />
          </div>
        </div>

        <h3
          className="leading-snug text-slate-100 mb-1.5"
          style={{ fontSize: 15, fontWeight: 500 }}
        >
          {item.title}
        </h3>

        <div className="ai-mono mb-3" style={{ fontSize: 11, color: "#64748b" }}>
          <span style={{ color: "#94a3b8" }}>{item.source}</span>
          <span className="mx-2" style={{ color: "#334155" }}>·</span>
          <span>{item.sourceMeta}</span>
        </div>

        <p
          className="text-slate-400 mb-4"
          style={{ fontSize: 13, lineHeight: 1.6 }}
        >
          {item.why}
        </p>

        <div className="flex items-center justify-between">
          <div className="flex flex-wrap gap-1.5">
            {item.tags.map((t) => (
              <Tag key={t}>{t.toUpperCase()}</Tag>
            ))}
          </div>
          <button
            className="ai-mono flex items-center gap-1 transition-colors"
            style={{ fontSize: 11, color: "#64748b" }}
            onMouseEnter={(e) => (e.currentTarget.style.color = FSO_GOLD)}
            onMouseLeave={(e) => (e.currentTarget.style.color = "#64748b")}
          >
            OPEN <ExternalLink size={11} />
          </button>
        </div>
      </div>
    </div>
  );
}

function StatsBar() {
  const stats = pipelineData.stats ?? [
    { label: "PAPERS SCANNED", value: "1,247", sub: "arXiv + Semantic Scholar" },
    { label: "REPOS INDEXED", value: "384", sub: "GitHub trending" },
    { label: "ARTICLES", value: "92", sub: "engineering + research blogs" },
    { label: "FSO-RELEVANT", value: "23", sub: "score ≥ 65", accent: true },
  ];
  return (
    <div
      className="grid grid-cols-4 border mb-8"
      style={{ borderColor: "#1c1f3f", backgroundColor: "#0c0e26" }}
    >
      {stats.map((s, i) => (
        <div
          key={i}
          className="px-6 py-5"
          style={{
            borderRight: i < 3 ? "1px solid #1c1f3f" : "none",
          }}
        >
          <div
            className="ai-mono mb-2"
            style={{
              fontSize: 10,
              letterSpacing: "0.18em",
              color: "#64748b",
            }}
          >
            {s.label}
          </div>
          <div
            className="ai-mono mb-0.5"
            style={{
              fontSize: 30,
              color: s.accent ? FSO_GOLD : "#f1f5f9",
              fontWeight: 500,
              letterSpacing: "-0.01em",
            }}
          >
            {s.value}
          </div>
          <div style={{ fontSize: 11, color: "#64748b" }}>{s.sub}</div>
        </div>
      ))}
    </div>
  );
}

function RepoList() {
  const [openRepo, setOpenRepo] = useState(REPOS[0]?.name ?? "");

  return (
    <div style={{ backgroundColor: "#0e1130", borderColor: "#1c1f3f" }} className="border">
      {REPOS.map((r, i) => (
        <div
          key={r.name}
          className="px-4 py-3"
          style={{
            borderBottom:
              i < REPOS.length - 1 ? "1px solid #1c1f3f" : "none",
          }}
        >
          <button
            type="button"
            onClick={() => setOpenRepo(openRepo === r.name ? "" : r.name)}
            className="w-full text-left"
          >
            <div className="flex items-center justify-between mb-1 gap-3">
              <div
                className="ai-mono truncate"
                style={{ fontSize: 12, color: "#e2e8f0" }}
              >
                {r.name}
              </div>
              <div
                className="ai-mono flex items-center gap-1 shrink-0"
                style={{ fontSize: 10, color: "#64748b" }}
              >
                <Activity size={11} />
                {r.lastUpdated ? `UPDATED ${r.lastUpdated}` : "RECENT"}
              </div>
            </div>
            <div className="flex items-center justify-between gap-3">
              <div
                className="truncate"
                style={{ fontSize: 11, color: "#64748b" }}
              >
                {r.desc}
              </div>
              <div
                className="ai-mono flex items-center gap-1 shrink-0"
                style={{ fontSize: 10, color: "#64748b" }}
              >
                <Star size={10} fill="currentColor" />
                {r.stars}
              </div>
            </div>
          </button>
          {openRepo === r.name && (
            <div className="mt-3 pt-3 border-t" style={{ borderColor: "rgba(28,31,63,0.7)" }}>
              <div className="flex items-center gap-2 flex-wrap mb-3">
                {r.language && <Tag>{r.language.toUpperCase()}</Tag>}
                {r.createdAt && <Tag>{`CREATED ${r.createdAt}`.toUpperCase()}</Tag>}
                {r.lastUpdated && <Tag>{r.lastUpdated.toUpperCase()}</Tag>}
                {r.license && <Tag>{r.license.toUpperCase()}</Tag>}
              </div>
              <ul className="space-y-1.5 mb-3">
                {(r.bullets ?? [r.desc]).slice(0, 3).map((bullet) => (
                  <li key={bullet} className="flex gap-2" style={{ fontSize: 11, color: "#94a3b8" }}>
                    <span style={{ color: FSO_GOLD, marginTop: 1 }}>•</span>
                    <span>{bullet}</span>
                  </li>
                ))}
              </ul>
              <div className="flex items-center justify-between gap-3">
                <div
                  className="ai-mono inline-flex items-center gap-1.5"
                  style={{ fontSize: 10, color: "#94a3b8" }}
                >
                  <Layers size={11} style={{ color: "#67e8f9" }} />
                  BEST FOR {r.bestFor ?? "AI ENGINEERING"}
                </div>
                <div className="flex items-center gap-3 shrink-0">
                  {r.latestReleaseUrl && (
                    <a
                      href={r.latestReleaseUrl}
                      target="_blank"
                      rel="noreferrer"
                      className="ai-mono inline-flex items-center gap-1"
                      style={{ fontSize: 10, color: "#67e8f9" }}
                    >
                      RELEASE
                      <ExternalLink size={11} />
                    </a>
                  )}
                  {r.url && (
                    <a
                      href={r.url}
                      target="_blank"
                      rel="noreferrer"
                      className="ai-mono inline-flex items-center gap-1"
                      style={{ fontSize: 10, color: FSO_GOLD }}
                    >
                      OPEN REPO
                      <ExternalLink size={11} />
                    </a>
                  )}
                </div>
              </div>
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

function ReleaseList({ items, accentColor, emptyLabel }) {
  const [openItem, setOpenItem] = useState(items[0]?.name ?? "");

  if (!items.length) {
    return (
      <div className="border px-4 py-3" style={{ backgroundColor: "#0e1130", borderColor: "#1c1f3f" }}>
        <div className="ai-mono" style={{ fontSize: 11, color: "#64748b" }}>
          {emptyLabel}
        </div>
      </div>
    );
  }

  return (
    <div style={{ backgroundColor: "#0e1130", borderColor: "#1c1f3f" }} className="border">
      {items.map((item, index) => {
        const links = item.links?.length
          ? item.links
          : item.url
            ? [{ label: "Read release", url: item.url }]
            : [];

        return (
          <div
            key={item.name}
            className="px-4 py-3"
            style={{
              borderBottom: index < items.length - 1 ? "1px solid #1c1f3f" : "none",
            }}
          >
            <button
              type="button"
              onClick={() => setOpenItem(openItem === item.name ? "" : item.name)}
              className="w-full text-left"
            >
              <div className="flex items-center justify-between mb-1 gap-3">
                <div className="truncate" style={{ fontSize: 13, color: "#f1f5f9", fontWeight: 500 }}>
                  {item.name}
                </div>
                <div className="ai-mono shrink-0" style={{ fontSize: 10, color: "#64748b" }}>
                  {item.date}
                </div>
              </div>
              <div className="flex items-center justify-between gap-3">
                <div className="truncate" style={{ fontSize: 11, color: "#64748b" }}>
                  {item.note}
                </div>
                <span
                  className="ai-mono px-1.5 py-0.5 border shrink-0"
                  style={{
                    fontSize: 9,
                    letterSpacing: "0.16em",
                    color: accentColor,
                    backgroundColor: `${accentColor}14`,
                    borderColor: `${accentColor}4d`,
                  }}
                >
                  {item.tag}
                </span>
              </div>
            </button>
            {openItem === item.name && (
              <div className="mt-3 pt-3 border-t" style={{ borderColor: "rgba(28,31,63,0.7)" }}>
                <div className="flex items-center gap-2 flex-wrap mb-3">
                  <Tag>{item.org.toUpperCase()}</Tag>
                  {item.date && <Tag>{item.date.toUpperCase()}</Tag>}
                  <Tag>{item.tag}</Tag>
                </div>
                <div style={{ fontSize: 12, color: "#94a3b8" }}>{item.note}</div>
                {links.length > 0 && (
                  <div className="flex flex-wrap gap-3 mt-3">
                    {links.map((link) => (
                      <a
                        key={`${item.name}-${link.label}-${link.url}`}
                        href={link.url}
                        target="_blank"
                        rel="noreferrer"
                        className="ai-mono inline-flex items-center gap-1"
                        style={{ fontSize: 10, color: accentColor }}
                      >
                        {link.label.toUpperCase()}
                        <ExternalLink size={11} />
                      </a>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

function ModelList() {
  return (
    <ReleaseList items={MODELS} accentColor={FSO_GOLD} emptyLabel="No recent model releases found." />
  );
}

function ToolsList() {
  return (
    <ReleaseList items={TOOLS_SERVICES} accentColor="#67e8f9" emptyLabel="No recent tool or service releases found." />
  );
}

function WeeklyBriefing({ fsoFilter }) {
  const items = fsoFilter ? ACTION_ITEMS.filter((i) => i.fsoRelevant) : ACTION_ITEMS;
  return (
    <div>
      <StatsBar />
      <div className="grid grid-cols-3 gap-8">
        <div className="col-span-2">
          <SectionHeader title="ACTION ITEMS" sub="curated for senior consultants" />
          <div className="space-y-3">
            {items.map((it, i) => (
              <ActionCard key={i} item={it} />
            ))}
          </div>
        </div>
        <div className="space-y-8">
          <div>
            <SectionHeader title="TRENDING REPOS" sub="this week" />
            <RepoList />
          </div>
          <div>
            <SectionHeader title="MODEL RELEASES" sub="this week" />
            <ModelList />
          </div>
          <div>
            <SectionHeader title="TOOLS & SERVICES" sub="this week" />
            <ToolsList />
          </div>
        </div>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Tab 2 — Research Papers                                            */
/* ------------------------------------------------------------------ */

function PaperCard({ paper }) {
  const [open, setOpen] = useState(false);
  return (
    <div
      className="border transition-colors"
      style={{ backgroundColor: "#0e1130", borderColor: "#1c1f3f" }}
      onMouseEnter={(e) => (e.currentTarget.style.borderColor = "#2a2e58")}
      onMouseLeave={(e) => (e.currentTarget.style.borderColor = "#1c1f3f")}
    >
      <button
        onClick={() => setOpen(!open)}
        className="w-full text-left px-6 py-5"
      >
        <div className="flex items-start gap-5">
          <div className="flex-1 min-w-0">
            <h3
              className="leading-snug mb-2"
              style={{ fontSize: 15, color: "#f1f5f9", fontWeight: 500 }}
            >
              {paper.title}
            </h3>
            <div
              className="ai-mono mb-3"
              style={{ fontSize: 11, color: "#64748b" }}
            >
              <span style={{ color: "#94a3b8" }}>{paper.authors}</span>
              <span className="mx-2" style={{ color: "#334155" }}>·</span>
              <span>{paper.org}</span>
              <span className="mx-2" style={{ color: "#334155" }}>·</span>
              <span>{paper.date}</span>
            </div>
            {paper.takeaways && <TakeawayList takeaways={paper.takeaways} />}
            <div className="flex items-center gap-2 flex-wrap mt-3">
              {paper.hasCode && (
                <span
                  className="ai-mono inline-flex items-center gap-1.5 px-2 py-0.5 border"
                  style={{
                    fontSize: 10,
                    letterSpacing: "0.14em",
                    color: "#34d399",
                    backgroundColor: "rgba(52,211,153,0.08)",
                    borderColor: "rgba(52,211,153,0.30)",
                  }}
                >
                  <Code2 size={10} />
                  CODE
                  <span style={{ color: "rgba(52,211,153,0.7)" }}>·</span>
                  <Star size={9} fill="currentColor" />
                  {paper.stars}
                </span>
              )}
              {paper.verticals.map((v) => (
                <Tag key={v}>{v.toUpperCase()}</Tag>
              ))}
            </div>
          </div>
          <div className="flex flex-col items-end gap-2 shrink-0">
            <CircularScore score={paper.score} size={50} />
            <div
              className="ai-mono"
              style={{
                fontSize: 9,
                letterSpacing: "0.18em",
                color: "#475569",
              }}
            >
              FSO SCORE
            </div>
            <ChevronRight
              size={16}
              style={{
                color: "#475569",
                transition: "transform 200ms",
                transform: open ? "rotate(90deg)" : "rotate(0deg)",
              }}
            />
          </div>
        </div>
      </button>

      {open && (
        <div
          className="px-6 pb-6 pt-2 border-t"
          style={{ borderColor: "rgba(28,31,63,0.7)" }}
        >
          <div
            className="ai-mono mb-2"
            style={{
              fontSize: 10,
              letterSpacing: "0.18em",
              color: "#475569",
            }}
          >
            ABSTRACT
          </div>
          <p
            className="mb-6"
            style={{ fontSize: 13, color: "#cbd5e1", lineHeight: 1.65 }}
          >
            {paper.abstract}
          </p>
          <div
            className="ai-mono mb-3"
            style={{
              fontSize: 10,
              letterSpacing: "0.18em",
              color: "#475569",
            }}
          >
            VERTICAL RELEVANCE
          </div>
          <div className="grid grid-cols-4 gap-3">
            {[
              { key: "wam", label: "Wealth & Asset Mgmt" },
              { key: "cm", label: "Capital Markets" },
              { key: "ins", label: "Insurance" },
              { key: "risk", label: "Risk" },
            ].map(({ key, label }) => {
              const lvl = paper.relevance[key];
              const r = RELEVANCE[lvl];
              return (
                <div
                  key={key}
                  className="border p-3"
                  style={{ borderColor: "#1c1f3f" }}
                >
                  <div
                    className="ai-mono mb-2"
                    style={{
                      fontSize: 10,
                      letterSpacing: "0.12em",
                      color: "#64748b",
                      textTransform: "uppercase",
                    }}
                  >
                    {label}
                  </div>
                  <div className="flex items-center gap-2">
                    <div
                      className="rounded-full"
                      style={{ width: 8, height: 8, backgroundColor: r.dot }}
                    />
                    <span
                      style={{
                        fontSize: 12,
                        color: r.text,
                        fontWeight: 500,
                      }}
                    >
                      {lvl}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}

function ResearchPapers({ fsoFilter }) {
  const [filter, setFilter] = useState("All");
  const filters = ["All", "WAM", "Capital Markets", "Insurance", "Risk"];

  let filtered = filter === "All" ? PAPERS : PAPERS.filter((p) => p.verticals.includes(filter));
  if (fsoFilter) filtered = filtered.filter((p) => p.fsoRelevant);

  return (
    <div>
      <div className="flex items-center justify-between mb-6 flex-wrap gap-3">
        <div className="flex items-center gap-2">
          <Filter size={14} style={{ color: "#64748b" }} />
          <div className="flex items-center gap-1.5 flex-wrap">
            {filters.map((f) => {
              const active = filter === f;
              return (
                <button
                  key={f}
                  onClick={() => setFilter(f)}
                  className="ai-mono px-3 py-1.5 border transition-colors"
                  style={{
                    fontSize: 11,
                    letterSpacing: "0.14em",
                    textTransform: "uppercase",
                    color: active ? FSO_GOLD : "#64748b",
                    backgroundColor: active
                      ? "rgba(251,191,36,0.08)"
                      : "transparent",
                    borderColor: active
                      ? "rgba(251,191,36,0.40)"
                      : "#1c1f3f",
                  }}
                >
                  {f}
                </button>
              );
            })}
          </div>
        </div>
        <div
          className="ai-mono"
          style={{ fontSize: 10, letterSpacing: "0.18em", color: "#475569" }}
        >
          SHOWING {filtered.length} OF {PAPERS.length} · WEEK 18 / 2026
        </div>
      </div>

      <div className="space-y-3">
        {filtered.map((p) => (
          <PaperCard key={p.title} paper={p} />
        ))}
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Tab 3 — AI Pulse (Engineering & Research Blogs)                    */
/* ------------------------------------------------------------------ */

function BlogCard({ blog }) {
  const [open, setOpen] = useState(false);
  return (
    <div
      className="group border transition-colors"
      style={{ backgroundColor: "#0e1130", borderColor: "#1c1f3f" }}
      onMouseEnter={(e) => (e.currentTarget.style.borderColor = "#2a2e58")}
      onMouseLeave={(e) => (e.currentTarget.style.borderColor = "#1c1f3f")}
    >
      <button onClick={() => setOpen(!open)} className="w-full text-left p-5">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <span
              className="ai-mono"
              style={{
                fontSize: 10,
                letterSpacing: "0.18em",
                color: blog.isCompetitor ? "#f87171" : FSO_GOLD,
              }}
            >
              {blog.tag}
            </span>
            {blog.isCompetitor && (
              <span
                className="ai-mono px-1.5 py-0.5 border"
                style={{
                  fontSize: 9,
                  letterSpacing: "0.12em",
                  color: "#f87171",
                  backgroundColor: "rgba(248,113,113,0.08)",
                  borderColor: "rgba(248,113,113,0.30)",
                }}
              >
                COMPETITOR
              </span>
            )}
          </div>
          <div className="flex items-center gap-3">
            <span
              className="ai-mono"
              style={{
                fontSize: 10,
                letterSpacing: "0.10em",
                color: "#475569",
              }}
            >
              {blog.date.toUpperCase()}
            </span>
            <ChevronRight
              size={14}
              style={{
                color: "#475569",
                transition: "transform 200ms",
                transform: open ? "rotate(90deg)" : "rotate(0deg)",
              }}
            />
          </div>
        </div>
        <div
          className="mb-2 leading-snug"
          style={{ fontSize: 14, color: "#f1f5f9", fontWeight: 500 }}
        >
          {blog.title}
        </div>
        <div className="flex items-center justify-between mb-1">
          <div
            className="ai-mono"
            style={{ fontSize: 11, color: "#64748b" }}
          >
            {blog.source}
          </div>
          <ExternalLink size={12} style={{ color: "#475569" }} />
        </div>
      </button>
      {blog.takeaways && (
        <div className="px-5 pb-5 border-t" style={{ borderColor: "rgba(28,31,63,0.7)" }}>
          <TakeawayList takeaways={blog.takeaways} />
        </div>
      )}
    </div>
  );
}

function AIPulse({ fsoFilter }) {
  const blogs = fsoFilter ? BLOGS.filter((b) => b.fsoRelevant) : BLOGS;

  return (
    <div>
      <SectionHeader title="ENGINEERING & RESEARCH BLOGS" sub="curated highlights" />
      <div className="grid grid-cols-2 gap-3">
        {blogs.map((b, i) => (
          <BlogCard key={i} blog={b} />
        ))}
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Tab 4 — Pipeline / Architecture                                    */
/* ------------------------------------------------------------------ */

function Pipeline() {
  const stages = [
    { name: "Harvester", icon: Database, sub: "arXiv · GitHub · RSS", color: "#7dd3fc" },
    { name: "Critic", icon: Search, sub: "LLM-judge · score", color: "#c4b5fd" },
    { name: "Summarizer", icon: Layers, sub: "multi-doc synth", color: "#67e8f9" },
    { name: "Curator", icon: Sparkles, sub: "FSO domain inj.", color: FSO_GOLD },
    { name: "Dashboard", icon: Inbox, sub: "weekly digest", color: "#6ee7b7" },
  ];

  const items = [];
  stages.forEach((s, i) => {
    const Icon = s.icon;
    items.push(
      <div
        key={s.name}
        className="flex-1 border p-4 transition-colors"
        style={{ borderColor: "#1c1f3f", backgroundColor: "#0a0a1a" }}
        onMouseEnter={(e) => (e.currentTarget.style.borderColor = "#2a2e58")}
        onMouseLeave={(e) => (e.currentTarget.style.borderColor = "#1c1f3f")}
      >
        <Icon size={18} style={{ color: s.color, marginBottom: 12 }} />
        <div style={{ fontSize: 13, color: "#f1f5f9", fontWeight: 500, marginBottom: 4 }}>
          {s.name}
        </div>
        <div
          className="ai-mono"
          style={{
            fontSize: 10,
            letterSpacing: "0.14em",
            color: "#64748b",
            textTransform: "uppercase",
          }}
        >
          {s.sub}
        </div>
      </div>
    );
    if (i < stages.length - 1) {
      items.push(
        <ArrowRight
          key={`arr-${i}`}
          size={14}
          className="shrink-0"
          style={{ color: "#334155" }}
        />
      );
    }
  });

  return (
    <div
      className="border p-6"
      style={{ backgroundColor: "#0e1130", borderColor: "#1c1f3f" }}
    >
      <div className="flex items-stretch gap-3">{items}</div>
      <div
        className="ai-mono mt-5 flex items-center gap-2"
        style={{ fontSize: 10, letterSpacing: "0.18em", color: "#475569" }}
      >
        <span
          className="rounded-full"
          style={{
            width: 6,
            height: 6,
            backgroundColor: "#34d399",
            boxShadow: "0 0 8px rgba(52,211,153,0.6)",
          }}
        />
        AGENT RUN · MAY 04 06:14 UTC · 142s · OK
      </div>
    </div>
  );
}

function CodeSnippet() {
  const code = `# fso/phase_ii/domain_injection.yaml
# Curator config — applied after summarization

verticals:
  wealth_asset_management:
    weight: 1.00
    keywords: [robo-advisor, sma, portfolio,
               glide-path, alts, family-office]
    eval_set: bench/wam_v3
    rubric: rubrics/wam_relevance.md

  capital_markets_banking:
    weight: 1.00
    keywords: [market-making, syndication, fx,
               clearing, prime-brokerage, t+1]
    eval_set: bench/cm_v2

  insurance:
    weight: 0.90
    keywords: [actuarial, claims, reserving,
               underwriting, reinsurance]

  risk:
    weight: 1.10  # boost — high signal density
    keywords: [stress-test, var, model-risk,
               bcbs-239, ccar, ifrs-9]

curator:
  model: claude-sonnet-4-6
  threshold: 0.65
  rerank: true
  max_items_per_vertical: 5`;

  const lines = code.split("\n");

  const colorFor = (line) => {
    const trimmed = line.trim();
    if (trimmed.startsWith("#")) return "#475569";
    if (/^\s{0,4}[a-zA-Z_][a-zA-Z0-9_]*:/.test(line)) {
      if (/^[a-zA-Z_]/.test(line)) return FSO_GOLD;
      return "#7dd3fc";
    }
    return "#cbd5e1";
  };

  return (
    <div
      className="border"
      style={{ backgroundColor: "#070818", borderColor: "#1c1f3f" }}
    >
      <div
        className="flex items-center justify-between px-4 py-2 border-b"
        style={{ borderColor: "#1c1f3f", backgroundColor: "#0a0a1a" }}
      >
        <div
          className="ai-mono flex items-center gap-2"
          style={{
            fontSize: 10,
            letterSpacing: "0.18em",
            color: "#64748b",
          }}
        >
          <FileCode size={11} />
          DOMAIN_INJECTION.YAML
        </div>
        <div
          className="ai-mono"
          style={{ fontSize: 10, color: "#475569" }}
        >
          PHASE II · v0.4.1
        </div>
      </div>
      <pre
        className="ai-mono overflow-x-auto"
        style={{
          padding: "16px 20px",
          fontSize: 12,
          lineHeight: 1.7,
          margin: 0,
        }}
      >
        {lines.map((line, i) => (
          <div key={i} style={{ color: colorFor(line) }}>
            {line || " "}
          </div>
        ))}
      </pre>
    </div>
  );
}

function ArchitectureTab() {
  return (
    <div className="space-y-10">
      <div>
        <SectionHeader title="AGENT PIPELINE" sub="harvester → curator" />
        <Pipeline />
      </div>
      <div>
        <SectionHeader title="PHASE II — DOMAIN INJECTION" sub="config pattern" />
        <CodeSnippet />
      </div>
      <div>
        <SectionHeader title="CURRENT STATUS & NEXT STEPS" sub="roadmap" />
        <div className="grid grid-cols-2 gap-4">
          <div
            className="border p-5"
            style={{ backgroundColor: "#0e1130", borderColor: "#1c1f3f" }}
          >
            <div className="ai-mono mb-3" style={{ fontSize: 10, letterSpacing: "0.18em", color: "#34d399" }}>
              OPERATIONAL NOW
            </div>
            <ul className="space-y-2">
              {[
                "Multi-source harvesting (arXiv, GitHub, RSS, blogs)",
                "LLM-judge scoring with FSO domain weighting",
                "Multi-document summarization pipeline",
                "Weekly digest generation with vertical tagging",
                "Social media signal integration (LinkedIn, Twitter)",
              ].map((item, i) => (
                <li key={i} className="flex items-start gap-2">
                  <CheckCircle size={12} className="shrink-0 mt-0.5" style={{ color: "#34d399" }} />
                  <span style={{ fontSize: 12, color: "#94a3b8" }}>{item}</span>
                </li>
              ))}
            </ul>
          </div>
          <div
            className="border p-5"
            style={{ backgroundColor: "#0e1130", borderColor: "#1c1f3f" }}
          >
            <div className="ai-mono mb-3" style={{ fontSize: 10, letterSpacing: "0.18em", color: "#a78bfa" }}>
              NEXT STEPS
            </div>
            <ul className="space-y-2">
              {[
                "Real-time streaming from social APIs (scheduled Q3)",
                "Automated competitor analysis classification",
                "Client-specific brief customization engine",
                "Feedback loop: user engagement → scoring refinement",
                "Slack/Teams integration for push notifications",
              ].map((item, i) => (
                <li key={i} className="flex items-start gap-2">
                  <ArrowRight size={12} className="shrink-0 mt-0.5" style={{ color: "#a78bfa" }} />
                  <span style={{ fontSize: 12, color: "#94a3b8" }}>{item}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Tab 5 — Social Media                                               */
/* ------------------------------------------------------------------ */

function SocialPostCard({ post }) {
  const isLinkedIn = post.platform === "linkedin";
  const platformColor = isLinkedIn ? "#0a66c2" : "#1d9bf0";

  return (
    <div
      className="border transition-colors"
      style={{ backgroundColor: "#0e1130", borderColor: "#1c1f3f" }}
      onMouseEnter={(e) => (e.currentTarget.style.borderColor = "#2a2e58")}
      onMouseLeave={(e) => (e.currentTarget.style.borderColor = "#1c1f3f")}
    >
      <div className="p-5">
        <div className="flex items-start justify-between mb-3">
          <div className="flex items-center gap-3">
            <div
              className="flex items-center justify-center rounded-full"
              style={{ width: 36, height: 36, backgroundColor: `${platformColor}20` }}
            >
              <span style={{ color: platformColor, fontSize: 14, fontWeight: 700 }}>
                {isLinkedIn ? "in" : "𝕏"}
              </span>
            </div>
            <div>
              <div className="flex items-center gap-1.5">
                <span style={{ fontSize: 13, color: "#f1f5f9", fontWeight: 500 }}>
                  {post.author}
                </span>
                {post.verified && (
                  <CheckCircle size={12} style={{ color: platformColor }} />
                )}
                {post.isCompetitor && (
                  <span
                    className="ai-mono px-1.5 py-0.5 border ml-1"
                    style={{
                      fontSize: 8,
                      letterSpacing: "0.12em",
                      color: "#f87171",
                      backgroundColor: "rgba(248,113,113,0.08)",
                      borderColor: "rgba(248,113,113,0.30)",
                    }}
                  >
                    COMPETITOR INTEL
                  </span>
                )}
              </div>
              <div className="ai-mono" style={{ fontSize: 10, color: "#64748b" }}>
                {post.handle} · {post.role}
              </div>
            </div>
          </div>
          <div className="ai-mono" style={{ fontSize: 10, color: "#475569" }}>
            {post.date}
          </div>
        </div>

        <p style={{ fontSize: 13, color: "#cbd5e1", lineHeight: 1.6, marginBottom: 12 }}>
          {post.content}
        </p>

        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <span className="ai-mono" style={{ fontSize: 10, color: "#64748b" }}>
              {post.engagement.likes.toLocaleString()} likes
            </span>
            <span className="ai-mono" style={{ fontSize: 10, color: "#64748b" }}>
              {post.engagement.comments.toLocaleString()} comments
            </span>
            <span className="ai-mono" style={{ fontSize: 10, color: "#64748b" }}>
              {post.engagement.reposts.toLocaleString()} reposts
            </span>
          </div>
          <div className="flex items-center gap-1.5 flex-wrap">
            {post.relatedTopics.map((t) => (
              <Tag key={t}>{t.toUpperCase()}</Tag>
            ))}
          </div>
        </div>

        {post.linkedContent && (
          <div
            className="mt-3 px-3 py-2 border flex items-center gap-2"
            style={{ borderColor: "rgba(251,191,36,0.20)", backgroundColor: "rgba(251,191,36,0.04)" }}
          >
            <Sparkles size={11} style={{ color: FSO_GOLD }} />
            <span className="ai-mono" style={{ fontSize: 10, color: "#64748b" }}>
              LINKED {post.linkedContent.type.toUpperCase()}:
            </span>
            <span style={{ fontSize: 11, color: "#fde68a" }}>
              {post.linkedContent.title}
            </span>
          </div>
        )}
      </div>
    </div>
  );
}

function SocialMedia({ fsoFilter }) {
  const [platformFilter, setPlatformFilter] = useState("all");

  let posts = SOCIAL_POSTS;
  if (fsoFilter) posts = posts.filter((p) => p.fsoRelevant);
  if (platformFilter === "linkedin") posts = posts.filter((p) => p.platform === "linkedin");
  if (platformFilter === "twitter") posts = posts.filter((p) => p.platform === "twitter");

  return (
    <div>
      <div className="flex items-center justify-between mb-6 flex-wrap gap-3">
        <div className="flex items-center gap-2">
          <Filter size={14} style={{ color: "#64748b" }} />
          <div className="flex items-center gap-1.5">
            {[
              { id: "all", label: "All" },
              { id: "linkedin", label: "LinkedIn" },
              { id: "twitter", label: "Twitter/X" },
            ].map((f) => {
              const active = platformFilter === f.id;
              return (
                <button
                  key={f.id}
                  onClick={() => setPlatformFilter(f.id)}
                  className="ai-mono px-3 py-1.5 border transition-colors"
                  style={{
                    fontSize: 11,
                    letterSpacing: "0.14em",
                    textTransform: "uppercase",
                    color: active ? FSO_GOLD : "#64748b",
                    backgroundColor: active ? "rgba(251,191,36,0.08)" : "transparent",
                    borderColor: active ? "rgba(251,191,36,0.40)" : "#1c1f3f",
                  }}
                >
                  {f.label}
                </button>
              );
            })}
          </div>
        </div>
        <div className="ai-mono flex items-center gap-2" style={{ fontSize: 10, letterSpacing: "0.18em", color: "#475569" }}>
          <Users size={11} />
          VERIFIED SOURCES ONLY · {posts.length} POSTS
        </div>
      </div>

      <div className="space-y-3">
        {posts.map((p, i) => (
          <SocialPostCard key={i} post={p} />
        ))}
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Shell                                                              */
/* ------------------------------------------------------------------ */

export default function Dashboard() {
  const [tab, setTab] = useState("briefing");
  const [fsoFilter, setFsoFilter] = useState(false);
  const refreshedAt = pipelineData.generatedAt
    ? new Date(pipelineData.generatedAt).toLocaleString(undefined, {
        month: "short",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      })
    : "MAY 04 — MAY 10";

  const tabs = [
    { id: "briefing", label: "Weekly Briefing" },
    { id: "papers", label: "Research Papers" },
    { id: "pulse", label: "AI Pulse" },
    { id: "social", label: "Social Pulse" },
    { id: "architecture", label: "Pipeline" },
  ];

  return (
    <div
      className="ai-root min-h-screen"
      style={{
        backgroundColor: "#0a0a1a",
        color: "#cbd5e1",
        fontFamily: "'DM Sans', system-ui, -apple-system, sans-serif",
      }}
    >
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap');
        .ai-root, .ai-root button, .ai-root h1, .ai-root h2, .ai-root h3, .ai-root p, .ai-root span, .ai-root div {
          font-family: 'DM Sans', system-ui, -apple-system, sans-serif;
        }
        .ai-root .ai-mono, .ai-root .ai-mono * {
          font-family: 'JetBrains Mono', ui-monospace, SFMono-Regular, Menlo, monospace;
        }
        .ai-root pre, .ai-root pre * {
          font-family: 'JetBrains Mono', ui-monospace, SFMono-Regular, Menlo, monospace;
        }
      `}</style>

      <header
        className="border-b sticky top-0 z-20"
        style={{ borderColor: "#1c1f3f", backgroundColor: "rgba(10,10,26,0.95)", backdropFilter: "blur(8px)" }}
      >
        <div className="max-w-[1400px] mx-auto px-8 pt-6">
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center gap-4">
              <div
                className="flex items-center justify-center"
                style={{
                  width: 32,
                  height: 32,
                  backgroundColor: FSO_GOLD,
                }}
              >
                <span
                  className="ai-mono"
                  style={{ fontSize: 13, fontWeight: 700, color: "#0a0a1a", letterSpacing: "0.04em" }}
                >
                  EY
                </span>
              </div>
              <div>
                <div
                  style={{
                    fontSize: 15,
                    color: "#f1f5f9",
                    fontWeight: 500,
                    letterSpacing: "0.01em",
                  }}
                >
                  FSO · AI Intelligence Brief
                </div>
                <div
                  className="ai-mono"
                  style={{
                    fontSize: 10,
                    letterSpacing: "0.22em",
                    color: "#64748b",
                    textTransform: "uppercase",
                  }}
                >
                  Financial Services · AI &amp; Data
                </div>
              </div>
            </div>
            <div className="flex items-center gap-6">
              {/* FSO Filter Toggle */}
              <button
                onClick={() => setFsoFilter(!fsoFilter)}
                className="flex items-center gap-2 px-3 py-2 border transition-colors"
                style={{
                  borderColor: fsoFilter ? "rgba(251,191,36,0.50)" : "#1c1f3f",
                  backgroundColor: fsoFilter ? "rgba(251,191,36,0.08)" : "transparent",
                }}
              >
                <div
                  className="relative"
                  style={{ width: 28, height: 16, borderRadius: 8, backgroundColor: fsoFilter ? FSO_GOLD : "#334155", transition: "background-color 200ms" }}
                >
                  <div
                    style={{
                      position: "absolute",
                      top: 2,
                      left: fsoFilter ? 14 : 2,
                      width: 12,
                      height: 12,
                      borderRadius: 6,
                      backgroundColor: fsoFilter ? "#0a0a1a" : "#64748b",
                      transition: "left 200ms, background-color 200ms",
                    }}
                  />
                </div>
                <span
                  className="ai-mono"
                  style={{
                    fontSize: 10,
                    letterSpacing: "0.14em",
                    color: fsoFilter ? FSO_GOLD : "#64748b",
                  }}
                >
                  FSO FILTER
                </span>
              </button>
              <div className="text-right">
                <div
                  className="ai-mono"
                  style={{
                    fontSize: 11,
                    letterSpacing: "0.18em",
                    color: "#94a3b8",
                  }}
                >
                  WEEK 18 · 2026
                </div>
                <div
                  className="ai-mono"
                  style={{ fontSize: 10, color: "#475569" }}
                >
                  REFRESHED {refreshedAt}
                </div>
              </div>
            </div>
          </div>
          <nav className="flex items-center gap-1" style={{ marginBottom: -1 }}>
            {tabs.map((t) => {
              const active = tab === t.id;
              return (
                <button
                  key={t.id}
                  onClick={() => setTab(t.id)}
                  className="ai-mono px-5 py-3 transition-colors"
                  style={{
                    fontSize: 12,
                    letterSpacing: "0.18em",
                    textTransform: "uppercase",
                    color: active ? "#fef3c7" : "#64748b",
                    borderBottom: active
                      ? `2px solid ${FSO_GOLD}`
                      : "2px solid transparent",
                  }}
                  onMouseEnter={(e) => {
                    if (!active) e.currentTarget.style.color = "#cbd5e1";
                  }}
                  onMouseLeave={(e) => {
                    if (!active) e.currentTarget.style.color = "#64748b";
                  }}
                >
                  {t.label}
                </button>
              );
            })}
            <div
              className="ai-mono ml-auto flex items-center gap-2 pb-3"
              style={{
                fontSize: 10,
                letterSpacing: "0.18em",
                color: "#475569",
              }}
            >
              <Activity size={11} style={{ color: "#34d399" }} />
              AGENT · LIVE
            </div>
          </nav>
        </div>
      </header>

      <main className="max-w-[1400px] mx-auto px-8 py-10">
        {tab === "briefing" && <WeeklyBriefing fsoFilter={fsoFilter} />}
        {tab === "papers" && <ResearchPapers fsoFilter={fsoFilter} />}
        {tab === "pulse" && <AIPulse fsoFilter={fsoFilter} />}
        {tab === "social" && <SocialMedia fsoFilter={fsoFilter} />}
        {tab === "architecture" && <ArchitectureTab />}
      </main>

      <footer
        className="border-t mt-20"
        style={{ borderColor: "#1c1f3f" }}
      >
        <div
          className="ai-mono max-w-[1400px] mx-auto px-8 py-5 flex items-center justify-between"
          style={{
            fontSize: 10,
            letterSpacing: "0.18em",
            color: "#475569",
          }}
        >
          <div>EY FSO INTERNAL · AI &amp; DATA · DO NOT DISTRIBUTE</div>
          <div>BUILD 2026.18.04 · COMPILED 06:14 UTC</div>
        </div>
      </footer>
    </div>
  );
}
