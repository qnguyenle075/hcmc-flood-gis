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

BOUNDARY_PATH = RAW_DIR / "boundary_hcmc.geojson"
FLOOD_POINTS_PATH = RAW_DIR / "flood_points.csv"
FEATURE_STACK_PATH = PROCESSED_DIR / "feature_stack.tif"
FLOOD_RISK_PROB_PATH = PROCESSED_DIR / "flood_risk_prob.tif"
FLOOD_RISK_CLASS_PATH = PROCESSED_DIR / "flood_risk_class.tif"
LABELS_PATH = INTERIM_DIR / "labels.gpkg"
TRAINING_TABLE_PATH = INTERIM_DIR / "training_table.csv"
DASHBOARD_PATH = OUTPUTS_DIR / "dashboard.html"
RF_MODEL_PATH = MODELS_DIR / "rf_model.pkl"

# --- GEE asset ids (mục 4.2 PROJECT_PLAN.md) ---
# Bản GLO30 gốc trong plan đã bị GEE đánh dấu deprecated -> dùng bản xử lý lại 2024.
# Cùng nguồn Copernicus GLO-30, cùng 30m, cùng band 'DEM'. Xem ghi chú mục 4.2 PROJECT_PLAN.md.
GEE_DEM = "COPERNICUS/DEM/GLO30_2024_1"
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
