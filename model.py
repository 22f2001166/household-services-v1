from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()


# -------------------- User Model -------------------- #
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    Email = db.Column(db.String(80), unique=True, nullable=False)
    Name = db.Column(db.String(80), nullable=False)
    Username = db.Column(db.String(80), nullable=False, unique=True)
    Password = db.Column(db.String(120), nullable=False)
    Role = db.Column(
        db.String(80), nullable=False
    )  # 'admin', 'customer', 'professional'
    flagged = db.Column(db.Boolean, nullable=False, default=False)

    customer = db.relationship(
        "Customer", backref="user", uselist=False, cascade="all, delete-orphan"
    )
    professional = db.relationship(
        "ServiceProfessional",
        backref="user",
        uselist=False,
        cascade="all, delete-orphan",
    )


# -------------------- Customer Model -------------------- #
class Customer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.String, db.ForeignKey("user.id", ondelete="CASCADE"), nullable=False
    )
    name = db.Column(db.String(100), nullable=True)
    service_requests = db.relationship(
        "ServiceRequest", backref="customer", lazy=True, cascade="all, delete-orphan"
    )


# -------------------- Service Professional Model -------------------- #
class ServiceProfessional(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("user.id", ondelete="CASCADE"), nullable=False
    )
    ServiceType = db.Column(
        db.String(80), nullable=False
    )  # Type of service (e.g., plumbing, cleaning)
    Experience = db.Column(db.Integer, nullable=False)  # Number of years of experience
    Document = db.Column(
        db.String(120), nullable=True
    )  # Field to store document filename

    services = db.relationship(
        "Service", backref="professional", lazy=True, cascade="all, delete-orphan"
    )
    service_requests = db.relationship(
        "ServiceRequest",
        backref="professional",
        lazy=True,
        cascade="all, delete-orphan",
    )


# -------------------- Service Model -------------------- #
class Service(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    professional_id = db.Column(
        db.Integer,
        db.ForeignKey("service_professional.id", ondelete="CASCADE"),
        nullable=True,
    )
    name = db.Column(db.String(100), nullable=False)  # Name of the service
    description = db.Column(db.Text, nullable=True)  # Service description
    price = db.Column(db.Float, nullable=False)  # Service price
    availability = db.Column(
        db.Boolean, nullable=False, default=True
    )  # Is the service currently available
    category = db.Column(
        db.String(80), nullable=True
    )  # Service category (e.g., home repair, cleaning)

    service_requests = db.relationship(
        "ServiceRequest", backref="service", lazy=True, cascade="all, delete-orphan"
    )


# -------------------- Service Request Model -------------------- #
class ServiceRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(
        db.Integer, db.ForeignKey("customer.id", ondelete="CASCADE"), nullable=False
    )
    service_id = db.Column(
        db.Integer, db.ForeignKey("service.id", ondelete="CASCADE"), nullable=False
    )
    professional_id = db.Column(
        db.Integer,
        db.ForeignKey("service_professional.id", ondelete="SET NULL"),
        nullable=True,
    )
    rating = db.Column(db.Integer)  # Rating between 1 and 5

    request_date = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(
        db.String(10), nullable=False, default="Pending"
    )  # 'Pending', 'Accepted', 'Completed'
    details = db.Column(
        db.Text, nullable=True
    )  # Additional details or requests by the customer
    completion_date = db.Column(db.DateTime, nullable=True)
    flagged = db.Column(db.Boolean, nullable=False, default=False)
