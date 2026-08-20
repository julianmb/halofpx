import tempfile
import unittest
from pathlib import Path
from unittest import mock

from halofpx import hardware


class ApuVramDetectionTests(unittest.TestCase):
    def _make_card(self, vram_bytes: int) -> Path:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        card = Path(tmp.name) / "card1" / "device"
        card.mkdir(parents=True)
        (card / "mem_info_vram_total").write_text(f"{vram_bytes}\n")
        return Path(tmp.name) / "card1"

    def test_dgpu_uses_sysfs_vram(self):
        card = self._make_card(2 * 1024**3)
        with mock.patch.object(hardware.Path, "glob", return_value=iter([card])):
            gib = hardware.get_gpu_vram_gib(is_apu=False)
        self.assertEqual(gib, 2.0)

    def test_apu_ignores_vram_carveout(self):
        # On APUs sysfs reports only the pre-allocated carveout (e.g. 2 GiB);
        # shared/unified memory must be used instead.
        meminfo = "MemTotal:       131000000 kB\n"
        with mock.patch("builtins.open", mock.mock_open(read_data=meminfo)):
            with mock.patch.object(hardware.Path, "exists", return_value=False):
                gib = hardware.get_gpu_vram_gib(is_apu=True)
        self.assertAlmostEqual(gib, 62.5, places=1)


if __name__ == "__main__":
    unittest.main()
