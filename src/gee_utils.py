"""Helper cho Google Earth Engine: xác thực, khởi tạo, export."""
import ee

from config import GEE_DEM, GEE_PROJECT


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


if __name__ == "__main__":
    # Smoke test cho Ngày 1: xác nhận GEE chạy được và đọc được DEM
    init_gee()
    dem = ee.ImageCollection(GEE_DEM).first()
    info = dem.getInfo()
    bands = [b["id"] for b in info["bands"]]
    print(f"DEM asset OK | id = {info.get('id')} | bands = {bands}")
