import unittest

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


if __name__ == "__main__":
    unittest.main()
