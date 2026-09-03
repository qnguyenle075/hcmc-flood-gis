# Bản đồ nguy cơ ngập TP.HCM + Định tuyến tránh ngập

Ước lượng nguy cơ ngập (flood **susceptibility**) cho toàn TP.HCM bằng machine learning
trên dữ liệu không gian, rồi dùng kết quả để định tuyến giao thông tránh vùng ngập.

> Đây là bài toán **susceptibility** (nguy cơ tĩnh dựa trên điều kiện địa hình/hạ tầng),
> KHÔNG phải **forecasting** (dự báo ngập theo thời gian thực).

Kế hoạch chi tiết và mọi quyết định kỹ thuật: xem [PROJECT_PLAN.md](PROJECT_PLAN.md).

## Cài đặt

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt

earthengine authenticate         # chạy 1 lần
```

Ngoài ra cần cài [QGIS](https://qgis.org) để xem/kiểm tra raster bằng mắt.

## Cấu trúc

| Thư mục | Nội dung |
|---|---|
| `data/raw/` | Dữ liệu gốc: ranh giới, điểm ngập nhập tay, cache OSM |
| `data/interim/` | Từng lớp raster riêng lẻ, điểm nhãn đã gán feature |
| `data/processed/` | `feature_stack.tif`, bản đồ nguy cơ đầu ra |
| `notebooks/` | Notebook theo từng bước (01 → 07) |
| `src/` | Code tái sử dụng; `config.py` chứa mọi hằng số |
| `outputs/` | Hình cho report, dashboard HTML, report.md |
