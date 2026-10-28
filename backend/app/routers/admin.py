import uuid
from io import BytesIO
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from PIL import Image, ImageOps, UnidentifiedImageError
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.config import settings
from app.database import get_db
from app.dependencies import require_admin, require_csrf
from app.models import Category, Order, OrderHistory, Product, ProductImage, ProductVariant, User
from app.schemas import CategoryOut, OrderOut, OrderStatusInput, ProductInput, ProductOut
from app.schemas import CategoryInput, CategoryOut, OrderOut, OrderStatusInput, ProductInput, ProductOut

router = APIRouter(prefix="/api/admin", tags=["administração"], dependencies=[Depends(require_admin)])


def load_product(db: Session, product_id: int) -> Product:
    product = db.scalar(select(Product).options(joinedload(Product.category), selectinload(Product.images), selectinload(Product.variants)).where(Product.id == product_id, Product.archived_at.is_(None)))
    if product is None:
        raise HTTPException(status_code=404, detail="Produto não encontrado.")
    return product


@router.get("/dashboard")
def dashboard(db: Session = Depends(get_db)) -> dict[str, int | str]:
    products_count = db.scalar(select(func.count(Product.id)).where(Product.archived_at.is_(None))) or 0
    available = db.scalar(select(func.count(Product.id)).where(Product.archived_at.is_(None), Product.is_available.is_(True))) or 0
    orders_count = db.scalar(select(func.count(Order.id))) or 0
    pending = db.scalar(select(func.count(Order.id)).where(Order.status == "pending")) or 0
    sales = db.scalar(select(func.coalesce(func.sum(Order.total), 0)).where(Order.status == "paid")) or Decimal("0.00")
    return {"products": products_count, "available_products": available, "unavailable_products": products_count - available, "orders": orders_count, "pending_orders": pending, "paid_sales": str(sales)}


@router.get("/categories", response_model=list[CategoryOut])
def admin_categories(db: Session = Depends(get_db)) -> list[Category]:
    return list(db.scalars(select(Category).order_by(Category.name)).all())


@router.post("/categories", response_model=CategoryOut, status_code=201, dependencies=[Depends(require_csrf)])
def create_category(payload: CategoryInput, db: Session = Depends(get_db)) -> Category:
    category = Category(name=payload.name, slug=payload.slug, description=payload.description)
    db.add(category)
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=409, detail="Não foi possível cadastrar a categoria.")
    db.refresh(category)
    return category


@router.get("/products", response_model=list[ProductOut])
def admin_products(db: Session = Depends(get_db)) -> list[Product]:
    query = select(Product).options(joinedload(Product.category), selectinload(Product.images), selectinload(Product.variants)).where(Product.archived_at.is_(None)).order_by(Product.name)
    return list(db.scalars(query).unique().all())


@router.post("/products", response_model=ProductOut, status_code=201, dependencies=[Depends(require_csrf)])
def create_product(payload: ProductInput, db: Session = Depends(get_db)) -> Product:
    if db.get(Category, payload.category_id) is None:
        raise HTTPException(status_code=422, detail="Categoria inválida.")
    product = Product(**payload.model_dump(exclude={"images", "variants"}))
    product.images = [ProductImage(**image.model_dump(), position=index) for index, image in enumerate(payload.images)]
    product.variants = [ProductVariant(**variant.model_dump()) for variant in payload.variants]
    db.add(product)
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=409, detail="Não foi possível salvar o produto. Verifique se o endereço já está em uso.")
    return load_product(db, product.id)


@router.put("/products/{product_id}", response_model=ProductOut, dependencies=[Depends(require_csrf)])
def update_product(product_id: int, payload: ProductInput, db: Session = Depends(get_db)) -> Product:
    product = load_product(db, product_id)
    if db.get(Category, payload.category_id) is None:
        raise HTTPException(status_code=422, detail="Categoria inválida.")
    for key, value in payload.model_dump(exclude={"images", "variants"}).items():
        setattr(product, key, value)
    product.images = [ProductImage(**image.model_dump(), position=index) for index, image in enumerate(payload.images)]
    product.variants = [ProductVariant(**variant.model_dump()) for variant in payload.variants]
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=409, detail="Não foi possível salvar o produto. Verifique se o endereço já está em uso.")
    return load_product(db, product.id)


@router.post("/products/{product_id}/archive", status_code=204, dependencies=[Depends(require_csrf)])
def archive_product(product_id: int, db: Session = Depends(get_db)) -> None:
    product = load_product(db, product_id)
    product.archived_at = datetime.now(timezone.utc)
    product.is_published = False
    db.commit()


@router.post("/uploads", dependencies=[Depends(require_csrf)])
async def upload_image(file: UploadFile = File(...)) -> dict[str, str]:
    suffix = Path(file.filename or "").suffix.lower()
    allowed = {".jpg", ".jpeg", ".png", ".webp"}
    if suffix not in allowed or file.content_type not in {"image/jpeg", "image/png", "image/webp"}:
        raise HTTPException(status_code=415, detail="Formato de imagem não aceito.")
    content = await file.read(8 * 1024 * 1024 + 1)
    if len(content) > 8 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="A imagem deve ter no máximo 8 MB.")
    try:
        with Image.open(BytesIO(content)) as source:
            if source.format not in {"JPEG", "PNG", "WEBP"} or source.width * source.height > 25_000_000:
                raise HTTPException(status_code=415, detail="Imagem inválida ou com dimensões excessivas.")
            image = ImageOps.exif_transpose(source)
            image.thumbnail((2000, 2000), Image.Resampling.LANCZOS)
            if image.mode not in {"RGB", "RGBA"}:
                image = image.convert("RGBA" if "transparency" in image.info else "RGB")
            optimized = BytesIO()
            image.save(optimized, format="WEBP", quality=82, method=6)
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError):
        raise HTTPException(status_code=415, detail="O arquivo enviado não contém uma imagem válida.")
    destination = Path(settings.upload_dir)
    destination.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid.uuid4().hex}.webp"
    (destination / filename).write_bytes(optimized.getvalue())
    return {"url": f"/media/{filename}"}


@router.get("/orders", response_model=list[OrderOut])
def orders(db: Session = Depends(get_db)) -> list[Order]:
    query = select(Order).options(joinedload(Order.customer), selectinload(Order.items), selectinload(Order.history)).order_by(Order.created_at.desc())
    return list(db.scalars(query).unique().all())


@router.patch("/orders/{order_id}/status", response_model=OrderOut, dependencies=[Depends(require_csrf)])
def update_order_status(order_id: int, payload: OrderStatusInput, user: User = Depends(require_admin), db: Session = Depends(get_db)) -> Order:
    order = db.scalar(select(Order).options(joinedload(Order.customer), selectinload(Order.items), selectinload(Order.history)).where(Order.id == order_id).with_for_update())
    if order is None:
        raise HTTPException(status_code=404, detail="Pedido não encontrado.")
    if order.status != payload.status:
        if payload.status == "cancelled" and order.stock_reserved:
            for item in order.items:
                if item.product_id is not None:
                    product = db.scalar(select(Product).where(Product.id == item.product_id).with_for_update())
                    if product is not None and product.stock is not None and item.reserved_product_stock:
                        product.stock += item.reserved_product_stock
                if item.variant_id is not None:
                    variant = db.scalar(select(ProductVariant).where(ProductVariant.id == item.variant_id).with_for_update())
                    if variant is not None and variant.stock is not None and item.reserved_variant_stock:
                        variant.stock += item.reserved_variant_stock
            order.stock_reserved = False
        elif order.status == "cancelled" and payload.status != "cancelled" and not order.stock_reserved:
            required_products: dict[int, int] = {}
            required_variants: dict[int, int] = {}
            for item in order.items:
                if item.product_id is None:
                    raise HTTPException(status_code=409, detail="Não é possível reabrir o pedido porque um produto foi removido.")
                if item.reserved_product_stock:
                    required_products[item.product_id] = required_products.get(item.product_id, 0) + item.reserved_product_stock
                if item.variant_id is not None and item.reserved_variant_stock:
                    required_variants[item.variant_id] = required_variants.get(item.variant_id, 0) + item.reserved_variant_stock
            for product_id, quantity in required_products.items():
                product = db.scalar(select(Product).where(Product.id == product_id).with_for_update())
                if product is None or (product.stock is not None and product.stock < quantity):
                    raise HTTPException(status_code=409, detail="Não há estoque para reabrir este pedido.")
            for variant_id, quantity in required_variants.items():
                variant = db.scalar(select(ProductVariant).where(ProductVariant.id == variant_id).with_for_update())
                if variant is None or (variant.stock is not None and variant.stock < quantity):
                    raise HTTPException(status_code=409, detail="A variação não tem estoque para reabrir este pedido.")
            for product_id, quantity in required_products.items():
                product = db.get(Product, product_id)
                if product is not None and product.stock is not None:
                    product.stock -= quantity
            for variant_id, quantity in required_variants.items():
                variant = db.get(ProductVariant, variant_id)
                if variant is not None and variant.stock is not None:
                    variant.stock -= quantity
            order.stock_reserved = True
        db.add(OrderHistory(order=order, user_id=user.id, old_status=order.status, new_status=payload.status))
        order.status = payload.status
        db.commit()
    return order