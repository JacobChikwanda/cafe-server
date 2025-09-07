from flask import Flask, request, jsonify
from flask_cors import CORS
from models import db, Customer, Reservation
from datetime import datetime
import random

app = Flask(__name__)
app.config.from_object('config.Config')
CORS(app, resources={r"/*": {"origins": "*"}})  # Allow Streamlit

# Initialize SQLAlchemy
db.init_app(app)

# Create tables
with app.app_context():
    db.create_all()

# Customer CRUD
@app.route('/customers', methods=['GET'])
def get_all_customers():
    try:
        customers = Customer.query.all()
        return jsonify([customer.to_dict() for customer in customers])
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/customers', methods=['POST'])
def create_customer():
    data = request.get_json()
    name = data.get('name')
    email = data.get('email')
    phone_number = data.get('phone_number')
    newsletter_signup = data.get('newsletter_signup', False)

    if not name or not email:
        return jsonify({'error': 'Name and email are required'}), 400

    try:
        customer = Customer(
            name=name,
            email=email,
            phone_number=phone_number,
            newsletter_signup=newsletter_signup
        )
        db.session.add(customer)
        db.session.commit()
        return jsonify({
            'message': 'Customer created',
            'customer': customer.to_dict()
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

@app.route('/customers/<customer_id>', methods=['GET'])
def get_customer(customer_id):
    try:
        customer = Customer.query.get_or_404(customer_id)
        return jsonify(customer.to_dict())
    except Exception as e:
        return jsonify({'error': str(e)}), 404

@app.route('/customers/<customer_id>', methods=['PUT'])
def update_customer(customer_id):
    data = request.get_json()
    name = data.get('name')
    email = data.get('email')
    phone_number = data.get('phone_number')
    newsletter_signup = data.get('newsletter_signup')

    try:
        customer = Customer.query.get_or_404(customer_id)
        if name:
            customer.name = name
        if email:
            customer.email = email
        if phone_number:
            customer.phone_number = phone_number
        if newsletter_signup is not None:
            customer.newsletter_signup = newsletter_signup
        db.session.commit()
        return jsonify({
            'message': 'Customer updated',
            'customer': customer.to_dict()
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

@app.route('/customers/<customer_id>', methods=['DELETE'])
def delete_customer(customer_id):
    try:
        customer = Customer.query.get_or_404(customer_id)
        # Check for existing reservations
        reservations = Reservation.query.filter_by(customer_id=customer_id).count()
        if reservations > 0:
            return jsonify({'error': 'Cannot delete customer with active reservations'}), 400
        db.session.delete(customer)
        db.session.commit()
        return jsonify({'message': 'Customer deleted'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

# Reservation CRUD
@app.route('/reservations', methods=['GET'])
def get_all_reservations():
    try:
        reservations = Reservation.query.all()
        return jsonify([reservation.to_dict() for reservation in reservations])
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/reserve', methods=['POST'])
def create_reservation():
    data = request.get_json()
    customer_id = data.get('customer_id')
    time_slot = data.get('time_slot')

    if not customer_id or not time_slot:
        return jsonify({'error': 'Customer ID and time slot are required'}), 400

    try:
        time_slot = datetime.fromisoformat(time_slot)
        # Verify customer exists
        customer = Customer.query.get_or_404(customer_id)
        # Check available tables (1–30)
        reserved_tables = db.session.query(Reservation.table_number).filter_by(time_slot=time_slot).all()
        reserved_tables = {t.table_number for t in reserved_tables}
        available_tables = set(range(1, 31)) - reserved_tables

        if not available_tables:
            return jsonify({'error': 'No tables available for this time slot'}), 400

        table_number = random.choice(list(available_tables))
        reservation = Reservation(
            customer_id=customer_id,
            time_slot=time_slot,
            table_number=table_number
        )
        db.session.add(reservation)
        db.session.commit()
        return jsonify({
            'message': 'Reservation successful',
            'reservation': reservation.to_dict()
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

@app.route('/reservations/<customer_id>', methods=['GET'])
def get_reservations(customer_id):
    try:
        # Verify customer exists
        Customer.query.get_or_404(customer_id)
        reservations = Reservation.query.filter_by(customer_id=customer_id).all()
        return jsonify([r.to_dict() for r in reservations])
    except Exception as e:
        return jsonify({'error': str(e)}), 404

@app.route('/reservation/<reservation_id>', methods=['GET'])
def get_reservation(reservation_id):
    try:
        reservation = Reservation.query.get_or_404(reservation_id)
        return jsonify(reservation.to_dict())
    except Exception as e:
        return jsonify({'error': str(e)}), 404

@app.route('/reservation/<reservation_id>', methods=['PUT'])
def update_reservation(reservation_id):
    data = request.get_json()
    time_slot = data.get('time_slot')

    if not time_slot:
        return jsonify({'error': 'Time slot is required'}), 400

    try:
        reservation = Reservation.query.get_or_404(reservation_id)
        new_time_slot = datetime.fromisoformat(time_slot)
        # Check available tables for new time slot
        reserved_tables = db.session.query(Reservation.table_number).filter_by(time_slot=new_time_slot).all()
        reserved_tables = {t.table_number for t in reserved_tables}
        available_tables = set(range(1, 31)) - reserved_tables

        if not available_tables:
            return jsonify({'error': 'No tables available for this time slot'}), 400

        reservation.time_slot = new_time_slot
        reservation.table_number = random.choice(list(available_tables))
        db.session.commit()
        return jsonify({
            'message': 'Reservation updated',
            'reservation': reservation.to_dict()
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

@app.route('/reservation/<reservation_id>', methods=['DELETE'])
def delete_reservation(reservation_id):
    try:
        reservation = Reservation.query.get_or_404(reservation_id)
        db.session.delete(reservation)
        db.session.commit()
        return jsonify({'message': 'Reservation deleted'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

@app.teardown_appcontext
def shutdown_db(exception=None):
    db.session.remove()

if __name__ == '__main__':
    app.run(debug=True)