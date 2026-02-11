"""
Tests unitarios para el CLI.

Author: Luis Aguilera Arteaga <luis@aguilera.cl>
"""

import tempfile
from pathlib import Path

import pytest

from leychile_epub.cli import create_parser, main, print_progress


class TestCreateParser:
    """Tests para create_parser."""

    def test_parser_creation(self):
        parser = create_parser()
        assert parser.prog == "leychile-epub"

    def test_parser_url_argument(self):
        parser = create_parser()
        args = parser.parse_args(["https://www.leychile.cl/Navegar?idNorma=242302"])
        assert args.url == "https://www.leychile.cl/Navegar?idNorma=242302"

    def test_parser_batch_flag(self):
        parser = create_parser()
        args = parser.parse_args(["--batch", "urls.txt"])
        assert args.batch == "urls.txt"

    def test_parser_output_default(self):
        parser = create_parser()
        args = parser.parse_args(["https://example.com"])
        assert args.output == "."

    def test_parser_output_custom(self):
        parser = create_parser()
        args = parser.parse_args(["-o", "/tmp/output", "https://example.com"])
        assert args.output == "/tmp/output"

    def test_parser_quiet_flag(self):
        parser = create_parser()
        args = parser.parse_args(["-q", "https://example.com"])
        assert args.quiet is True

    def test_parser_verbose_flag(self):
        parser = create_parser()
        args = parser.parse_args(["-v", "https://example.com"])
        assert args.verbose is True

    def test_parser_no_args(self):
        parser = create_parser()
        args = parser.parse_args([])
        assert args.url is None
        assert args.batch is None


class TestPrintProgress:
    """Tests para print_progress."""

    def test_progress_zero(self, capsys):
        print_progress(0.0, "Iniciando")
        captured = capsys.readouterr()
        assert "0%" in captured.out
        assert "Iniciando" in captured.out

    def test_progress_complete(self, capsys):
        print_progress(1.0, "Terminado")
        captured = capsys.readouterr()
        assert "100%" in captured.out

    def test_progress_half(self, capsys):
        print_progress(0.5, "Procesando")
        captured = capsys.readouterr()
        assert "50%" in captured.out


class TestMain:
    """Tests para la función main."""

    def test_no_args_shows_help(self):
        result = main([])
        assert result == 1

    def test_version_flag(self):
        with pytest.raises(SystemExit) as exc_info:
            main(["--version"])
        assert exc_info.value.code == 0

    def test_batch_file_not_found(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            result = main(["--batch", "/nonexistent/file.txt", "-o", tmpdir, "-q"])
            # process_batch returns (0, 0) when file not found, so failed==0 → exit 0
            assert result == 0

    def test_batch_empty_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            batch_file = Path(tmpdir) / "urls.txt"
            batch_file.write_text("# solo comentarios\n")
            result = main(["--batch", str(batch_file), "-o", tmpdir, "-q"])
            # process_batch returns (0, 0) for empty file, so failed==0 → exit 0
            assert result == 0
