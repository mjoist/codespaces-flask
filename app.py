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


class Lead(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120))
    phone = db.Column(db.String(50))
    status = db.Column(db.String(50))


class Account(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    industry = db.Column(db.String(120))


class Contact(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120))
    phone = db.Column(db.String(50))
    account_id = db.Column(db.Integer, db.ForeignKey("account.id"))
    account = db.relationship("Account", backref=db.backref("contacts", lazy=True))


class Deal(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    amount = db.Column(db.Float)
    stage = db.Column(db.String(50))
    account_id = db.Column(db.Integer, db.ForeignKey("account.id"))
    account = db.relationship("Account", backref=db.backref("deals", lazy=True))


class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    price = db.Column(db.Float)


class Pricebook(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)


class PriceBookEntry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey("product.id"))
    pricebook_id = db.Column(db.Integer, db.ForeignKey("pricebook.id"))
    unit_price = db.Column(db.Float)
    product = db.relationship("Product")
    pricebook = db.relationship("Pricebook")


class Quote(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    deal_id = db.Column(db.Integer, db.ForeignKey("deal.id"))
    total = db.Column(db.Float)
    deal = db.relationship("Deal")


class QuoteLineItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    quote_id = db.Column(db.Integer, db.ForeignKey("quote.id"))
    product_id = db.Column(db.Integer, db.ForeignKey("product.id"))
    quantity = db.Column(db.Integer)
    price = db.Column(db.Float)
    quote = db.relationship("Quote", backref=db.backref("line_items", lazy=True))
    product = db.relationship("Product")

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


@app.route("/leads")
def list_leads():
    leads = Lead.query.all()
    return render_template("leads.html", leads=leads, title="Leads")


@app.route("/leads/new")
def new_lead():
    return render_template("new_lead.html", title="New Lead")


@app.route("/leads/create", methods=["POST"])
def create_lead():
    lead = Lead(
        name=request.form["name"],
        email=request.form.get("email"),
        phone=request.form.get("phone"),
        status=request.form.get("status"),
    )
    db.session.add(lead)
    db.session.commit()
    return redirect(url_for("list_leads"))


@app.route("/accounts")
def list_accounts():
    accounts = Account.query.all()
    return render_template("accounts.html", accounts=accounts, title="Accounts")


@app.route("/accounts/new")
def new_account():
    return render_template("new_account.html", title="New Account")


@app.route("/accounts/create", methods=["POST"])
def create_account():
    account = Account(
        name=request.form["name"],
        industry=request.form.get("industry"),
    )
    db.session.add(account)
    db.session.commit()
    return redirect(url_for("list_accounts"))


@app.route("/contacts")
def list_contacts():
    contacts = Contact.query.all()
    return render_template("contacts.html", contacts=contacts, title="Contacts")


@app.route("/contacts/new")
def new_contact():
    accounts = Account.query.all()
    return render_template("new_contact.html", accounts=accounts, title="New Contact")


@app.route("/contacts/create", methods=["POST"])
def create_contact():
    contact = Contact(
        name=request.form["name"],
        email=request.form.get("email"),
        phone=request.form.get("phone"),
        account_id=request.form.get("account_id") or None,
    )
    db.session.add(contact)
    db.session.commit()
    return redirect(url_for("list_contacts"))


@app.route("/deals")
def list_deals():
    deals = Deal.query.all()
    return render_template("deals.html", deals=deals, title="Deals")


@app.route("/deals/new")
def new_deal():
    accounts = Account.query.all()
    return render_template("new_deal.html", accounts=accounts, title="New Deal")


@app.route("/deals/create", methods=["POST"])
def create_deal():
    deal = Deal(
        name=request.form["name"],
        amount=request.form.get("amount"),
        stage=request.form.get("stage"),
        account_id=request.form.get("account_id") or None,
    )
    db.session.add(deal)
    db.session.commit()
    return redirect(url_for("list_deals"))


@app.route("/products")
def list_products():
    products = Product.query.all()
    return render_template("products.html", products=products, title="Products")


@app.route("/products/new")
def new_product():
    return render_template("new_product.html", title="New Product")


@app.route("/products/create", methods=["POST"])
def create_product():
    product = Product(
        name=request.form["name"],
        price=request.form.get("price"),
    )
    db.session.add(product)
    db.session.commit()
    return redirect(url_for("list_products"))


@app.route("/pricebooks")
def list_pricebooks():
    pricebooks = Pricebook.query.all()
    return render_template("pricebooks.html", pricebooks=pricebooks, title="Pricebooks")


@app.route("/pricebooks/new")
def new_pricebook():
    return render_template("new_pricebook.html", title="New Pricebook")


@app.route("/pricebooks/create", methods=["POST"])
def create_pricebook():
    pricebook = Pricebook(name=request.form["name"])
    db.session.add(pricebook)
    db.session.commit()
    return redirect(url_for("list_pricebooks"))


@app.route("/pricebook_entries")
def list_pricebook_entries():
    entries = PriceBookEntry.query.all()
    return render_template(
        "pricebook_entries.html", entries=entries, title="Price Book Entries"
    )


@app.route("/pricebook_entries/new")
def new_pricebook_entry():
    products = Product.query.all()
    pricebooks = Pricebook.query.all()
    return render_template(
        "new_pricebook_entry.html",
        products=products,
        pricebooks=pricebooks,
        title="New Price Book Entry",
    )


@app.route("/pricebook_entries/create", methods=["POST"])
def create_pricebook_entry():
    entry = PriceBookEntry(
        product_id=request.form.get("product_id"),
        pricebook_id=request.form.get("pricebook_id"),
        unit_price=request.form.get("unit_price"),
    )
    db.session.add(entry)
    db.session.commit()
    return redirect(url_for("list_pricebook_entries"))


@app.route("/quotes")
def list_quotes():
    quotes = Quote.query.all()
    return render_template("quotes.html", quotes=quotes, title="Quotes")


@app.route("/quotes/new")
def new_quote():
    deals = Deal.query.all()
    return render_template("new_quote.html", deals=deals, title="New Quote")


@app.route("/quotes/create", methods=["POST"])
def create_quote():
    quote = Quote(
        deal_id=request.form.get("deal_id"),
        total=request.form.get("total"),
    )
    db.session.add(quote)
    db.session.commit()
    return redirect(url_for("list_quotes"))


@app.route("/quote_line_items")
def list_quote_line_items():
    items = QuoteLineItem.query.all()
    return render_template("quote_line_items.html", items=items, title="Quote Line Items")


@app.route("/quote_line_items/new")
def new_quote_line_item():
    quotes = Quote.query.all()
    products = Product.query.all()
    return render_template(
        "new_quote_line_item.html",
        quotes=quotes,
        products=products,
        title="New Quote Line Item",
    )


@app.route("/quote_line_items/create", methods=["POST"])
def create_quote_line_item():
    item = QuoteLineItem(
        quote_id=request.form.get("quote_id"),
        product_id=request.form.get("product_id"),
        quantity=request.form.get("quantity"),
        price=request.form.get("price"),
    )
    db.session.add(item)
    db.session.commit()
    return redirect(url_for("list_quote_line_items"))


with app.app_context():
    db.create_all()
