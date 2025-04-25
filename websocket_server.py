import asyncio
import json
import websockets
from datetime import datetime
from simulator import simulate_ais_messages, create_ais_payload

async def stream_ais_messages(websocket, speed_factor, route_file='route_output.json'):
    print("✅ stream_ais_messages() was called")
    
    positions = simulate_ais_messages(route_file)
    print(f"📍 Loaded {len(positions)} positions from {route_file}")
    
    route_data = json.load(open(route_file))
    mmsi = route_data.get('mmsi', "123456789")
    
    print("🚦 Client connected, starting AIS message stream...")

    prev_time = datetime.fromisoformat(positions[0]['timestamp'])

    for pos in positions:
        current_time = datetime.fromisoformat(pos['timestamp'])

        try:
            payload = create_ais_payload(
                mmsi, pos['lat'], pos['lon'],
                pos['speed'], pos['course'], current_time
            )
        except Exception as e:
            print("❌ Error creating AIS payload:", e)
            continue
        
        #raw_payload = str(create_ais_payload(mmsi, pos['lat'], pos['lon'], pos['speed'], pos['course'], datetime.fromisoformat(pos['timestamp'])))

        ais_payload = {
            "message": "AIVDM",
            "mmsi": mmsi,
            "timestamp": pos['timestamp'],
            "payload": payload  # Wrapped in list for standard compatibility
        }

        print("📤 Sent message to client:", ais_payload)
        await websocket.send(json.dumps(ais_payload))

        # Handle simulation timing
        if speed_factor > 0:
            delay = (current_time - prev_time).total_seconds()
            await asyncio.sleep(delay / speed_factor)
        elif speed_factor == -1:
            await asyncio.sleep(0)  # Send immediately, no delay

        prev_time = current_time

async def main():
    route_file = "route_output.json"
    speed_factor = 10  # Change as needed: 1 = real-time, 2 = 2x, -1 = no delay
    print("🚢 WebSocket AIS server is running on ws://localhost:8765")
    
    async def handler(websocket):
        print("📞 Client connected, invoking stream...")
        await stream_ais_messages(websocket, speed_factor, route_file)
        
    async with websockets.serve(handler, "localhost", 8765):
        await asyncio.Future()  # Run forever

if __name__ == "__main__":
    asyncio.run(main())
