from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class CategoryOut(ORMModel):
    id: int
    name: str
    slug: str
    description: str

class CategoryInput(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    slug: str = Field(min_length=2, max_length=120, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    description: str = Field(default="", max_length=1000)


class ImageInput(BaseModel):
    url: str = Field(min_length=1, max_length=500)
    alt_text: str = Field(default="", max_length=180)


class ImageOut(ORMModel):
    id: int
    url: str
    alt_text: str
    position: int


class VariantInput(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    price_delta: Decimal = Field(default=Decimal("0.00"), ge=0, max_digits=10, decimal_places=2)
    stock: int | None = Field(default=None, ge=0)
    is_available: bool = True


class VariantOut(ORMModel):
    id: int
    name: str
    price_delta: Decimal
    stock: int | None
    is_available: bool


class ProductInput(BaseModel):
    category_id: int
    name: str = Field(min_length=2, max_length=180)
    slug: str = Field(min_length=2, max_length=200, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    description: str = Field(min_length=2, max_length=5000)
    price: Decimal = Field(ge=0, max_digits=10, decimal_places=2)
    is_available: bool = True
    is_published: bool = False
    is_featured: bool = False
    is_demo: bool = False
    stock: int | None = Field(default=None, ge=0)
    images: list[ImageInput] = Field(default_factory=list, max_length=8)
    variants: list[VariantInput] = Field(default_factory=list, max_length=30)


class ProductOut(ORMModel):
    id: int
    category_id: int
    category: CategoryOut
    name: str
    slug: str
    description: str
    price: Decimal
    is_available: bool
    is_published: bool
    is_featured: bool
    is_demo: bool
    stock: int | None
    images: list[ImageOut]
    variants: list[VariantOut]


class LoginInput(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=200)


class UserOut(ORMModel):
    id: int
    email: EmailStr
    role: str


class OrderLineInput(BaseModel):
    product_id: int
    variant_id: int | None = None
    quantity: int = Field(ge=1, le=50)


class OrderInput(BaseModel):
    customer_name: str = Field(min_length=2, max_length=160)
    customer_email: EmailStr | None = None
    customer_phone: str = Field(min_length=8, max_length=30)
    fulfillment: str = Field(pattern="^(pickup|delivery)$")
    requested_for: datetime
    delivery_notes: str = Field(default="", max_length=500)
    items: list[OrderLineInput] = Field(min_length=1, max_length=30)


class OrderStatusInput(BaseModel):
    status: str = Field(pattern="^(pending|confirmed|preparing|ready|completed|cancelled|paid)$")


class OrderItemOut(ORMModel):
    product_name: str
    variant_name: str
    quantity: int
    unit_price: Decimal


class CustomerOut(ORMModel):
    name: str
    email: EmailStr | None
    phone: str


class HistoryOut(ORMModel):
    old_status: str
    new_status: str
    created_at: datetime


class OrderOut(ORMModel):
    id: int
    public_code: str
    status: str
    fulfillment: str
    delivery_notes: str
    requested_for: datetime
    total: Decimal
    created_at: datetime
    customer: CustomerOut
    items: list[OrderItemOut]
    history: list[HistoryOut]


class CheckoutOut(BaseModel):
    public_code: str
    total: Decimal
    whatsapp_url: str | None