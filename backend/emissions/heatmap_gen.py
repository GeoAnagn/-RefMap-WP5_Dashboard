"""Utility script to inspect coordinate formatting for the Leaflet overlays.

It loads the lat/lon regridded NetCDF files and reports:
- Which variables are used as longitude/latitude
- Their dimensions, units, and value ranges
- Detected CRS (if any) and bounding box in that CRS

Run from this folder with: python plot_leaflet.py
"""

from typing import Dict, Optional, Tuple
import json
import os
import shutil

import numpy as np
import xarray as xr
from pyproj import CRS, Transformer
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap, TwoSlopeNorm

try: 
    import cartopy.crs as ccrs
    import cartopy.feature as cfeature

    CARTOPY_AVAILABLE = True
except Exception:
    CARTOPY_AVAILABLE = False


LON_NAMES = ["lon", "longitude", "x"]
LAT_NAMES = ["lat", "latitude", "y"]
EUROPE_EXTENT = (-15.0, 50.0, 30.0, 80.0)

SHORT_NAME = {
    "PM25": "pm25",
    "SpeciesConcVV_NO2": "no2",
    "SpeciesConcVV_NO": "no",
    "SpeciesConcVV_O3": "o3",
}

CONTOUR_MAPS_ROOT = os.path.join(os.path.dirname(__file__), "contour_maps")
DEFAULT_LEVEL_DIR = "10"
CONTOUR_LEVELS = 40
CONTOUR_DPI = 300


def _get_coord(ds: xr.Dataset, names) -> Optional[xr.DataArray]:
    for name in names:
        if name in ds.coords:
            return ds[name]
        if name in ds:
            return ds[name]
    return None


def detect_crs(ds: xr.Dataset) -> Optional[CRS]:
    if "crs" in ds:
        try:
            return CRS.from_cf(ds["crs"].attrs)
        except Exception:
            pass
    for var in ds.data_vars:
        gm = ds[var].attrs.get("grid_mapping")
        if gm and gm in ds:
            try:
                return CRS.from_cf(ds[gm].attrs)
            except Exception:
                pass
    lon = _get_coord(ds, LON_NAMES)
    lat = _get_coord(ds, LAT_NAMES)
    lon_units = lon.attrs.get("units", "") if lon is not None else ""
    lat_units = lat.attrs.get("units", "") if lat is not None else ""
    if str(lon_units).startswith("degrees") or str(lat_units).startswith("degrees"):
        return CRS.from_epsg(4326)
    return None


def coord_summary(coord: xr.DataArray) -> Dict:
    arr = coord.values
    arr = np.asarray(arr)
    finite_arr = arr[np.isfinite(arr)]
    if finite_arr.size:
        vmin = float(finite_arr.min())
        vmax = float(finite_arr.max())
    else:
        vmin = vmax = np.nan
    monotonic = bool(np.all(np.diff(arr.reshape(-1)) >= 0)) if arr.size > 1 else True
    orientation = "1D" if arr.ndim == 1 else "2D"
    return {
        "name": coord.name,
        "dims": list(coord.dims),
        "shape": list(arr.shape),
        "units": coord.attrs.get("units", ""),
        "min": vmin,
        "max": vmax,
        "monotonic_non_decreasing": monotonic,
        "ndim": arr.ndim,
        "orientation": orientation,
    }


def dataset_summary(path: str) -> Dict:
    ds = xr.open_dataset(path)
    lon = _get_coord(ds, LON_NAMES)
    lat = _get_coord(ds, LAT_NAMES)
    crs = detect_crs(ds)
    summary: Dict[str, object] = {
        "path": path,
        "dims": {k: int(v) for k, v in ds.sizes.items()},
        "crs": crs.to_string() if crs else None,
    }
    if lon is not None:
        summary["lon"] = coord_summary(lon)
    if lat is not None:
        summary["lat"] = coord_summary(lat)

    if lon is not None and lat is not None:
        lon_arr = np.asarray(lon.values)
        lat_arr = np.asarray(lat.values)
        try:
            bbox = (
                float(np.nanmin(lon_arr)),
                float(np.nanmax(lon_arr)),
                float(np.nanmin(lat_arr)),
                float(np.nanmax(lat_arr)),
            )
        except Exception:
            bbox = None
        summary["bbox"] = bbox

        try:
            transformer = Transformer.from_crs("EPSG:4326", "EPSG:3857", always_xy=True)
            corners_lon = np.array([bbox[0], bbox[1], bbox[0], bbox[1]])
            corners_lat = np.array([bbox[2], bbox[2], bbox[3], bbox[3]])
            x_wm, y_wm = transformer.transform(corners_lon, corners_lat)
            bbox_wm = (
                float(np.nanmin(x_wm)),
                float(np.nanmax(x_wm)),
                float(np.nanmin(y_wm)),
                float(np.nanmax(y_wm)),
            )
            summary["bbox_web_mercator"] = bbox_wm
        except Exception:
            summary["bbox_web_mercator"] = None
    return summary


def subset_to_extent(ds: xr.Dataset, extent: Tuple[float, float, float, float]) -> xr.Dataset:
    lon = _get_coord(ds, LON_NAMES)
    lat = _get_coord(ds, LAT_NAMES)
    if lon is None or lat is None:
        return ds

    if lon.ndim == 1 and lat.ndim == 1:
        lon_min, lon_max, lat_min, lat_max = extent
        lon_slice = slice(lon_min, lon_max) if float(lon[0]) <= float(lon[-1]) else slice(lon_max, lon_min)
        lat_slice = slice(lat_min, lat_max) if float(lat[0]) <= float(lat[-1]) else slice(lat_max, lat_min)
        try:
            return ds.sel({lon.name: lon_slice, lat.name: lat_slice})
        except Exception:
            pass

    try:
        lon_arr, lat_arr = xr.broadcast(lon, lat)
        mask = (
            (lon_arr >= extent[0])
            & (lon_arr <= extent[1])
            & (lat_arr >= extent[2])
            & (lat_arr <= extent[3])
        )
        return ds.where(mask, drop=True)
    except Exception:
        return ds


def pick_var_for_plot(ds: xr.Dataset, lon_name: str, lat_name: str, preferred: Optional[Tuple[str, ...]] = None) -> Optional[str]:
    candidates = list(preferred or []) + [name for name in ds.data_vars if name not in (preferred or [])]
    for name in candidates:
        if name not in ds.data_vars:
            continue
        dims = set(ds[name].dims)
        if lon_name in dims and lat_name in dims:
            return name
    return None


def short_var_name(var_name: str) -> str:
    return SHORT_NAME.get(var_name, var_name.lower())


def spatial_vars(ds: xr.Dataset, lon_name: str, lat_name: str) -> Tuple[str, ...]:
    names = []
    for name, da in ds.data_vars.items():
        dims = set(da.dims)
        if lon_name in dims and lat_name in dims:
            names.append(name)
    return tuple(names)


def _finite_minmax(arr: np.ndarray) -> Optional[Tuple[float, float]]:
    finite = arr[np.isfinite(arr)]
    if finite.size == 0:
        return None
    return float(np.nanmin(finite)), float(np.nanmax(finite))


def padded_range(arr: np.ndarray, pad_fraction: float = 0.1) -> Optional[Tuple[float, float]]:
    mm = _finite_minmax(arr)
    if mm is None:
        return None
    vmin, vmax = mm
    span = vmax - vmin
    pad = pad_fraction * span if span != 0 else pad_fraction * max(abs(vmin), abs(vmax), 1e-9)
    return vmin - pad, vmax + pad


def plot_quicklook(
    ds: xr.Dataset,
    path: str,
    lon_name: str,
    lat_name: str,
    var_name: Optional[str] = None,
    preferred_vars: Optional[Tuple[str, ...]] = None,
    out_filename: Optional[str] = None,
) -> Optional[str]:
    target_var = var_name or pick_var_for_plot(ds, lon_name, lat_name, preferred_vars)
    if target_var is None:
        return None

    da = ds[target_var]

    da = da.transpose(lat_name, lon_name, missing_dims="ignore")

    for dim in list(da.dims):
        if dim not in {lon_name, lat_name}:
            da = da.isel({dim: 0})

    lon = ds[lon_name]
    lat = ds[lat_name]

    fig, ax = _make_map_axes(lon, lat, figsize=(8, 5))
    mesh_kwargs = {"shading": "auto"}
    if CARTOPY_AVAILABLE:
        mesh_kwargs["transform"] = ccrs.PlateCarree()
    mesh = ax.pcolormesh(lon, lat, da, **mesh_kwargs)
    if not CARTOPY_AVAILABLE:
        ax.set_xlabel(f"{lon_name} ({lon.attrs.get('units', '')})")
        ax.set_ylabel(f"{lat_name} ({lat.attrs.get('units', '')})")
    ax.set_title(f"{path} - {target_var}")
    fig.colorbar(mesh, ax=ax, label=da.attrs.get("units", ""))
    if out_filename:
        base_dir = os.path.dirname(os.path.abspath(path))
        out_path = os.path.join(base_dir, out_filename)
    else:
        out_path = path.replace(".nc4", f"_{target_var}_preview.png")
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    return out_path


def contour_overlay(
    ds: xr.Dataset,
    path: str,
    lon_name: str,
    lat_name: str,
    var_name: Optional[str] = None,
    preferred_vars: Optional[Tuple[str, ...]] = None,
    levels: int = CONTOUR_LEVELS,
    force_symmetric: bool = False,
    out_filename: Optional[str] = None,
    vmin_override: Optional[float] = None,
    vmax_override: Optional[float] = None,
) -> Optional[Tuple[str, Tuple[float, float, float, float]]]:
    target_var = var_name or pick_var_for_plot(ds, lon_name, lat_name, preferred_vars)
    if target_var is None:
        return None

    da = ds[target_var]
    da = da.transpose(lat_name, lon_name, missing_dims="ignore")
    for dim in list(da.dims):
        if dim not in {lon_name, lat_name}:
            da = da.isel({dim: 0})

    lon = np.asarray(ds[lon_name].values)
    lat = np.asarray(ds[lat_name].values)
    lon2d, lat2d = np.meshgrid(lon, lat)
    data = np.asarray(da.values)

    finite = data[np.isfinite(data)]
    if finite.size == 0:
        return None

    if vmin_override is not None and vmax_override is not None:
        vmin = float(vmin_override)
        vmax = float(vmax_override)
    elif force_symmetric:
        maxabs = float(np.nanmax(np.abs(finite)))
        if not np.isfinite(maxabs) or maxabs == 0:
            return None
        vmin = -maxabs
        vmax = maxabs
    else:
        vmin = float(np.nanpercentile(finite, 2))
        vmax = float(np.nanpercentile(finite, 98))
        if vmin == vmax:
            vmax = vmin + 1e-6
        if vmin >= 0:
            vmin = -max(vmax * 0.1, 1e-12)
        if vmax <= 0:
            vmax = max(-vmin * 0.1, 1e-12)

    if vmax <= vmin:
        vmax = vmin + 1e-6

    data = np.clip(data, vmin, vmax)
    cmap = LinearSegmentedColormap.from_list(
        "blue_transparent_red",
        [
            (0.0, (0.0, 0.0, 1.0, 0.9)),   
            (0.45, (0.0, 0.0, 1.0, 0.4)),  
            (0.5, (0.0, 0.0, 1.0, 0.0)),   
            (0.5, (1.0, 0.0, 0.0, 0.0)),   
            (0.55, (1.0, 0.0, 0.0, 0.4)),  
            (1.0, (1.0, 0.0, 0.0, 0.9)), 
        ],
    )
    norm = TwoSlopeNorm(vmin=vmin, vcenter=0.0, vmax=vmax)
    level_values = np.linspace(vmin, vmax, levels)

    fig, ax = plt.subplots(figsize=(8, 5), constrained_layout=True)
    ax.set_facecolor((0, 0, 0, 0))
    fig.patch.set_alpha(0)
    ax.contourf(lon2d, lat2d, data, levels=level_values, cmap=cmap, norm=norm)
    ax.set_xlim(float(lon.min()), float(lon.max()))
    ax.set_ylim(float(lat.min()), float(lat.max()))
    ax.axis("off")
    if out_filename:
        base_dir = os.path.dirname(os.path.abspath(path))
        out_path = os.path.join(base_dir, out_filename)
    else:
        out_path = path.replace(".nc4", f"_{target_var}_contour.png")
    fig.savefig(out_path, dpi=CONTOUR_DPI, transparent=True, bbox_inches="tight", pad_inches=0)
    plt.close(fig)
    bounds = (float(lon.min()), float(lon.max()), float(lat.min()), float(lat.max()))
    return out_path, bounds, (vmin, vmax)


def _make_map_axes(lon: xr.DataArray, lat: xr.DataArray, figsize=(8, 5)):
    """Create axes optionally backed by a cartopy basemap for preview plots."""

    lon_arr = np.asarray(lon.values)
    lat_arr = np.asarray(lat.values)
    lon_min, lon_max = float(np.nanmin(lon_arr)), float(np.nanmax(lon_arr))
    lat_min, lat_max = float(np.nanmin(lat_arr)), float(np.nanmax(lat_arr))

    if CARTOPY_AVAILABLE:
        fig, ax = plt.subplots(figsize=figsize, subplot_kw={"projection": ccrs.PlateCarree()})
        ax.set_extent([lon_min, lon_max, lat_min, lat_max], crs=ccrs.PlateCarree())
        ax.add_feature(cfeature.COASTLINE.with_scale("50m"), linewidth=0.6)
        ax.add_feature(cfeature.BORDERS.with_scale("50m"), linewidth=0.4)
        ax.add_feature(cfeature.LAKES.with_scale("50m"), linewidth=0.3)
        gl = ax.gridlines(draw_labels=True, linewidth=0.2, color="gray", alpha=0.5)
        gl.top_labels = False
        gl.right_labels = False
    else:
        fig, ax = plt.subplots(figsize=figsize)
        ax.set_xlim(lon_min, lon_max)
        ax.set_ylim(lat_min, lat_max)

    return fig, ax


def stash_contour(png_path: str, short_name: str, dataset_label: str, level_dir: str = DEFAULT_LEVEL_DIR) -> Optional[str]:
    """Move contour PNG into contour_maps/<level>/<SHORT>/ directory."""

    if not png_path or not os.path.exists(png_path):
        return None

    dest_dir = os.path.join(CONTOUR_MAPS_ROOT, level_dir, short_name.upper())
    try:
        os.makedirs(dest_dir, exist_ok=True)
        dest_path = os.path.join(dest_dir, f"{short_name}_ll_{dataset_label}_contour.png")
        shutil.move(png_path, dest_path)
        return dest_path
    except Exception:
        return None


def write_colorbar_metadata(
    short_name: str,
    dataset_label: str,
    vmin: Optional[float],
    vmax: Optional[float],
    level_dir: str = DEFAULT_LEVEL_DIR,
) -> Optional[str]:
    """Persist vmin/vmax per dataset in the metric subfolder for frontend colorbar use."""

    if vmin is None or vmax is None:
        return None

    dest_dir = os.path.join(CONTOUR_MAPS_ROOT, level_dir, short_name.upper())
    os.makedirs(dest_dir, exist_ok=True)
    meta_path = os.path.join(dest_dir, "colorbar.json")

    data: Dict[str, Dict[str, float]] = {}
    try:
        if os.path.exists(meta_path):
            with open(meta_path, "r", encoding="utf-8") as f:
                data = json.load(f)
    except Exception:
        data = {}

    data[str(dataset_label)] = {"vmin": float(vmin), "vmax": float(vmax)}

    try:
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        return meta_path
    except Exception:
        return None


def main():
    files = {
        "base": "latlon_regrid_base.nc4",
        "sens": "latlon_regrid_sens.nc4",
    }

    subsets = {}
    manifest = []

    for label, path in files.items():
        info = dataset_summary(path)
        print(f"\n=== {path} ===")
        print(f"Dims: {info['dims']}")
        print(f"CRS: {info['crs']}")
        lon_info = info.get("lon")
        lat_info = info.get("lat")
        if lon_info:
            print(f"Lon coord: {lon_info}")
        else:
            print("Lon coord: not found")
        if lat_info:
            print(f"Lat coord: {lat_info}")
        else:
            print("Lat coord: not found")
        bbox = info.get("bbox")
        if bbox:
            print(f"Bounding box (lon_min, lon_max, lat_min, lat_max): {bbox}")
        bbox_wm = info.get("bbox_web_mercator")
        if bbox_wm:
            print(f"Web Mercator bounds (x_min, x_max, y_min, y_max) meters: {bbox_wm}")

        try:
            ds_full = xr.open_dataset(path)
            ds_eu = subset_to_extent(ds_full, EUROPE_EXTENT)
            out_path = path.replace(".nc4", "_europe.nc4")
            ds_eu.to_netcdf(out_path)
            print(f"Saved Europe subset to {out_path} with dims {dict(ds_eu.sizes)}")
            lon = _get_coord(ds_eu, LON_NAMES)
            lat = _get_coord(ds_eu, LAT_NAMES)
            if lon is None or lat is None:
                continue

            subsets[label] = (ds_eu, lon.name, lat.name, out_path)
        except Exception as exc:
            print(f"Could not subset/save Europe extent for {path}: {exc}")

    preferred = ("PM25", "SpeciesConcVV_NO2", "SpeciesConcVV_O3")
    if "base" in subsets:
        ds_base, lon_b, lat_b, base_path = subsets["base"]
        all_base_vars = spatial_vars(ds_base, lon_b, lat_b)
        ordered_base = list(preferred) + [v for v in all_base_vars if v not in preferred]
        ds_sens = None
        lon_s = lat_s = sens_path = None
        if "sens" in subsets:
            ds_sens, lon_s, lat_s, sens_path = subsets["sens"]
        for var in ordered_base:
            if var not in ds_base:
                continue
            short = short_var_name(var)
            preview_name_base = f"{short}_ll_base_preview.png"
            contour_name_base = f"{short}_ll_base_contour.png"
            vmin_override = vmax_override = None
            if ds_sens is not None and var in ds_sens:
                base_range = _finite_minmax(np.asarray(ds_base[var].values))
                sens_range = _finite_minmax(np.asarray(ds_sens[var].values))
                candidates = []
                if base_range:
                    candidates.extend([abs(base_range[0]), abs(base_range[1])])
                if sens_range:
                    candidates.extend([abs(sens_range[0]), abs(sens_range[1])])
                maxabs = max(candidates) if candidates else None
                if maxabs is not None and np.isfinite(maxabs) and maxabs != 0:
                    vmin_override, vmax_override = -maxabs, maxabs
            if vmin_override is None or vmax_override is None:
                data_range = padded_range(np.asarray(ds_base[var].values), pad_fraction=0.1)
                if data_range:
                    vmin_override, vmax_override = data_range

            preview = plot_quicklook(ds_base, base_path, lon_b, lat_b, var_name=var, out_filename=preview_name_base)
            if preview:
                print(f"Saved preview plot to {preview}")
            contour = contour_overlay(
                ds_base,
                base_path,
                lon_b,
                lat_b,
                var_name=var,
                out_filename=contour_name_base,
                vmin_override=vmin_override,
                vmax_override=vmax_override,
            )
            if contour:
                png_path, bounds, vrange = contour
                print(
                    f"Saved contour overlay to {png_path} with bounds {bounds} (lon_min, lon_max, lat_min, lat_max)"
                    f" and v-range {vrange}"
                )
                meta_path = write_colorbar_metadata(short, "base", vrange[0], vrange[1], level_dir=DEFAULT_LEVEL_DIR)
                if meta_path:
                    print(f"Saved colorbar metadata to {meta_path}")
                stored = stash_contour(png_path, short, "base", level_dir=DEFAULT_LEVEL_DIR)
                if stored:
                    print(f"Moved contour to {stored}")
                manifest.append(
                    {
                        "dataset": "base",
                        "variable": var,
                        "preview": preview,
                        "contour": png_path,
                        "bounds": bounds,
                        "vmin": vrange[0],
                        "vmax": vrange[1],
                    }
                )

            if ds_sens is not None and var in ds_sens:
                preview_name_sens = f"{short}_ll_sens_preview.png"
                contour_name_sens = f"{short}_ll_sens_contour.png"
                preview_s = plot_quicklook(ds_sens, sens_path, lon_s, lat_s, var_name=var, out_filename=preview_name_sens)
                if preview_s:
                    print(f"Saved preview plot to {preview_s}")
                contour_s = contour_overlay(
                    ds_sens,
                    sens_path,
                    lon_s,
                    lat_s,
                    var_name=var,
                    out_filename=contour_name_sens,
                    vmin_override=vmin_override,
                    vmax_override=vmax_override,
                )
                if contour_s:
                    png_path, bounds, vrange = contour_s
                    print(
                        f"Saved contour overlay to {png_path} with bounds {bounds} (lon_min, lon_max, lat_min, lat_max)"
                        f" and v-range {vrange}"
                    )
                    meta_path = write_colorbar_metadata(short, "sens", vrange[0], vrange[1], level_dir=DEFAULT_LEVEL_DIR)
                    if meta_path:
                        print(f"Saved colorbar metadata to {meta_path}")
                    stored = stash_contour(png_path, short, "sens", level_dir=DEFAULT_LEVEL_DIR)
                    if stored:
                        print(f"Moved contour to {stored}")
                    manifest.append(
                        {
                            "dataset": "sens",
                            "variable": var,
                            "preview": preview_s,
                            "contour": png_path,
                            "bounds": bounds,
                            "vmin": vrange[0],
                            "vmax": vrange[1],
                        }
                    )

    if "base" in subsets and "sens" in subsets:
        ds_base, lon_b, lat_b, _ = subsets["base"]
        ds_sens, lon_s, lat_s, _ = subsets["sens"]
        if lon_b == lon_s and lat_b == lat_s:
            base_vars = set(spatial_vars(ds_base, lon_b, lat_b))
            sens_vars = set(spatial_vars(ds_sens, lon_s, lat_s))
            common = sorted(base_vars & sens_vars)
            diff_path = "latlon_regrid_diff.nc4"
            for var in common:
                try:
                    da_diff = ds_sens[var] - ds_base[var]
                    ds_diff = da_diff.to_dataset(name=var)
                    diff_range = _finite_minmax(np.asarray(da_diff.values))
                    if diff_range:
                        raw_vmin, raw_vmax = diff_range
                        maxabs = max(abs(raw_vmin), abs(raw_vmax))
                        if not np.isfinite(maxabs) or maxabs == 0:
                            diff_vmin = diff_vmax = None
                        else:
                            diff_vmin, diff_vmax = -maxabs, maxabs
                    else:
                        diff_vmin = diff_vmax = None
                    preview = plot_quicklook(ds_diff, diff_path, lon_b, lat_b, var_name=var)
                    if preview:
                        print(f"Saved diff preview for {var} to {preview}")
                    short = short_var_name(var)
                    contour_name = f"{short}_ll_diff_contour.png"
                    preview_name = f"{short}_ll_diff_preview.png"
                    if preview:
                        base_dir = os.path.dirname(os.path.abspath(diff_path))
                        new_preview = os.path.join(base_dir, preview_name)
                        try:
                            os.replace(preview, new_preview)
                            preview = new_preview
                        except Exception:
                            pass
                    contour = contour_overlay(
                        ds_diff,
                        diff_path,
                        lon_b,
                        lat_b,
                        var_name=var,
                        force_symmetric=False,
                        out_filename=contour_name,
                        vmin_override=diff_vmin,
                        vmax_override=diff_vmax,
                    )
                    if contour:
                        png_path, bounds, vrange = contour
                        print(
                            f"Saved diff contour for {var} to {png_path} with bounds {bounds} (lon_min, lon_max, lat_min, lat_max)"
                            f" and v-range {vrange}"
                        )
                        meta_path = write_colorbar_metadata(short, "diff", vrange[0], vrange[1], level_dir=DEFAULT_LEVEL_DIR)
                        if meta_path:
                            print(f"Saved colorbar metadata to {meta_path}")
                        stored = stash_contour(png_path, short, "diff", level_dir=DEFAULT_LEVEL_DIR)
                        if stored:
                            print(f"Moved contour to {stored}")
                        manifest.append(
                            {
                                "dataset": "diff",
                                "variable": var,
                                "preview": preview,
                                "contour": png_path,
                                "bounds": bounds,
                                "vmin": vrange[0],
                                "vmax": vrange[1],
                                "note": "sens - base",
                            }
                        )
                except Exception as exc:
                    print(f"Could not compute diff for {var}: {exc}")

    if manifest:
        manifest_path = os.path.join(os.path.dirname(__file__), "overlay_manifest.json")
        try:
            with open(manifest_path, "w", encoding="utf-8") as f:
                json.dump(manifest, f, indent=2)
            print(f"Saved overlay manifest to {manifest_path}")
        except Exception as exc:
            print(f"Could not write manifest: {exc}")


if __name__ == "__main__":
    main()
