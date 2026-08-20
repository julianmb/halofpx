import unittest

from pathlib import Path

from halofpx.engine_manager import build_cache_args, get_cache_profile, get_amd_env


class CacheProfileTests(unittest.TestCase):
    def test_32gb_profile(self):
        self.assertEqual(
            get_cache_profile(32),
            {"name": "32GB", "cache_ram_mib": 8192, "ctx_checkpoints": 4},
        )

    def test_64gb_profile(self):
        self.assertEqual(
            get_cache_profile(64),
            {"name": "64GB", "cache_ram_mib": 16384, "ctx_checkpoints": 8},
        )

    def test_128gb_profile(self):
        self.assertEqual(
            get_cache_profile(128),
            {"name": "128GB", "cache_ram_mib": 32768, "ctx_checkpoints": 16},
        )

    def test_engine_environment_function_is_imported(self):
        self.assertTrue(callable(get_amd_env))

    def test_128gb_cache_command(self):
        profile = get_cache_profile(128)
        profile.update({"cache_reuse": 256, "checkpoint_every": 4096})
        args = build_cache_args(profile, Path("/tmp/slots"), mmap_enabled=False, mlock=True)
        self.assertEqual(args[args.index("-cram") + 1], "32768")
        self.assertEqual(args[args.index("-ctxcp") + 1], "16")
        self.assertIn("--no-mmap", args)
        self.assertIn("--cont-batching", args)
        self.assertIn("--kv-unified", args)
        self.assertIn("--mlock", args)


if __name__ == "__main__":
    unittest.main()
