import json
import tempfile
import unittest
from pathlib import Path

import stare_parser


class ParseBlockTests(unittest.TestCase):
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
                "columns": [
                    {"key": "t", "unit": "s"},
                    {"key": "Signal", "unit": "mW"},
                ],
                "values": {"t": [0.0], "Signal": [1.5]},
            },
        )
        self.assertEqual(
            curve["Adjustment"],
            {
                "From": {"value": "-88.67 to 17.00", "unit": "min"},
                "Gas Factor": {"value": 1.0, "unit": ""},
                "E Indium": {"value": 5.8996e6, "unit": "1/mW"},
                "date": {"value": "10.08.2026 10:33:55", "unit": ""},
            },
        )

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

    def test_manifest_supports_curves_without_time(self):
        text = (
            "Curve Name:\nExample\nCurve Values:\n"
            "Index Abscissa Value\n[] [C]\n0 2.0 5.0\n"
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "curve.txt"
            path.write_text(text, encoding="utf-8")
            output = Path(directory) / "output"
            self.assertEqual(stare_parser.main([str(path), "-f", "json", "-o", str(output)]), 0)
            index = json.loads((output / "index.json").read_text(encoding="utf-8"))
            self.assertIsNone(index[0]["t_range"])
            result = json.loads((output / "curve.json").read_text(encoding="utf-8"))
            self.assertEqual(result["curves"][0]["data"]["values"]["Abscissa"], [2.0])


if __name__ == "__main__":
    unittest.main()
