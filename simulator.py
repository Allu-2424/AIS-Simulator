import json
from datetime import datetime, timedelta, timezone
from geopy.distance import geodesic
from pyais import encode_dict
from shapely.geometry import LineString
from math import radians, degrees, atan2, cos, sin

def calculate_bearing(lat1, lon1, lat2, lon2):
    dLon = radians(lon2 - lon1)
    lat1 = radians(lat1)
    lat2 = radians(lat2)

    x = sin(dLon) * cos(lat2)
    y = cos(lat1) * sin(lat2) - (sin(lat1) * cos(lat2) * cos(dLon))

    initial_bearing = atan2(x, y) # this contains the angle in radians btw true norht and the line joining our A and B
    compass_bearing = (degrees(initial_bearing) + 360) % 360
    return compass_bearing

def simulate_ais_messages(route_file = 'route_ouput.json', speed_knots = 20.0):
    with open(route_file, 'r') as f:
        route = json.load(f)
        
        waypoints = [(lat, lon) for lon, lat in route['route']]
        
        line = LineString(waypoints)
        total_distance_nm = line.length * 60
        
        interval_minutes = 5
        interval_hours = interval_minutes / 60.0
        distance_per_interval = speed_knots * interval_hours
        
        positions = []
        current_distance = 0.0
        timestamp = datetime.now(timezone.utc).replace(second=0, microsecond=0)
        
        while current_distance <= total_distance_nm:
            fraction = current_distance / total_distance_nm
            point = line.interpolate(fraction, normalized=True)
            lat, lon = point.y, point.x
        
            if positions:
                prev_lat, prev_lon = positions[-1]['lat'], positions[-1]['lon']
                course = calculate_bearing(prev_lat, prev_lon, lat, lon)
            else:
                course = 0.0
        
            positions.append({
                "timestamp": timestamp.isoformat(),
                "lat": lat,
                "lon": lon,
                    "course": course,
                "speed": speed_knots
        })
        
        
            timestamp += timedelta(minutes=interval_minutes)
            current_distance += distance_per_interval
        
    return positions

def create_ais_payload(mmsi, lat, lon, speed, course, timestamp):
    
    return encode_dict({
        'mmsi': mmsi,
        'type': 1,  # Position report (AIS message type 1)
        'lat': lat,
        'lon': lon,
        'sog': int(speed),  # Speed over ground (knots)
        'course': int(course),  # True heading in degrees
        'timestamp': int(timestamp.timestamp())  # Convert datetime to Unix epoch
    })
    
    
if __name__ == "__main__":
    # Example usage
    positions = simulate_ais_messages("route_output.json")
    for pos in positions:
        print(create_ais_payload("123456789", pos['lat'], pos['lon'], pos['speed'], pos['course'], datetime.fromisoformat(pos['timestamp'])))