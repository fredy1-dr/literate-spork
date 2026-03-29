from flask import Blueprint, jsonify, request
from app import db
from app.models import Product, Cart, CartItem, Order, OrderItem

products_bp = Blueprint('products', __name__, url_prefix='/api/products')
cart_bp = Blueprint('cart', __name__, url_prefix='/api/cart')
orders_bp = Blueprint('orders', __name__, url_prefix='/api/orders')

@products_bp.route('/', methods=['GET'])
def get_products():
    products = Product.query.all()
    return jsonify([p.to_dict() for p in products])

@products_bp.route('/<int:product_id>', methods=['GET'])
def get_product(product_id):
    product = Product.query.get_or_404(product_id)
    return jsonify(product.to_dict())

@products_bp.route('/', methods=['POST'])
def create_product():
    data = request.get_json()
    product = Product(name=data['name'], description=data.get('description'), price=data['price'], stock=data.get('stock', 0), image_url=data.get('image_url'))
    db.session.add(product)
    db.session.commit()
    return jsonify(product.to_dict()), 201

@cart_bp.route('/<int:user_id>', methods=['GET'])
def get_cart(user_id):
    cart = Cart.query.filter_by(user_id=user_id).first_or_404()
    items = [{'id': item.id, 'product': item.product.to_dict(), 'quantity': item.quantity, 'subtotal': item.get_subtotal()} for item in cart.items]
    return jsonify({'cart_id': cart.id, 'items': items, 'total': cart.get_total()})

@cart_bp.route('/<int:user_id>/add', methods=['POST'])
def add_to_cart(user_id):
    data = request.get_json()
    cart = Cart.query.filter_by(user_id=user_id).first()
    if not cart:
        cart = Cart(user_id=user_id)
        db.session.add(cart)
        db.session.commit()
    product = Product.query.get_or_404(data['product_id'])
    cart_item = CartItem.query.filter_by(cart_id=cart.id, product_id=data['product_id']).first()
    if cart_item:
        cart_item.quantity += data.get('quantity', 1)
    else:
        cart_item = CartItem(cart_id=cart.id, product_id=data['product_id'], quantity=data.get('quantity', 1))
        db.session.add(cart_item)
    db.session.commit()
    return jsonify({'message': 'Produit ajouté au panier'})

@cart_bp.route('/<int:user_id>/remove/<int:item_id>', methods=['DELETE'])
def remove_from_cart(user_id, item_id):
    cart_item = CartItem.query.get_or_404(item_id)
    db.session.delete(cart_item)
    db.session.commit()
    return jsonify({'message': 'Article supprimé du panier'})

@cart_bp.route('/<int:user_id>/clear', methods=['DELETE'])
def clear_cart(user_id):
    cart = Cart.query.filter_by(user_id=user_id).first_or_404()
    CartItem.query.filter_by(cart_id=cart.id).delete()
    db.session.commit()
    return jsonify({'message': 'Panier vidé'})

@orders_bp.route('/<int:user_id>', methods=['GET'])
def get_user_orders(user_id):
    orders = Order.query.filter_by(user_id=user_id).all()
    return jsonify([{'id': o.id, 'total_price': o.total_price, 'status': o.status, 'created_at': o.created_at.isoformat(), 'items': [{'product_id': item.product_id, 'product_name': item.product.name, 'quantity': item.quantity, 'price': item.price} for item in o.items]} for o in orders])

@orders_bp.route('/', methods=['POST'])
def create_order():
    data = request.get_json()
    user_id = data['user_id']
    cart = Cart.query.filter_by(user_id=user_id).first_or_404()
    if not cart.items:
        return jsonify({'error': 'Panier vide'}), 400
    order = Order(user_id=user_id, total_price=cart.get_total(), status='pending')
    for cart_item in cart.items:
        order_item = OrderItem(product_id=cart_item.product_id, quantity=cart_item.quantity, price=cart_item.product.price)
        order.items.append(order_item)
    db.session.add(order)
    CartItem.query.filter_by(cart_id=cart.id).delete()
    db.session.commit()
    return jsonify({'message': 'Commande créée', 'order_id': order.id}), 201

@orders_bp.route('/<int:order_id>/status', methods=['PATCH'])
def update_order_status(order_id):
    data = request.get_json()
    order = Order.query.get_or_404(order_id)
    order.status = data.get('status', order.status)
    db.session.commit()
    return jsonify({'message': 'Statut mis à jour', 'status': order.status})
