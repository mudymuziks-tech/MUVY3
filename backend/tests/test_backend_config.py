import importlib
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class SupabaseConfigurationTests(unittest.TestCase):
    def test_supabase_module_fails_fast_without_env(self):
        original = {key: os.environ.get(key) for key in ("SUPABASE_URL", "SUPABASE_KEY")}
        try:
            for key in ("SUPABASE_URL", "SUPABASE_KEY"):
                os.environ.pop(key, None)

            with patch("dotenv.load_dotenv"):
                with self.assertRaisesRegex(RuntimeError, "SUPABASE_URL is not configured"):
                    import app.db.supabase as supabase_module
                    importlib.reload(supabase_module)
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
