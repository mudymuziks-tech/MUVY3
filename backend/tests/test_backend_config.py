import importlib
import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class SupabaseConfigurationTests(unittest.TestCase):
    def test_supabase_module_does_not_crash_without_env(self):
        original = {key: os.environ.get(key) for key in ("SUPABASE_URL", "SUPABASE_KEY")}
        try:
            for key in ("SUPABASE_URL", "SUPABASE_KEY"):
                os.environ.pop(key, None)

            import app.db.supabase as supabase_module
            importlib.reload(supabase_module)
            self.assertIsNone(supabase_module.supabase)
        finally:
            for key, value in original.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value

    def test_match_clip_rejects_empty_query(self):
        from matcher.matcher import match_clip

        self.assertIsNone(match_clip([], object()))


if __name__ == "__main__":
    unittest.main()
