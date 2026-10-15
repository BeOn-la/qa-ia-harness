from __future__ import annotations

import unittest

from qa_harness.visual_interpretation import PageVisualEnriched, sort_visuals_canvas_order


def _v(vid: str, y: float, x: float) -> PageVisualEnriched:
    return PageVisualEnriched(
        visual_id=vid,
        visual_type="card",
        query_refs=(),
        native_refs=(),
        x=x,
        y=y,
        height=10,
        width=10,
        bookmark_ids=(),
        navigation_page_ids=(),
        action_button_kind=None,
        has_visual_link=False,
    )


class CanvasOrderTests(unittest.TestCase):
    def test_sort_top_to_bottom_left_to_right(self):
        visuals = [_v("b", 100, 50), _v("a", 10, 200), _v("c", 100, 10)]
        ordered = sort_visuals_canvas_order(visuals)
        self.assertEqual([v.visual_id for v in ordered], ["a", "c", "b"])


if __name__ == "__main__":
    unittest.main()
