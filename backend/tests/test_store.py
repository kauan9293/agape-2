from io import BytesIO
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from PIL import Image
from sqlalchemy import select

from app import cli
from app.config import Settings, settings
from app.models import Category, Product, ProductImage, ProductVariant, User, UserSession
from app.security import hash_password, verify_password


def create_admin_account(client):
    with client.app.state.test_session_factory() as db:
        db.add(User(email="owner@example.com", password_hash=hash_password("a-very-long-test-password"), role="admin"))
        db.commit()


def test_neon_unpooled_database_url_uses_psycopg_driver():
    configured = Settings(
        _env_file=None,
        AGAPE_DATABASE_URL_UNPOOLED="postgresql://user:password@db.example.test/store?sslmode=require",
    )
    assert configured.database_url == "postgresql+psycopg://user:password@db.example.test/store?sslmode=require"


def add_product(client):
    with client.app.state.test_session_factory() as db:
        category = Category(name="Bolos", slug="bolos", description="")
        product = Product(category=category, name="Bolo teste", slug="bolo-teste", description="Descrição do bolo.", price=Decimal("10.00"), is_available=True, is_published=True, is_featured=True, stock=4)
        product.images.append(ProductImage(url="https://example.com/bolo.jpg", alt_text="Bolo", position=0))
        db.add(product)
        db.commit()
        return product.id


def authenticated(client):
    csrf = client.get("/api/auth/csrf").json()["csrf_token"]
    response = client.post("/api/auth/login", headers={"X-CSRF-Token": csrf}, json={"email": "owner@example.com", "password": "a-very-long-test-password"})
    assert response.status_code == 200
    return client.get("/api/auth/csrf").json()["csrf_token"]


def test_admin_routes_reject_anonymous_users(client):
    response = client.get("/api/admin/dashboard")
    assert response.status_code == 401


def test_first_admin_setup_is_disabled_without_configured_token(client, monkeypatch):
    monkeypatch.setattr(settings, "admin_setup_token", "")
    assert client.get("/api/auth/setup-status").json() == {"available": False}


def test_first_admin_setup_requires_token_and_closes_after_creation(client, monkeypatch):
    setup_token = "test-setup-token-with-at-least-thirty-two-characters"
    monkeypatch.setattr(settings, "admin_setup_token", setup_token)
    assert client.get("/api/auth/setup-status").json() == {"available": True}
    csrf = client.get("/api/auth/csrf").json()["csrf_token"]
    payload = {"setup_token": "wrong-setup-token-with-at-least-thirty-two-chars", "email": "owner@example.com", "password": "a-very-long-test-password"}
    response = client.post("/api/auth/setup", headers={"X-CSRF-Token": csrf}, json=payload)
    assert response.status_code == 403
    payload["setup_token"] = setup_token
    response = client.post("/api/auth/setup", headers={"X-CSRF-Token": csrf}, json=payload)
    assert response.status_code == 201
    assert response.json()["email"] == "owner@example.com"
    assert client.get("/api/auth/me").status_code == 200
    assert client.get("/api/auth/setup-status").json() == {"available": False}
    csrf = client.get("/api/auth/csrf").json()["csrf_token"]
    response = client.post("/api/auth/setup", headers={"X-CSRF-Token": csrf}, json=payload)
    assert response.status_code == 409


def test_admin_mutations_require_csrf(client):
    create_admin_account(client)
    csrf = authenticated(client)
    assert client.get("/api/admin/dashboard").status_code == 200
    response = client.post("/api/admin/categories", json={"name": "Doces", "slug": "doces", "description": ""})
    assert response.status_code == 403
    response = client.post("/api/admin/categories", headers={"X-CSRF-Token": csrf}, json={"name": "Doces", "slug": "doces", "description": ""})
    assert response.status_code == 201


def test_public_catalog_only_shows_published_products(client):
    product_id = add_product(client)
    response = client.get("/api/products")
    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == [product_id]
    assert response.json()[0]["price"] == "10.00"


def test_checkout_uses_database_price_and_saves_snapshot(client):
    product_id = add_product(client)
    future = (datetime.now(timezone.utc) + timedelta(days=4)).isoformat()
    response = client.post("/api/orders", json={
        "customer_name": "Cliente Teste",
        "customer_phone": "+5511999999999",
        "fulfillment": "pickup",
        "requested_for": future,
        "items": [{"product_id": product_id, "quantity": 2}],
    })
    assert response.status_code == 201
    assert response.json()["total"] == "20.00"
    with client.app.state.test_session_factory() as db:
        product = db.scalar(select(Product).where(Product.id == product_id))
        assert product is not None and product.price == Decimal("10.00")


def test_checkout_rejects_insufficient_stock(client):
    product_id = add_product(client)
    future = (datetime.now(timezone.utc) + timedelta(days=4)).isoformat()
    response = client.post("/api/orders", json={
        "customer_name": "Cliente Teste",
        "customer_phone": "+5511999999999",
        "fulfillment": "pickup",
        "requested_for": future,
        "items": [{"product_id": product_id, "quantity": 5}],
    })
    assert response.status_code == 409


def test_quote_only_product_cannot_be_added_to_checkout(client):
    product_id = add_product(client)
    with client.app.state.test_session_factory() as db:
        product = db.get(Product, product_id)
        assert product is not None
        product.is_quote_only = True
        db.commit()
    catalog = client.get("/api/products?featured=true").json()
    quote_product = next(item for item in catalog if item["id"] == product_id)
    assert quote_product["price"] == "Sob consulta"
    assert quote_product["is_quote_only"] is True
    future = (datetime.now(timezone.utc) + timedelta(days=4)).isoformat()
    response = client.post("/api/orders", json={
        "customer_name": "Cliente Teste",
        "customer_phone": "+5511999999999",
        "fulfillment": "pickup",
        "requested_for": future,
        "items": [{"product_id": product_id, "quantity": 1}],
    })
    assert response.status_code == 422
    assert response.json()["detail"] == "Este produto precisa ser orçado pelo WhatsApp e não aceita pedido pelo carrinho."


def test_checkout_aggregates_repeated_product_lines_for_stock(client):
    product_id = add_product(client)
    future = (datetime.now(timezone.utc) + timedelta(days=4)).isoformat()
    response = client.post("/api/orders", json={
        "customer_name": "Cliente Teste",
        "customer_phone": "+5511999999999",
        "fulfillment": "pickup",
        "requested_for": future,
        "items": [
            {"product_id": product_id, "quantity": 3},
            {"product_id": product_id, "quantity": 3},
        ],
    })
    assert response.status_code == 409


def test_checkout_requires_variant_and_uses_database_surcharge(client):
    product_id = add_product(client)
    with client.app.state.test_session_factory() as db:
        variant = ProductVariant(product_id=product_id, name="Tamanho grande", price_delta=Decimal("5.00"), stock=3)
        db.add(variant)
        db.commit()
        variant_id = variant.id
    future = (datetime.now(timezone.utc) + timedelta(days=4)).isoformat()
    data = {
        "customer_name": "Cliente Teste",
        "customer_phone": "+5511999999999",
        "fulfillment": "pickup",
        "requested_for": future,
        "items": [{"product_id": product_id, "quantity": 1}],
    }
    assert client.post("/api/orders", json=data).status_code == 422
    data["items"] = [{"product_id": product_id, "variant_id": variant_id, "quantity": 1}]
    response = client.post("/api/orders", json=data)
    assert response.status_code == 201
    assert response.json()["total"] == "15.00"


def test_checkout_enforces_minimum_notice(client):
    product_id = add_product(client)
    soon = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
    response = client.post("/api/orders", json={
        "customer_name": "Cliente Teste",
        "customer_phone": "+5511999999999",
        "fulfillment": "pickup",
        "requested_for": soon,
        "items": [{"product_id": product_id, "quantity": 1}],
    })
    assert response.status_code == 422


def test_admin_status_update_is_recorded_in_history(client):
    create_admin_account(client)
    csrf = authenticated(client)
    product_id = add_product(client)
    future = (datetime.now(timezone.utc) + timedelta(days=4)).isoformat()
    response = client.post("/api/orders", json={
        "customer_name": "Cliente Teste",
        "customer_phone": "+5511999999999",
        "fulfillment": "pickup",
        "requested_for": future,
        "items": [{"product_id": product_id, "quantity": 1}],
    })
    assert response.status_code == 201
    order = client.get("/api/admin/orders").json()[0]
    response = client.patch(f"/api/admin/orders/{order['id']}/status", headers={"X-CSRF-Token": csrf}, json={"status": "confirmed"})
    assert response.status_code == 200
    assert response.json()["history"][0]["old_status"] == "pending"
    assert response.json()["history"][0]["new_status"] == "confirmed"
    with client.app.state.test_session_factory() as db:
        assert db.get(Product, product_id).stock == 3
    response = client.patch(f"/api/admin/orders/{order['id']}/status", headers={"X-CSRF-Token": csrf}, json={"status": "cancelled"})
    assert response.status_code == 200
    with client.app.state.test_session_factory() as db:
        assert db.get(Product, product_id).stock == 4
    future = (datetime.now(timezone.utc) + timedelta(days=4)).isoformat()
    competing_order = client.post("/api/orders", json={
        "customer_name": "Outro Cliente",
        "customer_phone": "+5511888888888",
        "fulfillment": "pickup",
        "requested_for": future,
        "items": [{"product_id": product_id, "quantity": 4}],
    })
    assert competing_order.status_code == 201
    response = client.patch(f"/api/admin/orders/{order['id']}/status", headers={"X-CSRF-Token": csrf}, json={"status": "confirmed"})
    assert response.status_code == 409
    competing_admin_order = client.get("/api/admin/orders").json()[0]
    response = client.patch(f"/api/admin/orders/{competing_admin_order['id']}/status", headers={"X-CSRF-Token": csrf}, json={"status": "cancelled"})
    assert response.status_code == 200
    response = client.patch(f"/api/admin/orders/{order['id']}/status", headers={"X-CSRF-Token": csrf}, json={"status": "confirmed"})
    assert response.status_code == 200
    with client.app.state.test_session_factory() as db:
        assert db.get(Product, product_id).stock == 3


def test_admin_upload_converts_image_to_webp(client, tmp_path, monkeypatch):
    create_admin_account(client)
    csrf = authenticated(client)
    monkeypatch.setattr(settings, "upload_dir", str(tmp_path))
    source = Image.new("RGB", (2400, 1000), color="white")
    source_bytes = BytesIO()
    source.save(source_bytes, format="PNG")
    response = client.post(
        "/api/admin/uploads",
        headers={"X-CSRF-Token": csrf},
        files={"file": ("cake.png", source_bytes.getvalue(), "image/png")},
    )
    assert response.status_code == 200
    filename = response.json()["url"].rsplit("/", 1)[-1]
    with Image.open(tmp_path / filename) as optimized:
        assert optimized.format == "WEBP"
        assert optimized.size == (2000, 833)


def test_cancellation_does_not_restore_stock_that_was_not_reserved(client):
    create_admin_account(client)
    csrf = authenticated(client)
    product_id = add_product(client)
    with client.app.state.test_session_factory() as db:
        db.get(Product, product_id).stock = None
        db.commit()
    future = (datetime.now(timezone.utc) + timedelta(days=4)).isoformat()
    response = client.post("/api/orders", json={
        "customer_name": "Cliente Teste",
        "customer_phone": "+5511999999999",
        "fulfillment": "pickup",
        "requested_for": future,
        "items": [{"product_id": product_id, "quantity": 1}],
    })
    assert response.status_code == 201
    order = client.get("/api/admin/orders").json()[0]
    with client.app.state.test_session_factory() as db:
        db.get(Product, product_id).stock = 2
        db.commit()
    response = client.patch(f"/api/admin/orders/{order['id']}/status", headers={"X-CSRF-Token": csrf}, json={"status": "cancelled"})
    assert response.status_code == 200
    with client.app.state.test_session_factory() as db:
        assert db.get(Product, product_id).stock == 2


def test_nonexistent_admin_mutation_cannot_create_products(client):
    response = client.post("/api/admin/products", json={"name": "Intruso"})
    assert response.status_code == 401


def test_admin_password_reset_changes_hash_and_revokes_sessions(client, monkeypatch):
    create_admin_account(client)
    with client.app.state.test_session_factory() as db:
        user = db.scalar(select(User).where(User.email == "owner@example.com"))
        assert user is not None
        db.add(UserSession(
            user_id=user.id,
            token_hash="a" * 64,
            csrf_token="test-csrf",
            expires_at=datetime.now(timezone.utc) + timedelta(days=1),
        ))
        db.commit()

    passwords = iter(["a-new-secure-test-password", "a-new-secure-test-password"])
    monkeypatch.setattr(cli, "SessionLocal", client.app.state.test_session_factory)
    monkeypatch.setattr("builtins.input", lambda _prompt: "owner@example.com")
    monkeypatch.setattr(cli, "getpass", lambda _prompt: next(passwords))

    cli.reset_admin_password()

    with client.app.state.test_session_factory() as db:
        user = db.scalar(select(User).where(User.email == "owner@example.com"))
        assert user is not None
        assert verify_password("a-new-secure-test-password", user.password_hash)
        assert db.scalar(select(UserSession).where(UserSession.user_id == user.id)) is None


def test_christmas_catalog_seed_updates_requested_catalog_positions(client, monkeypatch):
    expected_descriptions = {
        "pudim-120g": "Torta salgada disponível nos sabores Bauru ou Frango.",
        "bolo-de-ninho": "Pudim artesanal em porção de 120 g.",
        "torta-de-bauru-ou-frango": "Bolo de Ninho artesanal.",
    }
    with client.app.state.test_session_factory() as db:
        category = Category(name="Bolos", slug="bolos", description="")
        db.add(category)
        for slug in expected_descriptions:
            db.add(Product(
                category=category,
                name=f"Produto {slug}",
                slug=slug,
                description="Descrição incorreta.",
                price=Decimal("10.00"),
            ))
        db.commit()

    monkeypatch.setattr(cli, "SessionLocal", client.app.state.test_session_factory)
    cli.seed_christmas_catalog()

    with client.app.state.test_session_factory() as db:
        for slug, expected_description in expected_descriptions.items():
            product = db.scalar(select(Product).where(Product.slug == slug))
            assert product is not None
            assert product.description == expected_description
            assert product.name == f"Produto {slug}"