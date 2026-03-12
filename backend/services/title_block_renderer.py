from __future__ import annotations

import io
from dataclasses import dataclass
from typing import Dict

import fitz
from PIL import Image, ImageChops

MIN_CROP_EDGE_PIXELS = 24
CONTEXT_RENDER_DPI = 96
CONTEXT_MAX_WIDTH_PIXELS = 1600


@dataclass(frozen=True)
class PixelBox:
    x: int
    y: int
    width: int
    height: int


@dataclass(frozen=True)
class RenderedTitleBlock:
    crop_png: bytes
    context_png: bytes
    crop_box_pixels: PixelBox
    page_width_points: float
    page_height_points: float


def convert_pdf_points_to_pixels(coords: Dict[str, float], dpi: int) -> PixelBox:
    scale = float(dpi) / 72.0
    return PixelBox(
        x=max(0, int(round(float(coords.get('x', 0)) * scale))),
        y=max(0, int(round(float(coords.get('y', 0)) * scale))),
        width=max(0, int(round(float(coords.get('width', 0)) * scale))),
        height=max(0, int(round(float(coords.get('height', 0)) * scale))),
    )


def _render_pixmap(page: fitz.Page, *, dpi: int, clip_rect: fitz.Rect | None = None) -> Image.Image:
    scale = float(dpi) / 72.0
    pixmap = page.get_pixmap(matrix=fitz.Matrix(scale, scale), clip=clip_rect, alpha=False)
    return Image.frombytes("RGB", [pixmap.width, pixmap.height], pixmap.samples)


def _image_to_png_bytes(image: Image.Image) -> bytes:
    buffer = io.BytesIO()
    image.save(buffer, format='PNG')
    return buffer.getvalue()


def _is_blank_image(image: Image.Image) -> bool:
    return ImageChops.invert(image.convert('L')).getbbox() is None


def render_title_block_region(
    pdf_bytes: bytes,
    title_block_coords: Dict[str, float],
    *,
    render_dpi: int,
) -> RenderedTitleBlock:
    if not pdf_bytes:
        raise ValueError("PDF content is empty")

    document = fitz.open(stream=pdf_bytes, filetype='pdf')
    try:
        if document.page_count < 1:
            raise ValueError("PDF does not contain any pages")

        page = document.load_page(0)
        page_rect = page.rect

        x = max(page_rect.x0, float(title_block_coords.get('x', 0)))
        y = max(page_rect.y0, float(title_block_coords.get('y', 0)))
        width = max(0.0, float(title_block_coords.get('width', 0)))
        height = max(0.0, float(title_block_coords.get('height', 0)))
        if width <= 0 or height <= 0:
            raise ValueError("Title block coordinates must have positive width and height")

        clip_rect = fitz.Rect(
            x,
            y,
            min(page_rect.x1, x + width),
            min(page_rect.y1, y + height),
        )
        if clip_rect.width <= 0 or clip_rect.height <= 0:
            raise ValueError("Title block crop does not intersect the first page")

        crop_image = _render_pixmap(page, dpi=render_dpi, clip_rect=clip_rect)
        if (
            crop_image.width < MIN_CROP_EDGE_PIXELS
            or crop_image.height < MIN_CROP_EDGE_PIXELS
        ):
            raise ValueError("Title block crop is too small to process")
        if _is_blank_image(crop_image):
            raise ValueError("Title block crop is blank")

        context_image = _render_pixmap(page, dpi=CONTEXT_RENDER_DPI)
        if context_image.width > CONTEXT_MAX_WIDTH_PIXELS:
            scale = CONTEXT_MAX_WIDTH_PIXELS / float(context_image.width)
            context_image = context_image.resize(
                (
                    int(round(context_image.width * scale)),
                    int(round(context_image.height * scale)),
                ),
                Image.Resampling.LANCZOS,
            )

        return RenderedTitleBlock(
            crop_png=_image_to_png_bytes(crop_image),
            context_png=_image_to_png_bytes(context_image),
            crop_box_pixels=convert_pdf_points_to_pixels(title_block_coords, render_dpi),
            page_width_points=float(page_rect.width),
            page_height_points=float(page_rect.height),
        )
    finally:
        document.close()

