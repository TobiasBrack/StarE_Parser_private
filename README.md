# StarE_Parser

Parses text exports of METTLER TOLEDO STARe software into a universal
format (JSON, optionally HDF5). Optimized for **STARe SW 21.00** exports.

## Usage

```
python stare_parser.py <files or folders> [-o OUTDIR] [-f {h5,json,both}]
```

- `inputs`: one or more `.txt` files, or folders (searched recursively).
- `-o`, `--out`: optional output folder. By default each output file is
  written next to its source file and no folder is created.
- `-f`, `--format`: `h5` (default, requires `h5py`), `json`, or `both`.

Example: `python stare_parser.py curvefiles -f json`

One output file per input file is written, named after the input. No
`index.json` is created. Failures and warnings are printed to stderr.
Tests: `python -m unittest`.

## What it does

An export may contain several curves. For each curve the parser extracts
the header fields, the numeric data table, adjustment settings and results.

Output per curve (JSON):

- Header fields such as `name`, `Sample`, `Material Class`, `Evaluation`
  directly on the curve.
- `data`: object keyed by column name, each with `values` and `unit`,
  e.g. `"t": {"values": [0, 1], "unit": "s"}`. The table `Index` column is
  only used for validation and is not output.
- `Adjustment`: nested object of `name -> {value, unit}`, with groups
  (e.g. `Sample Temperature`, `Heat Flow`) as sub-objects and plain text
  stored as `description`.
- `results`: list of result groups, each with a `type` and `fields`
  (`name -> value/unit`).
- `unsectioned`: text after a blank line following `Classification`.

## Details: how the parser searches

1. **Encoding**: the file is read as UTF-8 (with BOM), falling back to
   cp1252, then latin-1, so symbols like `°` survive.
2. **Curve blocks**: a line `Curve Name:` starts a new curve; everything up
   to the next one (or the footer / rule line of underscores) belongs to it.
3. **Data table**: rows are recognised by a regex: an integer index followed
   by two or more numbers. The column header and unit lines above the first
   row give column names and units. The index must be contiguous, otherwise
   a warning is issued. Non-numeric lines after the table are still parsed.
4. **Sections**: unindented lines of the form `Name:` (nothing after the
   colon) open a section (`Sample:`, `Adjustment:`, `Method:` ...). The
   following lines belong to it until the next header. `Classification`
   ends at the first blank line after its content; later text goes to
   `unsectioned`.
5. **Adjustment**: indentation defines structure. A line ending in `:` with
   no value opens a group; deeper-indented lines belong to it until the
   indent drops. Lines `name : value unit` become fields; indented plain
   text becomes `description`. Numbers are split into value and unit;
   dates and polynomial formulas (`0.0 + 0.1*T`) are kept as text. `From X to Y unit` (numbers) is stored as `range` with `values: [X, Y]` and `unit`.
6. **Results**: lines under `Results:` are split into name and value at a
   tab or two or more spaces. Blank lines separate result groups. A line
   without a value is the group description (`type`); an indented
   continuation line is stored as `additional_values` of the previous field.
   Without a description, `type` is the first word of the first field name
   (that field is kept).

## Temporary

The current testing branch limits each curve to 10 data rows. Remove this
in `parse_block` before the final version.
