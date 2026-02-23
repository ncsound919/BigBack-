"""API code templates for rapid backend development.

Each template is a self-contained, production-ready snippet that developers
can drop straight into their projects.
"""

from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

templates_router = APIRouter(prefix="/templates", tags=["templates"])

# ---------------------------------------------------------------------------
# Template registry
# ---------------------------------------------------------------------------

_TEMPLATES: dict[str, dict] = {
    "fastapi-crud": {
        "id": "fastapi-crud",
        "label": "FastAPI CRUD Router",
        "framework": "fastapi",
        "lang": "Python",
        "description": (
            "Complete async CRUD endpoints with SQLAlchemy 2.0, "
            "Pydantic v2 schemas, and Redis caching."
        ),
        "code": '''\
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

router = APIRouter(prefix="/items", tags=["items"])


class ItemCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: Optional[str] = Field(default=None, max_length=1000)


class ItemResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    owner: str
    model_config = {"from_attributes": True}


@router.post("/", response_model=ItemResponse, status_code=201)
async def create_item(
    payload: ItemCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    item = Item(
        id=str(uuid.uuid4()),
        name=payload.name,
        description=payload.description,
        owner=current_user.sub,
    )
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return item


@router.get("/{item_id}", response_model=ItemResponse)
async def get_item(item_id: str, db: AsyncSession = Depends(get_db)):
    item = await db.get(Item, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return item


@router.put("/{item_id}", response_model=ItemResponse)
async def update_item(
    item_id: str, payload: ItemCreate, db: AsyncSession = Depends(get_db)
):
    item = await db.get(Item, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    item.name = payload.name
    item.description = payload.description
    await db.commit()
    await db.refresh(item)
    return item


@router.delete("/{item_id}", status_code=204)
async def delete_item(item_id: str, db: AsyncSession = Depends(get_db)):
    item = await db.get(Item, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    await db.delete(item)
    await db.commit()
''',
    },
    "fastapi-auth": {
        "id": "fastapi-auth",
        "label": "FastAPI JWT Auth",
        "framework": "fastapi",
        "lang": "Python",
        "description": (
            "JWT authentication with OAuth2 password flow, "
            "token creation, and protected route dependency."
        ),
        "code": '''\
from datetime import datetime, timedelta, timezone
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext

SECRET_KEY = "change-me-in-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(subject: str, expires_delta: timedelta | None = None) -> str:
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    return jwt.encode({"sub": subject, "exp": expire}, SECRET_KEY, algorithm=ALGORITHM)


async def get_current_user(token: str = Depends(oauth2_scheme)):
    exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise exc
        return username
    except JWTError:
        raise exc
''',
    },
    "express-crud": {
        "id": "express-crud",
        "label": "Express.js CRUD Router",
        "framework": "express",
        "lang": "JavaScript",
        "description": (
            "Full CRUD REST router with input validation, "
            "error forwarding, and async/await patterns."
        ),
        "code": '''\
const express = require('express');
const router = express.Router();

// GET /items
router.get('/', async (req, res, next) => {
  try {
    const items = await Item.findAll({ where: { userId: req.user.id } });
    res.json({ data: items });
  } catch (err) { next(err); }
});

// GET /items/:id
router.get('/:id', async (req, res, next) => {
  try {
    const item = await Item.findOne({
      where: { id: req.params.id, userId: req.user.id },
    });
    if (!item) return res.status(404).json({ error: 'Not found' });
    res.json(item);
  } catch (err) { next(err); }
});

// POST /items
router.post('/', async (req, res, next) => {
  try {
    const { name, description } = req.body;
    if (!name) return res.status(400).json({ error: 'name is required' });
    const item = await Item.create({ name, description, userId: req.user.id });
    res.status(201).json(item);
  } catch (err) { next(err); }
});

// PUT /items/:id
router.put('/:id', async (req, res, next) => {
  try {
    const item = await Item.findOne({
      where: { id: req.params.id, userId: req.user.id },
    });
    if (!item) return res.status(404).json({ error: 'Not found' });
    await item.update(req.body);
    res.json(item);
  } catch (err) { next(err); }
});

// DELETE /items/:id
router.delete('/:id', async (req, res, next) => {
  try {
    const item = await Item.findOne({
      where: { id: req.params.id, userId: req.user.id },
    });
    if (!item) return res.status(404).json({ error: 'Not found' });
    await item.destroy();
    res.status(204).send();
  } catch (err) { next(err); }
});

module.exports = router;
''',
    },
    "nestjs-controller": {
        "id": "nestjs-controller",
        "label": "NestJS CRUD Controller",
        "framework": "nestjs",
        "lang": "TypeScript",
        "description": (
            "NestJS controller with JWT guard, DTOs, "
            "and TypeORM service injection."
        ),
        "code": '''\
import {
  Controller, Get, Post, Put, Delete,
  Body, Param, UseGuards, Req, HttpCode, HttpStatus,
} from '@nestjs/common';
import { AuthGuard } from '@nestjs/passport';
import { CreateItemDto } from './dto/create-item.dto';
import { ItemsService } from './items.service';

@Controller('items')
@UseGuards(AuthGuard('jwt'))
export class ItemsController {
  constructor(private readonly itemsService: ItemsService) {}

  @Get()
  findAll(@Req() req) {
    return this.itemsService.findAll(req.user.id);
  }

  @Get(':id')
  findOne(@Param('id') id: string, @Req() req) {
    return this.itemsService.findOne(id, req.user.id);
  }

  @Post()
  @HttpCode(HttpStatus.CREATED)
  create(@Body() dto: CreateItemDto, @Req() req) {
    return this.itemsService.create(dto, req.user.id);
  }

  @Put(':id')
  update(@Param('id') id: string, @Body() dto: CreateItemDto, @Req() req) {
    return this.itemsService.update(id, dto, req.user.id);
  }

  @Delete(':id')
  @HttpCode(HttpStatus.NO_CONTENT)
  remove(@Param('id') id: string, @Req() req) {
    return this.itemsService.remove(id, req.user.id);
  }
}
''',
    },
    "gin-handler": {
        "id": "gin-handler",
        "label": "Gin CRUD Handlers",
        "framework": "gin",
        "lang": "Go",
        "description": (
            "Gin framework CRUD handlers with GORM, "
            "struct binding, and proper HTTP status codes."
        ),
        "code": '''\
package handlers

import (
    "net/http"
    "github.com/gin-gonic/gin"
    "gorm.io/gorm"
)

type ItemInput struct {
    Name        string `json:"name"        binding:"required,max=200"`
    Description string `json:"description" binding:"max=1000"`
}

func ListItems(db *gorm.DB) gin.HandlerFunc {
    return func(c *gin.Context) {
        var items []Item
        if err := db.Where("owner_id = ?", c.GetString("userID")).
            Find(&items).Error; err != nil {
            c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
            return
        }
        c.JSON(http.StatusOK, gin.H{"data": items})
    }
}

func CreateItem(db *gorm.DB) gin.HandlerFunc {
    return func(c *gin.Context) {
        var input ItemInput
        if err := c.ShouldBindJSON(&input); err != nil {
            c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
            return
        }
        item := Item{Name: input.Name, Description: input.Description,
                     OwnerID: c.GetString("userID")}
        if err := db.Create(&item).Error; err != nil {
            c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
            return
        }
        c.JSON(http.StatusCreated, item)
    }
}

func GetItem(db *gorm.DB) gin.HandlerFunc {
    return func(c *gin.Context) {
        var item Item
        if err := db.Where("id = ? AND owner_id = ?",
            c.Param("id"), c.GetString("userID")).First(&item).Error; err != nil {
            c.JSON(http.StatusNotFound, gin.H{"error": "not found"})
            return
        }
        c.JSON(http.StatusOK, item)
    }
}

func DeleteItem(db *gorm.DB) gin.HandlerFunc {
    return func(c *gin.Context) {
        if err := db.Where("id = ? AND owner_id = ?",
            c.Param("id"), c.GetString("userID")).Delete(&Item{}).Error; err != nil {
            c.JSON(http.StatusNotFound, gin.H{"error": "not found"})
            return
        }
        c.Status(http.StatusNoContent)
    }
}
''',
    },
    "django-viewset": {
        "id": "django-viewset",
        "label": "Django REST ViewSet",
        "framework": "django",
        "lang": "Python",
        "description": (
            "Django REST Framework ModelViewSet with permission classes, "
            "filtering, search, and custom stats action."
        ),
        "code": '''\
from rest_framework import viewsets, permissions, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from .models import Item
from .serializers import ItemSerializer


class ItemViewSet(viewsets.ModelViewSet):
    serializer_class = ItemSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["owner"]
    search_fields = ["name", "description"]
    ordering_fields = ["created_at", "name"]
    ordering = ["-created_at"]

    def get_queryset(self):
        return Item.objects.filter(owner=self.request.user).select_related("owner")

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    @action(detail=False, methods=["get"])
    def stats(self, request):
        qs = self.get_queryset()
        return Response({
            "total": qs.count(),
            "recent": list(qs.order_by("-created_at")[:5].values("id", "name")),
        })
''',
    },
    "sqlalchemy-model": {
        "id": "sqlalchemy-model",
        "label": "SQLAlchemy Model",
        "framework": "fastapi",
        "lang": "Python",
        "description": (
            "Async SQLAlchemy 2.0 declarative model with UUID primary key, "
            "indexed columns, and automatic timestamps."
        ),
        "code": '''\
import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class Item(Base):
    __tablename__ = "items"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    owner: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
''',
    },
    "redis-cache": {
        "id": "redis-cache",
        "label": "Redis Cache Decorator",
        "framework": "fastapi",
        "lang": "Python",
        "description": (
            "Async Redis caching decorator with TTL, "
            "key namespacing, and JSON serialization."
        ),
        "code": '''\
import functools
import json
from typing import Any, Callable

from app.cache.redis import cache_get, cache_set


def cached(key_prefix: str, ttl: int = 300):
    """Async cache decorator.

    Usage::

        @router.get("/{item_id}")
        @cached("items:{item_id}", ttl=60)
        async def get_item(item_id: str):
            ...
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            cache_key = key_prefix.format(**kwargs)
            hit = await cache_get(cache_key)
            if hit:
                return json.loads(hit)
            result = await func(*args, **kwargs)
            await cache_set(cache_key, json.dumps(result, default=str), ttl=ttl)
            return result

        return wrapper

    return decorator
''',
    },
}

# ---------------------------------------------------------------------------
# Pydantic response models
# ---------------------------------------------------------------------------


class TemplateSummary(BaseModel):
    id: str
    label: str
    framework: str
    lang: str
    description: str


class TemplateDetail(TemplateSummary):
    code: str


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@templates_router.get(
    "/",
    response_model=list[TemplateSummary],
    summary="List available API templates",
)
async def list_templates(framework: Optional[str] = None):
    """Return all available code templates, optionally filtered by framework."""
    return [
        TemplateSummary(**{k: v for k, v in t.items() if k != "code"})
        for t in _TEMPLATES.values()
        if framework is None or t["framework"] == framework
    ]


@templates_router.get(
    "/{template_id}",
    response_model=TemplateDetail,
    summary="Get template boilerplate code",
)
async def get_template(template_id: str):
    """Return a single template with its full boilerplate code."""
    template = _TEMPLATES.get(template_id)
    if not template:
        raise HTTPException(
            status_code=404, detail=f"Template '{template_id}' not found"
        )
    return TemplateDetail(**template)
