from io import BytesIO
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
from astropy.io import fits
from astropy.table import Table
from fastapi.testclient import TestClient

from app.main import app
from app.services import spherex_service

client = TestClient(app)
PARAMS = {"ra_deg": 210.80227, "dec_deg": 54.34895}


def test_endpoint_returns_png() -> None:
    with patch.object(spherex_service, "query_spherex", return_value=b"png") as query:
        response = client.get("/spherex", params=PARAMS)
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    assert response.content == b"png"
    query.assert_called_once_with(210.80227, 54.34895, 0.05, "gray")


@pytest.mark.parametrize("params", [
    {}, {**PARAMS, "ra_deg": 360}, {**PARAMS, "dec_deg": -91},
    {**PARAMS, "cutout_size_i": 0}, {**PARAMS, "ra_deg": "nan"},
])
def test_invalid_parameters_do_not_query_irsa(params) -> None:
    with patch.object(spherex_service, "query_spherex") as query:
        assert client.get("/spherex", params=params).status_code == 422
    query.assert_not_called()


@pytest.mark.parametrize("error, status", [
    (ValueError("Invalid colormap"), 422),
    (spherex_service.SpherexNotFoundError("No coverage"), 404),
    (spherex_service.SpherexUpstreamError("IRSA failed"), 502),
])
def test_endpoint_errors(error, status) -> None:
    with patch.object(spherex_service, "query_spherex", side_effect=error):
        response = client.get("/spherex", params=PARAMS)
    assert response.status_code == status
    assert response.json()["detail"] == str(error)


def test_service_renders_fits_in_memory() -> None:
    with BytesIO() as buffer:
        fits.HDUList([
            fits.PrimaryHDU(),
            fits.ImageHDU(np.arange(100, dtype=np.float32).reshape(10, 10), name="IMAGE"),
        ]).writeto(buffer)
        fits_bytes = buffer.getvalue()
    response = MagicMock()
    response.__enter__.return_value = response
    response.content = fits_bytes
    with patch.object(spherex_service.pyvo.dal, "TAPService") as tap, \
         patch.object(spherex_service.requests.Session, "get", return_value=response):
        tap.return_value.search.return_value.to_table.return_value = Table({
            "download_url": ["https://irsa.ipac.caltech.edu/example.fits"],
        })
        png = spherex_service.query_spherex(**PARAMS)
    assert png.startswith(b"\x89PNG\r\n\x1a\n")


def test_service_reports_no_coverage() -> None:
    with patch.object(spherex_service.pyvo.dal, "TAPService") as tap:
        tap.return_value.search.return_value.to_table.return_value = Table()
        with pytest.raises(spherex_service.SpherexNotFoundError):
            spherex_service.query_spherex(**PARAMS)


def test_service_rejects_unknown_colormap_before_query() -> None:
    with patch.object(spherex_service.pyvo.dal, "TAPService") as tap:
        with pytest.raises(ValueError):
            spherex_service.query_spherex(**PARAMS, fake_color_theme="invalid")
        tap.assert_not_called()
