from sqlalchemy import create_engine, text
from geopy.distance import geodesic
from datetime import datetime

def get_vessel_track(db_url, mmsi, start_time=None, end_time=None):
    engine = create_engine(db_url)
    query = """
        SELECT mmsi, timestamp, lat, lon, speed, course, raw
        FROM ais_messages
        WHERE mmsi = :mmsi
    """

    if start_time:
        query += " AND timestamp >= :start_time"
    if end_time:
        query += " AND timestamp <= :end_time"

    query += " ORDER BY timestamp"

    params = {"mmsi": mmsi}
    if start_time:
        params["start_time"] = start_time
    if end_time:
        params["end_time"] = end_time

    with engine.connect() as conn:
        result = conn.execute(text(query), params)
        # Properly fetch as dict using keys
        rows = result.fetchall()
        columns = result.keys()
        return [dict(zip(columns, row)) for row in rows]


def calculate_stats(track):
    if not track or len(track) < 2:
        return {
            "total_distance_nm": 0.0,
            "average_speed_knots": 0.0
        }

    total_distance = 0.0
    prev_point = None

    for point in track:
        if prev_point:
            total_distance += geodesic(
                (prev_point['lat'], prev_point['lon']),
                (point['lat'], point['lon'])
            ).nm
        prev_point = point

    start_time = datetime.fromisoformat(track[0]['timestamp'])
    end_time = datetime.fromisoformat(track[-1]['timestamp'])

    time_diff = (end_time - start_time).total_seconds() / 3600  # in hours
    avg_speed = total_distance / time_diff if time_diff > 0 else 0.0

    return {
        "total_distance_nm": total_distance,
        "average_speed_knots": avg_speed
    }

if __name__ == "__main__":
    db_url = "sqlite:///new_ais_data.db"
    mmsi = input("Enter MMSI (9 digits): ").strip()
    
    start_input = input("Start time (YYYY-MM-DDTHH:MM:SS) or press Enter to skip: ").strip()
    end_input = input("End time (YYYY-MM-DDTHH:MM:SS) or press Enter to skip: ").strip()

    start_dt = datetime.fromisoformat(start_input) if start_input else None
    end_dt = datetime.fromisoformat(end_input) if end_input else None

    track = get_vessel_track(db_url, mmsi, start_dt, end_dt)
    print(f"📍 Track for MMSI {mmsi}: {len(track)} points")

    stats = calculate_stats(track)
    print(f"📏 Total distance: {stats['total_distance_nm']:.2f} nautical miles")
    print(f"🚀 Average speed: {stats['average_speed_knots']:.2f} knots")

