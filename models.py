from flask_sqlalchemy import SQLAlchemy
import uuid
from datetime import datetime

db = SQLAlchemy()

class Customer(db.Model):
    __tablename__ = 'customers'
    id = db.Column(db.String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone_number = db.Column(db.String(20))
    newsletter_signup = db.Column(db.Boolean, default=False)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'phone_number': self.phone_number,
            'newsletter_signup': self.newsletter_signup
        }

class Reservation(db.Model):
    __tablename__ = 'reservations'
    id = db.Column(db.String, primary_key=True, default=lambda: str(uuid.uuid4()))
    customer_id = db.Column(db.String, db.ForeignKey('customers.id'), nullable=False)
    time_slot = db.Column(db.DateTime, nullable=False)
    table_number = db.Column(db.Integer, nullable=False)
    customer = db.relationship('Customer', backref=db.backref('reservations', lazy=True))

    def to_dict(self):
        return {
            'id': self.id,
            'customer_id': self.customer_id,
            'time_slot': self.time_slot.isoformat(),
            'table_number': self.table_number
        }