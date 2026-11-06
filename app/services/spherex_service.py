"""Query SPHEREx and return a PNG for the API response."""

from io import BytesIO
from threading import Lock

import pyvo
from astropy.coordinates import SkyCoord
import astropy.units as u
from astropy.io import fits
from astropy.visualization import simple_norm
import matplotlib

matplotlib.use("Agg")  # Render on the server without a graphical display.
import matplotlib.pyplot as plt
import numpy as np


class SpherexNotFoundError(Exception):
    """No spectral image overlaps the requested position."""


class SpherexUpstreamError(Exception):
    """IRSA could not supply a usable spectral image."""


_render_lock = Lock()  # Protect pyplot's shared state during concurrent requests.


# The default cutout size is 0.05 degrees, around 3 arc minutes.
def query_spherex(
    ra_deg: float,
    dec_deg: float,
    cutout_size_i: float = 0.05,
    fake_color_theme: str = "gray",
) -> bytes:
    """Query SPHEREx data at an ICRS coordinate in degrees and return PNG bytes."""
    coord = SkyCoord(ra=ra_deg, dec=dec_deg, unit="deg", frame="icrs")
    cutout_size = cutout_size_i * u.degree
    print(f"Querying SPHEREx data for: {coord.ra.value}, {coord.dec.value}")

    if fake_color_theme not in matplotlib.colormaps:
        raise ValueError("Unknown fake_color_theme; use a Matplotlib colormap such as gray or plasma.")

    service = pyvo.dal.TAPService("https://irsa.ipac.caltech.edu/TAP")
    query = f"""
SELECT
    'https://irsa.ipac.caltech.edu/' || a.uri || '?center={coord.ra.value},{coord.dec.value}d&size={cutout_size.value}' AS download_url,
    p.time_bounds_lower,
    p.energy_bandpassname
FROM spherex.artifact a
JOIN spherex.plane p ON a.planeid = p.planeid
WHERE 1 = CONTAINS(POINT('ICRS', {coord.ra.value}, {coord.dec.value}), p.poly)
ORDER BY p.time_bounds_lower
"""

    try:
        results_table = service.search(query).to_table()
    except Exception as e:
        raise SpherexUpstreamError("Unable to query SPHEREx data from IRSA.") from e

    print(f"Number of overlapping SPHEREx spectral images found: {len(results_table)}")

    if len(results_table) > 0:
        fits_url = results_table["download_url"][0]
        print(f"Fetching FITS cutout from: {fits_url}")
        try:
            # Read directly from the URL without saving or caching a FITS file.
            with fits.open(fits_url, cache=False) as hdul:
                print("\n--- FITS File Info ---")
                hdul.info()

                image_data = hdul["IMAGE"].data
                print(f"\nSuccessfully loaded IMAGE extension. Shape: {image_data.shape}")
                data = image_data.astype(np.float32)
        except Exception as e:
            raise SpherexUpstreamError("Error streaming or opening SPHEREx FITS file.") from e

        norm = simple_norm(data, stretch="asinh", percent=99.5)

        with _render_lock:
            fig, ax = plt.subplots(figsize=(8, 8))
            try:
                im = ax.imshow(data, origin="lower", cmap=fake_color_theme, norm=norm)
                plt.colorbar(im, ax=ax, label="MJy/sr")

                ax.set_title("SPHEREx Spectral Image")
                ax.axis("off")
                # Return the PNG to the endpoint instead of writing output.png.
                with BytesIO() as output:
                    plt.savefig(output, format="png", dpi=150, bbox_inches="tight")
                    return output.getvalue()
            finally:
                plt.close(fig)
    else:
        raise SpherexNotFoundError("No SPHEREx data found coverage for this coordinate.")
