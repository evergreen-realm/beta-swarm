from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from database import session
from models import SensorData, Sensor, Dashboard, User, Role
from schemas import SensorDataSchema, SensorSchema, DashboardSchema, UserSchema, RoleSchema

# Create routers for each model
sensor_data_router = APIRouter()
sensor_router = APIRouter()
dashboard_router = APIRouter()
user_router = APIRouter()
role_router = APIRouter()

# Define the SensorData routes
@sensor_data_router.post('/sensorData')
async def create_sensor_data(sensor_data: SensorDataSchema):
    sensor_data_obj = SensorData(timestamp=sensor_data.timestamp, value=sensor_data.value, sensor_id=sensor_data.sensor_id)
    session.add(sensor_data_obj)
    session.commit()
    return sensor_data_obj

@sensor_data_router.get('/sensorData/{id}')
async def get_sensor_data(id: int):
    sensor_data_obj = session.query(SensorData).filter(SensorData.id == id).first()
    if sensor_data_obj is None:
        raise HTTPException(status_code=404, detail='Sensor data not found')
    return sensor_data_obj

# Define the Sensor routes
@sensor_router.post('/sensor')
async def create_sensor(sensor: SensorSchema):
    sensor_obj = Sensor(name=sensor.name, description=sensor.description)
    session.add(sensor_obj)
    session.commit()
    return sensor_obj

@sensor_router.get('/sensor/{id}')
async def get_sensor(id: int):
    sensor_obj = session.query(Sensor).filter(Sensor.id == id).first()
    if sensor_obj is None:
        raise HTTPException(status_code=404, detail='Sensor not found')
    return sensor_obj

# Define the Dashboard routes
@dashboard_router.post('/dashboard')
async def create_dashboard(dashboard: DashboardSchema):
    dashboard_obj = Dashboard(name=dashboard.name, description=dashboard.description)
    session.add(dashboard_obj)
    session.commit()
    return dashboard_obj

@dashboard_router.get('/dashboard/{id}')
async def get_dashboard(id: int):
    dashboard_obj = session.query(Dashboard).filter(Dashboard.id == id).first()
    if dashboard_obj is None:
        raise HTTPException(status_code=404, detail='Dashboard not found')
    return dashboard_obj

# Define the User routes
@user_router.post('/user')
async def create_user(user: UserSchema):
    user_obj = User(username=user.username, password=user.password)
    session.add(user_obj)
    session.commit()
    return user_obj

@user_router.get('/user/{id}')
async def get_user(id: int):
    user_obj = session.query(User).filter(User.id == id).first()
    if user_obj is None:
        raise HTTPException(status_code=404, detail='User not found')
    return user_obj

# Define the Role routes
@role_router.post('/role')
async def create_role(role: RoleSchema):
    role_obj = Role(name=role.name, description=role.description)
    session.add(role_obj)
    session.commit()
    return role_obj

@role_router.get('/role/{id}')
async def get_role(id: int):
    role_obj = session.query(Role).filter(Role.id == id).first()
    if role_obj is None:
        raise HTTPException(status_code=404, detail='Role not found')
    return role_obj