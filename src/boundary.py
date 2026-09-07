"""Ranh giới TP.HCM cho project.

Quyết định (Ngày 2):
    - Vùng địa lý  : TP.HCM CŨ, trước đợt sáp nhập tỉnh 2025 (~2.100 km²)
    - Hành chính   : phường/xã MỚI theo cải cách 2025 (bỏ cấp quận/huyện)

Cách làm: GADM 4.1 (số hóa 2022, còn 63 tỉnh) cho ta hình dạng thành phố cũ, dùng làm
lưới lọc. OSM cho ta ranh giới phường/xã mới. Giữ những phường có tâm nằm trong vùng cũ,
rồi gộp lại thành ranh giới chính thức của project.

Vì sao không lấy thẳng ranh giới OSM của "Ho Chi Minh City": OSM đã cập nhật theo địa giới
mới, trả về 36.423 km² (gồm cả Bình Dương, Bà Rịa - Vũng Tàu, Côn Đảo và vùng biển).

Chạy:  python src/boundary.py
"""
import geopandas as gpd
import osmnx as ox

from config import (
    BOUNDARY_BUFFER_PATH,
    BOUNDARY_PATH,
    BUFFER_KM,
    CRS,
    GADM_RAW_PATH,
    OSM_CACHE_DIR,
    WARDS_PATH,
)

WGS84 = "EPSG:4326"          # hệ kinh/vĩ độ — chuẩn bắt buộc của định dạng GeoJSON
OSM_WARD_LEVEL = "6"         # sau cải cách 2025, phường/xã nằm ở admin_level=6 trên OSM


def log_gdf(gdf: gpd.GeoDataFrame, ten: str) -> None:
    """In thông tin kiểm tra của một lớp vector (quy ước mục 8 PROJECT_PLAN.md)."""
    g = gdf.to_crs(CRS)
    minx, miny, maxx, maxy = g.total_bounds
    print(
        f"  [{ten}] n={len(gdf)} | crs={gdf.crs} | "
        f"diện tích={g.geometry.area.sum() / 1e6:,.1f} km² | "
        f"bounds(m)=({minx:,.0f}, {miny:,.0f}) -> ({maxx:,.0f}, {maxy:,.0f})"
    )


def load_old_hcmc_extent() -> gpd.GeoDataFrame:
    """Vùng TP.HCM cũ từ GADM: gộp 24 quận/huyện thành một đa giác."""
    g = gpd.read_file(GADM_RAW_PATH)
    hcm = g[g["NAME_1"].str.contains("Minh", na=False)]
    if hcm.empty:
        raise RuntimeError(f"Không tìm thấy TP.HCM trong {GADM_RAW_PATH}")
    extent = hcm.dissolve()[["geometry"]].reset_index(drop=True)
    log_gdf(extent, "GADM - TP.HCM cũ")
    return extent


def fetch_new_wards(extent: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Phường/xã mới từ OSM, giữ lại những phường nằm trong vùng TP.HCM cũ."""
    ox.settings.use_cache = True
    ox.settings.cache_folder = str(OSM_CACHE_DIR)

    mask = extent.to_crs(WGS84).geometry.iloc[0]
    f = ox.features_from_polygon(mask, tags={"boundary": "administrative"})
    f = f[f.geometry.type.isin(["Polygon", "MultiPolygon"])]
    f = f[f["admin_level"] == OSM_WARD_LEVEL].to_crs(WGS84)

    # Lọc bằng TÂM đa giác, không phải giao nhau: phường của tỉnh lân cận có thể chạm
    # rìa vùng lọc, nhưng tâm của nó thì nằm ngoài.
    mask_m = extent.to_crs(CRS).geometry.iloc[0]
    keep = f.to_crs(CRS).geometry.representative_point().within(mask_m)
    wards = f[keep.values].copy()

    wards = wards.reset_index()[["name", "admin_level", "geometry"]]
    wards = wards.rename(columns={"name": "ward_name"}).sort_values("ward_name")
    wards = wards.reset_index(drop=True)

    log_gdf(wards, "OSM - phường/xã mới")
    return wards


def build_boundary(wards: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Gộp toàn bộ phường thành ranh giới thành phố."""
    b = wards.dissolve()[["geometry"]].reset_index(drop=True)
    log_gdf(b, "ranh giới thành phố")
    return b


def build_buffer(boundary: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Nới ranh giới ra BUFFER_KM km.

    Buffer BẮT BUỘC thực hiện ở hệ mét (CRS = EPSG:32648). Nếu buffer khi đang ở hệ
    kinh/vĩ độ, số 2000 sẽ được hiểu là 2000 ĐỘ — không báo lỗi, chỉ cho ra hình vô nghĩa.
    Lưu lại ở hệ kinh/vĩ độ vì chuẩn GeoJSON quy định vậy.
    """
    b_m = boundary.to_crs(CRS)
    buf = b_m.buffer(BUFFER_KM * 1000)
    out = gpd.GeoDataFrame(geometry=buf, crs=CRS).to_crs(WGS84)
    log_gdf(out, f"ranh giới + buffer {BUFFER_KM}km")
    return out


def main() -> None:
    print("1. Đọc vùng TP.HCM cũ từ GADM")
    extent = load_old_hcmc_extent()

    print("2. Lấy phường/xã mới từ OSM (lần đầu chậm, sau đó đọc từ cache)")
    wards = fetch_new_wards(extent)

    print("3. Gộp phường thành ranh giới thành phố")
    boundary = build_boundary(wards)

    print(f"4. Nới ranh giới thêm {BUFFER_KM}km")
    buffered = build_buffer(boundary)

    print("5. Lưu file")
    for gdf, path in [
        (wards, WARDS_PATH),
        (boundary, BOUNDARY_PATH),
        (buffered, BOUNDARY_BUFFER_PATH),
    ]:
        gdf.to_file(path, driver="GeoJSON")
        print(f"  -> {path}  ({path.stat().st_size / 1e6:.2f} MB)")


if __name__ == "__main__":
    main()
