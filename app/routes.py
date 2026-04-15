import os

from flask import flash, redirect, render_template, request, send_from_directory, session, url_for
from .database import (
    TICKETS_DIR,
    add_client,
    add_menu_item,
    create_order,
    delete_client,
    delete_menu_item,
    get_clients,
    get_menu,
    update_client,
    update_menu_item,
)

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
CSS_DIR = os.path.join(PROJECT_ROOT, 'css')
IMG_DIR = os.path.join(PROJECT_ROOT, 'img')


def _redirect_home(**params):
    clean_params = {key: value for key, value in params.items() if value not in (None, '', [])}
    return redirect(url_for('home', **clean_params))


def _get_numbered_menu():
    menu_by_category = {}
    numbered_menu = []

    for index, item in enumerate(get_menu(), start=1):
        numbered_item = {**item, 'number': index}
        numbered_menu.append(numbered_item)
        menu_by_category.setdefault(item['category'], []).append(numbered_item)

    return menu_by_category, numbered_menu


def _get_order():
    return list(session.get('current_order', []))


def _save_order(order):
    session['current_order'] = order
    session.modified = True


def _clear_order(clear_customer=False):
    session['current_order'] = []
    if clear_customer:
        session['order_owner'] = ''
    session.modified = True


def _get_order_total(order=None):
    active_order = order if order is not None else _get_order()
    return round(sum(item['price'] * item['quantity'] for item in active_order), 2)


def _build_home_context(edit_item_name=None, edit_client_id=None):
    menu_by_category, numbered_menu = _get_numbered_menu()
    clients = get_clients()
    editing_item = next((item for item in numbered_menu if item['name'] == edit_item_name), None)
    editing_client = next((client for client in clients if client['id'] == edit_client_id), None)
    order = _get_order()

    return {
        'menu_by_category': menu_by_category,
        'clients': clients,
        'order': order,
        'order_total': _get_order_total(order),
        'order_owner': session.get('order_owner', ''),
        'editing_item': editing_item,
        'editing_client': editing_client,
        'last_ticket_filename': session.get('last_ticket_filename'),
    }


def register_routes(app):
    @app.route('/')
    def home():
        edit_item_name = request.args.get('edit_item')
        edit_client_id = request.args.get('edit_client', type=int)
        return render_template('index.html', **_build_home_context(edit_item_name, edit_client_id))

    @app.route('/css/<path:filename>')
    def css_files(filename):
        return send_from_directory(CSS_DIR, filename)

    @app.route('/img/<path:filename>')
    def image_files(filename):
        return send_from_directory(IMG_DIR, filename)

    @app.route('/tickets/<path:filename>/download')
    def download_ticket(filename):
        return send_from_directory(TICKETS_DIR, filename, as_attachment=True, download_name=filename)

    @app.route('/clientes/guardar', methods=['POST'])
    def save_client_form():
        client_id = request.form.get('id', type=int)
        name = request.form.get('name', '')

        try:
            if client_id:
                client = update_client(client_id, name)
                flash(f'Cliente "{client.name}" actualizado correctamente.', 'success')
            else:
                client = add_client(name)
                flash(f'Cliente "{client.name}" creado correctamente.', 'success')
        except ValueError as exc:
            flash(str(exc), 'error')
            return _redirect_home(edit_client=client_id)

        return _redirect_home()

    @app.route('/clientes/seleccionar', methods=['POST'])
    def select_client_form():
        name = request.form.get('name', '').strip()
        if not name:
            flash('Selecciona un cliente válido.', 'error')
            return _redirect_home()

        session['order_owner'] = name
        flash(f'Cliente "{name}" seleccionado para la orden.', 'success')
        return _redirect_home()

    @app.route('/clientes/eliminar', methods=['POST'])
    def delete_client_form():
        client_id = request.form.get('id', type=int)
        client_name = request.form.get('name', '').strip()

        try:
            delete_client(client_id)
            if client_name and session.get('order_owner') == client_name:
                session['order_owner'] = ''
            flash('Cliente eliminado correctamente.', 'success')
        except ValueError as exc:
            flash(str(exc), 'error')

        return _redirect_home()

    @app.route('/menu/guardar', methods=['POST'])
    def save_menu_item_form():
        old_name = request.form.get('old_name', '')
        name = request.form.get('name', '')
        category = request.form.get('category', 'Extra')
        price = request.form.get('price')

        try:
            if old_name:
                item = update_menu_item(old_name, name, category, price)
                order = _get_order()
                for order_item in order:
                    if order_item['name'] == old_name:
                        order_item['name'] = item.name
                        order_item['price'] = item.price
                _save_order(order)
                flash(f'Producto "{item.name}" actualizado correctamente.', 'success')
            else:
                item = add_menu_item(name, category, price)
                flash(f'Producto "{item.name}" agregado al menú.', 'success')
        except ValueError as exc:
            flash(str(exc), 'error')
            return _redirect_home(edit_item=old_name or None)

        return _redirect_home()

    @app.route('/menu/eliminar', methods=['POST'])
    def delete_menu_item_form():
        name = request.form.get('name', '')

        try:
            delete_menu_item(name)
            order = [item for item in _get_order() if item['name'] != name]
            _save_order(order)
            flash(f'Producto "{name}" eliminado del menú.', 'success')
        except ValueError as exc:
            flash(str(exc), 'error')

        return _redirect_home()

    @app.route('/orden/cliente', methods=['POST'])
    def set_order_customer():
        customer = request.form.get('customer', '').strip()
        if not customer:
            flash('Ingresa el nombre de quien ordena.', 'error')
            return _redirect_home()

        session['order_owner'] = customer
        flash(f'La orden quedó asignada a "{customer}".', 'success')
        return _redirect_home()

    @app.route('/orden/agregar', methods=['POST'])
    def add_item_to_order():
        product_number = request.form.get('product_number', type=int)
        _, numbered_menu = _get_numbered_menu()
        item = next((menu_item for menu_item in numbered_menu if menu_item['number'] == product_number), None)

        if not item:
            flash('No existe un producto con ese número.', 'error')
            return _redirect_home()

        order = _get_order()
        existing = next((order_item for order_item in order if order_item['name'] == item['name']), None)
        if existing:
            existing['quantity'] += 1
        else:
            order.append({'name': item['name'], 'price': item['price'], 'quantity': 1})

        _save_order(order)
        flash(f'Se agregó "{item["name"]}" a la orden.', 'success')
        return _redirect_home()

    @app.route('/orden/quitar', methods=['POST'])
    def remove_item_from_order():
        index = request.form.get('index', type=int)
        order = _get_order()

        if index is None or index < 0 or index >= len(order):
            flash('No se encontró el producto en la orden.', 'error')
            return _redirect_home()

        removed_item = order.pop(index)
        _save_order(order)
        flash(f'Se eliminó "{removed_item["name"]}" de la orden.', 'success')
        return _redirect_home()

    @app.route('/orden/descartar', methods=['POST'])
    def discard_order_form():
        if not _get_order():
            flash('No hay ninguna orden activa para eliminar.', 'error')
            return _redirect_home()

        _clear_order(clear_customer=False)
        flash('Orden descartada correctamente.', 'success')
        return _redirect_home()

    @app.route('/orden/nueva', methods=['POST'])
    def new_order_form():
        _clear_order(clear_customer=True)
        flash('Lista la nueva orden.', 'success')
        return _redirect_home()

    @app.route('/orden/finalizar', methods=['POST'])
    def finalize_order_form():
        customer = request.form.get('customer', '').strip() or session.get('order_owner', '').strip()
        order = _get_order()

        try:
            saved_order = create_order(
                customer,
                [{'name': item['name'], 'quantity': item['quantity']} for item in order],
            )
        except ValueError as exc:
            flash(str(exc), 'error')
            return _redirect_home()

        session['order_owner'] = customer
        session['last_ticket_filename'] = saved_order.get('ticket_filename')
        _clear_order(clear_customer=False)
        flash(
            f'Orden guardada (ID {saved_order["id"]}) para {customer}. Total: ${saved_order["total"]:.2f}',
            'success',
        )
        return _redirect_home()

