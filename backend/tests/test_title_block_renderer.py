from __future__ import annotations

import unittest

import fitz

from services.title_block_renderer import (
    convert_pdf_points_to_pixels,
    render_title_block_region,
)


def _build_pdf(*, with_text: bool) -> bytes:
    document = fitz.open()
    try:
        page = document.new_page(width=500, height=300)
        if with_text:
            page.insert_text((360, 250), "A-101", fontsize=18)
            page.insert_text((360, 270), "Ground Floor Plan", fontsize=12)
        return document.tobytes()
    finally:
        document.close()


class TitleBlockRendererTests(unittest.TestCase):
    def test_convert_pdf_points_to_pixels_scales_from_pdf_points(self) -> None:
        box = convert_pdf_points_to_pixels(
            {'x': 72, 'y': 36, 'width': 144, 'height': 72},
            dpi=300,
        )
        self.assertEqual(box.x, 300)
        self.assertEqual(box.y, 150)
        self.assertEqual(box.width, 600)
        self.assertEqual(box.height, 300)

    def test_render_title_block_region_rejects_blank_crop(self) -> None:
        with self.assertRaisesRegex(ValueError, "blank"):
            render_title_block_region(
                _build_pdf(with_text=False),
                {'x': 320, 'y': 200, 'width': 140, 'height': 80},
                render_dpi=300,
            )

    def test_render_title_block_region_rejects_too_small_crop(self) -> None:
        with self.assertRaisesRegex(ValueError, "too small"):
            render_title_block_region(
                _build_pdf(with_text=True),
                {'x': 320, 'y': 200, 'width': 2, 'height': 2},
                render_dpi=300,
            )


if __name__ == '__main__':
    unittest.main()

