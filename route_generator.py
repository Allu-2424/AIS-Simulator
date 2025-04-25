import csv
import pandas as pd
import searoute as sr
import json
from shapely.geometry import LineString
import random

def generate_route(ports_file = 'UpdatedPub150.csv', output_file = None):
    with open(ports_file, 'r') as f:
        reader = csv.DictReader(f)
        ports = [row for row in reader]
        
    port_a, port_b = random.sample(ports, 2)
    
    origin = (float(port_a['Longitude']), float(port_a['Latitude']))
    destination = (float(port_b['Longitude']), float(port_b['Latitude']))
    
    route = sr.searoute(origin, destination)
    
    if route is None:
        print("No route could be generated between the selected ports.")
        return None
    
    route_coords = route['geometry']['coordinates']
    
    print(f"Route from {port_a['Main Port Name']} to {port_b['Main Port Name']}:")
    print(route_coords)
    
    if output_file:
        with open(output_file, 'w') as out:
            json.dump({
                'from': port_a['Main Port Name'],
                'to': port_b['Main Port Name'],
                'route': route_coords
            }, out)

    return route_coords

generate_route(output_file = 'route_output.json')