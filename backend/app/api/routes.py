import asyncio
import json
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import ItemCreate, ItemResponse
from app.auth.jwt import (
    Token,
    TokenData,
    create_access_token,
    get_current_user,
    hash_password,
    verify_password,
)
from app.cache.redis import cache_delete, cache_get, cache_set
from app.db.database import get_db
from app.db.models import Item
from app.middleware.rate_limit import limiter

router = APIRouter()

# ---------------------------------------------------------------------------
# Fake in-memory user store – replace with a real DB model in production.
# asyncio.Lock provides safety for concurrent requests within a single
# event loop, but NOT across multiple OS threads or worker processes.
# With uvicorn --workers > 1, each process has its own _USERS copy, causing
# registration inconsistencies. Migrate to the PostgreSQL db (db/database.py)
# before enabling multiple workers.
# ---------------------------------------------------------------------------
_USERS: dict[str, str] = {}
_USERS_LOCK = asyncio.Lock()


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_-]+$")
    password: str = Field(min_length=8, max_length=128)


class UserOut(BaseModel):
    username: str


# ---------------------------------------------------------------------------
# Auth endpoints
# ---------------------------------------------------------------------------

auth_router = APIRouter(prefix="/auth", tags=["auth"])


@auth_router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def register(payload: UserCreate):
    async with _USERS_LOCK:
        if payload.username in _USERS:
            raise HTTPException(status_code=400, detail="Username already registered")
        _USERS[payload.username] = hash_password(payload.password)
    return UserOut(username=payload.username)


@auth_router.post("/token", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    # Read hashed password under the lock, then verify outside it.
    # Verification is intentionally outside the lock: the hash is immutable
    # once written (no password-change endpoint exists), so there is no
    # TOCTOU risk and bcrypt.verify() need not block other requests.
    async with _USERS_LOCK:
        hashed = _USERS.get(form_data.username)
    if not hashed or not verify_password(form_data.password, hashed):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = create_access_token(subject=form_data.username, expires_delta=timedelta(minutes=30))
    return Token(access_token=token)


# ---------------------------------------------------------------------------
# Items endpoints (protected + cached)
# ---------------------------------------------------------------------------

items_router = APIRouter(prefix="/items", tags=["items"])


@items_router.post(
    "/",
    response_model=ItemResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create item",
)
async def create_item(
    payload: ItemCreate,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    now = datetime.now(timezone.utc)
    item = Item(
        id=str(uuid.uuid4()),
        name=payload.name,
        description=payload.description,
        owner=current_user.sub,
        created_at=now,
    )
    db.add(item)
    await db.commit()
    await db.refresh(item)
    response = ItemResponse.model_validate(item)
    await cache_set(f"items:{item.id}", response.model_dump_json())
    return response


@items_router.get("/", summary="List items")
@limiter.limit("100/minute")
async def list_items(
    request: Request,
    current_user: TokenData = Depends(get_current_user),
):
    cached = await cache_get("items:all")
    if cached:
        return {"source": "cache", "data": cached}
    data = ["item-1", "item-2", "item-3"]
    await cache_set("items:all", str(data))
    return {"source": "db", "data": data}


@items_router.get("/{item_id}", summary="Get item by ID")
async def get_item(
    item_id: str,
    current_user: TokenData = Depends(get_current_user),
):
    cached = await cache_get(f"items:{item_id}")
    if cached:
        try:
            data = json.loads(cached)
        except (json.JSONDecodeError, ValueError):
            data = cached
        return {"source": "cache", "item_id": item_id, "data": data}
    data = f"data-for-{item_id}"
    await cache_set(f"items:{item_id}", data)
    return {"source": "db", "item_id": item_id, "data": data}


@items_router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_item(
    item_id: str,
    current_user: TokenData = Depends(get_current_user),
):
    await cache_delete(f"items:{item_id}")
