"""The `metaseq` command.

    metaseq suites                          list suites
    metaseq tasks <suite> [--category C]    list a suite's tasks
    metaseq arms                            list the arm catalogue
    metaseq check [<suite> ...]             import every task module and check it
    metaseq run <experiment> [narrowing]    run (resumes; skips completed runs; --dry-run)
    metaseq score <experiment> [narrowing]  re-judge stored runs, no model calls
    metaseq report <experiment> [--model]   tables + paired contrasts
    metaseq port --source ... --suite ...   (re)port a suite from its source corpus

<experiment> is a name under configs/experiments/ or a path to a .toml.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from pathlib import Path

from errors import ConfigurationError, InfrastructureError, TaskSpecificationError


def _selection(args: argparse.Namespace):
    from evaluation.experiment import Selection

    shard = None
    if args.shard:
        index, count = (int(x) for x in args.shard.split("/"))
        if not 0 <= index < count:
            raise ConfigurationError("--shard is INDEX/COUNT with 0 <= INDEX < COUNT")
        shard = (index, count)
    return Selection(args.arm, args.model, args.task, shard)


def cmd_suites(args: argparse.Namespace) -> None:
    from tasks import Suite, available_suites

    for name in available_suites():
        suite = Suite.load(name)
        turns = sum(t.n_turns for t in suite.tasks.values())
        source = suite.source
        origin = f"{source.get('repository')}@{str(source.get('commit', ''))[:10]}"
        dirty = " (dirty tree)" if source.get("dirty") else ""
        domains = ", ".join(suite.domains)
        print(f"{name:16} {len(suite.tasks):3} tasks {turns:3} turns  [{domains}]"
              f"  from {origin}{dirty}")
        print(f"{'':16} {suite.description}")


def cmd_tasks(args: argparse.Namespace) -> None:
    from tasks import Suite

    for task in Suite.load(args.suite).select(categories=args.category):
        difficulty = task.difficulty or "-"
        print(f"{task.category:32} {task.name:48} {difficulty:8} {task.n_turns} turn(s)")


def cmd_arms(args: argparse.Namespace) -> None:
    from agents import load_arms

    for arm in load_arms().values():
        print(f"{arm.name:32} {arm.components:15} {arm.description}")


def cmd_check(args: argparse.Namespace) -> None:
    from domains import get_domain
    from tasks import Suite, available_suites

    failures = 0
    for name in args.suites or available_suites():
        suite = Suite.load(name)
        for domain in suite.domains:
            get_domain(domain)
        for task in suite.tasks.values():
            try:
                task.load()
            except Exception as exc:
                failures += 1
                print(f"FAIL {name}/{task.name}: {type(exc).__name__}: {exc}")
        print(f"{name}: {len(suite.tasks)} tasks checked")
    if failures:
        sys.exit(1)


def cmd_run(args: argparse.Namespace) -> None:
    from evaluation.experiment import ExperimentSpec, run_experiment

    spec = ExperimentSpec.load(args.experiment)
    asyncio.run(run_experiment(spec, _selection(args), rerun=args.rerun,
                               score=not args.no_score, dry_run=args.dry_run))


def cmd_score(args: argparse.Namespace) -> None:
    from evaluation.experiment import ExperimentSpec, rescore_experiment

    asyncio.run(rescore_experiment(ExperimentSpec.load(args.experiment), _selection(args)))


def cmd_report(args: argparse.Namespace) -> None:
    from analysis.failures import collect_failures
    from analysis.outcomes import collect
    from analysis.report import write_report
    from evaluation.experiment import ExperimentSpec
    from evaluation.store import ResultStore
    from settings import settings

    spec = ExperimentSpec.load(args.experiment)
    if args.model:
        unknown = sorted(set(args.model) - set(spec.models))
        if unknown:
            raise ConfigurationError(f"not models of {spec.name}: {unknown}")
        # A subset of the grid, in the experiment's own order.
        spec = spec.model_copy(update={"models": [m for m in spec.models
                                                  if m in args.model]})
    store = ResultStore(settings.results_dir, spec.name)
    outcomes = collect(store)
    if outcomes.empty:
        raise ConfigurationError(f"no stored runs under {store.root}")
    print(write_report(spec, outcomes, store.report_dir, collect_failures(store)))
    print(f"written to {store.report_dir}")


def _domain_pairs(pairs: list[str]) -> dict[str, str]:
    try:
        return dict(pair.split("=", 1) for pair in pairs)
    except ValueError:
        raise ConfigurationError(f"--domain takes LAB=SOURCE pairs, got {pairs}") from None


def cmd_port(args: argparse.Namespace) -> None:
    from settings import settings
    from tasks.porting import port_suite

    result = port_suite(
        args.source, args.registry, args.suite,
        suites_dir=settings.suites_dir,
        domains=_domain_pairs(args.domain or ["hk=HK"]),
        description=args.description, force=args.force,
    )
    dirty = ", dirty tree" if result.dirty else ""
    print(f"ported {result.tasks} tasks to {result.suite_dir}"
          f" (source commit {result.commit[:10]}{dirty})")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="metaseq", description=__doc__.splitlines()[0])
    parser.add_argument("-v", "--verbose", action="store_true")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("suites", help="list suites").set_defaults(func=cmd_suites)
    p = sub.add_parser("tasks", help="list a suite's tasks")
    p.add_argument("suite")
    p.add_argument("--category", action="append")
    p.set_defaults(func=cmd_tasks)
    sub.add_parser("arms", help="list the arm catalogue").set_defaults(func=cmd_arms)
    p = sub.add_parser("check", help="import and check task modules")
    p.add_argument("suites", nargs="*")
    p.set_defaults(func=cmd_check)

    for name, func, help_text in (
        ("run", cmd_run, "run an experiment (resumable)"),
        ("score", cmd_score, "re-judge stored runs"),
    ):
        p = sub.add_parser(name, help=help_text)
        p.add_argument("experiment")
        p.add_argument("--arm", action="append", help="only this arm (repeatable)")
        p.add_argument("--model", action="append", help="only this model (repeatable)")
        p.add_argument("--task", action="append", help="only this task (repeatable)")
        p.add_argument("--shard", help="INDEX/COUNT: run one of COUNT disjoint slices")
        if name == "run":
            p.add_argument("--rerun", action="store_true", help="rerun completed runs too")
            p.add_argument("--no-score", action="store_true", help="skip inline scoring")
            p.add_argument("--dry-run", action="store_true",
                           help="only report what would run and be scored")
        p.set_defaults(func=func)

    p = sub.add_parser("report", help="write the experiment report")
    p.add_argument("experiment")
    p.add_argument("--model", action="append",
                   help="only this of the experiment's models (repeatable)")
    p.set_defaults(func=cmd_report)

    p = sub.add_parser("port", help="(re)port a suite from an AirBench-layout repository")
    p.add_argument("--source", type=Path, required=True, help="source repository root")
    p.add_argument("--registry", required=True, help="registry JSON, relative to --source")
    p.add_argument("--suite", required=True, help="suite name to create under suites/")
    p.add_argument("--domain", action="append", metavar="LAB=SOURCE",
                   help="lab domain and its key in the source registry, e.g. beijing=Beijing"
                        " (repeatable; default hk=HK)")
    p.add_argument("--description", default="")
    p.add_argument("--force", action="store_true", help="replace an existing suite")
    p.set_defaults(func=cmd_port)
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format="%(levelname)s %(name)s: %(message)s",
    )
    try:
        args.func(args)
    except (ConfigurationError, TaskSpecificationError, InfrastructureError) as exc:
        sys.exit(f"error: {exc}")


if __name__ == "__main__":
    main()
