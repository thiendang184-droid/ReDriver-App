import streamlit as st
import folium
import polyline
from streamlit_folium import st_folium
import base64 

# 🔴 ĐÃ CẬP NHẬT: Gọi thêm MAPBOX_TOKEN để hiển thị bản đồ chuẩn Mapbox
from config import MAPBOX_TOKEN
from fuzzy_taxi import geocode_address, get_route_info, get_weather, is_peak_hour, calculate_price

# --- CẤU HÌNH TRANG ---
st.set_page_config(page_title="ReDriver", page_icon="🦊", layout="wide")

# ==========================================
# HÀM SET ẢNH NỀN TỪ MÁY TÍNH
# ==========================================
def set_background(image_file):
    try:
        with open(image_file, "rb") as f:
            encoded_string = base64.b64encode(f.read()).decode()
        st.markdown(
            f"""
            <style>
            [data-testid="stAppViewContainer"] {{
                background-image: url("data:image/png;base64,{encoded_string}");
                background-size: cover;
                background-position: center;
                background-repeat: no-repeat;
                background-attachment: fixed;
            }}
            </style>
            """,
            unsafe_allow_html=True
        )
    except FileNotFoundError:
        st.warning("⚠️ Không tìm thấy file ảnh nền! Hãy kiểm tra lại đường dẫn.")

# 🔴 ĐƯỜNG DẪN ẢNH NỀN
set_background("pngtree-abstract-circular-gray-white-gradient-background-image_754036.jpg")

# --- CUSTOM CSS KHÁC ---
st.markdown("""
    <style>
    [data-testid="stHeader"] { background: transparent !important; }

    .slogan-text { 
        font-size: 2.5rem; font-weight: 900; text-align: center; 
        color: #D32F2F; margin-top: -35px; margin-bottom: 30px;
        letter-spacing: 1px; text-transform: uppercase;
    }
    
    .price-tag { font-size: 4rem; color: #D32F2F; font-weight: 900; text-align: center; margin-top: 5px; margin-bottom: 15px;}
    
    div[data-testid="stVerticalBlockBorderWrapper"] { 
        background-color: rgba(255, 255, 255, 0.95) !important; 
        border-radius: 15px !important; border: none !important;
        box-shadow: 0px 8px 20px rgba(0, 0, 0, 0.2) !important;
    }
    
    .info-card {
        background: linear-gradient(135deg, #ffffff 0%, #f1f5f9 100%);
        padding: 15px;
        border-radius: 15px;
        text-align: center;
        border: 1px solid #e2e8f0;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        margin-bottom: 15px;
        transition: transform 0.3s ease, box-shadow 0.3s ease;
    }
    .info-card:hover {
        transform: translateY(-8px); 
        box-shadow: 0 10px 20px rgba(211, 47, 47, 0.15);
        border-color: #D32F2F;
    }
    .info-icon { font-size: 2.5rem; margin-bottom: 5px; }
    .info-title { font-size: 1.2rem; color: #64748b; font-weight: bold; }
    .info-value { font-size: 1.8rem; color: #D32F2F; font-weight: 900; }
    
    h3 { font-size: 2rem !important; font-weight: 900 !important; color: #D32F2F !important; text-align: center; }
    
    .stTextInput label p { font-size: 1.8rem !important; font-weight: bold !important; color: #D32F2F !important; }
    .stTextInput input { font-size: 1.8rem !important; padding: 20px 20px !important; height: 30px !important; }
    
    .stButton button {
        font-size: 2rem !important; font-weight: 900 !important;
        padding: 20px !important; margin-top: 10px !important;
        border-radius: 12px !important; text-transform: uppercase;
    }
    </style>
""", unsafe_allow_html=True)

if 'ride_data' not in st.session_state:
    st.session_state['ride_data'] = None

# ==========================================
# HEADER: LOGO VÀ SLOGAN
# ==========================================
col_space_left, col_logo, col_space_right = st.columns([3.5, 3, 3.5])

with col_logo:
    st.image("logo.png", use_container_width=True)
    st.markdown('<div class="slogan-text">Bật đỏ - Tới ngay</div>', unsafe_allow_html=True)

col_taskbar, col_map = st.columns([4.5, 5.5], gap="large")

# ==========================================
# CỘT TRÁI: TASKBAR NHẬP LIỆU & THÔNG TIN
# ==========================================
with col_taskbar:
    with st.container(border=True):
        start_address = st.text_input("📍 Điểm đón", placeholder="VD: 227 Nguyễn Văn Cừ, TP.HCM")
        end_address = st.text_input("🏁 Điểm đến", placeholder="VD: Landmark 81, TP.HCM")
        
        st.markdown("<br>", unsafe_allow_html=True)
        book_btn = st.button("🚀 Tìm Chuyến Xe", use_container_width=True, type="primary")

    if book_btn:
        if not start_address or not end_address:
            st.warning("⚠️ Vui lòng nhập đủ điểm đón và đến!")
        else:
            with st.spinner("Đang định vị... 🛰️"):
                start_geo = geocode_address(start_address)
                end_geo = geocode_address(end_address)

                if not start_geo or not end_geo:
                    st.error("❌ Không tìm thấy tọa độ. Hãy ghi rõ địa chỉ hơn.")
                else:
                    route = get_route_info(start_geo[:2], end_geo[:2])
                    
                    if route:
                        weather = get_weather(start_geo[0], start_geo[1])
                        is_peak = is_peak_hour()
                        price_info = calculate_price(route['distance_km'], route['duration_min'], weather['is_bad'], is_peak)

                        st.session_state['ride_data'] = {
                            'start_geo': start_geo, 'end_geo': end_geo,
                            'route': route, 'weather': weather,
                            'is_peak': is_peak, 'price_info': price_info
                        }
                    else:
                        st.error("❌ Không vẽ được đường xe hơi giữa 2 điểm này!")
                        st.warning(f"📍 Tọa độ định vị:\n- Đón: {start_geo[2]} ({start_geo[0]}, {start_geo[1]})\n- Đến: {end_geo[2]} ({end_geo[0]}, {end_geo[1]})")

    if st.session_state['ride_data']:
        data = st.session_state['ride_data']
        
        st.markdown("### 📋 Thông tin chuyến đi")
        with st.container(border=True):
            info_col1, info_col2 = st.columns(2)
            
            with info_col1:
                st.markdown(f"""
                <div class="info-card">
                    <div class="info-icon">📏</div>
                    <div class="info-title">Quãng đường</div>
                    <div class="info-value">{data['route']['distance_km']:.2f} km</div>
                </div>
                """, unsafe_allow_html=True)
                
                w_status = "Xấu ⛈️" if data['weather']['is_bad'] else "Tốt ☀️"
                st.markdown(f"""
                <div class="info-card">
                    <div class="info-icon">🌤️</div>
                    <div class="info-title">Thời tiết ({data['weather']['temp']}°C)</div>
                    <div class="info-value">{w_status}</div>
                </div>
                """, unsafe_allow_html=True)

            with info_col2:
                st.markdown(f"""
                <div class="info-card">
                    <div class="info-icon">⏱️</div>
                    <div class="info-title">Thời gian</div>
                    <div class="info-value">{data['route']['duration_min']:.1f} phút</div>
                </div>
                """, unsafe_allow_html=True)
                
                p_status = "Có 🔴" if data['is_peak'] else "Không 🟢"
                st.markdown(f"""
                <div class="info-card">
                    <div class="info-icon">🚦</div>
                    <div class="info-title">Giờ cao điểm</div>
                    <div class="info-value">{p_status}</div>
                </div>
                """, unsafe_allow_html=True)

# ==========================================
# CỘT PHẢI: BẢN ĐỒ MAPBOX CHÍNH CHỦ
# ==========================================
with col_map:
    with st.container(border=True):
        # 🔴 KHAI BÁO LINK MAPBOX VỚI GIAO DIỆN ĐƯỜNG PHỐ
        mapbox_tiles = f"https://api.mapbox.com/styles/v1/mapbox/streets-v12/tiles/{{z}}/{{x}}/{{y}}?access_token={MAPBOX_TOKEN}"
        
        if st.session_state['ride_data'] is None:
            m = folium.Map(location=[10.762622, 106.660172], zoom_start=12, tiles=mapbox_tiles, attr="Mapbox") 
            st_folium(m, height=750, use_container_width=True, returned_objects=[])
            
        else:
            data = st.session_state['ride_data']
            c_lat = (data['start_geo'][0] + data['end_geo'][0]) / 2
            c_lon = (data['start_geo'][1] + data['end_geo'][1]) / 2
            
            m = folium.Map(location=[c_lat, c_lon], zoom_start=13, tiles=mapbox_tiles, attr="Mapbox")
            
            folium.Marker(
                [data['start_geo'][0], data['start_geo'][1]], popup=f"Đi đón: {data['start_geo'][2]}", icon=folium.Icon(color='red', icon='play')
            ).add_to(m)
            
            folium.Marker(
                [data['end_geo'][0], data['end_geo'][1]], popup=f"Điểm đến: {data['end_geo'][2]}", icon=folium.Icon(color='black', icon='stop') 
            ).add_to(m)
            
            route_coords = polyline.decode(data['route']['geometry'], 6)
            folium.PolyLine(route_coords, weight=5, color='#D32F2F', opacity=0.8).add_to(m) 
            
            st_folium(m, height=750, use_container_width=True, returned_objects=[])

# ==========================================
# BOTTOM: GIÁ TIỀN & NÚT ĐẶT XE
# ==========================================
if st.session_state['ride_data']:
    data = st.session_state['ride_data']
    st.markdown("<br>", unsafe_allow_html=True)
    
    bot_col1, bot_col_center, bot_col3 = st.columns([2.5, 5, 2.5])
    
    with bot_col_center:
        with st.container(border=True):
            st.markdown("<div style='text-align: center; color: #666; font-size: 1.8rem; font-weight: bold; margin-top: 10px;'>TỔNG TIỀN THANH TOÁN</div>", unsafe_allow_html=True)
            st.markdown(f'<div class="price-tag">{data["price_info"]["final_price"]:,} ₫</div>', unsafe_allow_html=True)
            
            mult_str = f"Hệ số logic mờ: x{data['price_info']['multiplier']} ({data['price_info']['level']})"
            st.caption(f"<div style='text-align: center; font-size: 1.4rem;'>{mult_str}</div>", unsafe_allow_html=True)
            
            st.markdown("<br>", unsafe_allow_html=True)
            st.button("✅ XÁC NHẬN ĐẶT XE BÂY GIỜ", use_container_width=True, type="primary")
