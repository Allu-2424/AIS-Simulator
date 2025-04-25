import asyncio
import json
from datetime import datetime
from collections import defaultdict
import websockets

from pyais import decode
from sqlalchemy import (
    Column,
    String,
    Float,
    DateTime,
    create_engine,
    Index,
)
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.orm import declarative_base, Session

# ──────────────────────────────────────────────────────────────────────────────
# 1) Data Modeling: Define ORM model and initialize database
# ──────────────────────────────────────────────────────────────────────────────

Base = declarative_base()

class AISMessage(Base):
    __tablename__ = "ais_messages"
    mmsi      = Column(String(9), primary_key=True)
    timestamp = Column(DateTime, primary_key=True)
    lat       = Column(Float, nullable=False)
    lon       = Column(Float, nullable=False)
    speed     = Column(Float)  # SOG
    course    = Column(Float)  # COG
    raw       = Column(String, nullable=False)

    __table_args__ = (
        Index("idx_mmsi", "mmsi"),
        Index("idx_timestamp", "timestamp"),
        Index("idx_mmsi_timestamp", "mmsi", "timestamp"),
    )

def setup_database(db_url="sqlite:///new_ais_data.db"):
    engine = create_engine(db_url, future=True)
    Base.metadata.create_all(engine)
    return engine

# ──────────────────────────────────────────────────────────────────────────────
# 2) Ingestion Logic: Connect to WebSocket, parse AIVDM, upsert to DB
# ──────────────────────────────────────────────────────────────────────────────

WEBSOCKET_URL = "ws://localhost:8765"

async def ingest_ais(engine):
    total_messages = 0
    invalid_counts = {
        'mmsi': 0,
        'timestamp': 0,
        'coordinates': 0,
        'json': 0,
        'decode': 0,
        'missing_fields': 0,
        'other': 0
    }

    print(f"🔌 Connecting to {WEBSOCKET_URL}...")
    async with websockets.connect(WEBSOCKET_URL) as ws:
        print("✅ Connected.")
        async for raw_msg in ws:
            total_messages += 1
            try:
                envelope = json.loads(raw_msg)
                payloads = envelope.get("payload", [])
                mmsi     = envelope.get("mmsi")
                ts_str   = envelope.get("timestamp")

                if isinstance(payloads, str):
                    payloads = [payloads]

                if not (mmsi and mmsi.isdigit() and len(mmsi) == 9):
                    print(f"⚠️ Invalid MMSI: {mmsi}")
                    invalid_counts["mmsi"] += 1
                    continue

                try:
                    msg_ts = datetime.fromisoformat(ts_str)
                except Exception:
                    print("⚠️ Invalid timestamp:", ts_str)
                    invalid_counts["timestamp"] += 1
                    continue

                if not payloads:
                    print("⚠️ Missing payloads")
                    invalid_counts["missing_fields"] += 1
                    continue

                for sentence in payloads:
                    try:
                        ais = decode(sentence)
                    except Exception as e:
                        print(f"❌ Decode failed [{sentence}]:", e)
                        invalid_counts["decode"] += 1
                        continue

                    if not (-90 <= ais.lat <= 90) or not (-180 <= ais.lon <= 180):
                        print(f"⚠️ Out-of-range coords: {ais.lat},{ais.lon}")
                        invalid_counts["coordinates"] += 1
                        continue

                    stmt = (
                        insert(AISMessage)
                        .values(
                            mmsi=str(ais.mmsi),
                            timestamp=msg_ts,
                            lat=ais.lat,
                            lon=ais.lon,
                            speed=getattr(ais, "speed", None),
                            course=getattr(ais, "course", None),
                            raw=sentence
                        )
                        .on_conflict_do_nothing()
                    )

                    with Session(engine) as session:
                        session.execute(stmt)
                        session.commit()

                    print(f"✅ Stored MMSI={ais.mmsi} @ {msg_ts}")

            except json.JSONDecodeError:
                print("❌ Invalid JSON:", raw_msg)
                invalid_counts["json"] += 1

            except websockets.exceptions.ConnectionClosed:
                print("🔌 WebSocket closed")
                break

            except Exception as e:
                print("❌ Unexpected error:", e)
                invalid_counts["other"] += 1

                print(f"📊 Writing report: {total_messages} messages processed")

    # 📊 Final Data Quality Report
    with open("data_quality_report.txt", "w") as f:
        f.write("📊 Data Quality Report\n")
        f.write(f"Total Messages Processed: {total_messages}\n")
        for issue, count in invalid_counts.items():
            f.write(f"{issue.capitalize()} Issues: {count}\n")

# ──────────────────────────────────────────────────────────────────────────────
# 3) Entrypoint
# ──────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    engine = setup_database()
    asyncio.run(ingest_ais(engine))
