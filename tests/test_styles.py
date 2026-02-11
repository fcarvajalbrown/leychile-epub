"""
Tests unitarios para los estilos CSS.

Author: Luis Aguilera Arteaga <luis@aguilera.cl>
"""

from leychile_epub.styles import CHILEAN_BLUE, CHILEAN_RED, FONT_SIZES, get_premium_css


class TestConstants:
    """Tests para las constantes de estilos."""

    def test_chilean_blue(self):
        assert CHILEAN_BLUE == "#0b3d91"

    def test_chilean_red(self):
        assert CHILEAN_RED == "#de1f2a"

    def test_font_sizes_presets(self):
        assert "small" in FONT_SIZES
        assert "medium" in FONT_SIZES
        assert "large" in FONT_SIZES
        assert "extra-large" in FONT_SIZES

    def test_font_sizes_keys(self):
        for preset in FONT_SIZES.values():
            assert "base" in preset
            assert "h1" in preset
            assert "h2" in preset
            assert "h3" in preset


class TestGetPremiumCSS:
    """Tests para get_premium_css."""

    def test_returns_css_string(self):
        css = get_premium_css()
        assert isinstance(css, str)
        assert len(css) > 0

    def test_contains_body_rule(self):
        css = get_premium_css()
        assert "body {" in css

    def test_contains_dark_mode(self):
        css = get_premium_css()
        assert "prefers-color-scheme: dark" in css

    def test_contains_print_styles(self):
        css = get_premium_css()
        assert "@media print" in css

    def test_contains_accessibility(self):
        css = get_premium_css()
        assert "prefers-contrast: high" in css

    def test_font_size_small(self):
        css = get_premium_css(font_size="small")
        assert FONT_SIZES["small"]["base"] in css

    def test_font_size_large(self):
        css = get_premium_css(font_size="large")
        assert FONT_SIZES["large"]["base"] in css

    def test_custom_line_spacing(self):
        css = get_premium_css(line_spacing=2.0)
        assert "2.0" in css

    def test_custom_margin(self):
        css = get_premium_css(margin="2em")
        assert "2em" in css

    def test_invalid_font_size_falls_back(self):
        css = get_premium_css(font_size="nonexistent")
        assert FONT_SIZES["medium"]["base"] in css

    def test_contains_legal_classes(self):
        css = get_premium_css()
        assert ".articulo-titulo" in css
        assert ".derogado" in css
        assert ".cover" in css
        assert ".encabezado" in css

    def test_contains_chilean_colors(self):
        css = get_premium_css()
        assert CHILEAN_BLUE in css
        assert CHILEAN_RED in css
