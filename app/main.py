from pathlib import Path
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from .database import get_db
from .routers import users, auth, books, borrowings

app = FastAPI(title='Library Management API', version='1.0.0', description='Books, members, and lending with JWT authentication.')
for router in (users.router, auth.router, books.router, borrowings.router):
    app.include_router(router)


FRONTEND = Path(__file__).resolve().parent / 'frontend'
app.mount('/assets', StaticFiles(directory=FRONTEND / 'assets'), name='assets')


@app.get('/', include_in_schema=False)
def root():
    return FileResponse(FRONTEND / 'index.html')


@app.get('/health', tags=['health'])
@app.get('/test_db', include_in_schema=False)
def health(db: Session = Depends(get_db)):
    try:
        db.execute(text('SELECT 1'))
    except SQLAlchemyError:
        raise HTTPException(status_code=503, detail='Database unavailable')
    return {'status': 'ok'}
