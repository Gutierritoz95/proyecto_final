import os
from datetime import datetime

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url


db = SQLAlchemy()

TICKETS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'Tickets'))

DEFAULT_CLIENTS = ["Ana Pérez", "Carlos López", "María Sánchez"]
DEFAULT_MENU = {
    "Hamburguesa clásica": {"category": "Alimentos", "price": 85.00},
    "Hamburguesa doble": {"category": "Alimentos", "price": 110.00},
    "Papas fritas": {"category": "Alimentos", "price": 35.00},
    "Refresco": {"category": "Bebidas", "price": 25.00},
    "Extra 1": {"category": "Extra", "price": 20.00},
    "Combo 1": {"category": "Combos", "price": 150.00},
}


class Client(db.Model):
    __tablename__ = 'clients'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def as_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'created_at': self.created_at.isoformat(),
        }


class MenuItem(db.Model):
    __tablename__ = 'menu_items'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True, nullable=False)
    category = db.Column(db.String(64), nullable=False)
    price = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def as_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'category': self.category,
            'price': self.price,
            'created_at': self.created_at.isoformat(),
        }


class Order(db.Model):
    __tablename__ = 'orders'

    id = db.Column(db.Integer, primary_key=True)
    customer_name = db.Column(db.String(120), nullable=False)
    total = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    items = db.relationship('OrderItem', backref='order', cascade='all, delete-orphan')

    def as_dict(self):
        return {
            'id': self.id,
            'customer_name': self.customer_name,
            'total': self.total,
            'created_at': self.created_at.isoformat(),
            'items': [item.as_dict() for item in self.items],
        }


class OrderItem(db.Model):
    __tablename__ = 'order_items'

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)
    product_name = db.Column(db.String(120), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float, nullable=False)

    def as_dict(self):
        return {
            'id': self.id,
            'order_id': self.order_id,
            'product_name': self.product_name,
            'quantity': self.quantity,
            'price': self.price,
        }


def get_database_uri():
    database_url = os.getenv('DATABASE_URL')
    if database_url:
        return database_url

    user = os.getenv('MYSQL_USER', 'root')
    password = os.getenv('MYSQL_PASSWORD', '')
    host = os.getenv('MYSQL_HOST', '127.0.0.1')
    port = os.getenv('MYSQL_PORT', '3306')
    database = os.getenv('MYSQL_DB', 'happy_burger')

    return f'mysql+pymysql://{user}:{password}@{host}:{port}/{database}'


def ensure_database_exists(database_uri):
    url = make_url(database_uri)
    if url.drivername.startswith('mysql') and url.database:
        server_url = url.set(database='')
        engine = create_engine(server_url)
        with engine.connect().execution_options(isolation_level='AUTOCOMMIT') as connection:
            connection.execute(
                text(
                    f"CREATE DATABASE IF NOT EXISTS `{url.database}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
                )
            )


def init_app(app):
    app.config['SQLALCHEMY_DATABASE_URI'] = get_database_uri()
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)

    ensure_database_exists(app.config['SQLALCHEMY_DATABASE_URI'])

    with app.app_context():
        db.create_all()
        seed_default_data()


def seed_default_data():
    if Client.query.count() == 0:
        for name in DEFAULT_CLIENTS:
            db.session.add(Client(name=name))

    if MenuItem.query.count() == 0:
        for name, data in DEFAULT_MENU.items():
            db.session.add(MenuItem(name=name, category=data['category'], price=data['price']))

    db.session.commit()


def find_client_by_id(client_id):
    return Client.query.get(client_id)


def find_client_by_name(name):
    return Client.query.filter_by(name=name.strip()).first()


def get_or_create_client(name):
    cleaned_name = name.strip()
    client = find_client_by_name(cleaned_name)
    if not client:
        client = Client(name=cleaned_name)
        db.session.add(client)
        db.session.flush()
    return client


def get_clients():
    return [client.as_dict() for client in Client.query.order_by(Client.name).all()]


def add_client(name):
    if not name or not str(name).strip():
        raise ValueError('El nombre del cliente es obligatorio.')

    cleaned_name = name.strip()
    existing = find_client_by_name(cleaned_name)
    if existing:
        raise ValueError(f'El cliente "{cleaned_name}" ya existe.')

    client = Client(name=cleaned_name)
    db.session.add(client)
    db.session.commit()
    return client


def update_client(client_id, name):
    if not name or not str(name).strip():
        raise ValueError('El nombre del cliente es obligatorio.')

    client = find_client_by_id(client_id)
    if not client:
        raise ValueError('Cliente no encontrado.')

    cleaned_name = name.strip()
    if cleaned_name != client.name:
        existing = find_client_by_name(cleaned_name)
        if existing:
            raise ValueError(f'El cliente "{cleaned_name}" ya existe.')

    client.name = cleaned_name
    db.session.commit()
    return client


def delete_client(client_id):
    client = find_client_by_id(client_id)
    if not client:
        raise ValueError('Cliente no encontrado.')

    db.session.delete(client)
    db.session.commit()
    return True


def get_menu():
    return [
        {
            'name': item.name,
            'category': item.category,
            'price': item.price,
        }
        for item in MenuItem.query.order_by(MenuItem.category, MenuItem.name).all()
    ]


def find_menu_item(name):
    return MenuItem.query.filter_by(name=name.strip()).first()


def add_menu_item(name, category, price):
    if not name or not str(name).strip():
        raise ValueError('El nombre del producto es obligatorio.')

    if not category or not str(category).strip():
        category = 'Extra'

    try:
        price = float(price)
        if price <= 0:
            raise ValueError
    except (TypeError, ValueError):
        raise ValueError('El precio debe ser un número mayor que cero.')

    existing = MenuItem.query.filter_by(name=name.strip()).first()
    if existing:
        raise ValueError(f'El producto "{name}" ya existe en el menú.')

    item = MenuItem(name=name.strip(), category=category.strip(), price=price)
    db.session.add(item)
    db.session.commit()
    return item


def update_menu_item(old_name, name, category, price):
    if not old_name or not str(old_name).strip():
        raise ValueError('El nombre original del producto es obligatorio.')

    menu_item = find_menu_item(old_name)
    if not menu_item:
        raise ValueError(f'El producto "{old_name}" no existe.')

    if not name or not str(name).strip():
        raise ValueError('El nombre del producto es obligatorio.')

    if not category or not str(category).strip():
        category = 'Extra'

    try:
        price = float(price)
        if price <= 0:
            raise ValueError
    except (TypeError, ValueError):
        raise ValueError('El precio debe ser un número mayor que cero.')

    normalized_name = name.strip()
    if normalized_name != old_name.strip():
        exists = MenuItem.query.filter_by(name=normalized_name).first()
        if exists:
            raise ValueError(f'El producto "{normalized_name}" ya existe en el menú.')

    menu_item.name = normalized_name
    menu_item.category = category.strip()
    menu_item.price = price
    db.session.commit()
    return menu_item


def delete_menu_item(name):
    menu_item = find_menu_item(name)
    if not menu_item:
        raise ValueError(f'El producto "{name}" no existe en el menú.')

    db.session.delete(menu_item)
    db.session.commit()
    return True


def create_order(customer_name, items):
    if not customer_name or not str(customer_name).strip():
        raise ValueError('El nombre del cliente es obligatorio.')

    if not items or not isinstance(items, list):
        raise ValueError('La orden debe incluir al menos un producto.')

    menu_map = {item.name: item for item in MenuItem.query.all()}
    if not menu_map:
        raise ValueError('No hay productos disponibles para realizar la orden.')

    client = get_or_create_client(customer_name)
    order = Order(customer_name=client.name, total=0)
    db.session.add(order)

    total = 0
    for product in items:
        name = product.get('name')
        quantity = product.get('quantity', 0)

        if not name or name not in menu_map:
            raise ValueError(f'El producto "{name}" no existe en el menú.')

        try:
            quantity = int(quantity)
            if quantity <= 0:
                raise ValueError
        except (TypeError, ValueError):
            raise ValueError('La cantidad debe ser un número entero mayor que cero.')

        menu_item = menu_map[name]
        subtotal = menu_item.price * quantity
        total += subtotal

        order_item = OrderItem(
            order=order,
            product_name=menu_item.name,
            quantity=quantity,
            price=menu_item.price,
        )
        db.session.add(order_item)

    order.total = round(total, 2)
    db.session.commit()

    order_data = order.as_dict()
    order_data['ticket_filename'] = write_order_ticket(order_data)

    return order_data


def write_order_ticket(order_data):
    os.makedirs(TICKETS_DIR, exist_ok=True)

    timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
    filename = f"ticket_{order_data['id']}_{timestamp}.txt"
    file_path = os.path.join(TICKETS_DIR, filename)

    lines = [
        f"Orden ID: {order_data['id']}",
        f"Cliente: {order_data['customer_name']}",
        f"Fecha: {datetime.utcnow().isoformat()}",
        '---',
    ]

    for item in order_data['items']:
        lines.append(f"{item['product_name']} x{item['quantity']} - ${item['price']:.2f}")

    lines.extend([
        '---',
        f"Total: ${order_data['total']:.2f}",
    ])

    with open(file_path, 'w', encoding='utf-8') as ticket_file:
        ticket_file.write('\n'.join(lines))

    return filename