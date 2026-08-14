from fastapi import FastAPI
from sqlalchemy import text
from app.database import engine
from app import models
from .routers import users,auth


models.Base.metadata.create_all(bind=engine)


app = FastAPI()

app.include_router(users.router)
app.include_router(auth.router)


@app.get("/")
def root():
    return {"message": "Library Management API is running"}


@app.get("/test_db")
def test_db():
    try:
        with engine.connect() as connection:
            connection.execute(text("Select 1"))

        return {"message":"Conected successfully"}

    except Exception as e:
        return {
            "message": "Database connection failed",
            "error": str(e)
        }
