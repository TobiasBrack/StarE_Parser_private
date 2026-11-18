import json
import tempfile
import unittest
from pathlib import Path

import stare_parser


class ParseBlockTests(unittest.TestCase):
    def test_reads_all_rows_and_following_sections(self):
        lines = [
            "Example",
            "Curve Values:",
            "Index t Signal",
            "[s] [mW]",
            *(f"{i} {i} {i * 2}" for i in range(1, 16)),
            "Sample:",
            "  Example sample",
        ]
        curve = stare_parser.parse_block(lines, [], 1)
        self.assertEqual(curve["n_rows"], 15)
        self.assertEqual(curve["data"]["t"]["values"], list(range(1, 16)))
        self.assertEqual(curve["data"]["Signal"]["values"], list(range(2, 31, 2)))
        self.assertEqual(curve["Sample"], "Example sample")

    def test_sections_are_curve_fields_and_adjustment_values_are_structured(self):
        lines = [
            "Bismuth, 16.11.2026 15:13:53",
            "Bismuth sample",
            "Curve Values:",
            "Index t Signal",
            "[s] [mW]",
            "1 0 1.5",
            "Sample:",
            "  Bismuth (271.44\u00b0C, 52.16 J/g), 2.7958 mg",
            "Material Class:",
            "  Metal",
            "Adjustment:",
            "  From -88.67 to 17.00 min",
            "  Gas Factor    : 1",
            "  E Indium      : 5.8996e+06 1/mW",
            "    date        : 10.08.2026 10:33:55",
        ]

        curve = stare_parser.parse_block(lines, [], 1)

        self.assertEqual(
            curve["Sample"], "Bismuth (271.44\u00b0C, 52.16 J/g), 2.7958 mg"
        )
        self.assertEqual(curve["Material Class"], "Metal")
        self.assertNotIn("sections", curve)
        self.assertEqual(
            curve["data"],
            {
                "t": {"values": [0.0], "unit": "s"},
                "Signal": {"values": [1.5], "unit": "mW"},
            },
        )
        self.assertEqual(
            curve["Adjustment"],
            {
                "range": {"values": [-88.67, 17.0], "unit": "min"},
                "Gas Factor": {"value": 1.0, "unit": ""},
                "E Indium": {"value": 5.8996e6, "unit": "1/mW"},
                "date": {"value": "10.08.2026 10:33:55", "unit": ""},
            },
        )

    def test_labeled_sections_parse_named_values(self):
        fields = stare_parser.parse_section_fields([
            "Sample Holder:",
            "  Aluminum Standard 40ul",
            "  Weight  : 49.53 mg",
            "  Material: Aluminum",
            "TA Module:",
            "  Flash DSC 2+",
            "  Type           : Flash DSC 2+",
            "  Identification : 103",
            "Method:",
            "  Simple text value",
        ])

        self.assertEqual(fields["Sample Holder"], {
            "label": "Aluminum Standard 40ul",
            "Weight": {"value": 49.53, "unit": "mg"},
            "Material": {"value": "Aluminum", "unit": ""},
        })
        self.assertEqual(fields["TA Module"], {
            "label": "Flash DSC 2+",
            "Type": {"value": "Flash DSC 2+", "unit": ""},
            "Identification": {"value": 103.0, "unit": ""},
        })
        self.assertEqual(fields["Method"], "Simple text value")

    def test_performed_datetime_is_parsed_separately_from_curve_label(self):
        curve = stare_parser.parse_block([
            "Example",
            "Performed: 22.06.2026 12:42:01",
            "Curve Values:",
            "Index t Signal",
            "[s] [mW]",
            "1 0 1.5",
        ], [], 1)

        self.assertEqual(curve["performed"], "2026-06-22T12:42:01")
        self.assertIsNone(curve["label"])

    def test_formulas_and_text_after_section(self):
        fields = stare_parser.parse_section_fields([
            "Texts:",
            "",
            "  First line",
            "",
            "  Second line",
            "Adjustment:",
            "  dTs(T) : 0.0000 + 0.0000*T + 0.0000*T^2 \u00b0C",
            "  Tau Lag: 3.7425 + 2.6010e-03*T - 268.6718e-09*T^2 s",
            "  dE relative: 0.0000 + 0.0000*T + 0.0000*T^2",
            "Classification:",
            "  Not classified",
            "",
            "  1/F Plot",
        ])
        self.assertEqual(fields["Texts"], "First line\nSecond line")
        self.assertEqual(fields["Classification"], "Not classified")
        self.assertEqual(fields["unsectioned"], "1/F Plot")
        self.assertEqual(fields["Adjustment"]["dTs(T)"], {
            "value": "0.0000 + 0.0000*T + 0.0000*T^2", "unit": "\u00b0C",
        })
        self.assertEqual(fields["Adjustment"]["Tau Lag"], {
            "value": "3.7425 + 2.6010e-03*T - 268.6718e-09*T^2", "unit": "s",
        })
        self.assertEqual(fields["Adjustment"]["dE relative"], {
            "value": "0.0000 + 0.0000*T + 0.0000*T^2", "unit": "",
        })

    def test_json_output_supports_curves_without_time(self):
        text = (
            "Curve Name:\nExample\nCurve Values:\n"
            "Index Abscissa Value\n[] [C]\n0 2.0 5.0\n"
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "curve.txt"
            path.write_text(text, encoding="utf-8")
            output = Path(directory) / "output"
            self.assertEqual(stare_parser.main([str(path), "-f", "json", "-o", str(output)]), 0)
            self.assertFalse((output / "index.json").exists())
            result = json.loads((output / "curve.json").read_text(encoding="utf-8"))
            self.assertEqual(
                result["curves"][0]["data"]["Abscissa"],
                {"values": [2.0], "unit": ""},
            )

    def test_indented_adjustment_groups_and_tab_delimited_results(self):
        fields = stare_parser.parse_section_fields([
            "Adjustment:",
            "  From 0.00 to 77.58 min",
            "  Sample Temperature:",
            "    TGA/SF SDTA FRS2",
            "    Tc     : 25.00 \u00b0C",
            "    dTs(T) : 0.0000 + 0.0000*T + 0.0000*T^2 \u00b0C",
            "  Heat Flow:",
            "    E Indium      : 26.1822 1/mW",
            "    dE relative   : 0.0000 + 0.0000*T + 0.0000*T^2",
            "      date        : -",
            "Sample Holder:",
            "  Material: Ceramic",
        ])
        self.assertEqual(fields["Adjustment"], {
            "range": {"values": [0.0, 77.58], "unit": "min"},
            "Sample Temperature": {
                "description": "TGA/SF SDTA FRS2",
                "Tc": {"value": 25.0, "unit": "\u00b0C"},
                "dTs(T)": {
                    "value": "0.0000 + 0.0000*T + 0.0000*T^2",
                    "unit": "\u00b0C",
                },
            },
            "Heat Flow": {
                "E Indium": {"value": 26.1822, "unit": "1/mW"},
                "dE relative": {
                    "value": "0.0000 + 0.0000*T + 0.0000*T^2",
                    "unit": "",
                },
                "date": {"value": "-", "unit": ""},
            },
        })

        results = stare_parser.parse_results([
            "  Onset\t676.61 \u00b0C",
            "  Endset\t676.66 \u00b0C",
            "",
            "  Integral\t195.82e+03 mJ",
            "  Left Limit\t3.20 min",
            "  Right Limit\t9.96 min",
            "  Baseline Type\tline",
            "",
            "  Calibration Results",
            "  Temperature\t666.06 \u00b0C",
            "  Delta H\t373.76 Jg^-1",
        ])
        self.assertEqual(results, [
            {"type": "Onset", "fields": {
                "Onset": {"value": 676.61, "unit": "\u00b0C"},
                "Endset": {"value": 676.66, "unit": "\u00b0C"},
            }},
            {"type": "Integral", "fields": {
                "Integral": {"value": 195820.0, "unit": "mJ"},
                "Left Limit": {"value": 3.2, "unit": "min"},
                "Right Limit": {"value": 9.96, "unit": "min"},
                "Baseline Type": {"text": "line"},
            }},
            {"type": "Calibration Results", "fields": {
                "Temperature": {"value": 666.06, "unit": "\u00b0C"},
                "Delta H": {"value": 373.76, "unit": "Jg^-1"},
            }},
        ])

    def test_messy_export_has_nested_adjustment_and_parsed_results(self):
        path = Path(__file__).parent / (
            "curvefiles/TGA_DSC 3+ Adjust  TabVal  Expert  "
            "Al_F_ID2062_2_add2_messy.txt"
        )
        curve = stare_parser.parse_file(path)["curves"][0]
        self.assertEqual(
            curve["Adjustment"]["Sample Temperature"]["description"],
            "TGA/SF SDTA FRS2",
        )
        self.assertEqual(
            curve["Adjustment"]["Heat Flow"]["E Indium"],
            {"value": 26.1822, "unit": "1/mW"},
        )
        self.assertIn("t", curve["data"])
        self.assertEqual(curve["data"]["t"]["unit"], "s")
        self.assertEqual(len(curve["data"]["t"]["values"]), 4656)
        self.assertTrue(curve["results"])
        self.assertEqual(curve["results"][0]["fields"]["Onset"]["value"], 676.61)
        self.assertEqual(curve["results"][1]["type"], "Integral")
        self.assertIn("Integral", curve["results"][1]["fields"])
        self.assertEqual(
            curve["results"][2]["fields"]["Step"]["additional_values"][0],
            {"value": -2.4981, "unit": "mW"},
        )


if __name__ == "__main__":
    unittest.main()
