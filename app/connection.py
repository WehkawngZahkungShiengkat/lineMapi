from .settings import MONGO_DETAILS

from motor.motor_asyncio import AsyncIOMotorClient

db_client: AsyncIOMotorClient = None

motor = AsyncIOMotorClient(MONGO_DETAILS)

database = motor.user


user_collection = database.get_collection("user")

