from fastapi import FastAPI
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, Float, String, DateTime, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import requests
import pytz

from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ================= CONFIG =================
DATABASE_URL = "sqlite:///./weather.db"
TIMEZONE = "Africa/Lagos"

# Optional weather API (Open-Meteo free)
WEATHER_API = "https://api.open-meteo.com/v1/forecast?latitude=7.15&longitude=3.35&current_weather=true"

# =========================================

app = FastAPI()

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

# ================= DATABASE =================

class WeatherData(Base):
    __tablename__ = "weather_data"

    id = Column(Integer, primary_key=True, index=True)
    temp = Column(Float)
    pressure = Column(Integer)
    alt = Column(Float)
    lux = Column(Integer)
    rain = Column(String)

    batt_v = Column(Float)
    batt_pct = Column(Integer)

    sensors = Column(JSON)

    forecast = Column(JSON)

    timestamp = Column(DateTime)


Base.metadata.create_all(bind=engine)

# ================= SCHEMA =================

class SensorStatus(BaseModel):
    bmp180: str
    ldr: str
    rain: str
    battery: str


class WeatherPayload(BaseModel):
    temp: float
    pressure: int
    alt: float
    lux: int
    rain: str
    batt_v: float
    batt_pct: int
    sensors: SensorStatus


# ================= HELPERS =================

def get_current_time():
    tz = pytz.timezone(TIMEZONE)
    return datetime.now(tz)


def get_forecast():
    try:
        res = requests.get(WEATHER_API, timeout=5)
        if res.status_code == 200:
            return res.json()
    except:
        pass
    return {"status": "unavailable"}


# ================= ROUTES =================

@app.get("/ping")
def ping():
    return {"status": "ok", "message": "server running"}


@app.post("/api/weather")
def receive_weather(data: WeatherPayload):
    db = SessionLocal()

    now = get_current_time()
    forecast = get_forecast()

    record = WeatherData(
        temp=data.temp,
        pressure=data.pressure,
        alt=data.alt,
        lux=data.lux,
        rain=data.rain,
        batt_v=data.batt_v,
        batt_pct=data.batt_pct,
        sensors=data.sensors.dict(),
        forecast=forecast,
        timestamp=now
    )

    db.add(record)
    db.commit()
    db.refresh(record)

    db.close()

    return {
        "status": "success",
        "id": record.id,
        "timestamp": now
    }


@app.get("/api/weather")
def get_all_weather():
    db = SessionLocal()

    data = db.query(WeatherData).order_by(WeatherData.id.desc()).all()

    db.close()

    return data


@app.get("/api/weather/latest")
def get_latest():
    db = SessionLocal()

    record = db.query(WeatherData).order_by(WeatherData.id.desc()).first()

    db.close()

    if not record:
        return {"status": "no data"}

    return record
