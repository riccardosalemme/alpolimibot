import importlib.util
import unittest
from pathlib import Path

from bs4 import BeautifulSoup

_spec = importlib.util.spec_from_file_location(
    "arricchisci", Path(__file__).parents[1] / "jobs/spazi/5_arricchisci_occupazione.py"
)
arricchisci = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(arricchisci)

HTML = """<table>
<tr class="normalRow"><th class="data"></th><th class="dove"></th><th class="empty" colspan="4"></th></tr>
<tr class="normalRow"><td class="data" rowspan="2">Mar 06/10/2026</td><td class="dove" rowspan="2">B.0.2</td>
  <td class="slot" colspan="2"><a>CORSO A</a></td><td class="empty" colspan="2"></td></tr>
<tr class="normalRow"><td class="empty" colspan="2"></td><td class="slot" colspan="2"><a>CORSO B</a></td></tr>
<tr class="normalRow"><td class="data">Mer 07/10/2026</td><td class="dove">B.0.2</td>
  <td class="empty" colspan="4"></td></tr>
</table>"""


def parse(html):
    giorni = []
    for row in BeautifulSoup(html, "html.parser").find_all("tr", class_="normalRow"):
        if parsed := arricchisci._parse_schedule_row(row, giorni[-1] if giorni else None):
            giorni.append(parsed)
    return giorni


class ContinuationRows(unittest.TestCase):
    def test_second_row_inherits_date_and_keeps_its_slot(self):
        giorni = parse(HTML)
        self.assertEqual([g["data"] for g in giorni], ["06/10/2026", "06/10/2026", "07/10/2026"])
        self.assertEqual(giorni[1]["aula"], "B.0.2")
        self.assertEqual(
            [(o["corso"], o["inizio"], o["fine"]) for o in giorni[1]["occupazioni"]],
            [("CORSO B", "08:30", "09:00")],
        )

    def test_header_row_is_skipped(self):
        self.assertIsNone(arricchisci._parse_schedule_row(BeautifulSoup(HTML, "html.parser").find("tr")))


if __name__ == "__main__":
    unittest.main()
