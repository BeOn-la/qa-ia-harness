from __future__ import annotations

import unittest

from qa_harness.board_profiles import resolve_board
from qa_harness.common import ContractError


class BoardProfileTests(unittest.TestCase):
    def test_resolve_default_board(self):
        config = {
            "default_board": "b1",
            "boards": {"b1": {"board_qa_root": "x"}, "b2": {}},
        }
        bid, entry = resolve_board(config, None)
        self.assertEqual(bid, "b1")
        self.assertEqual(entry["board_qa_root"], "x")

    def test_resolve_explicit_board(self):
        config = {"default_board": "b1", "boards": {"b1": {}, "b2": {"label": "two"}}}
        bid, entry = resolve_board(config, "b2")
        self.assertEqual(bid, "b2")
        self.assertEqual(entry["label"], "two")

    def test_legacy_pbi_qa(self):
        config = {"pbi_qa": {"board_qa_root": "a/b"}}
        bid, entry = resolve_board(config, None)
        self.assertEqual(bid, "legacy")
        self.assertEqual(entry["board_qa_root"], "a/b")

    def test_unknown_board_raises(self):
        config = {"default_board": "b1", "boards": {"b1": {}}}
        with self.assertRaises(ContractError):
            resolve_board(config, "missing")


if __name__ == "__main__":
    unittest.main()
