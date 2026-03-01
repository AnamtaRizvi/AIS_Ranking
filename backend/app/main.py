from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select

from app.api.router import api_router
from app.db.session import engine, SessionLocal, Base
from app.db.models import Category
from app.core.journals import PAPER_CATEGORIES


def seed_categories(db) -> None:
    for name in PAPER_CATEGORIES:
        r = db.execute(select(Category).where(Category.name == name)).scalar_one_or_none()
        if not r:
            db.add(Category(name=name))
    db.commit()


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_categories(db)
    finally:
        db.close()
    yield
    # shutdown if needed
    pass


app = FastAPI(title="PaperRanking API", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(api_router)


@app.get("/health")
def health():
    return {"status": "ok"}
