"""Dựng từng lớp feature raster (F1..F8 theo bảng 4.2 PROJECT_PLAN.md).

Mọi lớp đều phải cùng CRS (EPSG:32648), cùng độ phân giải 30m, cùng vùng cắt
(ranh giới TP.HCM đã buffer 2km).

Chạy:  python src/features.py
"""
import ee
import geopandas as gpd

from config import BOUNDARY_BUFFER_PATH, FEATURES_DIR, GEE_DEM, GEE_DEM_BAND, NODATA
from gee_utils import (
    download_image,
    gdf_to_ee_geometry,
    init_gee,
    log_raster,
    mosaic_keep_scale,
)


def build_elevation(region: ee.Geometry):
    """F1 — độ cao mặt đất từ FABDEM (Copernicus GLO-30 đã loại nhà cửa và cây cối).

    Các bước, tất cả chạy trên máy Google:
      mosaic_keep_scale : ghép các tile thành ảnh liền, GIỮ độ phân giải gốc 30.92m
                          (nếu dùng .mosaic() trần, độ phân giải tụt về 111km)
      resample bilinear : độ cao là số đo liên tục nên nội suy trung bình lân cận.
                          Mặc định của GEE là 'nearest', hợp cho dữ liệu phân loại.
      clip              : cắt theo ranh giới đã buffer 2km
      unmask            : điền NODATA cho phần ngoài vùng cắt. Nếu để trống sẽ thành 0,
                          mà 0 là độ cao THẬT ở TP.HCM -> không phân biệt được.
                          sameFootprint=False là BẮT BUỘC: mặc định unmask chỉ điền bên
                          trong phạm vi ảnh gốc, phần ngoài vẫn rỗng và xuất ra vẫn là 0.
    """
    out = FEATURES_DIR / "elevation.tif"
    img = (
        mosaic_keep_scale(GEE_DEM, GEE_DEM_BAND)
        .resample("bilinear")
        .clip(region)
        .unmask(NODATA, sameFootprint=False)
        .rename("elevation")
    )
    download_image(img, region, out)
    log_raster(out)
    return out


def main() -> None:
    init_gee()

    boundary = gpd.read_file(BOUNDARY_BUFFER_PATH)
    region = gdf_to_ee_geometry(boundary)

    print("F1 — elevation (FABDEM: Copernicus GLO-30 đã loại nhà cửa và cây cối)")
    build_elevation(region)


if __name__ == "__main__":
    main()
