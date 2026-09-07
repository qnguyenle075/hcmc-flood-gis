# PROJECT: Bản đồ nguy cơ ngập TP.HCM + Định tuyến tránh ngập

> **File này là context chính cho AI assistant (Claude Code).**
> Đọc toàn bộ file này trước khi viết code. Mọi quyết định kỹ thuật đã được chốt ở đây — nếu cần đi chệch, hỏi lại người dùng trước.

---

## 0. TL;DR cho AI assistant

Đây là project GeoAI cá nhân, thời gian **2 tuần**, người làm **mới hoàn toàn với GIS** nhưng có nền tảng lập trình/ML.

**Mục tiêu:** Dự đoán nguy cơ ngập cho từng vị trí ở TP.HCM bằng machine learning trên dữ liệu không gian (địa hình, lớp phủ, thoát nước, mưa), rồi dùng kết quả đó để định tuyến giao thông tránh vùng ngập.

**Nguyên tắc làm việc:**
- Ưu tiên **chạy được** hơn là tối ưu. Không over-engineer.
- Mỗi bước phải có output kiểm tra được bằng mắt (vẽ bản đồ ra xem).
- Giải thích ngắn gọn các khái niệm GIS khi dùng lần đầu (người dùng đang học).
- Không tự ý đổi CRS, resolution, hay nguồn dữ liệu đã chốt ở mục 4.
- Khi gặp lỗi GEE/raster, in ra shape + CRS + bounds của object trước khi debug.

---

## 1. Bối cảnh & vấn đề thực tế

TP.HCM ngập nặng mỗi mùa mưa (tháng 5–11). Nguyên nhân được cho là kết hợp của:
- Địa hình thấp và phẳng (phần lớn dưới 2m so với mực nước biển)
- Bê tông hóa nhanh → mất bề mặt thấm nước tự nhiên
- Hệ thống thoát nước quá tải, thiết kế cho quy mô dân số cũ
- Triều cường sông Sài Gòn, đặc biệt khi trùng mưa lớn
- San lấp kênh rạch, ao hồ điều tiết

**Prior art:** Thành phố đã có app **UDI Maps** (Công ty TNHH MTV Thoát nước đô thị TP.HCM) cung cấp cảnh báo ngập, triều cường theo thời gian thực, dựa trên mạng cảm biến + camera + mô hình thủy lực + CSDL GIS hệ thống thoát nước.

**Khoảng trống project này lấp:**
- UDI Maps là hệ thống **đóng**, không có API công khai, dữ liệu lịch sử không mở
- Họ dự báo **thời gian thực** cho các điểm đã lắp cảm biến; project này ước lượng **nguy cơ tĩnh (susceptibility)** cho **toàn bộ thành phố**, kể cả nơi chưa có cảm biến
- Đóng góp thêm: bộ dữ liệu điểm ngập có cấu trúc + phân tích định lượng yếu tố nào gây ngập mạnh nhất

**Phân biệt rõ (quan trọng, tránh overclaim trong report):**
- ❌ Project này KHÔNG dự báo "chiều nay đường X có ngập không" (cần mô hình thủy lực + dữ liệu real-time)
- ✅ Project này trả lời "vị trí nào có **điều kiện tự nhiên/hạ tầng** khiến dễ ngập" → flood **susceptibility**, không phải flood **forecasting**

---

## 2. Phạm vi (Scope)

### 2.1 In-scope (BẮT BUỘC làm)
| # | Deliverable | Mô tả |
|---|---|---|
| D1 | Feature stack raster | 8 lớp dữ liệu không gian, 30m, cùng lưới, cùng CRS |
| D2 | Bộ nhãn điểm ngập | ~300–500 điểm ngập + số lượng tương đương điểm không ngập |
| D3 | Model ML | Random Forest + XGBoost, có spatial cross-validation |
| D4 | Bản đồ nguy cơ ngập | GeoTIFF xác suất + phân 5 mức, phủ toàn TP.HCM |
| D5 | Phân tích feature importance | Yếu tố nào ảnh hưởng mạnh nhất, có SHAP nếu kịp |
| D6 | Kiểm chứng Sentinel-1 | Đối chiếu với vùng nước phát hiện từ ảnh SAR (ngoại thành) |
| D7 | Định tuyến tránh ngập | Routing trên mạng đường OSM, weight theo risk |
| D8 | Dashboard HTML | Folium, nhiều layer, mở offline được |
| D9 | Report + README | Ghi rõ phương pháp, kết quả, và **giới hạn** |

### 2.2 Out-of-scope (KHÔNG làm, đã cân nhắc và loại)
- ❌ **NLP / phân tích văn bản** — người dùng đã yêu cầu bỏ hoàn toàn
- ❌ **Change detection đa thời gian** (phân tích bê tông hóa 2000→2026) — quá tốn thời gian, thay bằng snapshot WorldCover 1 năm
- ❌ **Mô hình thủy lực** (SWMM, HEC-RAS) — cần dữ liệu cống ngầm không công khai
- ❌ **Dự báo real-time** — cần API cảm biến không có
- ❌ **Deploy production** (Docker, cloud, CI/CD) — export HTML tĩnh là đủ
- ❌ **Deep learning** (CNN/U-Net trên ảnh) — tree-based model đủ tốt cho tabular spatial features, và giải thích được

---

## 3. Tech stack

### 3.1 Nền tảng chính
| Công cụ | Vai trò | Lý do chọn |
|---|---|---|
| **Google Earth Engine (GEE)** | Lấy & xử lý ảnh vệ tinh, DEM, lớp phủ | Xử lý trên cloud, không cần tải hàng GB về máy. Miễn phí cho nghiên cứu/phi thương mại. **Cách vào GIS nhanh nhất cho người mới.** |
| **Python 3.10+** | Ngôn ngữ chính | |
| **QGIS** (desktop, miễn phí) | Xem/kiểm tra raster & vector bằng mắt | Debug dữ liệu không gian nhanh hơn code |

### 3.2 Thư viện Python
```
# GIS & Remote sensing
earthengine-api      # client GEE
geemap               # cầu nối GEE <-> Python/folium, cực tiện
rasterio             # đọc/ghi GeoTIFF
rioxarray            # raster dạng xarray, tiện cho stack nhiều band
geopandas            # dữ liệu vector (điểm, đường, polygon)
shapely              # hình học
pyproj               # chuyển đổi CRS
osmnx                # tải mạng lưới đường OSM + routing
richdem              # tính flow accumulation cho TWI (hoặc pysheds)

# ML
scikit-learn         # RandomForest, metrics, pipeline
xgboost              # gradient boosting
shap                 # giải thích model (optional, nếu kịp)
imbalanced-learn     # nếu nhãn mất cân bằng

# Data & viz
pandas, numpy
folium               # bản đồ tương tác HTML
matplotlib, seaborn  # biểu đồ tĩnh cho report
```

### 3.3 Cài đặt
```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install earthengine-api geemap rasterio rioxarray geopandas osmnx \
            scikit-learn xgboost shap pandas numpy folium matplotlib seaborn richdem

# Xác thực GEE (chạy 1 lần)
earthengine authenticate
```

---

## 4. Dữ liệu — CHỐT, không tự đổi

### 4.1 Thông số không gian chuẩn (mọi raster phải tuân theo)
| Thông số | Giá trị | Ghi chú |
|---|---|---|
| CRS | **EPSG:32648** (WGS84 / UTM zone 48N) | Đơn vị mét, đúng cho TP.HCM. KHÔNG dùng EPSG:4326 cho tính toán khoảng cách/độ dốc |
| Resolution | **30m** | Khớp DEM Copernicus, đủ chi tiết cho quy mô thành phố |
| Extent | Ranh giới hành chính TP.HCM + buffer 2km | Buffer để tránh lỗi biên khi tính flow accumulation |
| NoData | `-9999` (float32) | |

### 4.2 Nguồn dữ liệu

**A. Ranh giới hành chính**
- GADM level 2 (quận/huyện): https://gadm.org/download_country.html → chọn Vietnam
- Hoặc `osmnx.geocode_to_gdf("Ho Chi Minh City, Vietnam")`
- ⚠️ TP.HCM đã sáp nhập đơn vị hành chính gần đây — kiểm tra ranh giới có khớp thực tế không, và ghi rõ trong report dùng ranh giới thời điểm nào.

**B. 8 lớp feature (D1)**

| # | Feature | Nguồn | GEE Asset ID | Cách tính |
|---|---|---|---|---|
| F1 | `elevation` | FABDEM (Copernicus GLO-30 đã bỏ nhà/cây) | `projects/sat-io/open-datasets/FABDEM` (band `b1`) | Lấy trực tiếp |
| F2 | `slope` | Từ F1 | — | `ee.Terrain.slope(dem)` |
| F3 | `twi` | Từ F1 | — | Topographic Wetness Index, xem 4.3 |
| F4 | `impervious_pct` | ESA WorldCover 2021 | `ESA/WorldCover/v200` | % pixel class 50 (Built-up) trong bán kính 500m |
| F5 | `dist_to_water` | OSM waterway + WorldCover class 80 | — | Khoảng cách Euclid tới thủy hệ gần nhất (mét) |
| F6 | `built_volume` | GHSL Built-up | `JRC/GHSL/P2023A/GHS_BUILT_S` | Mật độ xây dựng |
| F7 | `rain_max` | CHIRPS Daily | `UCSB-CHG/CHIRPS/DAILY` | Percentile 95 lượng mưa ngày, mùa mưa 2019–2024 |
| F8 | `drainage_density` | OSM `waterway=drain/ditch/canal` | — | Tổng chiều dài kênh/cống hở trong ô 500m |

> **Ghi chú thay đổi (Ngày 1):** asset gốc `COPERNICUS/DEM/GLO30` đã bị GEE đánh dấu *deprecated*,
> thay bằng `COPERNICUS/DEM/GLO30_2024_1` (bản xử lý lại năm 2024). Vẫn là Copernicus GLO-30, độ phân
> giải 30m, cùng bộ band (`DEM`, `EDM`, `FLM`, `HEM`, `WBM`). Đổi để tránh rủi ro Google gỡ asset cũ
> giữa chừng project. **Nêu lại trong report phần nguồn dữ liệu.**
>
> **Ghi chú thay đổi (Ngày 2) — F1 đổi sang FABDEM:** Copernicus GLO-30 là **DSM**, đo bề mặt trên
> cùng (nóc nhà, ngọn cây) chứ không phải mặt đất. Đo thử tại TP.HCM: Nhà thờ Đức Bà 27,25m,
> Thảo Điền 9,58m, đồng ruộng Bình Chánh 5,86m — đều cao hơn thực tế. FABDEM là chính bộ dữ liệu đó
> đã loại bỏ nhà cửa và cây cối, cho lần lượt 16,41m / 4,51m / 1,36m. Vì F2 (slope) và F3 (TWI) đều
> tính từ F1, dùng DSM sẽ mô phỏng dòng chảy trên mái nhà thay vì trên mặt đường — hỏng 3/8 feature,
> trong đó TWI là feature quan trọng nhất (mục 4.3). Đây chính là phương án dự phòng đã nêu ở rủi ro R3.
>
> Lưu ý khi viết report: FABDEM do cộng đồng host trên GEE (không thuộc kho chính thức của Google),
> giấy phép CC BY-NC-SA 4.0 — dùng được cho nghiên cứu phi thương mại. Nó là **sản phẩm suy diễn**
> bằng học máy từ Copernicus, không phải số liệu đo mặt đất trực tiếp. **Nêu rõ trong phần giới hạn.**
>
> **Giới hạn đã đo được (Ngày 2) — FABDEM còn sót tán rừng ở Cần Giờ:** thống kê theo xã cho thấy
> Thạnh An, Bình Khánh, Cần Giờ, An Thới Đông có trung vị 3,0–5,3m (chấp nhận được) nhưng **p95 đạt
> 10,9–12,0m** — đúng bằng chiều cao tán đước. Thuật toán loại bỏ rừng của FABDEM không xử lý tốt
> rừng ngập mặn dày trên nền nước. Ảnh hưởng tới project ở mức thấp vì Cần Giờ không có điểm nhãn
> huấn luyện, nhưng **phải nêu khi diễn giải bản đồ nguy cơ ở Cần Giờ và khi kiểm chứng SAR (D6)**.
>
> Đối chiếu kiểm tra (Ngày 2), thống kê độ cao theo phường/xã khớp thực địa: cao nhất là Linh Xuân
> 21,6m (Thủ Đức), An Nhơn Tây 15,7m và Nhuận Đức 14,3m (Củ Chi), Gò Vấp 11,6m; thấp nhất là
> Phú Thuận 1,6m, An Phú Đông 1,7m, Tân Nhựt 1,8m, Bình Chánh 2,0m.

**Backup nếu GEE không dùng được:**
- DEM: Copernicus Browser (dataspace.copernicus.eu) hoặc OpenTopography
- WorldCover: esa-worldcover.org tải tile trực tiếp
- Mưa: Open-Meteo Historical API (miễn phí, không cần key)

**C. Nhãn — điểm ngập (D2)**

Đây là **khâu quyết định chất lượng project**. Nguồn:
1. **Danh sách tuyến đường ngập do Sở Xây dựng / Trung tâm Quản lý hạ tầng kỹ thuật TP.HCM công bố hàng năm** — thường đăng lại trên báo (VnExpress, Tuổi Trẻ, Thanh Niên, SGGP) đầu mỗi mùa mưa. Tìm với từ khóa: `"danh sách tuyến đường ngập TP.HCM 2024"`, `"điểm ngập TP.HCM mùa mưa"`.
2. Ghi lại thủ công vào `data/raw/flood_points.csv` với schema ở 4.4.
3. Bổ sung từ quan sát cá nhân nếu có (ghi rõ nguồn `personal`).

⚠️ **Không dùng NLP để trích xuất tự động** — đã loại khỏi scope. Nhập tay ~30–60 tuyến đường là đủ và nhanh hơn.

**D. Kiểm chứng — Sentinel-1 (D6)**
- GEE Asset: `COPERNICUS/S1_GRD`
- Filter: `instrumentMode = 'IW'`, polarisation `VV`, orbit `DESCENDING`
- Chọn 1 cặp ảnh: trước mưa lớn & sau mưa lớn (tra ngày mưa lớn qua CHIRPS hoặc tin tức)

**E. Mạng lưới đường (D7)**
```python
import osmnx as ox
G = ox.graph_from_place("Ho Chi Minh City, Vietnam", network_type="drive")
```

### 4.3 Công thức TWI (Topographic Wetness Index)

TWI chỉ ra vùng nào có xu hướng tích nước dựa trên địa hình. **Đây thường là feature quan trọng nhất trong flood susceptibility.**

```
TWI = ln( a / tan(β) )
```
- `a` = flow accumulation area trên đơn vị chiều rộng đường đồng mức
- `β` = độ dốc (radian)

Lưu ý khi implement:
- Phải **fill sink** (lấp hố trũng giả do lỗi DEM) trước khi tính flow accumulation → dùng `richdem.FillDepressions` hoặc `pysheds`
- `tan(β)` = 0 ở vùng phẳng → thay bằng giá trị nhỏ (VD 0.001) để tránh chia cho 0. **TP.HCM rất phẳng nên lỗi này chắc chắn xảy ra.**
- TWI cao = dễ tích nước

### 4.4 Schema dữ liệu nhãn

`data/raw/flood_points.csv`:
```csv
id,street_name,district,lat,lon,severity,source,year,note
1,Nguyễn Hữu Cảnh,Bình Thạnh,10.7912,106.7185,3,sxd_2024,2024,ngập thường xuyên
2,Quốc Hương,Thủ Đức,10.8032,106.7345,2,sxd_2024,2024,
```
- `severity`: 1=nhẹ, 2=trung bình, 3=nặng (chỉ để tham khảo/phân tích, model chính dùng nhị phân)
- `source`: `sxd_2024` | `news` | `personal`

---

## 5. Cấu trúc thư mục

```
hcmc-flood-gis/
├── README.md
├── PROJECT_PLAN.md              # file này
├── requirements.txt
├── .env                          # GEE project id (không commit)
├── data/
│   ├── raw/
│   │   ├── flood_points.csv      # nhãn nhập tay
│   │   ├── boundary_hcmc.geojson
│   │   └── osm_cache/
│   ├── interim/
│   │   ├── features/             # từng lớp raster riêng lẻ
│   │   └── labels_sampled.gpkg   # điểm nhãn + đã gán feature
│   └── processed/
│       ├── feature_stack.tif     # 8 band, aligned
│       ├── flood_risk_prob.tif   # output model
│       └── flood_risk_class.tif  # phân 5 mức
├── notebooks/
│   ├── 01_explore_boundary.ipynb
│   ├── 02_build_features.ipynb
│   ├── 03_labels_eda.ipynb
│   ├── 04_train_model.ipynb
│   ├── 05_predict_map.ipynb
│   ├── 06_sar_validation.ipynb
│   └── 07_routing.ipynb
├── src/
│   ├── config.py                 # CRS, resolution, paths, GEE ids
│   ├── gee_utils.py              # auth, export, download helpers
│   ├── features.py               # build từng feature layer
│   ├── terrain.py                # slope, TWI, fill sink
│   ├── labels.py                 # sample điểm positive/negative
│   ├── model.py                  # train, spatial CV, evaluate
│   ├── predict.py                # apply model lên raster
│   ├── routing.py                # osmnx + flood-aware weight
│   └── viz.py                    # folium layers
├── outputs/
│   ├── figures/
│   ├── dashboard.html
│   └── report.md
└── models/
    └── rf_model.pkl
```

---

## 6. Kế hoạch 14 ngày

> Mỗi ngày ~3–4h. Ngày 14 là buffer, đừng lấp đầy.

### **Ngày 1 — Setup (LÀM NGAY, có blocker)**
- [ ] **Đăng ký Google Earth Engine ngay hôm nay** — duyệt có thể mất 1–2 ngày. Đây là blocker duy nhất không thể rút ngắn. Vào https://code.earthengine.google.com/ và đăng ký project (non-commercial).
- [ ] Tạo repo, venv, cài thư viện
- [ ] Cài QGIS
- [ ] `earthengine authenticate` chạy được
- **Output:** in ra được `ee.Image('COPERNICUS/DEM/GLO30').first().getInfo()`

### **Ngày 2 — Ranh giới & DEM**
- [ ] Tải ranh giới TP.HCM, lưu GeoJSON, buffer 2km
- [ ] Lấy DEM, clip theo ranh giới, reproject sang EPSG:32648, resample 30m
- [ ] Export GeoTIFF về local, mở trong QGIS xem
- [ ] Viết `src/config.py` với mọi hằng số
- **Output:** `data/interim/features/elevation.tif` xem được trong QGIS
- **Sanity check:** độ cao nội thành phải rất thấp (phần lớn 0–10m); nếu ra hàng trăm mét là sai CRS hoặc sai vùng clip

### **Ngày 3 — Terrain features (slope, TWI)**
- [ ] Slope từ DEM
- [ ] Fill sink → flow accumulation → TWI
- [ ] Xử lý chia-cho-0 ở vùng phẳng
- **Output:** `slope.tif`, `twi.tif`
- **Sanity check:** TWI cao phải nằm ở vùng trũng, gần kênh rạch. Mở QGIS chồng lên ảnh vệ tinh nền để xem có hợp lý không.

### **Ngày 4 — Các feature còn lại**
- [ ] F4 impervious_pct, F6 built_volume, F7 rain_max từ GEE
- [ ] F5 dist_to_water, F8 drainage_density từ OSM
- [ ] **Align tất cả về cùng lưới** — dùng `elevation.tif` làm reference grid, `rasterio.warp.reproject` cho từng lớp
- [ ] Stack thành `feature_stack.tif` (8 band)
- **Output:** `data/processed/feature_stack.tif`
- **Sanity check bắt buộc:** mọi band phải có cùng `shape`, `transform`, `crs`. Assert trong code:
```python
assert all(b.shape == ref.shape for b in bands)
assert all(b.transform == ref.transform for b in bands)
```

### **Ngày 5 — Tạo nhãn** ⚠️ *bước dễ hỏng nhất*
- [ ] Nhập tay danh sách tuyến đường ngập vào CSV
- [ ] Với mỗi tuyến: lấy geometry đường từ OSM, sample điểm dọc tuyến mỗi 50m → **positive samples**
- [ ] **Negative samples — làm ĐÚNG cách:**
  - ❌ KHÔNG sample ngẫu nhiên toàn thành phố → sẽ toàn rơi vào ngoại thành, model chỉ học "nội thành = ngập", vô dụng
  - ✅ Sample trên **các tuyến đường khác trong CÙNG quận** không nằm trong danh sách ngập
  - ✅ Số lượng negative ≈ số lượng positive (cân bằng)
  - ✅ Loại bỏ negative nằm trong bán kính 100m của bất kỳ positive nào
- **Output:** `data/interim/labels.gpkg` với cột `label` (0/1)
- **Sanity check:** vẽ cả 2 nhóm điểm lên folium, xem có phân bố đan xen trong cùng khu vực không

### **Ngày 6 — Trích xuất feature tại điểm nhãn**
- [ ] `rasterio.sample` lấy 8 giá trị feature tại mỗi điểm
- [ ] Xử lý NoData, điểm rơi ngoài raster
- **Output:** `data/interim/training_table.csv` (~600–1000 dòng × 8 cột + label)

### **Ngày 7 — EDA**
- [ ] Phân bố từng feature theo nhóm label (boxplot)
- [ ] Ma trận tương quan — elevation & TWI thường tương quan mạnh, cân nhắc bỏ 1
- [ ] **Sanity check quan trọng:** điểm ngập có `elevation` thấp hơn và `twi` cao hơn điểm không ngập không? Nếu KHÔNG có khác biệt gì → dừng lại, kiểm tra lại pipeline trước khi train. Đừng train mù.
- **Output:** `outputs/figures/eda_*.png`

### **Ngày 8 — Train model**
- [ ] Random Forest baseline
- [ ] **BẮT BUỘC dùng spatial cross-validation:**
```python
# Chia theo lưới 2km x 2km, mỗi fold = 1 nhóm ô
# KHÔNG dùng train_test_split ngẫu nhiên
from sklearn.model_selection import GroupKFold
df['grid_id'] = (df.x // 2000).astype(int) * 10000 + (df.y // 2000).astype(int)
cv = GroupKFold(n_splits=5)
scores = cross_val_score(model, X, y, groups=df['grid_id'], cv=cv, scoring='roc_auc')
```
> **Lý do:** điểm gần nhau có giá trị feature gần giống nhau (spatial autocorrelation). Random split khiến điểm train và test nằm cạnh nhau → accuracy ảo 95%+ nhưng model vô dụng ngoài thực tế. Đây là lỗi kinh điển trong ML không gian.
- [ ] Báo cáo **AUC-ROC**, precision, recall — KHÔNG chỉ accuracy

### **Ngày 9 — XGBoost + tuning**
- [ ] XGBoost, so sánh với RF cùng CV scheme
- [ ] Tuning nhẹ (grid nhỏ, đừng sa đà)
- [ ] Feature importance + SHAP nếu kịp
- [ ] Lưu model tốt nhất
- **Output:** `models/rf_model.pkl`, `outputs/figures/feature_importance.png`

### **Ngày 10 — Predict toàn bản đồ**
- [ ] Đọc `feature_stack.tif` → reshape thành (n_pixels, 8)
- [ ] Predict theo chunk nếu hết RAM (`rasterio.windows`)
- [ ] Ghi ra `flood_risk_prob.tif`
- [ ] Phân 5 mức bằng quantile → `flood_risk_class.tif`
- **Sanity check:** vùng nguy cơ cao có trùng với các điểm ngập nổi tiếng (Nguyễn Hữu Cảnh, An Dương Vương, Thảo Điền...) không?

### **Ngày 11 — Kiểm chứng Sentinel-1**
- [ ] Tìm 1 ngày mưa cực lớn có ảnh S1 trong vòng 24h sau
- [ ] Lọc speckle, thresholding VV → mask nước
- [ ] So sánh mask nước với bản đồ nguy cơ
- ⚠️ **Giới hạn phải nêu rõ:** SAR khó phát hiện ngập trong khu đô thị dày đặc do tán xạ phức tạp từ nhà cửa. Chỉ kiểm chứng đáng tin ở **vùng trống/ngoại thành** (Bình Chánh, Nhà Bè, Củ Chi, Cần Giờ). Nêu thẳng trong report, không giấu.

### **Ngày 12 — Routing tránh ngập**
```python
G = ox.graph_from_place("Ho Chi Minh City, Vietnam", network_type="drive")
# Gán risk cho mỗi edge: sample raster tại midpoint của edge
# weight = length * (1 + PENALTY * risk)   với PENALTY ~ 3-5
route_short = ox.shortest_path(G, orig, dest, weight="length")
route_safe  = ox.shortest_path(G, orig, dest, weight="flood_weight")
```
- [ ] So sánh 2 tuyến: chênh bao nhiêu km, giảm bao nhiêu % risk
- [ ] Demo 3–5 cặp điểm quen thuộc (VD: Q1 → Thủ Đức)

### **Ngày 13 — Dashboard + report**
- [ ] Folium: layer nguy cơ (raster overlay) + điểm ngập thực tế + demo routing + layer control
- [ ] Export `outputs/dashboard.html` (mở offline được, không cần server)
- [ ] Viết `report.md`: phương pháp, kết quả, feature importance, **giới hạn**

### **Ngày 14 — Buffer + README**
- [ ] README có ảnh screenshot, hướng dẫn chạy lại
- [ ] Dọn code, xóa cell rác trong notebook
- [ ] Dự phòng cho việc trễ tiến độ

---

## 7. Rủi ro & phương án dự phòng

| # | Rủi ro | Xác suất | Phương án B |
|---|---|---|---|
| R1 | **GEE duyệt tài khoản chậm/từ chối** | Trung bình | Tải dữ liệu trực tiếp: Copernicus Browser (DEM), esa-worldcover.org (lớp phủ), Open-Meteo API (mưa). Chậm hơn nhưng làm được. **Vì vậy phải đăng ký NGAY ngày 1.** |
| R2 | **Không tìm đủ điểm ngập (<100)** | Trung bình | Đổi đơn vị phân tích từ pixel sang **phường/xã**: đếm số điểm ngập mỗi phường → bài toán hồi quy thay vì phân loại. Ít nhãn hơn vẫn chạy được. |
| R3 | **TP.HCM quá phẳng, DEM 30m không đủ phân giải** | **Cao** | Nếu `elevation` và `slope` có feature importance ~0: đây KHÔNG phải thất bại mà là **phát hiện** — kết luận "ngập TP.HCM do hạ tầng thoát nước và bê tông hóa nhiều hơn do địa hình". Đẩy trọng tâm phân tích sang F4, F8. Cân nhắc thêm FABDEM (đã loại bỏ nhà cửa/cây khỏi DEM). |
| R4 | **Không có ảnh S1 phù hợp trong mùa mưa** | Thấp | Bỏ D6, thay bằng validation thủ công: đối chiếu top-20 vùng nguy cơ cao với tin tức ngập gần nhất |
| R5 | **Model AUC thấp (<0.7)** | Trung bình | Chấp nhận và báo cáo trung thực + phân tích tại sao. Một report giải thích rõ vì sao model kém có giá trị hơn một model overfit khoe AUC 0.98. |
| R6 | Hết RAM khi predict toàn raster | Trung bình | Predict theo window/chunk với `rasterio.windows` |
| R7 | Trễ tiến độ | Cao | Thứ tự cắt bỏ: D6 (SAR) → D7 (routing) → SHAP. **Không bao giờ cắt D1–D5.** |

---

## 8. Quy ước code

- **Config tập trung** trong `src/config.py` — mọi path, CRS, resolution, GEE asset id. Không hardcode rải rác.
- **Notebook để khám phá, `src/` để tái sử dụng.** Logic ổn định thì chuyển vào `src/`.
- **Mỗi hàm xử lý raster phải log:** `shape`, `crs`, `bounds`, `nodata count`.
- **Không commit dữ liệu lớn.** `.gitignore`: `data/`, `models/*.pkl`, `.env`
- **Random seed = 42** ở mọi chỗ có tính ngẫu nhiên.
- Đặt tên file raster theo tên feature trong bảng 4.2 (`elevation.tif`, `twi.tif`...), không đặt `data1.tif`.

---

## 9. Định nghĩa "hoàn thành" (Definition of Done)

Project được coi là thành công nếu đạt đủ:

- [ ] `feature_stack.tif` có đủ 8 band, cùng lưới, mở được trong QGIS
- [ ] ≥ 200 điểm nhãn mỗi lớp, negative sampling đúng cách (cùng quận, không trùng vị trí positive)
- [ ] Model được đánh giá bằng **spatial CV**, báo cáo AUC-ROC
- [ ] Bản đồ nguy ngập phủ toàn TP.HCM, có kiểm tra mắt thường tại các điểm ngập nổi tiếng
- [ ] Có biểu đồ feature importance kèm diễn giải bằng lời
- [ ] Dashboard HTML mở được offline
- [ ] Report nêu rõ **ít nhất 4 giới hạn** của phương pháp

**Tiêu chí chất lượng quan trọng nhất:** report trung thực về giới hạn. Susceptibility ≠ forecasting; nhãn từ danh sách hành chính có thiên lệch (chỉ ghi nhận tuyến đường lớn, bỏ sót hẻm nhỏ); DEM 30m thô so với quy mô đô thị; không tính được hệ thống cống ngầm vì dữ liệu không công khai.

---

## 10. Thuật ngữ GIS cần biết

| Thuật ngữ | Nghĩa |
|---|---|
| **Raster** | Dữ liệu dạng lưới pixel, mỗi pixel một giá trị (như ảnh). VD: DEM, ảnh vệ tinh |
| **Vector** | Dữ liệu dạng hình học: điểm, đường, đa giác. VD: đường phố, ranh giới quận |
| **CRS** | Hệ tọa độ quy chiếu. EPSG:4326 = kinh/vĩ độ (đơn vị độ). EPSG:32648 = UTM 48N (đơn vị mét) |
| **DEM** | Digital Elevation Model — bản đồ độ cao địa hình |
| **Resample** | Đổi độ phân giải pixel |
| **Reproject** | Đổi hệ tọa độ |
| **Clip** | Cắt dữ liệu theo một ranh giới |
| **Flow accumulation** | Số pixel chảy dồn về một pixel — chỉ ra nơi nước tập trung |
| **Fill sink** | Lấp các hố trũng giả trong DEM do lỗi đo, cần làm trước khi tính dòng chảy |
| **TWI** | Topographic Wetness Index — chỉ số ẩm địa hình, cao = dễ tích nước |
| **Speckle** | Nhiễu hạt đặc trưng của ảnh radar SAR, cần lọc trước khi phân tích |
| **Spatial autocorrelation** | Hiện tượng điểm gần nhau có giá trị giống nhau → lý do phải dùng spatial CV |
| **Susceptibility** | Mức độ dễ bị tổn thương/xảy ra, dựa trên điều kiện tĩnh — khác với dự báo theo thời gian |

---

## 11. Câu hỏi mở cần quyết định khi làm

Ghi lại quyết định vào `outputs/report.md` khi chốt:

1. Có bỏ `elevation` nếu tương quan quá mạnh với `twi` không?
2. Buffer bán kính bao nhiêu cho `impervious_pct` — 300m, 500m hay 1000m? (thử vài giá trị, chọn theo CV score)
3. Kích thước ô lưới cho spatial CV — 1km, 2km hay 5km?
4. `PENALTY` cho routing — bao nhiêu thì tuyến đường đổi có ý nghĩa mà không vòng quá xa?
5. Có thêm feature "khoảng cách tới trạm bơm/dự án chống ngập" không? (dữ liệu khó, chỉ làm nếu dư thời gian)
