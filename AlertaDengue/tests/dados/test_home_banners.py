from html.parser import HTMLParser
from pathlib import Path
import struct

from django.template.loader import render_to_string
from django.utils import translation
import pytest


class _CarouselParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.indicators: list[dict[str, str | None]] = []
        self.items: list[dict[str, str | None]] = []
        self.links: list[dict[str, str | None]] = []

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        attributes = dict(attrs)
        classes = attributes.get("class", "").split()
        if tag == "li" and attributes.get("data-target") == "#carouselTop":
            self.indicators.append(attributes)
        if tag == "div" and "carousel-item" in classes:
            self.items.append(attributes)
        if tag == "a":
            self.links.append(attributes)


@pytest.mark.parametrize(
    "language, suffix", [("pt-br", "pt"), ("en", "en"), ("es", "es")]
)
def test_home_banner_renders_localized_epidesc_slide(
    language: str, suffix: str
) -> None:
    with translation.override(language):
        content = render_to_string("components/home/home_banners_section.html")

    assert (
        "https://cran.r-project.org/web/packages/epidesc/index.html" in content
    )
    assert f"/static/img/home/banners/banner_epidesc_{suffix}.svg" in content
    assert (
        f"/static/img/home/banners/banner_epidesc_mobile_{suffix}.svg"
        in content
    )
    assert 'media="(max-width: 575.98px)"' in content
    assert "banner_epidesc_" in content
    assert content.count("carousel-item--epidesc") == 1

    asset_directory = (
        Path(__file__).resolve().parents[2] / "static/img/home/banners"
    )
    assert (asset_directory / f"banner_epidesc_{suffix}.svg").is_file()
    assert (asset_directory / f"banner_epidesc_mobile_{suffix}.svg").is_file()

    carousel = _CarouselParser()
    carousel.feed(content)
    epidesc_link = next(
        link
        for link in carousel.links
        if link.get("href")
        == "https://cran.r-project.org/web/packages/epidesc/index.html"
    )
    assert epidesc_link["target"] == "_blank"
    assert epidesc_link["rel"] == "noopener noreferrer"


def test_home_banner_has_matching_indicators_and_slides() -> None:
    carousel = _CarouselParser()
    carousel.feed(
        render_to_string("components/home/home_banners_section.html")
    )

    assert [
        indicator["data-slide-to"] for indicator in carousel.indicators
    ] == [
        "0",
        "1",
        "2",
        "3",
    ]
    assert len(carousel.items) == 4
    assert (
        sum(
            "active" in item.get("class", "").split()
            for item in carousel.items
        )
        == 1
    )
    assert "active" in carousel.items[0].get("class", "").split()
    assert (
        sum(
            "active" in indicator.get("class", "").split()
            for indicator in carousel.indicators
        )
        == 1
    )
    assert 'data-interval="7000"' in render_to_string(
        "components/home/home_banners_section.html"
    )


@pytest.mark.parametrize(
    "language, suffix", [("pt-br", "pt"), ("en", "en"), ("es", "es")]
)
def test_home_banner_renders_localized_webinar_slide(
    language: str, suffix: str
) -> None:
    with translation.override(language):
        content = render_to_string("components/home/home_banners_section.html")

    assert (
        f"/static/img/home/banners/banner_dengue_2027_{suffix}.png" in content
    )
    assert (
        f"/static/img/home/banners/banner_dengue_2027_mobile_{suffix}.svg"
        in content
    )
    assert "https://forms.cloud.microsoft/r/8EgGB5yVR4" in content
    expected_label = {
        "pt-br": "Webinário: Preparação para a temporada de dengue 2027",
        "en": "Webinar: Preparing for the 2027 dengue season",
        "es": "Webinario: Preparación para la temporada de dengue 2027",
    }[language]
    assert f'aria-label="{expected_label}"' in content

    asset_directory = (
        Path(__file__).resolve().parents[2] / "static/img/home/banners"
    )
    image_path = asset_directory / f"banner_dengue_2027_{suffix}.png"
    image_bytes = image_path.read_bytes()
    assert image_bytes[:8] == b"\x89PNG\r\n\x1a\n"
    assert struct.unpack(">II", image_bytes[16:24]) == (1280, 720)

    mobile_image = (
        asset_directory / f"banner_dengue_2027_mobile_{suffix}.svg"
    ).read_text()
    assert 'viewBox="0 0 390 650"' in mobile_image
    assert "data:image/png;base64," in mobile_image

    carousel = _CarouselParser()
    carousel.feed(content)
    webinar_link = next(
        link
        for link in carousel.links
        if link.get("href") == "https://forms.cloud.microsoft/r/8EgGB5yVR4"
    )
    assert webinar_link["target"] == "_blank"
    assert webinar_link["rel"] == "noopener noreferrer"
    assert webinar_link.get("aria-label") == expected_label
