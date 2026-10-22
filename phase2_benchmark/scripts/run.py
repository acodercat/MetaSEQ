"""Unified benchmark runner.

Usage:
    python -m scripts.run --model deepseek                                       # every domain in the registry
    python -m scripts.run --domain HK --model deepseek                           # one domain
    python -m scripts.run --domain HK --model deepseek --category data_retrieval # one category
    python -m scripts.run --domain HK --model deepseek --benchmark calm_wind     # by name
    python -m scripts.run --model deepseek --exp myexp/run2                      # repeat run (nested exp)
    python -m scripts.run --model deepseek --topology multi                      # multi-agent topology

Output: experiments/{exp}/{domain}/{category}/{benchmark}/{model}_{ts}.json
(--exp may nest, e.g. Neuro-Air/single-agent/run1, to separate arms/repeats.)
Runs are resumable (completed benchmarks are skipped unless --no-skip).
"""

import argparse
import asyncio
import importlib
import json
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from adapters import CaveAgentFactory
from adapters.multiagent_adapter import MultiAgentCaveFactory
from cave_agent.models import LiteLLMModel
from cave_agent.models.litellm import _LiteLLMStreamResponse
from config import BENCHMARKS_JSON, MODELS_TOML, PROJECT_ROOT
from core.llm import ModelRegistry
from core.results import main_result_files, result_is_complete, sanitize_model_id
from runner import evaluate

EXPERIMENTS_DIR = PROJECT_ROOT / "experiments"


class _StreamWithUsage(_LiteLLMStreamResponse):
    async def _open_stream(self):
        import litellm

        params = self._model._prepare_params(self._messages)
        return await litellm.acompletion(**params, stream=True,
                                         stream_options={"include_usage": True})


class UsageReportingModel(LiteLLMModel):
    """`LiteLLMModel` whose streamed calls ask for token usage.

    cave-agent 0.7 streams every agent step without `stream_options`, so an
    OpenAI-compatible endpoint sends no usage and each streamed step counted
    0 tokens. Asked for on the streamed path only: a non-streamed call rejects
    `stream_options`. Response content is unaffected.
    """

    def stream(self, messages):
        return _StreamWithUsage(self, messages)


def build_cave_agent_model(model_name: str) -> tuple[LiteLLMModel, str]:
    """Build cave_agent's OpenAI-compatible model wrapper from a models.toml entry.

    `LiteLLMModel` is cave_agent's own model class (unrelated to the deleted
    `adapters/litellm_adapter.py`). All AirBench-configured endpoints are
    OpenAI-compatible, so we hard-code custom_llm_provider="openai".
    Returns (model, api_model_id).
    """
    cfg = ModelRegistry.load(MODELS_TOML).get(model_name)
    kwargs = dict(
        model_id=cfg.api_model,
        api_key=cfg.api_key,
        custom_llm_provider="openai",
    )
    if cfg.base_url:
        kwargs["base_url"] = cfg.base_url
    if cfg.max_tokens:
        kwargs["max_tokens"] = cfg.max_tokens
    if cfg.timeout:
        kwargs["timeout"] = cfg.timeout
    # Transport-level resilience: let litellm retry transient failures
    # (esp. 429 RateLimitError) with exponential backoff + Retry-After, so a
    # rate-limited call recovers instead of returning steps=0. Purely a
    # networking concern — identical for single and multi, and never changes
    # the content of a successful response — so it does not touch the frozen
    # config fingerprint or the fairness of the ablation.
    kwargs["num_retries"] = 10
    if cfg.extra_body:
        kwargs["extra_body"] = dict(cfg.extra_body)
    # Send a top-level temperature unless the config routes it through
    # extra_body (some self-hosted endpoints want it in the raw body), so we
    # never send it twice.
    if not (cfg.extra_body and "temperature" in cfg.extra_body):
        kwargs["temperature"] = cfg.temperature
    return UsageReportingModel(**kwargs), cfg.api_model


def load_domain(domain: str):
    """Load a domain module. Convention: domains.{domain}"""
    return importlib.import_module(f"domains.{domain}")


def load_benchmarks_config() -> dict:
    """Load benchmark registry from benchmarks.json."""
    if not BENCHMARKS_JSON.exists():
        raise FileNotFoundError(f"{BENCHMARKS_JSON} not found.")
    with open(BENCHMARKS_JSON) as f:
        return json.load(f)


def resolve_benchmarks(
    domain: str,
    categories: list[str] | None = None,
    names: list[str] | None = None,
) -> list[tuple[str, str, str]]:
    """Resolve benchmarks from the registry.

    Returns list of (name, category, path) tuples.
    """
    registry = load_benchmarks_config()
    if domain not in registry:
        raise ValueError(
            f"Domain '{domain}' not found in {BENCHMARKS_JSON}. "
            f"Available: {sorted(registry.keys())}"
        )

    domain_cfg = registry[domain]
    results = []

    if names:
        all_benchmarks = {}
        for cat, benchmarks in domain_cfg.items():
            for bench_name, bench_path in benchmarks.items():
                all_benchmarks[bench_name] = (cat, bench_path)

        for name in names:
            if name not in all_benchmarks:
                raise ValueError(
                    f"Benchmark '{name}' not found for domain '{domain}'. "
                    f"Available: {sorted(all_benchmarks.keys())}"
                )
            cat, path = all_benchmarks[name]
            results.append((name, cat, path))

    elif categories:
        for cat in categories:
            if cat not in domain_cfg:
                raise ValueError(
                    f"Category '{cat}' not found for domain '{domain}'. "
                    f"Available: {sorted(domain_cfg.keys())}"
                )
            for bench_name, bench_path in domain_cfg[cat].items():
                results.append((bench_name, cat, bench_path))

    else:
        for cat, benchmarks in domain_cfg.items():
            for bench_name, bench_path in benchmarks.items():
                results.append((bench_name, cat, bench_path))

    return results


# ---------------------------------------------------------------------------
# Evaluation core (shared by the CLI)
# ---------------------------------------------------------------------------

def is_benchmark_complete(bench_dir: Path, model_id: str) -> bool:
    """True if any main result file for `model_id` is fully evaluated.

    "Fully evaluated" (see `core.results.result_is_complete`) means every
    turn carries a `success` verdict — pass OR fail — and no turn has an
    infrastructure `error`. Results frozen by an API/DB outage are therefore
    NOT complete: resume retries them instead of permanently recording the
    outage as a model failure. Sibling files (`*_scores.json`, `*_claims.json`)
    are excluded so an RQ/CC output can never mask a missing PV result.
    """
    for f in main_result_files(bench_dir, f"{model_id}_*.json"):
        try:
            data = json.loads(f.read_text())
        except (json.JSONDecodeError, OSError):
            continue  # truncated/corrupt file — treat as not complete
        if result_is_complete(data):
            return True
    return False


def build_factory(topology: str, model, domain_mod):
    """Build the single- or multi-agent factory for a domain.

    Both topologies share the domain's prompt / variables / functions; only the
    factory class differs, so single vs multi is a matched comparison.
    """
    factory_cls = MultiAgentCaveFactory if topology == "multi" else CaveAgentFactory
    return factory_cls(
        model,
        system_instructions=domain_mod.SYSTEM_PROMPT,
        base_variables=domain_mod.BASE_VARIABLES,
        extra_functions=getattr(domain_mod, "EXTRA_FUNCTIONS", []),
    )


async def run_domain(
    model,
    model_id: str,
    domain: str,
    topology: str,
    output_root: Path,
    *,
    categories: list[str] | None = None,
    names: list[str] | None = None,
    skip: bool = True,
) -> None:
    """Evaluate a domain's benchmarks into
    ``output_root/{domain}/{category}/{name}/{model_id}_{ts}.json``.

    Completed benchmarks are skipped unless ``skip=False`` (resumable). Shared by
    the single-domain CLI and the all-domains loop in ``main()``.
    """
    domain_mod = load_domain(domain)
    factory = build_factory(topology, model, domain_mod)
    benchmarks = resolve_benchmarks(domain, categories, names)

    to_run, skipped = [], 0
    for name, category, bench_path in benchmarks:
        bench_dir = output_root / domain / category / name
        if skip and is_benchmark_complete(bench_dir, model_id):
            skipped += 1
        else:
            to_run.append((name, category, bench_path))

    print(f"[{domain}] {len(benchmarks)} benchmarks, {skipped} skipped, {len(to_run)} to run")
    for i, (name, category, bench_path) in enumerate(to_run, 1):
        print(f"  [{i}/{len(to_run)}] [{category}] {name}")
        scenarios = json.loads(Path(bench_path).read_text())
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output = output_root / domain / category / name / f"{model_id}_{timestamp}.json"
        await evaluate(factory, scenarios, str(output))


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

async def main():
    parser = argparse.ArgumentParser(
        description="Run air-bench evaluations",
        epilog="Examples:\n"
               "  python -m scripts.run --model gemini                        # all domains\n"
               "  python -m scripts.run --domain HK --model gemini --exp exp2\n"
               "  python -m scripts.run --model gemini --exp exp2/run2         # repeat run (nested exp)\n"
               "  python -m scripts.run --model gemini --topology multi\n",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--domain", default=None,
                        help="Domain to evaluate (e.g. HK, HB, Beijing). "
                             "Omit to run every domain in the registry.")
    parser.add_argument("--model", required=True,
                        help="Model section name in models.toml (e.g. deepseek, qwen35)")
    parser.add_argument("--exp", default=None, dest="exp_id", metavar="ID",
                        help="Experiment identifier — directory name under experiments/ "
                             "(default: {model_id}_{YYYYMMDD}_{HHMMSS}). May contain '/' "
                             "to nest arms/repeats, e.g. Neuro-Air/single-agent/run1.")
    parser.add_argument("--category", nargs="+", default=None,
                        help="Capability categories (e.g. data_retrieval spatial_analysis)")
    parser.add_argument("--benchmark", nargs="+", default=None,
                        help="Benchmark names (e.g. station_reading osm_poi)")
    parser.add_argument("--no-skip", action="store_true",
                        help="Disable auto-skip of completed benchmarks")
    parser.add_argument("--topology", choices=["single", "multi"], default="single",
                        help="Agent topology: 'single' (one CaveAgent, default) or "
                             "'multi' (Coordinator + 5 workers over a shared runtime). "
                             "Everything else (model, domain, benchmarks, prompts) is "
                             "held identical, so the two are a matched ablation.")
    args = parser.parse_args()

    if args.benchmark and args.category:
        parser.error("--benchmark and --category are mutually exclusive")
    if (args.benchmark or args.category) and not args.domain:
        parser.error("--benchmark/--category are per-domain, so they require --domain")

    model, api_model_id = build_cave_agent_model(args.model)
    model_id = sanitize_model_id(api_model_id)

    exp_id = args.exp_id or f"{model_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    # Results root: experiments/{exp}; run_domain appends {domain}/... . exp_id may
    # nest ('/') to separate arms/repeats, e.g. Neuro-Air/single-agent/run1. Anchored
    # to PROJECT_ROOT so the scoring/stats scripts find results regardless of cwd.
    output_root = EXPERIMENTS_DIR / exp_id

    domains = [args.domain] if args.domain else list(load_benchmarks_config().keys())

    print(f"Model:      {model_id}")
    print(f"Experiment: {exp_id}")
    print(f"Topology:   {args.topology}")
    print(f"Domains:    {', '.join(domains)}")

    for domain in domains:
        await run_domain(
            model, model_id, domain, args.topology, output_root,
            categories=args.category, names=args.benchmark, skip=not args.no_skip,
        )


if __name__ == "__main__":
    asyncio.run(main())
