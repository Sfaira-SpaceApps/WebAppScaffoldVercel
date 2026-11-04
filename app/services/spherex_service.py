"""Retrieve the earliest overlapping SPHEREx image as an in-memory PNG."""

from io import BytesIO
from threading import Lock

import matplotlib
import numpy as np
import pyvo
import requests
from astropy.coordinates import SkyCoord
from astropy.io import fits
from astropy.visualization import simple_norm
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure


class SpherexNotFoundError(Exception):
    """No spectral image overlaps the requested position."""


class SpherexUpstreamError(Exception):
    """IRSA could not supply a usable spectral image."""


_render_lock = Lock()  # Matplotlib rendering is not thread safe.


class _IRSASession(requests.Session):
    def request(self, method, url, **kwargs):
        kwargs.setdefault("timeout", 30)
        return super().request(method, url, **kwargs)


def query_spherex(
    ra_deg: float,
    dec_deg: float,
    cutout_size_i: float = 0.05,
    fake_color_theme: str = "gray",
) -> bytes:
    """Return PNG bytes; raise on invalid input, missing coverage, or IRSA errors."""
    if not (np.isfinite(ra_deg) and 0 <= ra_deg < 360):
        raise ValueError("ra_deg must be finite and in [0, 360).")
    if not (np.isfinite(dec_deg) and -90 <= dec_deg <= 90):
        raise ValueError("dec_deg must be finite and in [-90, 90].")
    if not (np.isfinite(cutout_size_i) and 0 < cutout_size_i <= 1):
        raise ValueError("cutout_size_i must be finite, greater than 0, and at most 1 degree.")
    if fake_color_theme not in matplotlib.colormaps:
        raise ValueError("Unknown fake_color_theme; use a Matplotlib colormap such as gray or plasma.")

    coord = SkyCoord(ra=ra_deg, dec=dec_deg, unit="deg", frame="icrs")
    query = f"""
SELECT TOP 1
    'https://irsa.ipac.caltech.edu/' || a.uri || '?center={coord.ra.deg},{coord.dec.deg}d&size={cutout_size_i}' AS download_url,
    p.time_bounds_lower,
    p.energy_bandpassname
FROM spherex.artifact a
JOIN spherex.plane p ON a.planeid = p.planeid
WHERE 1 = CONTAINS(POINT('ICRS', {coord.ra.deg}, {coord.dec.deg}), p.poly)
ORDER BY p.time_bounds_lower
"""
    try:
        with _IRSASession() as session:
            service = pyvo.dal.TAPService("https://irsa.ipac.caltech.edu/TAP", session=session)
            results = service.search(query).to_table()
            if len(results) == 0:
                raise SpherexNotFoundError("No SPHEREx coverage found for this coordinate.")
            with session.get(str(results["download_url"][0]), timeout=60) as response:
                response.raise_for_status()
                with fits.open(BytesIO(response.content), memmap=False) as hdul:
                    data = np.array(hdul["IMAGE"].data, dtype=np.float32, copy=True)
            if data.ndim != 2 or not np.isfinite(data).any():
                raise ValueError("SPHEREx IMAGE extension has no usable two-dimensional data.")
    except SpherexNotFoundError:
        raise
    except Exception as exc:
        raise SpherexUpstreamError("Unable to retrieve SPHEREx image from IRSA.") from exc

    with _render_lock:
        fig = Figure(figsize=(8, 8))
        FigureCanvasAgg(fig)
        try:
            ax = fig.subplots()
            masked_data = np.ma.masked_invalid(data)
            norm = simple_norm(masked_data, stretch="asinh", percent=99.5)
            image = ax.imshow(masked_data, origin="lower", cmap=fake_color_theme, norm=norm)
            fig.colorbar(image, ax=ax, label="MJy/sr")
            ax.set_title("SPHEREx Spectral Image")
            ax.axis("off")
            with BytesIO() as output:
                fig.savefig(output, format="png", dpi=150, bbox_inches="tight")
                return output.getvalue()
        finally:
            fig.clear()
