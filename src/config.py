"""Cấu hình tập trung: CRS, resolution, paths, GEE asset ids.
Mọi hằng số dùng chung trong project phải khai báo ở đây, không hardcode rải rác.
"""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# Google Cloud project gắn với tài khoản Earth Engine, đọc từ .env (không commit)
GEE_PROJECT = os.getenv("GEE_PROJECT")

# --- Spatial params (mục 4.1 PROJECT_PLAN.md) — KHÔNG tự đổi ---
CRS = "EPSG:32648"          # WGS84 / UTM zone 48N, đơn vị mét
RESOLUTION = 30              # mét, khớp DEM Copernicus GLO-30
BUFFER_KM = 2                # buffer quanh ranh giới hành chính, tránh lỗi biên flow accumulation
NODATA = -9999.0

RANDOM_SEED = 42

# --- Paths ---
ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
INTERIM_DIR = DATA_DIR / "interim"
FEATURES_DIR = INTERIM_DIR / "features"
PROCESSED_DIR = DATA_DIR / "processed"
OUTPUTS_DIR = ROOT_DIR / "outputs"
FIGURES_DIR = OUTPUTS_DIR / "figures"
MODELS_DIR = ROOT_DIR / "models"

# Ranh giới: vùng địa lý = TP.HCM CŨ (trước sáp nhập 2025), đơn vị hành chính = phường/xã MỚI.
# GADM (63 tỉnh, bản 2022) chỉ dùng làm lưới lọc để chọn phường thuộc thành phố cũ.
GADM_RAW_PATH = RAW_DIR / "gadm41_VNM_2.json"
OSM_CACHE_DIR = RAW_DIR / "osm_cache"                  # osmnx lưu kết quả tải, tránh gọi lại server
WARDS_PATH = RAW_DIR / "wards_hcmc.geojson"            # 102 phường/xã mới — cần cho Ngày 5
BOUNDARY_PATH = RAW_DIR / "boundary_hcmc.geojson"      # gộp 102 phường
BOUNDARY_BUFFER_PATH = INTERIM_DIR / "boundary_hcmc_buffer2km.geojson"
FLOOD_POINTS_PATH = RAW_DIR / "flood_points.csv"
FEATURE_STACK_PATH = PROCESSED_DIR / "feature_stack.tif"
FLOOD_RISK_PROB_PATH = PROCESSED_DIR / "flood_risk_prob.tif"
FLOOD_RISK_CLASS_PATH = PROCESSED_DIR / "flood_risk_class.tif"
LABELS_PATH = INTERIM_DIR / "labels.gpkg"
TRAINING_TABLE_PATH = INTERIM_DIR / "training_table.csv"
DASHBOARD_PATH = OUTPUTS_DIR / "dashboard.html"
RF_MODEL_PATH = MODELS_DIR / "rf_model.pkl"

# --- GEE asset ids (mục 4.2 PROJECT_PLAN.md) ---
# F1 dùng FABDEM chứ không phải Copernicus (quyết định Ngày 2, xem ghi chú mục 4.2).
# Copernicus GLO-30 là DSM: đo nóc nhà và ngọn cây, không phải mặt đất. FABDEM là chính
# bộ đó đã loại bỏ nhà cửa/cây cối. Vì F2 (slope) và F3 (TWI) đều tính từ F1, dùng DSM
# sẽ mô phỏng nước chảy trên mái nhà.
GEE_DEM = "projects/sat-io/open-datasets/FABDEM"
GEE_DEM_BAND = "b1"
# Bản DSM gốc, giữ lại để đối chiếu khi cần (hiệu số hai bản ≈ chiều cao nhà cửa/cây)
GEE_DEM_DSM = "COPERNICUS/DEM/GLO30_2024_1"
GEE_DEM_DSM_BAND = "DEM"
GEE_WORLDCOVER = "ESA/WorldCover/v200"
GEE_GHSL_BUILT = "JRC/GHSL/P2023A/GHS_BUILT_S"
GEE_CHIRPS = "UCSB-CHG/CHIRPS/DAILY"
GEE_S1_GRD = "COPERNICUS/S1_GRD"

WORLDCOVER_BUILTUP_CLASS = 50
WORLDCOVER_WATER_CLASS = 80

# --- Feature layer names (dùng đúng tên này khi đặt tên file raster) ---
FEATURE_NAMES = [
    "elevation",
    "slope",
    "twi",
    "impervious_pct",
    "dist_to_water",
    "built_volume",
    "rain_max",
    "drainage_density",
]

# Bán kính buffer mặc định cho impervious_pct / drainage_density (mét)
# — thử nhiều giá trị, chọn theo CV score (câu hỏi mở #2, mục 11)
BUFFER_RADIUS_M = 500

PLACE_NAME = "Ho Chi Minh City, Vietnam"

# Khoảng thời gian mưa dùng cho F7 rain_max (percentile 95, mùa mưa)
RAIN_YEARS = (2019, 2024)
RAIN_SEASON_MONTHS = (5, 11)
