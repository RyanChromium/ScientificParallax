"""Command-line entry points for reproducible project experiments."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from scientific_parallax.baselines.gray_scott import (
    GrayScottBaselineConfig,
    run_gray_scott_benchmark,
)
from scientific_parallax.protocol.dry_run import run_protocol_dry_run
from scientific_parallax.protocol.final_world import (
    provision_local_final_world,
    verify_local_final_world,
)
from scientific_parallax.step0.benchmark import run_benchmark
from scientific_parallax.step0.experiment import ExperimentConfig, run_experiment
from scientific_parallax.step0.ledger import verify_ledger
from scientific_parallax.step0.strategies import SELECTORS


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="scientific-parallax")
    command = parser.add_subparsers(dest="command", required=True)

    step0 = command.add_parser("step0", help="run the Step 0 fixed-candidate protocol")
    action = step0.add_subparsers(dest="action", required=True)

    run = action.add_parser("run", help="run one strategy once")
    run.add_argument("--config", type=Path, required=True)
    run.add_argument("--strategy", choices=sorted(SELECTORS), required=True)
    run.add_argument("--output", type=Path, required=True)
    run.add_argument("--seed", type=int)

    benchmark = action.add_parser("benchmark", help="compare all configured strategies")
    benchmark.add_argument("--config", type=Path, required=True)
    benchmark.add_argument("--output", type=Path, required=True)
    benchmark.add_argument("--replicates", type=int)

    verify = action.add_parser("verify-ledger", help="verify a ledger hash chain")
    verify.add_argument("ledger", type=Path)

    gray_scott = command.add_parser("gray-scott", help="run Gray–Scott development baselines")
    gray_action = gray_scott.add_subparsers(dest="gray_action", required=True)
    gray_benchmark = gray_action.add_parser("benchmark", help="compare fixed baselines")
    gray_benchmark.add_argument("--config", type=Path, required=True)
    gray_benchmark.add_argument("--output", type=Path, required=True)

    protocol = command.add_parser("protocol", help="run pre-freeze protocol diagnostics")
    protocol_action = protocol.add_subparsers(dest="protocol_action", required=True)
    dry_run = protocol_action.add_parser("dry-run", help="run Step 3.5 synthetic diagnostics")
    dry_run.add_argument("--config", type=Path, required=True)
    dry_run.add_argument("--output", type=Path, required=True)
    seal_world = protocol_action.add_parser(
        "seal-world", help="create a local single-account final-world commitment"
    )
    seal_world.add_argument("--config", type=Path, required=True)
    seal_world.add_argument("--output", type=Path, required=True)
    seal_world.add_argument("--development-root", type=Path, default=Path.cwd())
    seal_world.add_argument("--acknowledge-local-self-audit", action="store_true")
    verify_world = protocol_action.add_parser(
        "verify-world", help="verify a local final-world commitment"
    )
    verify_world.add_argument("--root", type=Path, required=True)
    verify_world.add_argument("--protocol-hash", required=True)
    verify_world.add_argument("--development-root", type=Path, default=Path.cwd())
    return parser


def main() -> None:
    args = _parser().parse_args()
    if args.command == "gray-scott":
        config = GrayScottBaselineConfig.from_json(args.config)
        raw_config = json.loads(args.config.read_text(encoding="utf-8"))
        report = run_gray_scott_benchmark(
            config,
            args.output,
            raw_config["strategies"],
        )
        print(json.dumps(report, indent=2, sort_keys=True))
        return
    if args.command == "protocol":
        if args.protocol_action == "dry-run":
            report = run_protocol_dry_run(args.config, args.output)
        elif args.protocol_action == "seal-world":
            if not args.acknowledge_local_self_audit:
                raise SystemExit(
                    "seal-world requires --acknowledge-local-self-audit because this mode "
                    "does not provide independent custody"
                )
            report = provision_local_final_world(
                config_path=args.config,
                output_root=args.output,
                development_root=args.development_root,
            )
        else:
            report = verify_local_final_world(
                sealed_root=args.root,
                expected_protocol_hash=args.protocol_hash,
                development_root=args.development_root,
            )
        print(json.dumps(report, indent=2, sort_keys=True))
        return
    if args.action == "verify-ledger":
        verify_ledger(args.ledger)
        print(f"valid ledger: {args.ledger}")
        return
    config = ExperimentConfig.from_json(args.config)
    if args.action == "run":
        result = run_experiment(config, args.strategy, args.output, seed=args.seed)
        print(json.dumps(result.to_dict(), indent=2, sort_keys=True))
        return
    raw_config = json.loads(args.config.read_text(encoding="utf-8"))
    strategies = raw_config.get("strategies", list(SELECTORS))
    replicates = args.replicates or raw_config.get("replicates", 30)
    report = run_benchmark(config, args.output, strategies, replicates)
    print(json.dumps(report["summaries"], indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
