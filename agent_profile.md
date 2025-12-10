- **L2 Research & Analysis Layer**
  - *Positioning*: Core productivity layer, containing experts in macroeconomics, industry, company fundamentals, commodities, funds, and sentiment.
- **L4 Risk & Compliance Layer**
  - *Positioning*: Gatekeeper, responsible for risk channel review, regulatory compliance, and suitability checks.
- **L1 Management & Cognitive Layer**
  - *Positioning*: The brain of the system, responsible for task orchestration (Orchestrator) and final decision-making (CIO).
- **L5 Execution & Generation Layer**
  - *Positioning*: The hands of the system, responsible for structured chain-of-thought recording and final report generation. :contentReference[oaicite:3]{index=3}  

### 2.2 MasRouter: Action Space of the Reinforcement Learning Router

The core task of MasRouter is to learn **“under which problem, hire which experts, and in what collaboration mode.”**

**Action space \(A = (m, \mathbf{r})\):**

1. **Collaboration Mode \(m\)**  
   - \(m \in \{\text{Star}, \text{Chain}, \text{Debate}, \text{Tree}\}\)  
   - Determines the interaction topology among agents within the same layer (e.g., independent analysis and aggregation, or internal debate).  

2. **Role Vector \(\mathbf{r}\)**  
   - In RL implementation, still a finite-dimensional multi-hot vector mapped to the system-level agent set.  
   - In practical engineering, some “general/tool-type” agents can be downgraded to Tools, and routing is learned only for core system-level agents to keep the action space manageable. :contentReference[oaicite:4]{index=4}  

---

## 3. Detailed Configuration of Core Agents (Reordered by the New Four-Layer Organizational Mimicry)

> This section reorganizes and completes the V3.0 content according to the latest **L1–L2–L3–L4 four-layer structure** and your assigned responsible persons.  
> The current version includes **25 system-level agents**, with some optionally downgraded to tools or merged as routing units, satisfying KPI-2 “≥20 system-level agents collaborating.”

### 3.1 L1 Management & Orchestration Layer (2 Agents)

| ID | Agent Name | Owner | Core Responsibilities |
| :-- | :-- | :-- | :-- |
| 01 | Capital Market Cognitive Decision-Making Agent | TBD | Acts as the “Chief Cognition Officer (CIO)”, ensuring **logical completeness and directional alignment** of the overall research conclusion; exercises veto power for major risks, organizes reviews, and dynamically adjusts agent weights and collaboration rules. |
| 02 | Task Parsing & Collaboration Orchestration Agent | TBD | Parses user questions, performs **task decomposition, intent recognition, agent routing**; selects collaboration modes (Star/Chain/Debate/CoT), generates routing traces, and invokes MasRouter RL policy with rule-based fallback strategies. |

---

### 3.2 L2 Analysis Layer (Research–Advisory–Sentiment–Behavior)

The L2 layer hosts most of the system’s cognitive production, divided into **Macroeconomic Analysis / Fundamental Analysis / Sentiment Analysis / Technical Analysis / Behavioral Analysis** groups.

---

#### 3.2.1 Macro Analysis Team (3 Agents)

| ID | Agent Name | Owner | Core Responsibilities |
| :-- | :-- | :-- | :-- |
| 03 | Macroeconomics & Monetary Policy Research Agent | Wang Meiyi | Analyzes macro cycles (recovery/overheating/stagflation/recession), monetary/fiscal/regulatory policy direction and marginal shifts; constructs macro factors such as interest rates, inflation, growth, liquidity, and risk premiums, providing macro scenarios and inputs for industry, company, and risk layers. |
| 04 | Industry Chain & Sector Structure Research Agent | Ou Xingyu | Studies industries from the perspectives of **industry chain–value chain–ecosystem**; identifies lifecycle stages, measures industry concentration (HHI), analyzes cost/policy transmission along the chain, and assesses competitive structure. |
| 05 | Commodity Valuation & Futures Strategy Agent | Zhu Haoran | Analyzes supply-demand, inventory, spot–futures basis, and term structure of major commodities; designs hedging/arbitrage strategies (intertemporal, inter-product, cross-market), outputs hedge ratios and commodity risk factors for portfolios and risk layers. |

---

#### 3.2.2 Fundamental Analysis Team (3 Agents)

| ID | Agent Name | Owner | Core Responsibilities |
| :-- | :-- | :-- | :-- |
| 06 | Annual Report & Fundamental Analysis Agent | Yang Yang | Performs structured parsing of long-text documents like annual/quarterly reports and announcements; extracts business structure, profit model, governance, shareholding, risk items, forming a “company profile” for valuation and risk agents. |
| 07 | Financial Statement & General Valuation Agent | Yang Yang | Conducts ratio analysis (profitability, solvency, efficiency), applies DCF / PE / PB / EV/EBITDA frameworks, outputs valuation ranges and percentiles, and performs financial risk warnings (Z-score, Ohlson O-score). |
| 08 | Hard-Tech & Sci-Tech Innovation Valuation Agent | Yang Yang | Evaluates hard-tech firms using non-traditional indicators such as technology roadmap, patent barriers, R&D intensity, and TRL; produces scenario-tree-based valuation ranges with sensitivity analysis. |

---

#### 3.2.3 Sentiment Analysis Team (4 Agents)

> Fully aligned with the “macro / meso / micro” sentiment perception structure, including a dedicated capital-flow sentiment agent.

| ID | Agent Name | Owner | Core Responsibilities |
| :-- | :-- | :-- | :-- |
| 09 | Macro Sentiment Perception Agent | Sentiment Team | Monitors macro-level sentiment (policy commentary, economic outlook, geopolitical events), extracts polarity and policy uncertainty indices, builds macro sentiment heat indices for macro and risk agents. |
| 10 | Industry Sentiment Perception Agent | Sentiment Team | Tracks industry-level policies and events, builds “industry sentiment indices” via topic modeling and sentiment aggregation, analyzes impacts on industry fundamentals and valuation anchors. |
| 11 | Stock-Level Sentiment Perception Agent | Sentiment Team | Tracks micro-level sentiment (company news, announcement interpretation, social media discussion), outputs stock sentiment thermometer and turning points for trading and risk layers. |
| 12 | Capital-Flow Sentiment Agent | Gong Haoran | Uses northbound/southbound flows, institutional vs retail flows, and microstructure metrics (turnover, order book imbalance, Amihud liquidity) to build greed–fear indices and capital sentiment factors. |

---

#### 3.2.4 Technical Analysis Team (2 Agents)

| ID | Agent Name | Owner | Core Responsibilities |
| :-- | :-- | :-- | :-- |
| 13 | Market & Industry Index Time-Series Forecasting Agent | Gong Haoran | Builds ARIMA/GARCH/LSTM/Transformer models for index prediction and volatility forecasting; constructs trend/volatility/volume-price factors for portfolio and risk layers. |
| 14 | Stock Technical Analysis Agent | Gong Haoran | Analyzes K-line patterns, technical indicators, and price–volume relations; outputs buy/sell signals (technical dimension only), backtests signal reliability, and provides actionable signals for portfolios. |

---

#### 3.2.5 Behavioral Analysis Team (3 Agents)

| ID | Agent Name | Owner | Core Responsibilities |
| :-- | :-- | :-- | :-- |
| 15 | Analyst Reports & Viewpoint Integration Agent | Ling Long | Parses sell-side reports, extracts ratings, target prices, key assumptions, scenario analyses; builds “consensus–divergence maps” and quantifies expectation gaps. |
| 16 | Fund & Fund Manager Analysis Agent | Ling Long | Profiles funds/fund managers using performance, factor exposures, drawdowns, and style stability; supports product recommendations, asset allocation, and portfolio construction. |
| 17 | Client Profiling (Risk Preference) Agent | Ling Long | Constructs risk profiles using client information, financial status, investment experience, and KYC data; links with portfolios and compliance layers for suitability assessment. |

---

### 3.3 L3 Valuation–Risk–Compliance–Portfolio–General Layer (7 Agents)

This layer transforms L2’s fragmented insights into structured valuation, risk evaluation, compliance enforcement, and portfolio decisions.

---

#### 3.3.1 Valuation: Primary & Secondary Market Valuation Agent (1 Agent)

| ID | Agent Name | Owner | Core Responsibilities |
| :-- | :-- | :-- | :-- |
| 18 | Primary & Secondary Market Valuation Agent | Hu Lintao | Finalizes valuation for both IPO-stage and listed companies using comparable analysis, case studies, and scenario DCF; outputs valuation scores and labels (overvalued/neutral/undervalued) for portfolio decisions. |

---

#### 3.3.2 Risk: Price-Risk & Fundamental-Risk Agents (2 Agents)

| ID | Agent Name | Owner | Core Responsibilities |
| :-- | :-- | :-- | :-- |
| 19 | Market Price Risk Agent | Yan Mengyi | Computes VaR/ES/volatility/Beta/drawdowns; evaluates liquidity risk and market impact; performs scenario and stress testing. |
| 20 | Fundamental Risk Agent | Li Fangfang | Evaluates profitability quality, cash-flow health, leverage risk; applies Z-score, O-score, ESG/green-risk frameworks to produce fundamental risk scores. |

---

#### 3.3.3 Compliance: Regulatory Review & Suitability Matching (2 Agents)

| ID | Agent Name | Owner | Core Responsibilities |
| :-- | :-- | :-- | :-- |
| 21 | Regulatory Compliance Review Agent | Qian Chen | Matches investment advice/products against regulatory rules; uses rule graphs and reasoning engines to detect violations and produce compliance rectification suggestions. |
| 22 | Suitability & Risk Tolerance Matching Agent | Liu Yang | Matches client risk levels (from L2 profiling) with product/portfolio risks; outputs “prohibit/warning/manual review” signals and automatically generates required disclosure statements. |

---

#### 3.3.4 Portfolio: Portfolio Optimization & Backtesting Agent (1 Agent)

| ID | Agent Name | Owner | Core Responsibilities |
| :-- | :-- | :-- | :-- |
| 23 | Portfolio Optimization & Backtesting Agent | Hu Lintao | Integrates valuation, risk, sentiment, technical, and capital-flow factors to determine allocations; uses mean–variance, risk parity, and robust optimization (with VaR/ES constraints); runs backtests and produces standardized portfolios for different client risk levels. |

---

#### 3.3.5 General: General Business & Data Support Agent (1 Agent)

| ID | Agent Name | Owner | Core Responsibilities |
| :-- | :-- | :-- | :-- |
| 24 | General Business & Data Support Agent | TBD | Provides ETL, feature engineering, factor construction; connects with macro databases, financial reports, sentiment databases, and regulatory libraries; supports RAG retrieval. |

> Note: In RL, this agent often functions more like a collection of tools rather than a single routable role.

---

### 3.4 L4 Integrated Reasoning & Report Generation Layer (1 Agent)

| ID | Agent Name | Owner | Core Responsibilities |
| :-- | :-- | :-- | :-- |
| 25 | Integrated Reasoning & Report Generation Agent | TBD | Aggregates outputs from L1–L3 and completes global reasoning; produces structured reports including “question → collaboration trace → intermediate analysis → conclusion → risk & compliance opinions → suitability notes”; outputs versions tailored for researchers, portfolio managers, clients, and regulators; generates valuation charts, risk radar charts, and attribution visualizations. |
