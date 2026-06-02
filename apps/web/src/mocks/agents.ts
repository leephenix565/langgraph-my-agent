import type { AgentCatalogModel } from "../types/agents";

export const AGENT_CATALOG: AgentCatalogModel = {
  "totals": {
    "configCount": 21,
    "runtimeCount": 21,
    "disabledIds": []
  },
  "layers": [
    {
      "layer": "L1",
      "agents": [
        {
          "id": "a01_cio_orchestrator",
          "name": "资本市场决策协作智能体",
          "description": "功能：基于大语言模型完成复杂金融任务的拆解与路由编排，分层协作组织多类底层专业能力，在执行与汇总阶段引入结构化约束与证据校验，实现稳定可控的多智能体协同。\n输入：用户的复杂自然语言提问/业务指令（如“评估某行业受宏观政策影响及个股投资价值”）；底层各智能体的状态反馈。\n输出：任务拆解与路由编排结论方案；多智能体协同调用日志；最终的综合分析决策结果指引。",
          "capabilities": [
            "orchestration",
            "routing",
            "evidence_control"
          ],
          "layer": "L1",
          "team": "management",
          "roleType": "system",
          "defaultEnabled": true
        }
      ]
    },
    {
      "layer": "L2",
      "agents": [
        {
          "id": "a03_macro_industry_research",
          "name": "宏观经济与产业链行业研究智能体",
          "description": "功能：捕捉宏观经济指标非线性关联，实现经济周期拐点预测；通过动态图神经网络实现产业链结构演化路径量化与行业竞争格局动态推演。\n输入：宏观经济数据（GDP/CPI/M2/利率等）、货币政策文本、产业链上下游结构数据、行业供需指标及进出口数据。\n输出：宏观经济趋势及拐点预测报告；跨周期风险热力图；产业链韧性评估与竞争策略模拟方案。",
          "capabilities": [
            "macro",
            "industry_chain",
            "cycle_prediction"
          ],
          "layer": "L2",
          "team": "fundamental",
          "roleType": "system",
          "defaultEnabled": true
        },
        {
          "id": "a04_commodity_hedging",
          "name": "商品定价分析智能体",
          "description": "功能：分析大宗商品期货市场的定价影响力与境内外市场定价关系，比较中国期货市场与境外相关市场之间的影响力变化。\n输入：商品品种、时间范围、时间窗口、交易时段，以及定价影响力或期货市场影响力分析意图。\n输出：商品定价影响力指标、双向影响力对比、指定窗口和时段下的结构变化说明。该智能体不作为通用实时行情预测、交易建议或投资预测工具。",
          "capabilities": [
            "commodity_pricing",
            "pricing_influence",
            "futures_market"
          ],
          "layer": "L2",
          "team": "fundamental",
          "roleType": "system",
          "defaultEnabled": true
        },
        {
          "id": "a05_annual_report_analysis",
          "name": "公司年报分析智能体",
          "description": "功能：运用深度学习从长文本年报（尤其是MD&A管理层讨论）中提取关键经营数据并进行情感倾向分析，发掘企业隐性价值及战略转向。\n输入：上市公司年度财务报告（PDF/长文本格式）、公司日常重大公告、同行业企业可比年报。\n输出：年报核心财务与业务摘要；管理层情感偏离度打分（乐观/悲观态度量化）；隐性风险提示点。",
          "capabilities": [
            "annual_report",
            "mdna",
            "text_sentiment"
          ],
          "layer": "L2",
          "team": "fundamental",
          "roleType": "system",
          "defaultEnabled": true
        },
        {
          "id": "a06_financial_statement_analysis",
          "name": "公司财报分析智能体",
          "description": "功能：结合结构化财务指标（三大表）与非结构化附注文本，通过多模态特征融合模型，评估企业真实盈利能力、营运效率，识别粉饰报表风险。\n输入：结构化财务数据（资产负债表、利润表、现金流量表季度/年度数据）、财务报表附注文本。\n输出：综合财务健康度评分（如Z-score变体）；异常财务指标预警；杜邦分析拆解归因结果。",
          "capabilities": [
            "financial_statement",
            "profitability",
            "fraud_risk"
          ],
          "layer": "L2",
          "team": "fundamental",
          "roleType": "system",
          "defaultEnabled": true
        },
        {
          "id": "a07_macro_sentiment",
          "name": "宏观情绪感知智能体",
          "description": "功能：实时监控并量化全市场的宏观新闻与社交媒体舆情，构建宏观市场健康指数，洞察大盘整体资金的风险偏好与情绪周期变化。\n输入：宏观经济新闻报道、央行及监管机构动态/发言、知名机构观点、全网主流社交媒体大盘情绪文本。\n输出：宏观市场情感量化指数；市场健康指数实时数值；情绪拐点预警与风险偏好状态（Risk-On/Off）。",
          "capabilities": [
            "macro_sentiment",
            "market_health",
            "risk_preference"
          ],
          "layer": "L2",
          "team": "sentiment",
          "roleType": "system",
          "defaultEnabled": true
        },
        {
          "id": "a08_industry_hotspot",
          "name": "行业热点洞悉智能体",
          "description": "功能：基于语义检索与主题动态提取模型，实时跟踪行业新闻热点，计算细粒度行业情感得分，识别资金与舆论共振的板块轮动方向。\n输入：行业主流媒体新闻、产业链相关政策文本、投资者社区各行业板块的高频讨论帖。\n输出：行业热点主题词云及演化路径图；细粒度行业情绪热力图；短期行业主题轮动预测信号。",
          "capabilities": [
            "industry_hotspot",
            "topic_mining",
            "sector_rotation"
          ],
          "layer": "L2",
          "team": "sentiment",
          "roleType": "system",
          "defaultEnabled": true
        },
        {
          "id": "a09_company_sentiment_radar",
          "name": "企业舆情雷达智能体",
          "description": "功能：全天候监控特定企业的多源舆情，从海量新闻中抽取特定事件及其论元，结合风险级联演化模型评估舆情发酵对个股的冲击。\n输入：企业相关新闻、自媒体评论、投资者互动平台问答、产品投诉数据、各类突发事件文本。\n输出：企业实时情感得分；具体事件抽取结果（时间/主体/触发词）；负面舆情预警及风险传染推演。",
          "capabilities": [
            "company_sentiment",
            "event_extraction",
            "risk_contagion"
          ],
          "layer": "L2",
          "team": "sentiment",
          "roleType": "system",
          "defaultEnabled": true
        },
        {
          "id": "a10_stock_technical_analysis",
          "name": "个股技术分析智能体",
          "description": "功能：运用可视图模型等时序分析技术，对个股历史量价进行图谱化特征提取，捕捉趋势动量、支撑/阻力位及异动形态。\n输入：个股高频及日频的量价数据（开/高/低/收、成交量、换手率）、资金流向明细、融资融券余额。\n输出：经典技术形态识别结果（如突破、背离）；短期趋势及动量研判结论；异常交易异动警报。",
          "capabilities": [
            "stock_technical",
            "momentum",
            "support_resistance"
          ],
          "layer": "L2",
          "team": "technical",
          "roleType": "system",
          "defaultEnabled": true
        },
        {
          "id": "a11_index_technical_analysis",
          "name": "指数技术分析智能体",
          "description": "功能：针对市场主要指数，进行波动率测算与趋势跟踪，测算市场广度，评估系统性行情的强弱及关键拐点。\n输入：各大宽基/行业指数历史量价序列、成分股涨跌停统计、北向/南向资金净流入、期权隐含波动率。\n输出：指数级别趋势判定；系统性风险/反弹技术面预警；指数估值分位与技术指标共振分析。",
          "capabilities": [
            "index_technical",
            "volatility",
            "market_breadth"
          ],
          "layer": "L2",
          "team": "technical",
          "roleType": "system",
          "defaultEnabled": true
        },
        {
          "id": "a12_research_synthesis",
          "name": "分析师研报与观点集成智能体",
          "description": "功能：利用大模型阅读全市场卖方研报，提取核心逻辑、目标价及盈利预测，识别市场机构的一致预期方向与观点分歧度。\n输入：全市场券商卖方研报（文本）、分析师盈利预测调整明细（EPS、目标价）、研报评级数据。\n输出：一致预期数据统计图表；分析师盈利预测上修/下调趋势动向；研报核心逻辑摘要与观点分歧度测算。",
          "capabilities": [
            "research_synthesis",
            "consensus",
            "forecast_revision"
          ],
          "layer": "L2",
          "team": "behavior",
          "roleType": "system",
          "defaultEnabled": true
        },
        {
          "id": "a13_fund_manager_behavior",
          "name": "基金经理投资行为分析智能体",
          "description": "功能：分析公募及私募机构的历史持仓与净值变动，刻画其投资风格漂移、抱团行为与调仓逻辑。\n输入：基金季报/年报持仓明细（十大重仓等）、基金净值高频序列、基金经理公开发言及路演纪要。\n输出：基金经理投资风格画像归因；投资风格漂移监测；机构抱团股网络识别及抱团松动预警。",
          "capabilities": [
            "fund_manager",
            "position_behavior",
            "style_drift"
          ],
          "layer": "L2",
          "team": "behavior",
          "roleType": "system",
          "defaultEnabled": true
        },
        {
          "id": "a14_ipo_investor_behavior",
          "name": "IPO投资者构成与行为分析智能体",
          "description": "功能：分析IPO网下询价机构与网上散户的认购行为，刻画打新资金情绪与剔除偏好，预测新股定价效率与上市初期的博弈特征。\n输入：IPO招股说明书、网下机构询价明细表、网上中签率数据、新股上市初期的高频分笔交易流水。\n输出：网下机构报价分布特征与“人情报价”识别；打新资金情绪指数；新股首发溢价评估及上市表现预测。",
          "capabilities": [
            "ipo",
            "investor_behavior",
            "pricing_efficiency"
          ],
          "layer": "L2",
          "team": "behavior",
          "roleType": "system",
          "defaultEnabled": true
        },
        {
          "id": "a15_entity_relation_extraction",
          "name": "实体关系抽取智能体",
          "description": "功能：从非结构化文本中抽取金融实体及其关联（如共同投资、一致行动、上下游），更新底层的穿透式关联网络与图数据库（如Neo4j）。\n输入：财经新闻报道、招股说明书、法院判决书、企业股权披露文件等高潜关联文本。\n输出：结构化的实体知识三元组（实体-关系-实体）；动态更新的股票/基金关联网络与资本派系图谱。",
          "capabilities": [
            "entity_relation",
            "knowledge_graph",
            "capital_network"
          ],
          "layer": "L2",
          "team": "behavior",
          "roleType": "system",
          "defaultEnabled": true
        }
      ]
    },
    {
      "layer": "L3",
      "agents": [
        {
          "id": "a16_ml_valuation",
          "name": "机器学习估值智能体",
          "description": "功能：学习多因子间的非线性交互关系（如研发占比与ROE提升的指数级溢价）；结合动态窗口学习，提取标的前推12个季度的财务演变趋势以捕捉基本面动量，提供非线性创新估值。\n输入：结构化财务指标，包含：成长性因子（营收/利润增长率）、效率因子（资产周转率/毛利率变动）、资本结构因子（资产负债率），及隐性替代数据。\n输出：科创企业内在价值综合评估（非线性定价域）；无形资产与技术创新效用的量化溢价贡献率。",
          "capabilities": [
            "ml_valuation",
            "nonlinear_factors",
            "innovation_premium"
          ],
          "layer": "L3",
          "team": "valuation",
          "roleType": "system",
          "defaultEnabled": true
        },
        {
          "id": "a17_traditional_valuation",
          "name": "传统估值智能体",
          "description": "功能：实现传统经典模型的自动化进阶，例如通过蒙特卡洛模拟针对WACC和永续增长率进行上万次随机模拟以输出估值概率分布；并针对现金流极其稳定的标的自动切换动态分红折现模型。\n输入：实时无风险利率（如10年期国债收益率）、Beta值（结合标的与沪深300相关性）、基于经营性净现金流减去资本开支推算的自由现金流（FCFF）及一致预期数据。\n输出：绝对估值模型测算结果（如DCF目标价域）；同业相对估值对比矩阵；不同假设情景下的敏感性分析。",
          "capabilities": [
            "dcf",
            "relative_valuation",
            "sensitivity_analysis"
          ],
          "layer": "L3",
          "team": "valuation",
          "roleType": "system",
          "defaultEnabled": true
        },
        {
          "id": "a18_meta_valuation",
          "name": "元学习估值智能体",
          "description": "功能：在宏观体制转换或突发黑天鹅事件中，利用元学习实现少样本快速自适应，提供跨周期、跨情境的动态估值修正。\n输入：宏观突变事件标签、行业极端政策冲击信号、跨市场相似历史情境的少量映射数据、标的高频波动指标。\n输出：结构突变下的自适应估值调整幅度；极端冲击情境下（如黑天鹅事件）的目标价压力测试结果。",
          "capabilities": [
            "meta_learning",
            "scenario_adaptation",
            "stress_test"
          ],
          "layer": "L3",
          "team": "valuation",
          "roleType": "system",
          "defaultEnabled": true
        },
        {
          "id": "a19_risk_identification",
          "name": "风险识别智能体",
          "description": "功能：将监管规则、财务约束与关联关系编码为市场约束图，结合大模型推理生成的候选规则，通过合并标准化，精准测度投机性风险、信用评级风险与市场波动性风险。\n输入：多源风险预警规则、实体网络关联关系（主体联系）、公开财务数据、市场高频交易数据与资产资源预算等结构化上下文。\n输出：面向投机性、信用评级、波动性等典型资本市场风险的识别结果与规则溯源依据；可计算、可比较的结构化风险特征指标。",
          "capabilities": [
            "risk_identification",
            "constraint_graph",
            "risk_rules"
          ],
          "layer": "L3",
          "team": "risk",
          "roleType": "system",
          "defaultEnabled": true
        },
        {
          "id": "a20_compliance_review",
          "name": "合规审查智能体",
          "description": "功能：构建多维度文本评价框架，通过深度理解海量上市公司公告与问询函内容，精准匹配交易所信披评价及监管合规规则，识别潜在违规隐患。\n输入：历年上市公司公告文本、交易所问询函及回复（百万级样本）、交易所信披评价规则库、各项投资者保护与监管规章。\n输出：涵盖十个维度的信披文本综合质量评价与结构化得分；合规性审查诊断结果（标注违规异常隐患及措辞异常特征）。",
          "capabilities": [
            "compliance",
            "disclosure_quality",
            "regulatory_review"
          ],
          "layer": "L3",
          "team": "compliance",
          "roleType": "system",
          "defaultEnabled": true
        },
        {
          "id": "a21_portfolio_manager",
          "name": "投资组合经理智能体",
          "description": "功能：整合多维预测信号，结合用户风险偏好，运用组合优化算法动态生成并调整大类资产配置及股票持仓权重。\n输入：资产池标的预期收益率及协方差矩阵（由底层智能体提供）、用户设定的风险容忍度/最大回撤约束条件。\n输出：最优资产配置方案及成分股权重；投资组合风险敞口（VaR等）评估测算；动态再平衡（调仓）指令建议。",
          "capabilities": [
            "portfolio",
            "asset_allocation",
            "rebalancing"
          ],
          "layer": "L3",
          "team": "investment",
          "roleType": "system",
          "defaultEnabled": true
        }
      ]
    },
    {
      "layer": "L4",
      "agents": [
        {
          "id": "a25_report_center",
          "name": "综合推理结构与报告生成智能体",
          "description": "功能：归集底层所有智能体的图谱、数据与文字推论，按照投研逻辑自动生成结构化、可视化、可交互的多模态研报（日报/周报/复盘）。\n输入：各底层智能体产出的分析结论、指标数值、情感得分、K线图/事件图谱截图；用户设定的报告时间区间。\n输出：自动化生成的智能分析报表（含行情研判、舆情事件追踪、价情联动、多源特征融合预警等完整版块）。",
          "capabilities": [
            "report",
            "synthesis",
            "multimodal_research_report"
          ],
          "layer": "L4",
          "team": "reporting",
          "roleType": "system",
          "defaultEnabled": true
        }
      ]
    }
  ],
  "disabledAgents": []
};
