from __future__ import annotations

import json

from percolation_inversion_compiler.agent import AgentIntakeRequest, run_agent_intake


def main() -> None:
    report = run_agent_intake(
        AgentIntakeRequest(
            agent_output=(
                "Candidate packet: An AI agent produced an output. "
                "Preserve residuals and list missing obligations before reuse."
            ),
            profile="development",
        )
    )
    missing = report.runtime_report.missing_obligations if report.runtime_report is not None else []
    print(
        json.dumps(
            {
                "accepted": report.accepted,
                "settled": report.settled,
                "residual_summary": report.residual_summary,
                "missing_obligation_count": len(missing),
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
