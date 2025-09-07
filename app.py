from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_restx import Api, Resource, fields
from models import db, Customer, Reservation
from datetime import datetime
import random

app = Flask(__name__)
app.config.from_object('config.Config')
CORS(app, resources={r"/*": {"origins": "*"}})  # Allow Streamlit

# Initialize Flask-RESTX
api = Api(
    app,
    title="Café Fausse Reservation API",
    description="API for managing customers and reservations at Café Fausse",
    doc="/docs"  # Swagger UI at /docs
)

# Initialize SQLAlchemy
db.init_app(app)

# Create tables
with app.app_context():
    db.create_all()

# Define namespaces
customer_ns = api.namespace('customers', description='Customer operations')
reservation_ns = api.namespace('reservations', description='Reservation operations')

# Define models for Swagger documentation
customer_model = customer_ns.model('Customer', {
    'id': fields.String(readonly=True, description='Customer UUID'),
    'name': fields.String(required=True, description='Customer name'),
    'email': fields.String(required=True, description='Customer email'),
    'phone_number': fields.String(description='Customer phone number'),
    'newsletter_signup': fields.Boolean(description='Newsletter subscription status')
})

reservation_model = reservation_ns.model('Reservation', {
    'id': fields.String(readonly=True, description='Reservation UUID'),
    'customer_id': fields.String(required=True, description='Customer UUID'),
    'time_slot': fields.String(required=True, description='Reservation time (ISO format, e.g., 2025-09-10T18:00:00)'),
    'table_number': fields.Integer(readonly=True, description='Assigned table number (1–30)')
})

# Customer CRUD
@customer_ns.route('')
class CustomerList(Resource):
    @customer_ns.doc('get_all_customers')
    @customer_ns.marshal_list_with(customer_model)
    def get(self):
        """Retrieve all customers"""
        try:
            customers = Customer.query.all()
            return [customer.to_dict() for customer in customers]
        except Exception as e:
            api.abort(400, str(e))

    @customer_ns.doc('create_customer')
    @customer_ns.expect(customer_model)
    @customer_ns.marshal_with(customer_model, code=201)
    def post(self):
        """Create a new customer"""
        data = request.get_json()
        name = data.get('name')
        email = data.get('email')
        phone_number = data.get('phone_number')
        newsletter_signup = data.get('newsletter_signup', False)

        if not name or not email:
            api.abort(400, 'Name and email are required')

        try:
            customer = Customer(
                name=name,
                email=email,
                phone_number=phone_number,
                newsletter_signup=newsletter_signup
            )
            db.session.add(customer)
            db.session.commit()
            return customer.to_dict(), 201
        except Exception as e:
            db.session.rollback()
            api.abort(400, str(e))

@customer_ns.route('/<string:customer_id>')
class CustomerResource(Resource):
    @customer_ns.doc('get_customer')
    @customer_ns.marshal_with(customer_model)
    def get(self, customer_id):
        """Retrieve a customer by ID"""
        try:
            customer = Customer.query.get_or_404(customer_id)
            return customer.to_dict()
        except Exception as e:
            api.abort(404, str(e))

    @customer_ns.doc('update_customer')
    @customer_ns.expect(customer_model)
    @customer_ns.marshal_with(customer_model)
    def put(self, customer_id):
        """Update a customer by ID"""
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
            return customer.to_dict()
        except Exception as e:
            db.session.rollback()
            api.abort(400, str(e))

    @customer_ns.doc('delete_customer')
    def delete(self, customer_id):
        """Delete a customer by ID"""
        try:
            customer = Customer.query.get_or_404(customer_id)
            reservations = Reservation.query.filter_by(customer_id=customer_id).count()
            if reservations > 0:
                api.abort(400, 'Cannot delete customer with active reservations')
            db.session.delete(customer)
            db.session.commit()
            return {'message': 'Customer deleted'}
        except Exception as e:
            db.session.rollback()
            api.abort(400, str(e))

# Reservation CRUD
@reservation_ns.route('')
class ReservationList(Resource):
    @reservation_ns.doc('get_all_reservations')
    @reservation_ns.marshal_list_with(reservation_model)
    def get(self):
        """Retrieve all reservations"""
        try:
            reservations = Reservation.query.all()
            return [reservation.to_dict() for reservation in reservations]
        except Exception as e:
            api.abort(400, str(e))

@reservation_ns.route('/reserve')
class ReservationCreate(Resource):
    @reservation_ns.doc('create_reservation')
    @reservation_ns.expect(reservation_model)
    @reservation_ns.marshal_with(reservation_model, code=201)
    def post(self):
        """Create a new reservation"""
        data = request.get_json()
        customer_id = data.get('customer_id')
        time_slot = data.get('time_slot')

        if not customer_id or not time_slot:
            api.abort(400, 'Customer ID and time slot are required')

        try:
            time_slot = datetime.fromisoformat(time_slot)
            customer = Customer.query.get_or_404(customer_id)
            reserved_tables = db.session.query(Reservation.table_number).filter_by(time_slot=time_slot).all()
            reserved_tables = {t.table_number for t in reserved_tables}
            available_tables = set(range(1, 31)) - reserved_tables

            if not available_tables:
                api.abort(400, 'No tables available for this time slot')

            table_number = random.choice(list(available_tables))
            reservation = Reservation(
                customer_id=customer_id,
                time_slot=time_slot,
                table_number=table_number
            )
            db.session.add(reservation)
            db.session.commit()
            return reservation.to_dict(), 201
        except Exception as e:
            db.session.rollback()
            api.abort(400, str(e))

@reservation_ns.route('/<string:customer_id>')
class CustomerReservations(Resource):
    @reservation_ns.doc('get_reservations_by_customer')
    @reservation_ns.marshal_list_with(reservation_model)
    def get(self, customer_id):
        """Retrieve all reservations for a customer"""
        try:
            Customer.query.get_or_404(customer_id)
            reservations = Reservation.query.filter_by(customer_id=customer_id).all()
            return [r.to_dict() for r in reservations]
        except Exception as e:
            api.abort(404, str(e))

@reservation_ns.route('/reservation/<string:reservation_id>')
class ReservationResource(Resource):
    @reservation_ns.doc('get_reservation')
    @reservation_ns.marshal_with(reservation_model)
    def get(self, reservation_id):
        """Retrieve a reservation by ID"""
        try:
            reservation = Reservation.query.get_or_404(reservation_id)
            return reservation.to_dict()
        except Exception as e:
            api.abort(404, str(e))

    @reservation_ns.doc('update_reservation')
    @reservation_ns.expect(reservation_model)
    @reservation_ns.marshal_with(reservation_model)
    def put(self, reservation_id):
        """Update a reservation by ID"""
        data = request.get_json()
        time_slot = data.get('time_slot')

        if not time_slot:
            api.abort(400, 'Time slot is required')

        try:
            reservation = Reservation.query.get_or_404(reservation_id)
            new_time_slot = datetime.fromisoformat(time_slot)
            reserved_tables = db.session.query(Reservation.table_number).filter_by(time_slot=new_time_slot).all()
            reserved_tables = {t.table_number for t in reserved_tables}
            available_tables = set(range(1, 31)) - reserved_tables

            if not available_tables:
                api.abort(400, 'No tables available for this time slot')

            reservation.time_slot = new_time_slot
            reservation.table_number = random.choice(list(available_tables))
            db.session.commit()
            return reservation.to_dict()
        except Exception as e:
            db.session.rollback()
            api.abort(400, str(e))

    @reservation_ns.doc('delete_reservation')
    def delete(self, reservation_id):
        """Delete a reservation by ID"""
        try:
            reservation = Reservation.query.get_or_404(reservation_id)
            db.session.delete(reservation)
            db.session.commit()
            return {'message': 'Reservation deleted'}
        except Exception as e:
            db.session.rollback()
            api.abort(400, str(e))

@app.teardown_appcontext
def shutdown_db(exception=None):
    db.session.remove()

if __name__ == '__main__':
    app.run(debug=True)