import unittest

from halofpx.server import app


class ServerRouteTests(unittest.TestCase):
    def test_method_and_path_pairs_are_unique(self):
        pairs = []
        for route in app.routes:
            for method in getattr(route, "methods", set()):
                pairs.append((method, route.path))
        self.assertEqual(len(pairs), len(set(pairs)))


if __name__ == "__main__":
    unittest.main()
