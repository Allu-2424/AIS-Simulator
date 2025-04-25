import folium
from geopy.geocoders import Nominatim
from sqlalchemy import create_engine, text
from datetime import datetime
from time import sleep

# Function to get location names from coordinates
def get_location_name(lat, lon):
    geolocator = Nominatim(user_agent="ais_tracker")
    try:
        location = geolocator.reverse((lat, lon), exactly_one=True, timeout=10)
        return location.address if location else "Unknown Location"
    except Exception as e:
        print(f"⚠️ Reverse geocoding failed: {e}")
        return "Unknown Location"

# Function to get vessel track from the database
def get_vessel_track(db_url, mmsi, start_time=None, end_time=None):
    engine = create_engine(db_url)
    query = "SELECT lat, lon, timestamp FROM ais_messages WHERE mmsi = :mmsi"
    
    params = {"mmsi": mmsi}
    if start_time and end_time:
        query += " AND timestamp BETWEEN :start_time AND :end_time"
        params["start_time"] = start_time
        params["end_time"] = end_time
    
    query += " ORDER BY timestamp"
    
    with engine.connect() as conn:
        result = conn.execute(text(query), params)
        return [(float(r.lat), float(r.lon), r.timestamp) for r in result]

# Function to plot vessel route on the map
def plot_vessel_route(points, mmsi):
    if not points:
        print("❌ No points found to plot.")
        return

    print(f"✅ Received {len(points)} points to plot.")

    # Center map on average location
    avg_lat = sum([pt[0] for pt in points]) / len(points)
    avg_lon = sum([pt[1] for pt in points]) / len(points)
    m = folium.Map(location=[avg_lat, avg_lon], zoom_start=6)

    # Draw route
    route = [(lat, lon) for lat, lon, _ in points]
    folium.PolyLine(route, color="blue", weight=3, tooltip="Vessel Route").add_to(m)

    # Get location names for start and end
    start_lat, start_lon = route[0]
    end_lat, end_lon = route[-1]
    
    print("📍 Looking up location names...")
    start_location = get_location_name(start_lat, start_lon)
    sleep(1)  # To avoid rate limiting
    end_location = get_location_name(end_lat, end_lon)

    # Markers with location names
    folium.Marker(
        location=route[0],
        popup=f"Start: {start_location}",
        icon=folium.Icon(color="green")
    ).add_to(m)

    folium.Marker(
        location=route[-1],
        popup=f"End: {end_location}",
        icon=folium.Icon(color="red")
    ).add_to(m)

    # Tooltip with time for each point
    for lat, lon, ts in points:
        if isinstance(ts, str):
            ts = datetime.fromisoformat(ts)
        ts_str = ts.strftime('%Y-%m-%d %H:%M:%S')
        folium.CircleMarker(
            location=(lat, lon),
            radius=3,
            color="blue",
            fill=True,
            fill_opacity=0.7,
            popup=folium.Popup(f"Lat: {lat:.4f}<br>Lon: {lon:.4f}<br>Time: {ts_str}", max_width=200),
            tooltip=f"{ts_str}"
        ).add_to(m)

    map_file = f"vessel_track.1_{mmsi}.html"
    m.save(map_file)
    print(f"🗺️ Map saved to {map_file}")

# Main function to run the script
if __name__ == "__main__":
    print("📢 Running vessel map tracker")
    
    mmsi = input("Enter MMSI: ")
    db_url = "sqlite:///new_ais_data.db"
    
    start = input("Start time (YYYY-MM-DDTHH:MM:SS) or press Enter: ")
    end = input("End time (YYYY-MM-DDTHH:MM:SS) or press Enter: ")
    
    start_dt = datetime.fromisoformat(start) if start else None
    end_dt = datetime.fromisoformat(end) if end else None

    points = get_vessel_track(db_url, mmsi, start_dt, end_dt)
    print(f"First 3 points: {points[:3]}")
    print(f"Found {len(points)} points.")

    plot_vessel_route(points, mmsi)
