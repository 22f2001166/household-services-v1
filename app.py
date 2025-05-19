# ---------------- Imports ----------------

from flask import (
    Flask,
    render_template,
    redirect,
    url_for,
    request,
    session,
    flash,
    send_from_directory,
)
from werkzeug.utils import secure_filename

from model import (
    db,
    User,
    Customer,
    ServiceProfessional,
    Service,
    ServiceRequest,
)
from datetime import datetime
from sqlalchemy import union, or_

import os
import matplotlib
import io
import matplotlib.pyplot as plt
from flask import Response

# ---------------- SQL Connection ----------------

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///household_services.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SECRET_KEY"] = "supersecretkey"

db.init_app(app)
with app.app_context():
    db.create_all()


# ---------------- Home Page ----------------


@app.route("/")
def index():
    return render_template("index.html")


# ---------------- User Login ----------------


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        # Check if the credentials are for the hardcoded admin
        if username == "admin" and password == "123":
            session["user_id"] = "admin"  # Optionally set an identifier for the admin
            session["role"] = "admin"
            return redirect(url_for("admin_dashboard"))

        # Check in the database for other users (customers, professionals, etc.)
        user = User.query.filter_by(Username=username, Password=password).first()

        if user and not user.flagged:
            session["user_id"] = user.id
            session["role"] = user.Role

            if user.Role == "customer":
                return redirect(url_for("customer_dashboard"))
            elif user.Role == "professional":
                return redirect(url_for("professional_dashboard"))
            elif user.Role == "admin":
                return redirect(url_for("admin_dashboard"))
        else:
            return render_template(
                "login.html", error="Invalid credentials or account flagged."
            )

    return render_template("login.html")


# ---------------- Logout ----------------


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))


# ---------------- Customer Signup ----------------


@app.route("/customer/signup", methods=["GET", "POST"])
def customer_signup():
    if request.method == "POST":
        email = request.form["email"]
        name = request.form["name"]
        username = request.form["username"]
        password = request.form["password"]

        if (
            User.query.filter_by(Email=email).first()
            or User.query.filter_by(Username=username).first()
        ):
            return render_template(
                "customer_signup.html", error="Email or Username already exists."
            )

        user = User(
            Email=email,
            Name=name,
            Username=username,
            Password=password,
            Role="customer",
        )
        db.session.add(user)
        db.session.commit()

        customer = Customer(user_id=user.id, name=name)
        db.session.add(customer)
        db.session.commit()

        return redirect(url_for("thank_you"))

    return render_template("customer_signup.html")


# ---------------- Customer Edit Profile ----------------


@app.route("/customer/edit_profile", methods=["GET", "POST"])
def edit_customer_profile():
    customer = Customer.query.filter_by(user_id=session["user_id"]).first()

    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        username = request.form["username"]
        password = request.form["password"]

        # Update customer and user details
        user = User.query.get(customer.user_id)
        user.Name = name
        user.Email = email
        user.Username = username
        user.Password = password

        db.session.commit()
        return redirect(url_for("customer_dashboard"))

    return render_template(
        "edit_customer_profile.html", customer=customer, user=customer.user
    )


# ---------------- Service Professional Signup ----------------


UPLOAD_FOLDER = os.path.join(app.root_path, "uploads", "documents")
ALLOWED_EXTENSIONS = {"pdf"}

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER


# Utility function to check allowed file types
def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route("/uploads/documents/<filename>")
def serve_file(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)


@app.route("/professional/signup", methods=["GET", "POST"])
def professional_signup():
    service_categories = Service.query.with_entities(Service.category).distinct().all()

    if request.method == "POST":
        email = request.form["email"]
        name = request.form["name"]
        username = request.form["username"]
        password = request.form["password"]
        service_type = request.form["service_type"]
        experience = request.form["experience"]
        file = request.files["work_document"]

        # Check if file is a valid PDF
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            # Save the file to the upload directory
            file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))
        else:
            return render_template(
                "professional_signup.html",
                error="Invalid file type. Only PDF files are allowed.",
                service_categories=service_categories,
            )

        # Check for existing users with the same email or username
        if (
            User.query.filter_by(Email=email).first()
            or User.query.filter_by(Username=username).first()
        ):
            return render_template(
                "professional_signup.html",
                error="Email or Username already exists.",
                service_categories=service_categories,
            )

        # Create a new User and ServiceProfessional entry
        user = User(
            Email=email,
            Name=name,
            Username=username,
            Password=password,
            Role="professional",
        )
        db.session.add(user)
        db.session.commit()

        professional = ServiceProfessional(
            user_id=user.id,
            ServiceType=service_type,
            Experience=experience,
            Document=filename,  # Save the filename to the database
        )
        db.session.add(professional)
        db.session.commit()

        return redirect(url_for("thank_you"))

    return render_template(
        "professional_signup.html", service_categories=service_categories
    )


# ---------------- Service Professional Edit Profile ----------------


@app.route("/professional/edit_profile", methods=["GET", "POST"])
def edit_professional_profile():
    professional = ServiceProfessional.query.filter_by(
        user_id=session["user_id"]
    ).first()

    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        username = request.form["username"]
        password = request.form["password"]

        user = User.query.get(professional.user_id)
        user.Name = name
        user.Email = email
        user.Username = username
        user.Password = password

        db.session.commit()
        return redirect(url_for("professional_dashboard"))

    return render_template(
        "edit_professional_profile.html",
        professional=professional,
        user=professional.user,
    )


# ---------------- CUSTOMER DASHBOARD ----------------


@app.route("/customer/dashboard")
def customer_dashboard():
    if "role" in session and session["role"] == "customer":
        customer = Customer.query.filter_by(user_id=session["user_id"]).first()
        search_query = request.args.get("search")

        if search_query:
            service = Service.query.filter(
                Service.availability == True,
                Service.name.ilike(f"%{search_query}%"),  # Case-insensitive search
            ).all()
        else:
            service = Service.query.filter_by(availability=True).all()

        accepted_services = ServiceRequest.query.filter_by(
            customer_id=customer.id,  # status="Accepted"
        ).all()

        return render_template(
            "customer_dashboard.html",
            service=service,
            accepted_services=accepted_services,
        )
    return redirect(url_for("login"))


# ---------------- Request a Service (Customer) ----------------


@app.route("/customer/request_service/<int:service_id>", methods=["GET", "POST"])
def request_service(service_id):
    if "role" in session and session["role"] == "customer":
        customer = Customer.query.filter_by(user_id=session["user_id"]).first()
        service = Service.query.get_or_404(service_id)

        # Create a new service request
        service_request = ServiceRequest(
            service_id=service.id,
            customer_id=customer.id,
            status="requested",  # Initial status set to 'requested'
            request_date=datetime.utcnow(),  # Store the request date
        )

        db.session.add(service_request)
        db.session.commit()

        # flash(f"Service '{service.name}' has been requested successfully!", "success")
        # return redirect(url_for("customer_dashboard"))
        return render_template("request_service.html", service_name=service.name)

    return redirect(url_for("login"))


# ---------------- Update a Request (Customer) ----------------


@app.route("/update_request/<int:request_id>", methods=["POST"])
def update_request(request_id):
    service_request = ServiceRequest.query.get_or_404(request_id)

    if "role" in session and session["role"] == "customer":
        status = request.form.get("status")
        rating = request.form.get("rating")

        # Update status and rating if provided
        if status:
            service_request.status = status
        if rating:
            service_request.rating = int(rating)

        db.session.commit()
        return redirect(url_for("customer_dashboard"))

    return redirect(url_for("login"))


# ---------------- Delete a Request (Customer) ----------------


@app.route("/customer/delete_request/<int:request_id>", methods=["POST"])
def delete_request(request_id):
    # Check if the user is logged in and is a customer
    if "role" in session and session["role"] == "customer":
        # Find the service request by ID and ensure the customer is the owner
        service_request = ServiceRequest.query.filter_by(
            id=request_id, customer_id=session["user_id"]
        ).first()

        if service_request:
            db.session.delete(service_request)
            db.session.commit()
            flash("Request deleted successfully.", "success")
        else:
            flash("Request not found or you are not authorized to delete it.", "danger")

        return redirect(url_for("customer_dashboard"))
    else:
        return redirect(url_for("login"))


# ---------------- PROFESSIONAL DASHBOARD ----------------


@app.route("/professional/dashboard", methods=["GET", "POST"])
def professional_dashboard():
    if "role" in session and session["role"] == "professional":
        professional = ServiceProfessional.query.filter_by(
            user_id=session["user_id"]
        ).first()
        if professional:
            # Get the search query from the request
            search_date = request.args.get("search_date")

            # Filter eligible service requests based on the search date
            eligible_requests_query = ServiceRequest.query.join(Service).filter(
                Service.category == professional.ServiceType,
                ServiceRequest.status == "requested",
            )

            # If search_date is provided, filter by request_date
            if search_date:
                try:
                    # Convert search_date string to datetime object
                    search_date_obj = datetime.strptime(search_date, "%Y-%m-%d")
                    eligible_requests_query = eligible_requests_query.filter(
                        db.func.date(ServiceRequest.request_date)
                        == search_date_obj.date()
                    )
                except ValueError:
                    # Handle invalid date format
                    flash("Invalid date format. Please enter a valid date.")

            eligible_requests = eligible_requests_query.all()

            # Fetch accepted requests (no need for search filter here)
            accepted_requests = (
                ServiceRequest.query.join(Service)
                .filter(
                    ServiceRequest.professional_id == professional.id,
                    or_(
                        ServiceRequest.status == "Accepted",
                        ServiceRequest.status == "completed",
                    ),
                )
                .all()
            )

        return render_template(
            "professional_dashboard.html",
            service_requests=eligible_requests,
            accepted_requests=accepted_requests,
        )
    return redirect(url_for("login"))


# ---------------- Accept a Service (Professional) ----------------


@app.route("/accept_service/<int:request_id>", methods=["POST"])
def accept_service(request_id):
    service_request = ServiceRequest.query.get_or_404(request_id)
    professional = ServiceProfessional.query.filter_by(
        user_id=session["user_id"]
    ).first()

    if service_request.status == "requested" and professional:
        service = Service.query.get(service_request.service_id)
        if professional.ServiceType == service.category:
            service_request.professional_id = professional.id

            service_request.status = "Accepted"
        try:
            db.session.commit()
            flash("Service request accepted successfully.", "success")

        except Exception as e:
            db.session.rollback()
            flash(f"Error accepting service: {str(e)}", "danger")

    return redirect(url_for("professional_dashboard"))


# ---------------- ADMIN DASHBOARD ----------------


@app.route("/admin/dashboard")
def admin_dashboard():
    if "role" in session and session["role"] == "admin":

        search_query = request.args.get("searchc")

        if search_query:
            # Filter customers by name or email, case-insensitive search
            customers = (
                Customer.query.join(User)
                .filter(
                    (User.Name.ilike(f"%{search_query}%"))
                    | (User.Email.ilike(f"%{search_query}%"))
                )
                .all()
            )
        else:
            # If no search query, display all customers
            customers = Customer.query.all()

        search_query = request.args.get("searchp")

        if search_query:
            # Filter professionals by name or email, case-insensitive search
            professionals = (
                ServiceProfessional.query.join(User)
                .filter(
                    (User.Name.ilike(f"%{search_query}%"))
                    | (User.Email.ilike(f"%{search_query}%"))
                )
                .all()
            )
        else:
            # If no search query, display all professionals
            professionals = ServiceProfessional.query.all()

        service_requests = (
            ServiceRequest.query.join(Service)
            .join(
                ServiceProfessional,
                ServiceProfessional.id == ServiceRequest.professional_id,
            )
            .join(Customer, Customer.id == ServiceRequest.customer_id)
            .all()
        )

        unaccepted_requests = ServiceRequest.query.filter_by(status="requested").all()

        status_counts = (
            db.session.query(ServiceRequest.status, db.func.count(ServiceRequest.id))
            .group_by(ServiceRequest.status)
            .all()
        )

        service = Service.query.all()

        return render_template(
            "admin_dashboard.html",
            customers=customers,
            professionals=professionals,
            service=service,
            service_requests=service_requests,
            unaccepted_requests=unaccepted_requests,
            status_counts=status_counts,
        )
    return redirect(url_for("login"))


# ---------------- Create a New Service (Admin) ----------------


@app.route("/admin/add_service", methods=["GET", "POST"])
def add_service():
    if (
        "role" in session and session["role"] == "admin"
    ):  # Only allow admin to add services
        if request.method == "POST":
            name = request.form["name"]
            description = request.form["description"]
            price = request.form["price"]
            category = request.form["category"]

            service = Service(
                name=name,
                description=description,
                price=price,
                category=category,
                availability=True,  # Set the service as available
            )
            db.session.add(service)
            db.session.commit()

            return redirect(
                url_for("admin_dashboard")
            )  # Redirect back to admin dashboard

        return render_template("add_service.html")  # Render form to add a new service
    return redirect(url_for("login"))


# ---------------- Thank You Page ----------------


@app.route("/thank_you")
def thank_you():
    return render_template("thank_you.html")


# ---------------- User Management (Admin)----------------


@app.route("/flag_user/<int:user_id>", methods=["POST"])
def flag_user(user_id):
    user = User.query.get_or_404(user_id)
    user.flagged = True
    db.session.commit()
    return redirect(url_for("admin_dashboard"))


@app.route("/unflag_user/<int:user_id>", methods=["POST"])
def unflag_user(user_id):
    user = User.query.get_or_404(user_id)
    user.flagged = False
    db.session.commit()
    return redirect(url_for("admin_dashboard"))


@app.route("/delete_user/<int:user_id>", methods=["POST"])
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    try:
        db.session.delete(user)
        db.session.commit()
        return redirect(url_for("admin_dashboard"))
    except Exception as e:
        db.session.rollback()
        print(f"Error deleting user: {e}")
        return redirect(url_for("admin_dashboard"))


# ---------------- Delete Service (Admin)----------------


@app.route("/admin/delete_service/<int:service_id>", methods=["POST"])
def delete_service(service_id):
    service = Service.query.get(service_id)

    if service:
        try:
            db.session.delete(service)
            db.session.commit()
            flash("Service deleted successfully.", "success")
        except Exception as e:
            db.session.rollback()
            flash(f"Error deleting service: {str(e)}", "danger")
    else:
        flash("Service not found.", "danger")

    return redirect(url_for("admin_dashboard"))


# ---------------- Availability of Service (Admin) ----------------
@app.route("/available_service/<int:service_id>", methods=["POST"])
def available_service(service_id):
    # Fetch the service based on the service_id
    service = Service.query.get_or_404(service_id)

    # Update the service availability to True
    service.availability = True

    # Commit the changes to the database
    db.session.commit()

    # Redirect back to the service management page or dashboard
    return redirect(url_for("admin_dashboard"))


@app.route("/unavailable_service/<int:service_id>", methods=["POST"])
def unavailable_service(service_id):
    # Fetch the service based on the service_id
    service = Service.query.get_or_404(service_id)

    # Update the service availability to False
    service.availability = False

    # Commit the changes to the database
    db.session.commit()

    # Redirect back to the service management page or dashboard
    return redirect(url_for("admin_dashboard"))


# ---------------- Service Request Summary ----------------
matplotlib.use("Agg")


@app.route("/admin/service_requests_summary.png")
def service_requests_summary():
    # Data for chart
    status_counts = (
        db.session.query(ServiceRequest.status, db.func.count(ServiceRequest.id))
        .group_by(ServiceRequest.status)
        .all()
    )

    # Extract labels (statuses) and values (counts)
    labels = [status for status, count in status_counts]
    values = [count for status, count in status_counts]

    # Plot using matplotlib
    fig, ax = plt.subplots()
    ax.bar(labels, values, color=["#1f77b4", "#ff7f0e", "#2ca02c"])
    ax.set_xlabel("Status")
    ax.set_ylabel("Number of Requests")
    ax.set_title("Summary of Service Requests by Status")

    # Save plot to a BytesIO object
    img = io.BytesIO()
    plt.savefig(img, format="png")
    img.seek(0)
    plt.close(fig)

    return Response(img.getvalue(), mimetype="image/png")


if __name__ == "__main__":
    app.run(debug=True)
