# Unknown Values And Thresholds

PIC uses three coordinate states: `known`, `unknown`, and `not_applicable`.
A known coordinate has a finite value, unit, validity domain, and evidence
references. Unknown means the checker lacks enough information. It is not zero,
false, empty success, or a positive contribution. Not applicable must be stated
by the governing protocol; it is not a substitute for missing evidence.

Phase thresholds return `abstain` when a required coordinate is unknown. Upper
bounds such as hazard, residual debt, queue occupation, and false liquidity do
not pass by omission. Public JSON boundaries reject numeric strings, string
booleans, non-finite numbers, negative zero, oversized input, excessive depth,
and YAML aliases.
