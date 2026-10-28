import secrets
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.config import settings
from app.database import get_db
from app.models import Category, Customer, Order, OrderItem, Product, ProductVariant
from app.schemas import CategoryOut, CheckoutOut, OrderInput, ProductOut

router = APIRouter(prefix="/api", tags=["loja"])


@router.get("/storefront-config")
def storefront_config() -> dict[str, int | str]:
    return {
        "minimum_order_notice_hours": settings.minimum_order_notice_hours,
        "instagram_url": settings.instagram_url,
        "business_whatsapp": settings.business_whatsapp,
        "business_email": settings.business_email,
    }


@router.get("/categories", response_model=list[CategoryOut])
def categories(db: Session = Depends(get_db)) -> list[Category]:
    return list(db.scalars(select(Category).order_by(Category.name)).all())


@router.get("/products", response_model=list[ProductOut])
def products(q: str | None = Query(default=None, max_length=100), category: str | None = None, featured: bool | None = None, db: Session = Depends(get_db)) -> list[Product]:
    query = select(Product).options(joinedload(Product.category), selectinload(Product.images), selectinload(Product.variants)).where(Product.is_published.is_(True), Product.archived_at.is_(None))
    if q:
        query = query.where(Product.name.ilike(f"%{q.strip()}%"))
    if category:
        query = query.join(Category).where(Category.slug == category)
    if featured is not None:
        query = query.where(Product.is_featured.is_(featured))
    return list(db.scalars(query.order_by(Product.is_featured.desc(), Product.name)).unique().all())


@router.get("/products/{slug}", response_model=ProductOut)
def product_detail(slug: str, db: Session = Depends(get_db)) -> Product:
    product = db.scalar(select(Product).options(joinedload(Product.category), selectinload(Product.images), selectinload(Product.variants)).where(Product.slug == slug, Product.is_published.is_(True), Product.archived_at.is_(None)))
    if product is None:
        raise HTTPException(status_code=404, detail="Produto não encontrado.")
    return product


@router.post("/orders", response_model=CheckoutOut, status_code=201)
def create_order(payload: OrderInput, db: Session = Depends(get_db)) -> CheckoutOut:
    requested_for = payload.requested_for
    if requested_for.tzinfo is None:
        requested_for = requested_for.replace(tzinfo=timezone.utc)
    minimum_time = datetime.now(timezone.utc) + timedelta(hours=settings.minimum_order_notice_hours)
    if requested_for < minimum_time:
        raise HTTPException(status_code=422, detail=f"Escolha uma data com pelo menos {settings.minimum_order_notice_hours} horas de antecedência.")
    if payload.fulfillment == "delivery" and not payload.delivery_notes.strip():
        raise HTTPException(status_code=422, detail="Informe os dados necessários para a entrega.")
    customer = Customer(name=payload.customer_name.strip(), email=str(payload.customer_email).lower() if payload.customer_email else None, phone=payload.customer_phone.strip())
    db.add(customer)
    db.flush()
    order = Order(public_code=secrets.token_hex(5).upper(), customer=customer, status="pending", stock_reserved=True, fulfillment=payload.fulfillment, delivery_notes=payload.delivery_notes.strip(), requested_for=requested_for, total=Decimal("0.00"))
    product_quantities: dict[int, int] = {}
    variant_quantities: dict[tuple[int, int], int] = {}
    for line in payload.items:
        product_quantities[line.product_id] = product_quantities.get(line.product_id, 0) + line.quantity
        if line.variant_id is not None:
            key = (line.product_id, line.variant_id)
            variant_quantities[key] = variant_quantities.get(key, 0) + line.quantity
    total = Decimal("0.00")
    for line in payload.items:
        product = db.scalar(select(Product).where(Product.id == line.product_id, Product.is_published.is_(True), Product.archived_at.is_(None)).with_for_update())
        if product is None or not product.is_available or (product.stock is not None and product.stock < product_quantities[line.product_id]):
            raise HTTPException(status_code=409, detail="Um produto não está disponível na quantidade solicitada.")
        variant = None
        if product.variants and line.variant_id is None:
            raise HTTPException(status_code=422, detail="Selecione uma variação para cada produto que oferece opções.")
        if line.variant_id:
            variant = db.scalar(select(ProductVariant).where(ProductVariant.id == line.variant_id, ProductVariant.product_id == product.id).with_for_update())
            required_quantity = variant_quantities.get((line.product_id, line.variant_id), 0)
            if variant is None or not variant.is_available or (variant.stock is not None and variant.stock < required_quantity):
                raise HTTPException(status_code=409, detail="Uma variação não está disponível na quantidade solicitada.")
        unit_price = product.price + (variant.price_delta if variant else Decimal("0.00"))
        total += unit_price * line.quantity
        order.items.append(OrderItem(
            product_id=product.id,
            variant_id=variant.id if variant else None,
            product_name=product.name,
            variant_name=variant.name if variant else "",
            quantity=line.quantity,
            unit_price=unit_price,
            reserved_product_stock=line.quantity if product.stock is not None else 0,
            reserved_variant_stock=line.quantity if variant and variant.stock is not None else 0,
        ))
    for product_id, quantity in product_quantities.items():
        product = db.get(Product, product_id)
        if product is not None and product.stock is not None:
            product.stock -= quantity
    for (product_id, variant_id), quantity in variant_quantities.items():
        variant = db.get(ProductVariant, variant_id)
        if variant is not None and variant.stock is not None:
            variant.stock -= quantity
    order.total = total
    db.add(order)
    db.commit()
    whatsapp_url = None
    if settings.business_whatsapp:
        message = f"Olá! Gostaria de confirmar o pedido {order.public_code} no valor de R$ {total:.2f}."
        whatsapp_url = f"https://wa.me/{settings.business_whatsapp}?text={quote(message)}"
    return CheckoutOut(public_code=order.public_code, total=total, whatsapp_url=whatsapp_url)