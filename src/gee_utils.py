"""Helper cho Google Earth Engine: xác thực, khởi tạo, export."""
from pathlib import Path

import ee
import geopandas as gpd
import numpy as np
import rasterio
import requests
from rasterio.merge import merge

from config import CRS, GEE_DEM, GEE_PROJECT, NODATA, RESOLUTION


def init_gee(project: str | None = None) -> None:
    """Khởi tạo GEE. Nếu chưa xác thực thì mở trình duyệt yêu cầu đăng nhập.

    Chạy `earthengine authenticate` một lần trước đó là đủ cho mọi lần sau.
    """
    project = project or GEE_PROJECT
    if not project:
        raise RuntimeError(
            "Thiếu GEE_PROJECT. Thêm dòng GEE_PROJECT=<cloud-project-id> vào file .env"
        )

    try:
        ee.Initialize(project=project)
    except Exception:
        # Chưa có credentials -> chạy luồng xác thực rồi thử lại
        ee.Authenticate()
        ee.Initialize(project=project)

    print(f"GEE initialized | project = {project}")


def mosaic_keep_scale(collection_id: str, band: str | None = None) -> ee.Image:
    """Ghép ImageCollection thành một ảnh mà KHÔNG mất độ phân giải gốc.

    Bẫy của Earth Engine: `.mosaic()` trả về ảnh mang độ phân giải mặc định 1 độ
    (~111 km/pixel). Nếu sau đó gọi `.resample()`, nó sẽ nội suy từ lưới 111 km xuống
    30 m — bôi nhoè toàn bộ dữ liệu mà KHÔNG báo lỗi. Đã kiểm chứng ở Ngày 2: cả
    TP.HCM bị san phẳng thành ~21 m.

    Cách sửa: lấy phép chiếu của ảnh gốc rồi gán lại bằng setDefaultProjection.
    """
    col = ee.ImageCollection(collection_id)
    proj = col.first().select(0 if band is None else band).projection()
    img = col.mosaic()
    if band is not None:
        img = img.select(band)
    return img.setDefaultProjection(proj)


def gdf_to_ee_geometry(gdf: gpd.GeoDataFrame) -> ee.Geometry:
    """Đổi ranh giới GeoPandas -> ee.Geometry để gửi lên Earth Engine.

    GEE luôn nhận toạ độ ở hệ kinh/vĩ độ (EPSG:4326), nên đổi về hệ đó trước.
    """
    geom = gdf.to_crs("EPSG:4326").geometry.union_all()
    return ee.Geometry(geom.__geo_interface__)


MAX_TILE_MB = 24          # ngưỡng an toàn dưới giới hạn ~32MB của getDownloadURL


def _fetch_tile(image: ee.Image, crs: str, scale: int,
                xmin: float, ymin: float, xmax: float, ymax: float) -> bytes:
    """Tải một mảnh GeoTIFF theo khung chữ nhật cho sẵn (toạ độ hệ mét).

    Dùng `region` + `scale`. KHÔNG dùng `crsTransform` + `dimensions`: Earth Engine bỏ
    qua crsTransform và nhét toàn bộ ảnh vừa khít kích thước yêu cầu, làm pixel méo
    (đã kiểm chứng: res ra 29.9 x 59.5 m thay vì 30 x 30). Các mép mảnh đều là bội số
    của `scale` nên các mảnh tự khít cùng một lưới.
    """
    rect = ee.Geometry.Rectangle([xmin, ymin, xmax, ymax], proj=crs, geodesic=False)
    url = image.getDownloadURL({
        "region": rect,
        "scale": scale,
        "crs": crs,
        "format": "GEO_TIFF",
    })
    r = requests.get(url, timeout=600)
    r.raise_for_status()
    return r.content


def download_image(
    image: ee.Image,
    region: ee.Geometry,
    out_path: Path,
    scale: int = RESOLUTION,
    crs: str = CRS,
) -> Path:
    """Tải một ee.Image về máy thành GeoTIFF đúng chuẩn khoa học.

    Việc đổi hệ toạ độ và độ phân giải diễn ra TRÊN MÁY GOOGLE — ta chỉ khai báo `crs`
    và `scale` mong muốn, Google xử lý xong mới gửi kết quả về.

    KHÔNG dùng geemap.ee_export_image: hàm đó tải qua endpoint 'thumbnails' (ảnh xem
    trước), làm sai lệch cả giá trị lẫn vị trí pixel. Đã kiểm chứng ở Ngày 2.

    Vùng lớn được tự động cắt thành nhiều mảnh rồi ghép lại, vì getDownloadURL giới
    hạn khoảng 32MB mỗi lần gọi.
    """
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # Neo lưới vào bội số của `scale` để mọi lớp feature dùng chung một lưới
    b = region.bounds().transform(crs, 1).coordinates().getInfo()[0]
    xs, ys = [p[0] for p in b], [p[1] for p in b]
    x0 = np.floor(min(xs) / scale) * scale
    y0 = np.floor(min(ys) / scale) * scale
    x1 = np.ceil(max(xs) / scale) * scale
    y1 = np.ceil(max(ys) / scale) * scale
    W, H = int((x1 - x0) / scale), int((y1 - y0) / scale)

    n_tile = max(1, int(np.ceil(W * H * 4 / (MAX_TILE_MB * 1e6))))
    rows = int(np.ceil(np.sqrt(n_tile)))
    cols = int(np.ceil(n_tile / rows))
    th, tw = int(np.ceil(H / rows)), int(np.ceil(W / cols))
    print(f"    lưới {W} x {H} px, chia {rows} x {cols} mảnh")

    parts, tmp_dir = [], out_path.parent / "_tiles"
    tmp_dir.mkdir(exist_ok=True)
    for r in range(rows):
        for c in range(cols):
            h = min(th, H - r * th)
            w = min(tw, W - c * tw)
            if h <= 0 or w <= 0:
                continue
            tx0 = x0 + c * tw * scale
            ty1 = y1 - r * th * scale
            data = _fetch_tile(image, crs, scale,
                               tx0, ty1 - h * scale, tx0 + w * scale, ty1)
            p = tmp_dir / f"t{r}_{c}.tif"
            p.write_bytes(data)
            parts.append(p)
            print(f"      mảnh {len(parts)}/{rows * cols}: {w}x{h} px, {len(data) / 1e6:.1f} MB")

    if len(parts) == 1:
        srcs = [rasterio.open(parts[0])]
        arr, transform = srcs[0].read(), srcs[0].transform
        profile = srcs[0].profile
    else:
        srcs = [rasterio.open(p) for p in parts]
        arr, transform = merge(srcs)
        profile = srcs[0].profile

    profile.update(height=arr.shape[1], width=arr.shape[2], count=arr.shape[0],
                   transform=transform, crs=crs, nodata=NODATA, compress="deflate")
    with rasterio.open(out_path, "w", **profile) as dst:
        dst.write(arr)

    for s in srcs:
        s.close()
    for p in parts:
        p.unlink()
    tmp_dir.rmdir()
    return out_path


def log_raster(path: Path) -> None:
    """In thông tin kiểm tra của một raster (quy ước mục 8 PROJECT_PLAN.md)."""
    import numpy as np

    with rasterio.open(path) as src:
        a = src.read(1, masked=True)
        b = src.bounds
        print(f"  [{path.name}]")
        print(f"    shape   : {src.height} x {src.width}  ({src.count} band)")
        print(f"    crs     : {src.crs}")
        print(f"    pixel   : {src.res[0]:.1f} x {src.res[1]:.1f} m")
        print(f"    bounds  : ({b.left:,.0f}, {b.bottom:,.0f}) -> ({b.right:,.0f}, {b.top:,.0f})")
        print(f"    dtype   : {src.dtypes[0]} | nodata = {src.nodata}")
        print(f"    nodata  : {int(a.mask.sum()):,} pixel ({a.mask.mean() * 100:.1f}%)")
        print(
            f"    giá trị : min={a.min():.2f} | trung vị={np.ma.median(a):.2f} | "
            f"max={a.max():.2f}"
        )


if __name__ == "__main__":
    # Smoke test cho Ngày 1: xác nhận GEE chạy được và đọc được DEM
    init_gee()
    dem = ee.ImageCollection(GEE_DEM).first()
    info = dem.getInfo()
    bands = [b["id"] for b in info["bands"]]
    print(f"DEM asset OK | id = {info.get('id')} | bands = {bands}")
