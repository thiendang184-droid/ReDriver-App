"""
HỆ THỐNG ĐẶT XE FUZZY LOGIC - MAPBOX
"""

from config import MAPBOX_TOKEN, OPENWEATHERMAP_API_KEY
import numpy as np
import skfuzzy as fuzz
from skfuzzy import control as ctrl
import requests
from datetime import datetime
import webbrowser
import os
import polyline

# ============================================================
# 1. HỆ THỐNG FUZZY LOGIC
# ============================================================

def create_fuzzy_system():
    # Input
    distance = ctrl.Antecedent(np.arange(0, 21, 0.1), 'distance')
    duration = ctrl.Antecedent(np.arange(0, 61, 1), 'duration')
    weather = ctrl.Antecedent(np.arange(0, 2, 0.1), 'weather')
    peak = ctrl.Antecedent(np.arange(0, 2, 0.1), 'peak')

    # Output
    price = ctrl.Consequent(np.arange(0.5, 2.1, 0.1), 'price')

    # Membership Functions
    distance['near'] = fuzz.trimf(distance.universe, [0, 0, 3])
    distance['medium'] = fuzz.trimf(distance.universe, [2, 6, 10])
    distance['far'] = fuzz.trimf(distance.universe, [8, 20, 20])

    duration['short'] = fuzz.trimf(duration.universe, [0, 0, 12])
    duration['long'] = fuzz.trimf(duration.universe, [10, 35, 60])

    weather['clear'] = fuzz.trimf(weather.universe, [0, 0, 0.5])
    weather['bad'] = fuzz.trimf(weather.universe, [0.5, 1, 1])

    peak['false'] = fuzz.trimf(peak.universe, [0, 0, 0.5])
    peak['true'] = fuzz.trimf(peak.universe, [0.5, 1, 1])

    price['low'] = fuzz.trimf(price.universe, [0.5, 0.8, 1.0])
    price['medium'] = fuzz.trimf(price.universe, [0.9, 1.0, 1.2])
    price['high'] = fuzz.trimf(price.universe, [1.1, 1.3, 1.5])
    price['very_high'] = fuzz.trimf(price.universe, [1.4, 1.6, 2.0])

    # Rules
    rules = [
        ctrl.Rule(distance['near'] & weather['clear'] & peak['false'], price['low']),
        ctrl.Rule(distance['near'] & (weather['bad'] | peak['true']), price['medium']),
        ctrl.Rule(distance['medium'] & weather['clear'] & peak['false'], price['medium']),
        ctrl.Rule(distance['medium'] & (weather['bad'] | peak['true']), price['high']),
        ctrl.Rule(distance['far'] & weather['clear'] & peak['false'], price['high']),
        ctrl.Rule(distance['far'] & (weather['bad'] | peak['true']), price['very_high']),
        ctrl.Rule(duration['long'] & (weather['bad'] | peak['true']), price['high']),
    ]

    return ctrl.ControlSystemSimulation(ctrl.ControlSystem(rules))


# ============================================================
# 2. MAPBOX FUNCTIONS
# ============================================================

def geocode_address(address: str):
    """Chuyển địa chỉ thành tọa độ bằng Mapbox"""
    url = f"https://api.mapbox.com/geocoding/v5/mapbox.places/{requests.utils.quote(address)}.json"
    params = {
        "access_token": MAPBOX_TOKEN,
        "country": "vn",
        "limit": 1
    }
    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        
        if data.get("features"):
            feature = data["features"][0]
            lon, lat = feature["center"]
            name = feature.get("place_name", address)
            return (lat, lon, name)  # (lat, lon, display_name)
    except Exception as e:
        print(f"❌ Geocoding lỗi: {e}")
    return None


def get_route_info(start_coords: tuple, end_coords: tuple):
    """Lấy thông tin đường đi bằng Mapbox"""
    url = f"https://api.mapbox.com/directions/v5/mapbox/driving/{start_coords[1]},{start_coords[0]};{end_coords[1]},{end_coords[0]}"
    params = {
        "access_token": MAPBOX_TOKEN,
        "geometries": "polyline6",
        "overview": "full"
    }
    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        
        route = data["routes"][0]
        return {
            "distance_km": route["distance"] / 1000,
            "duration_min": route["duration"] / 60,
            "geometry": route["geometry"]
        }
    except Exception as e:
        print(f"❌ Lỗi tính đường: {e}")
        return None


def get_weather(lat: float, lon: float):
    """Lấy thông tin thời tiết"""
    if not OPENWEATHERMAP_API_KEY:
        return {"is_bad": False, "description": "Không xác định", "temp": 0}
    
    url = "https://api.openweathermap.org/data/2.5/weather"
    params = {"lat": lat, "lon": lon, "appid": OPENWEATHERMAP_API_KEY, "units": "metric", "lang": "vi"}
    try:
        resp = requests.get(url, params=params, timeout=10)
        data = resp.json()
        weather_id = data["weather"][0]["id"]
        return {
            "is_bad": weather_id < 700,
            "description": data["weather"][0]["description"],
            "temp": data["main"]["temp"]
        }
    except:
        return {"is_bad": False, "description": "Không xác định", "temp": 0}


def is_peak_hour():
    now = datetime.now()
    minutes = now.hour * 60 + now.minute
    peak_times = [(630, 780), (990, 1020), (1200, 1260)]
    return any(start <= minutes <= end for start, end in peak_times)


# ============================================================
# 3. TÍNH GIÁ & HIỂN THỊ
# ============================================================

def calculate_price(distance_km: float, duration_min: float, bad_weather: bool, is_peak: bool):
    sim = create_fuzzy_system()
    
    sim.input['distance'] = min(max(distance_km, 0), 20)
    sim.input['duration'] = min(max(duration_min, 0), 60)
    sim.input['weather'] = 1 if bad_weather else 0
    sim.input['peak'] = 1 if is_peak else 0
    
    sim.compute()
    multiplier = sim.output['price']
    
    base_price = 10000 + (distance_km * 5000)
    final_price = base_price * multiplier
    
    if multiplier <= 0.9: level = "RẺ"
    elif multiplier <= 1.1: level = "TRUNG BÌNH"
    elif multiplier <= 1.4: level = "CAO"
    else: level = "RẤT CAO"
    
    return {
        "base_price": round(base_price),
        "multiplier": round(multiplier, 2),
        "final_price": round(final_price),
        "level": level
    }


def generate_map(start, end, start_name, end_name, geometry):
    try:
        import folium
        route_coords = polyline.decode(geometry, precision=6)
        
        m = folium.Map(location=[(start[0]+end[0])/2, (start[1]+end[1])/2], zoom_start=14)
        
        folium.Marker(start, popup=f"🚗 {start_name}", icon=folium.Icon(color="green")).add_to(m)
        folium.Marker(end, popup=f"📍 {end_name}", icon=folium.Icon(color="red")).add_to(m)
        
        folium.PolyLine(route_coords, weight=6, color="#0066ff", opacity=0.9).add_to(m)
        
        m.save("route_map.html")
        print(f"\n🗺️ Bản đồ đã được tạo: {os.path.abspath('route_map.html')}")
        webbrowser.open('file://' + os.path.realpath("route_map.html"))
    except ImportError:
        print("⚠️ Cần cài: pip install folium polyline")
    except Exception as e:
        print(f"❌ Lỗi tạo bản đồ: {e}")


# ============================================================
# MAIN
# ============================================================

def book_ride(start_address: str, end_address: str):
    print("\n" + "🚕" * 30)
    print("   HỆ THỐNG ĐẶT XE FUZZY LOGIC - MAPBOX")
    print("🚕" * 30)

    # Geocoding
    print("\n📍 Đang định vị...")
    start = geocode_address(start_address)
    end = geocode_address(end_address)
    if not start or not end:
        print("❌ Không thể định vị địa chỉ!")
        return

    # Route
    print("🛣️ Đang tính quãng đường...")
    route = get_route_info(start[:2], end[:2])
    if not route: return

    # Weather & Peak
    print("🌤️ Đang kiểm tra thời tiết...")
    weather = get_weather(start[0], start[1])
    peak = is_peak_hour()

    # Price
    print("💰 Đang tính giá bằng Fuzzy Logic...")
    price_info = calculate_price(route['distance_km'], route['duration_min'], weather['is_bad'], peak)

    # Result
    print("\n" + "="*65)
    print("📋 KẾT QUẢ")
    print("="*65)
    print(f"""
    🚗 Từ: {start[2]}
    📍 Đến: {end[2]}
    
    📏 Khoảng cách : {route['distance_km']:.2f} km
    ⏱️  Thời gian  : {route['duration_min']:.1f} phút
    🌤️  Thời tiết  : {weather['description']}
    ⏰ Giờ cao điểm: {"🔴 Có" if peak else "🟢 Không"}
    
    💵 Giá cơ bản : {price_info['base_price']:,} VND
    📊 Hệ số     : x{price_info['multiplier']} ({price_info['level']})
    💰 TỔNG TIỀN: {price_info['final_price']:,} VND
    """)
    print("="*65)

    generate_map(start[:2], end[:2], start[2], end[2], route['geometry'])


if __name__ == "__main__":
    start = input("🚗 Điểm đón: ").strip() or "Thảo Cầm Viên, TP.HCM"
    end = input("📍 Điểm đến: ").strip() or "Bến Thành, TP.HCM"
    
    book_ride(start, end)