"""Wall Street Valuation Workbench.

Local-first IB-grade valuation tool for: 人 / 暧昧对象 / 一段感情 / 自己.
Computes EPS, P/E, P/B, DCF, terminal value, WACC, sensitivity tables,
forward-looking scenarios; outputs archetype classification + investment strategy.

Pure Python stdlib. Half-serious meme tool, not financial or relationship advice.
"""

from .models import (
    SchemaField, Schema, Answers, Scenario,
    ValuationCore, RatiosResult, DCFResult, SensitivityResult,
    ArchetypeResult, StrategyResult, ForensicsReport,
    Session,
    IBInputs, DCF3StageResult, MultiplesResult, AssetResult,
    BlendedValuation, MonteCarloResult,
    DynamicField, DynamicSubtheme, DynamicStage, DynamicSchema,
)
from .schemas import get_schema, list_targets, TARGET_LABELS
from .valuation.core import compute_core
from .valuation.ratios import compute_ratios
from .valuation.dcf import compute_dcf, sensitivity_table
from .valuation.archetype import classify, classify_ib
from .valuation.strategy import recommend
from .valuation.ib_engine import (
    aggregate_ib_inputs, compute_dcf_3stage, compute_multiples,
    compute_asset, blend_valuations, monte_carlo,
)
from .forward import build_scenarios, run_pipeline, run_pipeline_ib, build_scenarios_ib
from .dynamic_schema import parse_dyn_schema, get_fallback_schema
from .llm import (
    call_llm, PROVIDERS, ProviderError, probe_connection, CUSTOM_MODEL_SENTINEL,
    parse_llm_json, ParseError,
    build_schema_prompt, FALLBACK_SCHEMA, IB_PARAMS, SIX_STAGES,
    build_forward_prompt, FALLBACK_FORWARD,
    schema_to_summary, answers_to_summary, ib_to_summary,
    build_narrative_prompt, fallback_narrative,
    valuation_to_summary, archetype_to_summary, forward_to_summary,
)
from .session import save_session, load_session, new_session
from .exporter import to_markdown, to_json
from .svg_renderer import (
    render_tear_sheet,
    render_sensitivity_heatmap,
    render_scenario_comparison,
)

__version__ = "0.2.0"

CITATIONS = (
    "Modigliani, F., Miller, M. H. (1958). The Cost of Capital, Corporation Finance and the Theory of Investment. American Economic Review, 48, 261–297.",
    "Modigliani, F., Miller, M. H. (1961). Dividend Policy, Growth, and the Valuation of Shares. Journal of Business, 34, 411–433.",
    "Gordon, M. J. (1962). The Investment, Financing, and Valuation of the Corporation. Irwin.",
    "Sharpe, W. F. (1964). Capital Asset Prices: A Theory of Market Equilibrium. Journal of Finance, 19, 425–442.",
    "Lintner, J. (1965). The Valuation of Risk Assets. Review of Economics and Statistics, 47, 13–37.",
    "Fama, E. F., French, K. R. (1993). Common risk factors in returns. Journal of Financial Economics, 33, 3–56.",
    "Damodaran, A. (2002). Investment Valuation: Tools and Techniques for Determining the Value of Any Asset. Wiley.",
    "Koller, T., Goedhart, M., Wessels, D. (2020). Valuation: Measuring and Managing the Value of Companies. McKinsey & Co.",
    "Markowitz, H. (1952). Portfolio Selection. Journal of Finance, 7, 77–91.",
    "Black, F., Scholes, M. (1973). The Pricing of Options and Corporate Liabilities. Journal of Political Economy, 81, 637–654.",
    "Tversky, A., Kahneman, D. (1979). Prospect Theory. Econometrica, 47, 263–291.",
    "Bowlby, J. (1969). Attachment and Loss, Vol. 1. Basic Books.",
)
