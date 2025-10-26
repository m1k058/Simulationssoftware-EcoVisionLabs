import sys
import json
import tempfile
import unittest
from pathlib import Path

# Ensure the local source-code directory is importable
sys.path.insert(0, str(Path.cwd() / "source-code"))

from config_manager import ConfigManager


class TestConfigManager(unittest.TestCase):
    def setUp(self):
        # create a temporary directory with a minimal config.json
        self.tmpdir = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self.tmpdir.name)
        self.config_file = self.tmp_path / "config.json"

        cfg = {
            "GLOBAL": {"max_datasets": 10, "output_dir": str(self.tmp_path / "out")},
            "DATAFRAMES": [
                {
                    "id": 0,
                    "name": "DS0",
                    "path": str(Path.cwd() / "raw-data" / "DATA_EXAMPLE.csv"),
                    "datatype": "SMARD",
                    "description": ""
                }
            ],
            "PLOTS": []
        }

        with open(self.config_file, "w", encoding="utf-8") as f:
            json.dump(cfg, f)

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_create_plot_from_ui(self):
        cm = ConfigManager(config_path=self.config_file)

        ui = {
            "dataset": {"id": 0, "name": "DS0"},
            "date_start": "01.01.2023 00:00",
            "date_end": "02.01.2023 00:00",
            "energy_sources": ["PV"],
            "plot_name": "UnitTest Plot",
            "save_plot": False,
        }

        new_id = cm.create_plot_from_ui(ui)
        self.assertIsInstance(new_id, int)

        # The new plot should be present in the manager's in-memory config
        plots = cm.get_plots()
        self.assertTrue(any(p.get("id") == new_id for p in plots))

        # Because save_plot was False, the on-disk config should remain unchanged
        with open(self.config_file, "r", encoding="utf-8") as f:
            on_disk = json.load(f)
        self.assertEqual(on_disk.get("PLOTS", []), [])

    def test_create_plot_and_save(self):
        # Verify that when save_plot=True the new plot is written to disk
        cm = ConfigManager(config_path=self.config_file)

        ui = {
            "dataset": {"id": 0, "name": "DS0"},
            "date_start": "01.01.2023 00:00",
            "date_end": "02.01.2023 00:00",
            "energy_sources": ["PV"],
            "plot_name": "SaveTest Plot",
            "save_plot": True,
        }

        new_id = cm.create_plot_from_ui(ui)
        self.assertIsInstance(new_id, int)

        # The new plot should be present in-memory
        plots = cm.get_plots()
        self.assertTrue(any(p.get("id") == new_id for p in plots))

        # Because save_plot was True, the on-disk config should include the new plot
        with open(self.config_file, "r", encoding="utf-8") as f:
            on_disk = json.load(f)
        self.assertTrue(any(p.get("id") == new_id for p in on_disk.get("PLOTS", [])))


if __name__ == "__main__":
    unittest.main()
