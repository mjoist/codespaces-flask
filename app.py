from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///crm.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)


class Customer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120))
    phone = db.Column(db.String(50))
    notes = db.Column(db.Text)

    def __repr__(self) -> str:
        return f"<Customer {self.name}>"

@app.route("/")
def hello_world():
    return render_template("index.html", title="Hello")


@app.route("/customers")
def list_customers():
    customers = Customer.query.all()
    return render_template("customers.html", customers=customers, title="Customers")


@app.route("/customers/new")
def new_customer():
    return render_template("new_customer.html", title="New Customer")


@app.route("/customers/create", methods=["POST"])
def create_customer():
    name = request.form["name"]
    email = request.form.get("email")
    phone = request.form.get("phone")
    notes = request.form.get("notes")
    customer = Customer(name=name, email=email, phone=phone, notes=notes)
    db.session.add(customer)
    db.session.commit()
    return redirect(url_for("list_customers"))


with app.app_context():
    db.create_all()
