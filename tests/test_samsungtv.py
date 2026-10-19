import contextlib
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import samsungtv  # noqa: E402
from mock_tv import MockTV  # noqa: E402


class ModelYearTest(unittest.TestCase):
    def test_from_platform_field(self):
        self.assertEqual(samsungtv.model_year({"model": "18_KANTM2_UHD"}), 2018)
        self.assertEqual(samsungtv.model_year({"model": "16_JAZZM_UHD"}), 2016)

    def test_from_model_name(self):
        self.assertEqual(samsungtv.model_year({"modelName": "UE55MU6100"}), 2017)
        self.assertEqual(samsungtv.model_year({"modelName": "UE50RU7105"}), 2019)
        self.assertEqual(samsungtv.model_year({"modelName": "UE43AU7105"}), 2021)
        self.assertEqual(samsungtv.model_year({"modelName": "QE55Q60R"}), 2019)
        self.assertEqual(samsungtv.model_year({"modelName": "QE65QN90A"}), 2021)

    def test_unknown(self):
        self.assertIsNone(samsungtv.model_year({"modelName": "LG-OLED55C1"}))
        self.assertIsNone(samsungtv.model_year({}))


class GuideTest(unittest.TestCase):
    def test_guia_md_is_generated(self):
        committed = (ROOT / "GUIA.md").read_text(encoding="utf-8")
        self.assertEqual(committed, samsungtv.guide_markdown(),
                         "GUIA.md está desactualizada: python3 tools/samsungtv.py guia --markdown > GUIA.md")

    def test_steps_are_complete(self):
        ids = [s["id"] for s in samsungtv.GUIDE]
        self.assertEqual(len(ids), len(set(ids)))
        for step in samsungtv.GUIDE:
            self.assertEqual(set(step["pasos"]), {samsungtv.OLD, samsungtv.NEW}, step["id"])

    def test_year_group(self):
        self.assertEqual(samsungtv.year_group(2018), samsungtv.OLD)
        self.assertEqual(samsungtv.year_group(2023), samsungtv.NEW)
        self.assertEqual(samsungtv.year_group(None), samsungtv.OLD)


class AgainstMockTV(unittest.TestCase):
    def setUp(self):
        samsungtv.KEY_DELAY = 0
        self.tmp = tempfile.TemporaryDirectory()
        self.config = os.path.join(self.tmp.name, "config.json")
        self.env = mock.patch.dict(os.environ, {"CLEANSAMSUNGTV_CONFIG": self.config})
        self.env.start()

    def tearDown(self):
        self.env.stop()
        self.tmp.cleanup()

    def run_cli(self, tv, *args):
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
            code = samsungtv.main(["--ip", "127.0.0.1", "--puerto", str(tv.port), *args])
        tv.wait_idle()
        return code, out.getvalue()

    def start(self, **kw):
        tv = MockTV(**kw)
        self.addCleanup(tv.stop)
        return tv

    def test_info(self):
        tv = self.start()
        code, out = self.run_cli(tv, "info")
        self.assertEqual(code, 0)
        self.assertIn("UE55NU7405", out)
        self.assertIn("2018", out)
        self.assertIn("Wi-Fi", out)
        self.assertEqual(json.load(open(self.config))["ip"], "127.0.0.1")

    def test_apps_marks_running(self):
        tv = self.start(running={"11101200001"})
        code, out = self.run_cli(tv, "apps")
        self.assertEqual(code, 0)
        self.assertIn("* Netflix", out)
        self.assertIn("  YouTube", out)

    def test_limpiar_closes_running_apps_and_goes_home(self):
        tv = self.start(running={"11101200001", "111299001912"})
        code, out = self.run_cli(tv, "limpiar")
        self.assertEqual(code, 0)
        self.assertEqual(tv.running, set())
        self.assertIn("Cerrada: Netflix", out)
        self.assertIn("2 apps cerradas", out)
        self.assertEqual(tv.keys, [("Click", "KEY_HOME")])

    def test_limpiar_with_nothing_open(self):
        tv = self.start()
        code, out = self.run_cli(tv, "limpiar")
        self.assertEqual(code, 0)
        self.assertIn("ninguna app abierta", out)

    def test_token_is_saved(self):
        tv = self.start()
        self.run_cli(tv, "tecla", "home")
        self.assertEqual(json.load(open(self.config))["tokens"]["127.0.0.1"], "12345678")
        self.assertEqual(tv.keys, [("Click", "KEY_HOME")])

    def test_rejected_pairing_is_explained(self):
        tv = self.start(authorize=False)
        code, out = self.run_cli(tv, "tecla", "HOME")
        self.assertEqual(code, 1)
        self.assertIn("rechazado", out)

    def test_reiniciar_holds_power(self):
        tv = self.start()
        with mock.patch.object(samsungtv.time, "sleep"):
            code, _ = self.run_cli(tv, "reiniciar", "--si")
        self.assertEqual(code, 0)
        self.assertEqual(tv.keys, [("Press", "KEY_POWER"), ("Release", "KEY_POWER")])

    def test_abrir_and_cerrar_by_name(self):
        tv = self.start()
        code, out = self.run_cli(tv, "abrir", "youtube")
        self.assertEqual(code, 0)
        self.assertEqual(tv.launched, ["111299001912"])
        code, out = self.run_cli(tv, "cerrar", "YouTube")
        self.assertEqual(code, 0)
        self.assertNotIn("111299001912", tv.running)

    def test_abrir_ambiguous(self):
        tv = self.start(apps=[{"appId": "1", "name": "Rakuten TV"}, {"appId": "2", "name": "Pluto TV"}])
        code, out = self.run_cli(tv, "abrir", "tv")
        self.assertEqual(code, 1)
        self.assertIn("varias", out)

    def test_diagnostico_old_wifi_tv(self):
        tv = self.start(model="17_KANTM_UHD", model_name="UE55MU6100", running={"11101200001"})
        code, out = self.run_cli(tv, "diagnostico", "--muestras", "2")
        self.assertEqual(code, 0)
        self.assertIn("2017", out)
        self.assertIn("poca memoria", out)
        self.assertIn("red:", out)
        self.assertIn("limpiar:", out)
        self.assertNotIn("device-care", out)

    def test_diagnostico_new_wired_tv(self):
        tv = self.start(model="21_NIKEM_UHD", model_name="UE43AU7105", network="wired")
        code, out = self.run_cli(tv, "diagnostico", "--muestras", "2")
        self.assertEqual(code, 0)
        self.assertIn("cable", out)
        self.assertIn("device-care", out)
        self.assertNotIn("limpiar:", out)

    def test_unreachable_tv(self):
        code = samsungtv.main(["--ip", "127.0.0.1", "--puerto", "1", "info"])
        self.assertEqual(code, 1)

    def test_guia_interactive(self):
        answers = iter(["s"] * 3 + ["q"])
        out = io.StringIO()
        with mock.patch("builtins.input", lambda *_: next(answers)), contextlib.redirect_stdout(out):
            code = samsungtv.main(["guia", "--anyo", "2017"])
        self.assertEqual(code, 0)
        self.assertIn("Hechos: actualizar, reinicio-frio, autoejecutar", out.getvalue())
        self.assertNotIn("Cuidado del dispositivo > Iniciar", out.getvalue())  # no existe en 2017


if __name__ == "__main__":
    unittest.main()
