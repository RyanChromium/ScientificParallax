"""Command-line entry points for reproducible project experiments."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from scientific_parallax.baselines.gray_scott import (
    GrayScottBaselineConfig,
    run_gray_scott_benchmark,
)
from scientific_parallax.challenge.runner import run_step7_development_challenge
from scientific_parallax.coevolution.scheduler import run_step6_control
from scientific_parallax.discovery.latent_final_world import (
    evaluate_latent_final_world_once,
    freeze_latent_strategy,
    provision_latent_final_world,
)
from scientific_parallax.discovery.latent_runner import run_latent_discovery_pilot
from scientific_parallax.discovery.llm_discrimination import run_memory_discrimination
from scientific_parallax.discovery.llm_hypothesis import (
    evaluate_blind_response,
    prepare_blind_screen,
)
from scientific_parallax.evolution.experiment import run_step4_control
from scientific_parallax.protocol.dry_run import run_protocol_dry_run
from scientific_parallax.protocol.final_world import (
    provision_local_final_world,
    verify_local_final_world,
)
from scientific_parallax.questions.experiment import run_step5_control
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

    step4 = command.add_parser("step4", help="run Step 4 paradigm-evolution controls")
    step4_action = step4.add_subparsers(dest="step4_action", required=True)
    step4_run = step4_action.add_parser(
        "run", help="run the fixed-question paradigm-only evolution control"
    )
    step4_run.add_argument("--config", type=Path, required=True)
    step4_run.add_argument("--output", type=Path, required=True)

    step5 = command.add_parser("step5", help="run Step 5 question-evolution controls")
    step5_action = step5.add_subparsers(dest="step5_action", required=True)
    step5_run = step5_action.add_parser(
        "run", help="run the fixed-paradigm question-only evolution control"
    )
    step5_run.add_argument("--config", type=Path, required=True)
    step5_run.add_argument("--output", type=Path, required=True)

    step6 = command.add_parser("step6", help="run the Step 6 co-evolution scheduler")
    step6_action = step6.add_subparsers(dest="step6_action", required=True)
    step6_run = step6_action.add_parser(
        "run", help="run the development-only paradigm-question co-evolution control"
    )
    step6_run.add_argument("--config", type=Path, required=True)
    step6_run.add_argument("--output", type=Path, required=True)
    step6_run.add_argument("--resume", action="store_true")

    step7 = command.add_parser("step7", help="run the blinded Step 7 development challenge")
    step7_action = step7.add_subparsers(dest="step7_action", required=True)
    step7_run = step7_action.add_parser(
        "run", help="run preregistered development tasks without opening the final world"
    )
    step7_run.add_argument("--config", type=Path, required=True)
    step7_run.add_argument("--output", type=Path, required=True)

    discovery = command.add_parser("discovery", help="run open-structure discovery pilots")
    discovery_action = discovery.add_subparsers(dest="discovery_action", required=True)
    latent_pilot = discovery_action.add_parser(
        "latent-pilot", help="discover an unobserved dynamical state from wrong founders"
    )
    latent_pilot.add_argument("--config", type=Path, required=True)
    latent_pilot.add_argument("--output", type=Path, required=True)
    latent_seal = discovery_action.add_parser(
        "seal-latent-world", help="create a new external Protocol v2 test commitment"
    )
    latent_seal.add_argument("--config", type=Path, required=True)
    latent_seal.add_argument("--output", type=Path, required=True)
    latent_seal.add_argument("--development-root", type=Path, default=Path.cwd())
    latent_seal.add_argument("--acknowledge-local-self-audit", action="store_true")
    latent_freeze = discovery_action.add_parser(
        "freeze-latent-strategy", help="bind clean strategy bytes to the v2 commitment"
    )
    latent_freeze.add_argument("--config", type=Path, required=True)
    latent_freeze.add_argument("--root", type=Path, required=True)
    latent_freeze.add_argument("--development-root", type=Path, default=Path.cwd())
    latent_final = discovery_action.add_parser(
        "latent-confirmatory", help="open and evaluate the Protocol v2 world once"
    )
    latent_final.add_argument("--config", type=Path, required=True)
    latent_final.add_argument("--root", type=Path, required=True)
    latent_final.add_argument("--development-root", type=Path, default=Path.cwd())
    llm_prepare = discovery_action.add_parser(
        "llm-screen-prepare", help="build an anonymous development prompt for an external LLM"
    )
    llm_prepare.add_argument("--config", type=Path, required=True)
    llm_prepare.add_argument("--output", type=Path, required=True)
    llm_prepare.add_argument("--world", choices=("positive", "null"), default="positive")
    llm_evaluate = discovery_action.add_parser(
        "llm-screen-evaluate", help="validate and score blind LLM equation proposals"
    )
    llm_evaluate.add_argument("--config", type=Path, required=True)
    llm_evaluate.add_argument("--request", type=Path, required=True)
    llm_evaluate.add_argument("--response", type=Path, required=True)
    llm_evaluate.add_argument("--output", type=Path, required=True)
    llm_evaluate.add_argument("--parameter-draws", type=int, default=64)
    llm_evaluate.add_argument("--world", choices=("positive", "null"), default="positive")
    llm_discriminate = discovery_action.add_parser(
        "llm-screen-discriminate",
        help="select and run one development intervention between frozen LLM proposals",
    )
    llm_discriminate.add_argument("--config", type=Path, required=True)
    llm_discriminate.add_argument("--response", type=Path, required=True)
    llm_discriminate.add_argument("--evaluation", type=Path, required=True)
    llm_discriminate.add_argument("--protocol", type=Path, required=True)
    llm_discriminate.add_argument("--output", type=Path, required=True)
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
    if args.command == "step4":
        report = run_step4_control(args.config, args.output)
        print(json.dumps(report, indent=2, sort_keys=True))
        return
    if args.command == "step5":
        report = run_step5_control(args.config, args.output)
        print(json.dumps(report, indent=2, sort_keys=True))
        return
    if args.command == "step6":
        report = run_step6_control(args.config, args.output, resume=args.resume)
        print(json.dumps(report, indent=2, sort_keys=True))
        return
    if args.command == "step7":
        report = run_step7_development_challenge(args.config, args.output)
        print(json.dumps(report, indent=2, sort_keys=True))
        return
    if args.command == "discovery":
        if args.discovery_action == "latent-pilot":
            report = run_latent_discovery_pilot(args.config, args.output)
        elif args.discovery_action == "seal-latent-world":
            if not args.acknowledge_local_self_audit:
                raise SystemExit("seal-latent-world requires --acknowledge-local-self-audit")
            report = provision_latent_final_world(
                config_path=args.config,
                output_root=args.output,
                development_root=args.development_root,
            )
        elif args.discovery_action == "freeze-latent-strategy":
            report = freeze_latent_strategy(
                config_path=args.config,
                sealed_root=args.root,
                development_root=args.development_root,
            )
        elif args.discovery_action == "latent-confirmatory":
            report = evaluate_latent_final_world_once(
                config_path=args.config,
                sealed_root=args.root,
                development_root=args.development_root,
            )
        elif args.discovery_action == "llm-screen-prepare":
            report = prepare_blind_screen(args.config, args.output, source_world=args.world)
        elif args.discovery_action == "llm-screen-evaluate":
            report = evaluate_blind_response(
                args.config,
                args.request,
                args.response,
                args.output,
                parameter_draws=args.parameter_draws,
                source_world=args.world,
            )
        else:
            report = run_memory_discrimination(
                args.config,
                args.response,
                args.evaluation,
                args.protocol,
                args.output,
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
