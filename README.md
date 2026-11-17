# StarE_Parser
parse StarE txt output to universal format

Each curve in JSON output has a `data` object containing `columns` (column
keys and units) and `values` (arrays keyed by column name). The table index
is used for validation and is not included in the output.

The current testing branch temporarily limits each curve to 10 data rows.
