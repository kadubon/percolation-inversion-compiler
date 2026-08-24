# Result semantics

Keep these states separate in reports:

| State | Narrow meaning | Does not mean |
| --- | --- | --- |
| `accepted` | checked input meets its declared admission rule | settled or action allowed |
| `finite_checks_passed` | named finite checks passed when emitted | complete verification |
| `workflow_usable` | current report is usable for scoped routing | settlement or execution |
| `operationally_usable` | usable in its scoped protocol | dispatch or physical success |
| `settled` | scoped obligations are resolved under rules | universal truth |
| blockers/residuals | work or uncertainty remains | command failure only |
| acceleration metrics certified | declared diagnostic metrics passed | real capability growth or ASI |

Inspect raw report field names for the installed version. Do not derive an absent field from nearby fields.
