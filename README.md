# StarE_Parser
parse StarE txt output to universal format

Each curve in JSON output has a `data` object keyed by column name. Each
column contains its `values` array and `unit`, for example
`"t": {"values": [0, 1], "unit": "s"}`. The table index is used for
validation and is not included in the output.
Text after a blank line following `Classification` is preserved in the curve's
`unsectioned` field.
Adjustment formulas are kept as text values with their units, when present.
The manifest's `t_range` is null for curves without a time column.

The current testing branch temporarily limits each curve to 10 data rows.
