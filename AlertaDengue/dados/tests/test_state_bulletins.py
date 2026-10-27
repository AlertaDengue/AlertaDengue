"""Tests for state weekly bulletin PDF discovery and navigation (issue #1146).

Covers:
1. The parent report page keeps its selectors; the state page hosts bulletins.
2. State and epidemiological week validation and PDF URL construction.
3. PDF availability checks and graceful errors.
4. Existing state and municipal report routes remain unchanged.
5. Year-boundary and 52/53-week-year handling uses the epiweeks library.
"""

from __future__ import annotations

from io import BytesIO
from itertools import pairwise
import socket
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError

from django.core.cache import cache
from django.core.exceptions import ImproperlyConfigured
from django.test import TestCase
from django.urls import reverse
from epiweeks import Week

from dados.dbdata import UF_CODES
from dados.state_bulletins import (
    VALID_UF_CODES,
    BulletinAvailability,
    EpiWeekInfo,
    build_bulletin_url,
    epiweek_options,
    get_bulletins_base_url,
    is_bulletin_available,
    validate_uf,
    validate_year_week,
    week_label,
)

# ---------------------------------------------------------------------------
# Unit tests: state_bulletins module
# ---------------------------------------------------------------------------


class TestValidateUf(TestCase):
    """validate_uf: accept valid codes, reject everything else."""

    def test_valid_uf_uppercase(self):
        self.assertEqual(validate_uf("RJ"), "RJ")

    def test_valid_uf_lowercase_normalised(self):
        self.assertEqual(validate_uf("rj"), "RJ")

    def test_valid_uf_with_whitespace(self):
        self.assertEqual(validate_uf("  SP  "), "SP")

    def test_all_known_ufs_accepted(self):
        for uf in VALID_UF_CODES:
            self.assertEqual(validate_uf(uf), uf)

    def test_valid_uf_codes_match_dbdata_mapping(self):
        self.assertEqual(VALID_UF_CODES, frozenset(UF_CODES))

    def test_blank_raises(self):
        with self.assertRaises(ValueError):
            validate_uf("")

    def test_none_raises(self):
        with self.assertRaises(ValueError):
            validate_uf(None)  # type: ignore[arg-type]

    def test_unknown_uf_raises(self):
        with self.assertRaises(ValueError):
            validate_uf("XX")

    def test_path_traversal_raises(self):
        with self.assertRaises(ValueError):
            validate_uf("../etc")

    def test_digits_raise(self):
        with self.assertRaises(ValueError):
            validate_uf("12")

    def test_too_long_raises(self):
        with self.assertRaises(ValueError):
            validate_uf("RJX")


class TestValidateYearWeek(TestCase):
    """validate_year_week: accept valid YYYYWW, reject garbage."""

    def test_valid_standard_week(self):
        year, week = validate_year_week("202640")
        self.assertEqual(year, 2026)
        self.assertEqual(week, 40)

    def test_valid_week_01(self):
        year, week = validate_year_week("202601")
        self.assertEqual(year, 2026)
        self.assertEqual(week, 1)

    def test_blank_raises(self):
        with self.assertRaises(ValueError):
            validate_year_week("")

    def test_none_raises(self):
        with self.assertRaises(ValueError):
            validate_year_week(None)  # type: ignore[arg-type]

    def test_non_digits_raise(self):
        with self.assertRaises(ValueError):
            validate_year_week("ABCDEF")

    def test_too_short_raises(self):
        with self.assertRaises(ValueError):
            validate_year_week("20261")

    def test_too_long_raises(self):
        with self.assertRaises(ValueError):
            validate_year_week("2026401")

    def test_week_zero_raises(self):
        with self.assertRaises(ValueError):
            validate_year_week("202600")

    def test_week_54_raises(self):
        with self.assertRaises(ValueError):
            validate_year_week("202654")

    def test_week_53_accepted_for_long_years(self):
        year, week = validate_year_week("202053")
        self.assertEqual((year, week), (2020, 53))

    def test_week_53_rejected_when_not_valid_for_year(self):
        with self.assertRaises(ValueError):
            validate_year_week("202153")

    def test_year_boundary_next_year_week1(self):
        # Some dates late in December belong to epiweek 1 of the next year.
        # validate_year_week just parses; it does not enforce a date range.
        year, week = validate_year_week("202701")
        self.assertEqual(year, 2027)
        self.assertEqual(week, 1)


class TestBuildBulletinUrl(TestCase):
    """build_bulletin_url: correct URL for known states and weeks."""

    def test_rj_week_40_2026(self):
        url = build_bulletin_url("RJ", 2026, 40)
        self.assertIn("/RJ/Estado/ERJ-2026/ERJ-202640.pdf", url)
        self.assertTrue(url.startswith("https://"))

    def test_sp_week_01(self):
        url = build_bulletin_url("SP", 2026, 1)
        self.assertIn("/SP/Estado/ESP-2026/ESP-202601.pdf", url)

    def test_week_number_is_zero_padded(self):
        url = build_bulletin_url("MG", 2025, 5)
        self.assertIn("EMG-202505.pdf", url)

    def test_uses_configured_base_url(self):
        with self.settings(
            STATE_BULLETINS_BASE_URL=(
                "https://info.dengue.mat.br/test-publications"
            )
        ):
            url = build_bulletin_url("RJ", 2026, 40)
        self.assertTrue(
            url.startswith("https://info.dengue.mat.br/test-publications/")
        )

    def test_rejects_configured_non_official_origin(self):
        with self.settings(
            STATE_BULLETINS_BASE_URL="https://cdn.example.com/pdfs"
        ):
            with self.assertRaises(ImproperlyConfigured):
                get_bulletins_base_url()

    def test_rejects_non_https_configured_base(self):
        with self.settings(
            STATE_BULLETINS_BASE_URL=(
                "http://info.dengue.mat.br/relatorios/Estados"
            )
        ):
            with self.assertRaises(ImproperlyConfigured):
                get_bulletins_base_url()

    def test_rejects_path_traversal_in_configured_base(self):
        with self.settings(
            STATE_BULLETINS_BASE_URL=(
                "https://info.dengue.mat.br/relatorios/%2e%2e/private"
            )
        ):
            with self.assertRaises(ImproperlyConfigured):
                get_bulletins_base_url()

    def test_invalid_uf_raises(self):
        with self.assertRaises(ValueError):
            build_bulletin_url("XX", 2026, 40)

    def test_week_zero_raises(self):
        with self.assertRaises(ValueError):
            build_bulletin_url("RJ", 2026, 0)

    def test_week_54_raises(self):
        with self.assertRaises(ValueError):
            build_bulletin_url("RJ", 2026, 54)

    def test_invalid_week_53_for_year_raises(self):
        with self.assertRaises(ValueError):
            build_bulletin_url("RJ", 2021, 53)

    def test_year_out_of_range_raises(self):
        with self.assertRaises(ValueError):
            build_bulletin_url("RJ", 1800, 40)

    def test_path_traversal_not_possible(self):
        """The UF is validated before URL construction; path traversal must fail."""
        with self.assertRaises(ValueError):
            build_bulletin_url("../etc", 2026, 40)


class TestEpiweekOptions(TestCase):
    """epiweek_options: returns EpiWeekInfo tuples, most-recent first."""

    def test_returns_correct_count(self):
        opts = epiweek_options(n_weeks=10)
        self.assertEqual(len(opts), 10)

    def test_most_recent_first(self):
        opts = epiweek_options(n_weeks=5)
        for i in range(len(opts) - 1):
            a, b = opts[i], opts[i + 1]
            # Earlier in the list should be >= later (most-recent first)
            self.assertGreaterEqual(
                (a.year, a.week),
                (b.year, b.week),
            )

    def test_results_are_epiweekinfo(self):
        opts = epiweek_options(n_weeks=3)
        for item in opts:
            self.assertIsInstance(item, EpiWeekInfo)
            self.assertGreaterEqual(item.week, 1)
            self.assertLessEqual(item.week, 53)

    def test_year_boundary_handled(self):
        """Adjacent options remain consecutive across epidemiological years."""
        opts = epiweek_options(n_weeks=60)
        for newer, older in pairwise(opts):
            older_week = Week(older.year, older.week, system="CDC")
            newer_week = Week(newer.year, newer.week, system="CDC")
            self.assertEqual(older_week + 1, newer_week)

    def test_five_year_archive_range_crosses_year_boundaries(self):
        opts = epiweek_options(n_weeks=260)
        self.assertEqual(len(opts), 260)
        self.assertGreater(len({item.year for item in opts}), 4)


class TestWeekLabel(TestCase):
    def test_format(self):
        self.assertEqual(week_label(EpiWeekInfo(2026, 40)), "SE 40/2026")

    def test_zero_padded(self):
        self.assertEqual(week_label(EpiWeekInfo(2026, 5)), "SE 05/2026")


class TestBulletinAvailability(TestCase):
    def setUp(self):
        cache.clear()

    @staticmethod
    def _http_error(status: int) -> HTTPError:
        return HTTPError(
            "https://info.dengue.mat.br/test.pdf",
            status,
            "upstream response",
            {},
            BytesIO(),
        )

    @staticmethod
    def _response(status: int) -> MagicMock:
        response = MagicMock()
        response.status = status
        response.read.return_value = b"%"
        response.__enter__.return_value = response
        return response

    def test_head_request_is_bounded_and_does_not_follow_redirects(self):
        response = self._response(200)
        with patch(
            "dados.state_bulletins.urllib.request.build_opener"
        ) as build_opener:
            opener = build_opener.return_value
            opener.open.return_value = response

            self.assertIs(
                is_bulletin_available("https://info.dengue.mat.br/test.pdf"),
                BulletinAvailability.AVAILABLE,
            )

        request = opener.open.call_args.args[0]
        self.assertEqual(request.get_method(), "HEAD")
        self.assertEqual(opener.open.call_args.kwargs["timeout"], 5)
        self.assertEqual(
            build_opener.call_args.args[0].__name__,
            "_NoRedirectHandler",
        )

    def test_missing_pdf_is_distinct_from_upstream_error(self):
        with patch(
            "dados.state_bulletins.urllib.request.build_opener"
        ) as build_opener:
            build_opener.return_value.open.side_effect = self._http_error(404)
            self.assertIs(
                is_bulletin_available(
                    "https://info.dengue.mat.br/missing.pdf"
                ),
                BulletinAvailability.MISSING,
            )

    def test_upstream_http_error_is_not_reported_as_missing(self):
        with patch(
            "dados.state_bulletins.urllib.request.build_opener"
        ) as build_opener:
            build_opener.return_value.open.side_effect = self._http_error(503)
            self.assertIs(
                is_bulletin_available(
                    "https://info.dengue.mat.br/upstream-error.pdf"
                ),
                BulletinAvailability.UPSTREAM_ERROR,
            )

    def test_timeout_is_reported_separately(self):
        with patch(
            "dados.state_bulletins.urllib.request.build_opener"
        ) as build_opener:
            build_opener.return_value.open.side_effect = socket.timeout(
                "request timed out"
            )
            self.assertIs(
                is_bulletin_available(
                    "https://info.dengue.mat.br/timeout.pdf"
                ),
                BulletinAvailability.TIMEOUT,
            )

    def test_redirect_is_rejected_without_following(self):
        with patch(
            "dados.state_bulletins.urllib.request.build_opener"
        ) as build_opener:
            opener = build_opener.return_value
            opener.open.side_effect = self._http_error(302)
            self.assertIs(
                is_bulletin_available(
                    "https://info.dengue.mat.br/redirect.pdf"
                ),
                BulletinAvailability.REDIRECT_REJECTED,
            )
        self.assertEqual(opener.open.call_count, 1)

    def test_head_unsupported_falls_back_to_bounded_range_get(self):
        head_opener = MagicMock()
        head_opener.open.side_effect = self._http_error(405)
        get_opener = MagicMock()
        response = self._response(206)
        get_opener.open.return_value = response
        with patch(
            "dados.state_bulletins.urllib.request.build_opener",
            side_effect=[head_opener, get_opener],
        ):
            self.assertIs(
                is_bulletin_available(
                    "https://info.dengue.mat.br/head-unsupported.pdf"
                ),
                BulletinAvailability.AVAILABLE,
            )
        request = get_opener.open.call_args.args[0]
        self.assertEqual(request.get_method(), "GET")
        self.assertEqual(request.get_header("Range"), "bytes=0-0")
        response.read.assert_called_once_with(1)

    def test_fallback_head_unsupported_is_reported(self):
        head_opener = MagicMock()
        head_opener.open.side_effect = self._http_error(501)
        get_opener = MagicMock()
        get_opener.open.side_effect = self._http_error(405)
        with patch(
            "dados.state_bulletins.urllib.request.build_opener",
            side_effect=[head_opener, get_opener],
        ):
            self.assertIs(
                is_bulletin_available(
                    "https://info.dengue.mat.br/head-also-unsupported.pdf"
                ),
                BulletinAvailability.HEAD_UNSUPPORTED,
            )

    def test_arbitrary_origin_is_rejected_before_network_request(self):
        with patch(
            "dados.state_bulletins.urllib.request.build_opener"
        ) as build_opener:
            with self.assertRaises(ValueError):
                is_bulletin_available("https://example.com/test.pdf")
        build_opener.assert_not_called()

    def test_confirmed_results_are_cached(self):
        with patch(
            "dados.state_bulletins.urllib.request.build_opener"
        ) as build_opener:
            build_opener.return_value.open.return_value = self._response(200)
            for _ in range(2):
                result = is_bulletin_available(
                    "https://info.dengue.mat.br/cached.pdf"
                )
        self.assertIs(result, BulletinAvailability.AVAILABLE)
        self.assertEqual(build_opener.call_count, 1)


# ---------------------------------------------------------------------------
# Integration tests: views and URL routing
# ---------------------------------------------------------------------------


class TestReportPageRendering(TestCase):
    """The parent report page retains only the existing report selector."""

    def test_report_page_returns_200(self):
        response = self.client.get(reverse("dados:report"))
        self.assertEqual(response.status_code, 200)

    def test_report_page_does_not_contain_bulletin_form(self):
        response = self.client.get(reverse("dados:report"))
        content = response.content.decode("utf-8")
        self.assertNotIn("boletins-semanais-pdf", content)
        self.assertNotIn("bulletin-year-week", content)
        self.assertNotIn("Abrir boletim em PDF", content)

    def test_existing_report_form_still_present(self):
        """The original municipal/state report form must not be removed."""
        response = self.client.get(reverse("dados:report"))
        content = response.content.decode("utf-8")
        self.assertIn("form-report", content)
        self.assertIn("report-type", content)


class TestStateReportPageRendering(TestCase):
    def setUp(self):
        self.response = self.client.get("/report/RJ/state")
        self.content = self.response.content.decode("utf-8")

    def test_state_page_displays_bulletin_form_and_inherited_state(self):
        self.assertEqual(self.response.status_code, 200)
        self.assertIn("Boletins semanais em PDF", self.content)
        self.assertIn("Rio de Janeiro (RJ)", self.content)
        self.assertIn('action="/report/RJ/bulletin-pdf/"', self.content)

    def test_bulletin_form_has_week_selector_but_no_uf_selector(self):
        self.assertIn('name="bulletin_year_week"', self.content)
        self.assertNotIn("bulletin_uf", self.content)
        self.assertNotIn('name="state"', self.content)

    def test_existing_date_based_report_form_is_preserved(self):
        self.assertIn('id="epidate"', self.content)
        self.assertIn('id="form-report"', self.content)
        self.assertIn("Abrir Relatório", self.content)

    def test_invalid_route_state_is_rejected(self):
        response = self.client.get("/report/XX/state")
        self.assertEqual(response.status_code, 404)

    def test_page_render_does_not_check_remote_pdf_availability(self):
        with patch("dados.views.is_bulletin_available") as availability_check:
            response = self.client.get("/report/RJ/state")
        self.assertEqual(response.status_code, 200)
        availability_check.assert_not_called()

    def test_municipal_report_selector_still_renders(self):
        with patch(
            "dados.views.RegionalParameters.get_cities", return_value={}
        ):
            response = self.client.get("/report/RJ/city")
        self.assertEqual(response.status_code, 200)
        self.assertIn(
            "report_filter_city.html",
            [template.name for template in response.templates],
        )


class TestStateBulletinPdfView(TestCase):
    """StateBulletinPdfView: POST validation and redirect behaviour."""

    def _post(self, state: str, year_week: str):
        return self.client.post(
            reverse("dados:report_bulletin_pdf", kwargs={"state": state}),
            data={"bulletin_year_week": year_week},
        )

    def test_valid_rj_week_redirects(self):
        with patch(
            "dados.views.is_bulletin_available",
            return_value=BulletinAvailability.AVAILABLE,
        ):
            response = self._post("RJ", "202640")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response["Location"],
            "https://info.dengue.mat.br/relatorios/Estados/RJ/Estado/"
            "ERJ-2026/ERJ-202640.pdf",
        )

    def test_valid_sp_week_redirects(self):
        with patch(
            "dados.views.is_bulletin_available",
            return_value=BulletinAvailability.AVAILABLE,
        ):
            response = self._post("SP", "202601")
        self.assertEqual(response.status_code, 302)
        self.assertIn(
            "/SP/Estado/ESP-2026/ESP-202601.pdf", response["Location"]
        )

    def test_redirect_url_uses_configured_base(self):
        with self.settings(
            STATE_BULLETINS_BASE_URL=(
                "https://info.dengue.mat.br/test-publications"
            )
        ):
            with patch(
                "dados.views.is_bulletin_available",
                return_value=BulletinAvailability.AVAILABLE,
            ):
                response = self._post("RJ", "202640")
        self.assertEqual(response.status_code, 302)
        self.assertIn(
            "https://info.dengue.mat.br/test-publications/",
            response["Location"],
        )

    def test_invalid_year_week_returns_error_page(self):
        response = self._post("RJ", "ABCDEF")
        self.assertEqual(response.status_code, 400)
        self.assertIn(
            "Boletins semanais em PDF",
            response.content.decode("utf-8"),
        )

    def test_week_zero_returns_error_page(self):
        response = self._post("RJ", "202600")
        self.assertEqual(response.status_code, 400)

    def test_week_54_returns_error_page(self):
        response = self._post("RJ", "202654")
        self.assertEqual(response.status_code, 400)

    def test_empty_week_returns_error_page(self):
        response = self._post("RJ", "")
        self.assertEqual(response.status_code, 400)

    def test_future_week_is_rejected(self):
        current_week = epiweek_options(n_weeks=1)[0]
        future_week = (
            Week(
                current_week.year,
                current_week.week,
                system="CDC",
            )
            + 1
        )
        response = self._post(
            "RJ",
            f"{future_week.year}{future_week.week:02d}",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn(
            "report_filter_state.html",
            [template.name for template in response.templates],
        )

    def test_invalid_state_is_not_routable(self):
        response = self.client.post(
            "/report/XX/bulletin-pdf/",
            data={"bulletin_year_week": "202640"},
        )
        self.assertEqual(response.status_code, 404)

    def test_missing_pdf_keeps_user_on_state_page_and_preserves_week(self):
        with patch(
            "dados.views.is_bulletin_available",
            return_value=BulletinAvailability.MISSING,
        ):
            response = self._post("RJ", "202640")
        self.assertEqual(response.status_code, 404)
        content = response.content.decode("utf-8")
        self.assertIn("Boletins semanais em PDF", content)
        self.assertIn("Rio de Janeiro (RJ)", content)
        self.assertRegex(content, r'value="202640"\s+selected')
        self.assertIn('id="epidate"', content)
        self.assertIn("ainda não foi publicado", content)

    def test_upstream_errors_render_distinct_responses(self):
        for availability, status_code, expected_message in (
            (
                BulletinAvailability.UPSTREAM_ERROR,
                502,
                "servidor de boletins",
            ),
            (
                BulletinAvailability.TIMEOUT,
                504,
                "demorou para responder",
            ),
            (
                BulletinAvailability.REDIRECT_REJECTED,
                502,
                "redirecionou a consulta",
            ),
            (
                BulletinAvailability.HEAD_UNSUPPORTED,
                502,
                "não permitiu verificar",
            ),
        ):
            with self.subTest(availability=availability):
                with patch(
                    "dados.views.is_bulletin_available",
                    return_value=availability,
                ):
                    response = self._post("RJ", "202640")
                self.assertEqual(response.status_code, status_code)
                self.assertIn(
                    expected_message,
                    response.content.decode("utf-8"),
                )

    def test_invalid_week_rerenders_child_with_state_and_date_selector(self):
        response = self._post("RJ", "202654")
        content = response.content.decode("utf-8")
        self.assertEqual(response.status_code, 400)
        self.assertIn("Boletins semanais em PDF", content)
        self.assertIn("Rio de Janeiro (RJ)", content)
        self.assertIn('id="epidate"', content)
        self.assertIn('action="/report/RJ/bulletin-pdf/"', content)

    def test_existing_report_navigation_unchanged(self):
        """A GET to the existing report state filter still works."""
        response = self.client.get("/report/RJ/state")
        self.assertEqual(response.status_code, 200)

    def test_pdf_availability_is_checked_before_redirect(self):
        with patch(
            "dados.views.is_bulletin_available",
            return_value=BulletinAvailability.MISSING,
        ) as availability_check:
            response = self._post("RJ", "202640")
        availability_check.assert_called_once_with(
            build_bulletin_url("RJ", 2026, 40)
        )
        self.assertEqual(response.status_code, 404)

    def test_bulletin_route_does_not_collide_with_report_routes(self):
        from django.urls import resolve

        self.assertEqual(
            resolve("/report/RJ/state").url_name,
            "report_filter",
        )
        self.assertEqual(
            resolve("/report/RJ/202640").url_name,
            "report_state",
        )
        self.assertEqual(
            resolve("/report/RJ/city").url_name,
            "report_filter",
        )
        self.assertEqual(
            resolve("/report/RJ/bulletin-pdf/").url_name,
            "report_bulletin_pdf",
        )


class TestBulletinUrlConstruction(TestCase):
    """End-to-end URL construction checks against the known PDF pattern."""

    def test_rj_pattern(self):
        """ERJ-202640.pdf at the expected path."""
        url = build_bulletin_url("RJ", 2026, 40)
        expected_suffix = "/RJ/Estado/ERJ-2026/ERJ-202640.pdf"
        self.assertTrue(
            url.endswith(expected_suffix),
            f"URL {url!r} does not end with {expected_suffix!r}",
        )

    def test_all_ufs_build_without_error(self):
        """Every supported state must be able to build a URL for week 40 of 2026."""
        for uf in sorted(VALID_UF_CODES):
            url = build_bulletin_url(uf, 2026, 40)
            self.assertIn(uf, url)

    def test_52_week_year_week_52(self):
        """2026 has 52 epiweeks; week 52 must build fine."""
        url = build_bulletin_url("RJ", 2026, 52)
        self.assertIn("ERJ-202652.pdf", url)

    def test_53_week_year_week_53(self):
        """The CDC calendar's valid week 53 uses the same URL convention."""
        url = build_bulletin_url("RJ", 2020, 53)
        self.assertIn("ERJ-202053.pdf", url)

    def test_no_path_traversal_in_output(self):
        """The constructed URL must not contain '..' sequences."""
        url = build_bulletin_url("RJ", 2026, 40)
        self.assertNotIn("..", url)
