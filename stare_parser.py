"""Parse METTLER TOLEDO STARe text exports (1..n curves per file) to JSON / HDF5.

No recomputation is done: results are taken verbatim from the STARe export.
Parsing needs only the standard library; HDF5 output needs h5py + numpy.
"""
import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

CURVE_START = re.compile(r"^Curve Name:\s*$")
NUMERIC_ROW = re.compile(r"^\s*-?\d+\s+-?[\d.eE+-]+(\s+-?[\d.eE+-]+)+\s*$")
SECTION = re.compile(r"^([A-Za-z][A-Za-z ]*):\s*$")
NUM_UNIT = re.compile(r"^(-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)\s*(.*)$")
FORMULA = re.compile(
    r"^(-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?"
    r"(?:\s*[+-]\s*\d+(?:\.\d+)?(?:[eE][+-]?\d+)?\s*\*\s*T(?:\^\d+)?)+)"
    r"(?:\s+(\S+))?$"
)
FOOTER = re.compile(r"^(Not signed|Signed)\b(.*)$")
RULE = re.compile(r"^_{10,}$")


def read_text(path):
    raw = Path(path).read_bytes()
    for enc in ("utf-8-sig", "cp1252"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("latin-1")


def parse_date(text):
    for fmt in ("%d.%m.%Y %H:%M:%S", "%d.%m.%Y %H:%M"):
        try:
            return datetime.strptime(text.strip(), fmt).isoformat()
        except ValueError:
            pass
    return None


def split_name_line(line):
    """'  name, 22.06.2026 12:42:01' -> (name, iso timestamp or None)."""
    line = line.strip()
    name, _, stamp = line.rpartition(", ")
    iso = parse_date(stamp) if name else None
    return (name, iso) if iso else (line, None)


def parse_units(line):
    return re.findall(r"\[([^\]]*)\]", line)


def parse_value(text):
    m = NUM_UNIT.match(text.strip())
    if m:
        return {"value": float(m.group(1)), "unit": m.group(2).strip()}
    return {"text": text.strip()}


def parse_results(lines):
    """Parse tab- or spacing-delimited result fields, preserving result groups."""
    results = []
    current = None

    def finish():
        nonlocal current
        if current is not None and (current["type"] or current["fields"]):
            results.append(current)
        current = None

    for line in lines:
        if not line.strip():
            finish()
            continue
        indent = len(line) - len(line.lstrip())
        parts = re.split(r"(?:\t+|\s{2,})", line.strip(), maxsplit=1)
        if len(parts) == 1:
            if current is None:
                current = {"type": "", "fields": {}}
            text = parts[0]
            if current["fields"] and indent > 0:
                key = next(reversed(current["fields"]))
                value = parse_value(text)
                previous = current["fields"][key]
                previous.setdefault("additional_values", []).append(value)
            elif not current["type"]:
                current["type"] = text
            else:
                current["type"] = f"{current['type']} {text}"
            continue
        if current is None:
            current = {"type": "", "fields": {}}
        key, val = parts
        current["fields"][key.strip()] = parse_value(val.strip())
    finish()
    return results


def parse_sections(lines):
    """Collect named sections and text outside them."""
    sections, unsectioned, current = {}, [], None
    for line in lines:
        m = SECTION.match(line)
        if m and not line.startswith(" "):
            current = m.group(1)
            sections.setdefault(current, [])
        elif not line.strip():
            if current == "Classification" and sections[current]:
                current = None
        elif current is not None:
            sections[current].append(line.strip())
        else:
            unsectioned.append(line.strip())
    return sections, unsectioned


def parse_section_fields(lines):
    """Convert curve sections to curve fields and parse Adjustment entries."""
    sections, unsectioned = parse_sections(lines)
    sections.pop("Adjustment", None)

    fields = {name: "\n".join(values) for name, values in sections.items()}
    if unsectioned:
        fields["unsectioned"] = "\n".join(unsectioned)
    adjustment = _parse_adjustment(lines)
    if adjustment:
        fields["Adjustment"] = adjustment
    return fields


def _adjustment_value(text, name):
    formula = FORMULA.fullmatch(text)
    if formula:
        return {"value": formula.group(1), "unit": formula.group(2) or ""}
    parsed = (
        {"text": text}
        if name.casefold() == "date" and parse_date(text)
        else parse_value(text)
    )
    return {
        "value": parsed.get("value", parsed.get("text")),
        "unit": parsed.get("unit", ""),
    }


def _parse_adjustment(lines):
    adjustment = {}
    start = _find(lines, "Adjustment:")
    if start < 0:
        return adjustment

    group = None
    group_indent = None
    for line in lines[start + 1:]:
        if SECTION.match(line) and not line.startswith(" "):
            break
        if not line.strip():
            continue
        expanded = line.expandtabs(8)
        indent = len(expanded) - len(expanded.lstrip())
        text = expanded.strip()
        if text.endswith(":") and not text[:-1].strip():
            continue
        if text.endswith(":") and not text.split(":", 1)[1].strip():
            name = text[:-1].strip()
            if group is None or indent <= group_indent:
                group = name
                group_indent = indent
                adjustment[group] = {}
                continue
        if ":" in text:
            name, value = (part.strip() for part in text.split(":", 1))
            if group is not None and indent > group_indent:
                adjustment[group][name] = _adjustment_value(value, name)
            else:
                group = None
                adjustment[name] = _adjustment_value(value, name)
            continue
        if text.startswith("From "):
            match = re.fullmatch(r"From\s+(.+?)\s+to\s+(.+?)\s+(\S+)", text)
            if match:
                adjustment["From"] = {
                    "value": f"{match.group(1)} to {match.group(2)}",
                    "unit": match.group(3),
                }
            else:
                adjustment["details"] = {"value": text, "unit": ""}
        elif group is not None and indent > group_indent:
            adjustment[group]["description"] = text
        else:
            group = None
            adjustment["details"] = {"value": text, "unit": ""}
    return adjustment


def parse_block(lines, warnings, curve_no):
    i = 0
    name_lines = []
    while i < len(lines) and not lines[i].startswith("Curve Values:"):
        if lines[i].strip():
            name_lines.append(lines[i])
        i += 1
    if i >= len(lines) or not name_lines:
        raise ValueError("block without 'Curve Values:' table")
    name, measured = split_name_line(name_lines[0])
    label = name_lines[1].strip() if len(name_lines) > 1 else None

    i += 1
    columns = lines[i].split()
    units = parse_units(lines[i + 1])
    if len(units) != len(columns) - 1:
        warnings.append(f"curve {curve_no}: {len(columns)} columns vs {len(units)} units")
    i += 2

    rows = []
    # Temporary testing cap; remove before the final version.
    while i < len(lines) and len(rows) < 10 and NUMERIC_ROW.match(lines[i]):
        rows.append(lines[i].split())
        i += 1
    while i < len(lines) and NUMERIC_ROW.match(lines[i]):
        i += 1
    data = {c: [float(r[k]) for r in rows] for k, c in enumerate(columns)}

    index = data.pop("Index", None)
    if index is not None and index != list(range(int(index[0]), int(index[0]) + len(index))):
        warnings.append(f"curve {curve_no}: Index not contiguous")
    t = data.get("t", [])
    if any(b < a for a, b in zip(t, t[1:])):
        warnings.append(f"curve {curve_no}: t not monotonic")

    tail = lines[i:]
    section_fields = parse_section_fields(tail)
    section_fields.pop("Results", None)
    start = _find(tail, "Results:")
    results = parse_results(tail[start + 1:_results_end(tail)]) if start >= 0 else []

    curve = {
        "name": name,
        "label": label,
        "measured": measured,
        "n_rows": len(rows),
        "data": {
            "columns": [{"key": c, "unit": units[k] if k < len(units) else ""} for k, c in enumerate(columns[1:])],
            "values": data,
        },
        "results": results,
    }
    curve.update(section_fields)
    return curve


def _find(lines, header):
    for k, line in enumerate(lines):
        if line.strip() == header:
            return k
    return -1


def _results_end(lines):
    start = _find(lines, "Results:") + 1
    for k in range(start, len(lines)):
        if SECTION.match(lines[k]) and not lines[k].startswith(" "):
            return k
    return len(lines)


def parse_file(path):
    path = Path(path)
    lines = read_text(path).splitlines()
    warnings = []

    exported = None
    if lines and lines[0].startswith("Title"):
        exported = parse_date(lines[0][5:].strip())

    starts = [k for k, line in enumerate(lines) if CURVE_START.match(line)]
    if not starts:
        raise ValueError("no 'Curve Name:' found")

    software, signed = None, None
    for line in lines:
        m = FOOTER.match(line.strip())
        if m:
            signed = m.group(1) == "Signed"
            software = m.group(2).strip() or None
    # Keep footer out of the last block's sections
    end = len(lines)
    for k in range(len(lines) - 1, starts[-1], -1):
        if RULE.match(lines[k]):
            end = k
            break

    curves = []
    for n, s in enumerate(starts):
        stop = starts[n + 1] if n + 1 < len(starts) else end
        try:
            curves.append(parse_block(lines[s + 1:stop], warnings, n + 1))
        except ValueError as exc:
            warnings.append(f"curve {n + 1}: {exc}")

    return {
        "schema_version": 1,
        "source": {"file": path.name, "exported": exported, "software": software, "signed": signed},
        "curves": curves,
        "warnings": warnings,
    }


def write_json(parsed, out_path):
    Path(out_path).write_text(json.dumps(parsed, ensure_ascii=False, indent=1), encoding="utf-8")


def write_h5(parsed, out_path):
    import h5py
    import numpy as np

    def write_adjustment(parent, name, field):
        entry = parent.create_group(name)
        if "value" in field:
            entry.attrs["value"] = field["value"]
            entry.attrs["unit"] = field["unit"]
        else:
            for subname, subfield in field.items():
                if isinstance(subfield, dict):
                    write_adjustment(entry, subname, subfield)
                else:
                    entry.attrs[subname] = subfield

    with h5py.File(out_path, "w") as f:
        for k, v in parsed["source"].items():
            if v is not None:
                f.attrs[k] = v
        f.attrs["schema_version"] = parsed["schema_version"]
        f.attrs["n_curves"] = len(parsed["curves"])
        for n, c in enumerate(parsed["curves"], 1):
            g = f.create_group(f"curve_{n:02d}")
            g.attrs["name"] = c["name"]
            for key in ("label", "measured"):
                if c[key]:
                    g.attrs[key] = c[key]
            units = {col["key"]: col["unit"] for col in c["data"]["columns"]}
            for key, values in c["data"]["values"].items():
                ds = g.create_dataset(key, data=np.asarray(values, dtype="f8"), compression="gzip")
                ds.attrs["unit"] = units.get(key, "")
            for key, value in c.items():
                if key in {"name", "label", "measured", "n_rows", "data", "results"}:
                    continue
                if key == "Adjustment":
                    ag = g.create_group(key)
                    for name, field in value.items():
                        write_adjustment(ag, name, field)
                else:
                    g.attrs[key] = value
            rg = g.create_group("results")
            for r, res in enumerate(c["results"], 1):
                eg = rg.create_group(f"{r:02d}")
                eg.attrs["type"] = res["type"]
                for key, val in res["fields"].items():
                    if "value" in val:
                        eg.attrs[key] = val["value"]
                        eg.attrs[key + " [unit]"] = val["unit"]
                        if "additional_values" in val:
                            eg.attrs[key + " [additional values]"] = json.dumps(
                                val["additional_values"], ensure_ascii=False
                            )
                    else:
                        eg.attrs[key] = val["text"]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("inputs", nargs="+", help="txt files or folders (searched recursively)")
    ap.add_argument("-o", "--out", default="out", help="output folder")
    ap.add_argument("-f", "--format", choices=["h5", "json", "both"], default="h5")
    args = ap.parse_args(argv)

    files = []
    for p in map(Path, args.inputs):
        files += sorted(p.rglob("*.txt")) if p.is_dir() else [p]
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    manifest, failed = [], 0
    for path in files:
        try:
            parsed = parse_file(path)
        except Exception as exc:
            print(f"FAIL {path}: {exc}", file=sys.stderr)
            failed += 1
            continue
        stem = path.stem
        if args.format in ("h5", "both"):
            write_h5(parsed, out / f"{stem}.h5")
        if args.format in ("json", "both"):
            write_json(parsed, out / f"{stem}.json")
        for n, c in enumerate(parsed["curves"], 1):
            time = c["data"]["values"].get("t", [])
            manifest.append({
                "file": str(path), "curve": n, "name": c["name"], "measured": c["measured"],
                "n_rows": c["n_rows"],
                "t_range": [min(time), max(time)] if time else None,
                "results": [{"type": r["type"], **{k: v.get("value", v.get("text")) for k, v in r["fields"].items()}}
                            for r in c["results"]],
            })
        for w in parsed["warnings"]:
            print(f"WARN {path.name}: {w}", file=sys.stderr)
    (out / "index.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(files) - failed}/{len(files)} files parsed, {len(manifest)} curves -> {out}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
