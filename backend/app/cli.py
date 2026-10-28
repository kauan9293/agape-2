import argparse
from decimal import Decimal
from getpass import getpass

from email_validator import EmailNotValidError, validate_email
from sqlalchemy import select

from app.database import Base, SessionLocal, engine
from app.models import Category, Product, ProductImage, User
from app.security import hash_password
from app import models  # noqa: F401


def create_admin() -> None:
    try:
        email = validate_email(input("E-mail do administrador: ").strip(), check_deliverability=False).normalized.lower()
    except EmailNotValidError:
        raise SystemExit("Informe um endereço de e-mail válido.")
    password = getpass("Senha (mínimo 12 caracteres; a digitação fica oculta): ")
    confirmation = getpass("Repita a senha (também fica oculta): ")
    if len(password) < 12:
        raise SystemExit("A senha precisa ter pelo menos 12 caracteres.")
    if password != confirmation:
        raise SystemExit("As senhas não conferem.")
    with SessionLocal() as db:
        if db.scalar(select(User).where(User.email == email)):
            raise SystemExit("Já existe uma conta com esse e-mail.")
        db.add(User(email=email, password_hash=hash_password(password), role="admin"))
        db.commit()
    print("Administrador criado. A senha não foi armazenada em texto puro.")


def reset_admin_password() -> None:
    try:
        email = validate_email(input("E-mail do administrador: ").strip(), check_deliverability=False).normalized.lower()
    except EmailNotValidError:
        raise SystemExit("Informe um endereço de e-mail válido.")
    password = getpass("Nova senha (mínimo 12 caracteres; a digitação fica oculta): ")
    confirmation = getpass("Repita a nova senha (também fica oculta): ")
    if len(password) < 12:
        raise SystemExit("A senha precisa ter pelo menos 12 caracteres.")
    if password != confirmation:
        raise SystemExit("As senhas não conferem.")
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == email, User.role == "admin"))
        if user is None:
            raise SystemExit("Conta administrativa não encontrada.")
        user.password_hash = hash_password(password)
        user.sessions.clear()
        db.commit()
    print("Senha atualizada e sessões anteriores encerradas.")


def seed_demo() -> None:
    Base.metadata.create_all(engine)
    definitions = [
        ("Bolos", "bolos", "Bolos artesanais para compartilhar."),
        ("Docinhos", "docinhos", "Pequenos doces para momentos especiais."),
        ("Sobremesas", "sobremesas", "Sobremesas preparadas artesanalmente."),
    ]
    with SessionLocal() as db:
        categories: dict[str, Category] = {}
        for name, slug, description in definitions:
            category = db.scalar(select(Category).where(Category.slug == slug))
            if category is None:
                category = Category(name=name, slug=slug, description=description)
                db.add(category)
                db.flush()
            categories[slug] = category
        examples = [
            ("Bolo de chocolate (demonstração)", "bolo-chocolate-demo", "bolos", "Bolo ilustrativo. Substitua descrição e dados por informações aprovadas pela confeitaria.", "89.90", "https://images.unsplash.com/photo-1578985545062-69928b1d9587?auto=format&fit=crop&w=1000&q=85"),
            ("Docinhos variados (demonstração)", "docinhos-demo", "docinhos", "Produto e preço fictícios, destinados somente à demonstração do fluxo.", "45.00", "https://images.unsplash.com/photo-1551024506-0bccd828d307?auto=format&fit=crop&w=1000&q=85"),
            ("Sobremesa da casa (demonstração)", "sobremesa-demo", "sobremesas", "Produto e preço fictícios. Edite no painel antes de publicar comercialmente.", "32.00", "https://images.unsplash.com/photo-1488477181946-6428a0291777?auto=format&fit=crop&w=1000&q=85"),
        ]
        for name, slug, category_slug, description, price, image_url in examples:
            product = db.scalar(select(Product).where(Product.slug == slug))
            if product is None:
                product = Product(category=categories[category_slug], name=name, slug=slug, description=description, price=Decimal(price), is_available=True, is_published=True, is_featured=True, is_demo=True)
                product.images.append(ProductImage(url=image_url, alt_text=name, position=0))
                db.add(product)
            else:
                product.is_demo = True
        db.commit()
    print("Categorias e produtos fictícios inseridos; os preços são exemplos, não valores comerciais.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Utilitários da Confeitaria Ágape Artesanal")
    parser.add_argument("command", choices=["create-admin", "reset-admin-password", "seed-demo"])
    command = parser.parse_args().command
    if command == "create-admin":
        create_admin()
    elif command == "reset-admin-password":
        reset_admin_password()
    else:
        seed_demo()


if __name__ == "__main__":
    main()