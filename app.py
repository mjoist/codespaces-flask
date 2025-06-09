from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///crm.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)


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
    email = db.Column(db.String(120))
    phone = db.Column(db.String(50))
    notes = db.Column(db.Text)


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


class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(255))
    due_date = db.Column(db.String(50))
    model = db.Column(db.String(50))
    record_id = db.Column(db.Integer)

@app.route("/")
def dashboard():
    counts = {
        "leads": Lead.query.count(),
        "accounts": Account.query.count(),
        "contacts": Contact.query.count(),
        "deals": Deal.query.count(),
        "products": Product.query.count(),
        "pricebooks": Pricebook.query.count(),
        "quotes": Quote.query.count(),
    }
    return render_template("dashboard.html", counts=counts, title="Dashboard")




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


@app.route("/leads/<int:lead_id>")
def show_lead(lead_id):
    lead = Lead.query.get_or_404(lead_id)
    tasks = Task.query.filter_by(model="leads", record_id=lead_id).all()
    return render_template(
        "lead_detail.html", lead=lead, tasks=tasks, title="Lead Detail"
    )


@app.route("/leads/<int:lead_id>/edit")
def edit_lead(lead_id):
    lead = Lead.query.get_or_404(lead_id)
    return render_template("edit_lead.html", lead=lead, title="Edit Lead")


@app.route("/leads/<int:lead_id>/update", methods=["POST"])
def update_lead(lead_id):
    lead = Lead.query.get_or_404(lead_id)
    lead.name = request.form["name"]
    lead.email = request.form.get("email")
    lead.phone = request.form.get("phone")
    lead.status = request.form.get("status")
    db.session.commit()
    return redirect(url_for("show_lead", lead_id=lead.id))


@app.route("/leads/<int:lead_id>/convert", methods=["POST"])
def convert_lead(lead_id):
    lead = Lead.query.get_or_404(lead_id)
    account = Account(
        name=lead.name,
        industry="",
        email=lead.email,
        phone=lead.phone,
        notes=None,
    )
    db.session.add(account)
    db.session.commit()
    contact = Contact(
        name=lead.name,
        email=lead.email,
        phone=lead.phone,
        account_id=account.id,
    )
    db.session.add(contact)
    db.session.delete(lead)
    db.session.commit()
    return redirect(url_for("show_account", account_id=account.id))


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
        email=request.form.get("email"),
        phone=request.form.get("phone"),
        notes=request.form.get("notes"),
    )
    db.session.add(account)
    db.session.commit()
    return redirect(url_for("list_accounts"))


@app.route("/accounts/<int:account_id>")
def show_account(account_id):
    account = Account.query.get_or_404(account_id)
    tasks = Task.query.filter_by(model="accounts", record_id=account_id).all()
    return render_template(
        "account_detail.html", account=account, tasks=tasks, title="Account Detail"
    )


@app.route("/accounts/<int:account_id>/edit")
def edit_account(account_id):
    account = Account.query.get_or_404(account_id)
    return render_template(
        "edit_account.html", account=account, title="Edit Account"
    )


@app.route("/accounts/<int:account_id>/update", methods=["POST"])
def update_account(account_id):
    account = Account.query.get_or_404(account_id)
    account.name = request.form["name"]
    account.industry = request.form.get("industry")
    account.email = request.form.get("email")
    account.phone = request.form.get("phone")
    account.notes = request.form.get("notes")
    db.session.commit()
    return redirect(url_for("show_account", account_id=account.id))


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


@app.route("/contacts/<int:contact_id>")
def show_contact(contact_id):
    contact = Contact.query.get_or_404(contact_id)
    tasks = Task.query.filter_by(model="contacts", record_id=contact_id).all()
    return render_template(
        "contact_detail.html", contact=contact, tasks=tasks, title="Contact Detail"
    )


@app.route("/contacts/<int:contact_id>/edit")
def edit_contact(contact_id):
    contact = Contact.query.get_or_404(contact_id)
    accounts = Account.query.all()
    return render_template(
        "edit_contact.html", contact=contact, accounts=accounts, title="Edit Contact"
    )


@app.route("/contacts/<int:contact_id>/update", methods=["POST"])
def update_contact(contact_id):
    contact = Contact.query.get_or_404(contact_id)
    contact.name = request.form["name"]
    contact.email = request.form.get("email")
    contact.phone = request.form.get("phone")
    contact.account_id = request.form.get("account_id") or None
    db.session.commit()
    return redirect(url_for("show_contact", contact_id=contact.id))


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


@app.route("/deals/<int:deal_id>")
def show_deal(deal_id):
    deal = Deal.query.get_or_404(deal_id)
    tasks = Task.query.filter_by(model="deals", record_id=deal_id).all()
    return render_template(
        "deal_detail.html", deal=deal, tasks=tasks, title="Deal Detail"
    )


@app.route("/deals/<int:deal_id>/edit")
def edit_deal(deal_id):
    deal = Deal.query.get_or_404(deal_id)
    accounts = Account.query.all()
    return render_template("edit_deal.html", deal=deal, accounts=accounts, title="Edit Deal")


@app.route("/deals/<int:deal_id>/update", methods=["POST"])
def update_deal(deal_id):
    deal = Deal.query.get_or_404(deal_id)
    deal.name = request.form["name"]
    deal.amount = request.form.get("amount")
    deal.stage = request.form.get("stage")
    deal.account_id = request.form.get("account_id") or None
    db.session.commit()
    return redirect(url_for("show_deal", deal_id=deal.id))


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


@app.route("/products/<int:product_id>")
def show_product(product_id):
    product = Product.query.get_or_404(product_id)
    tasks = Task.query.filter_by(model="products", record_id=product_id).all()
    return render_template(
        "product_detail.html", product=product, tasks=tasks, title="Product Detail"
    )


@app.route("/products/<int:product_id>/edit")
def edit_product(product_id):
    product = Product.query.get_or_404(product_id)
    return render_template(
        "edit_product.html", product=product, title="Edit Product"
    )


@app.route("/products/<int:product_id>/update", methods=["POST"])
def update_product(product_id):
    product = Product.query.get_or_404(product_id)
    product.name = request.form["name"]
    product.price = request.form.get("price")
    db.session.commit()
    return redirect(url_for("show_product", product_id=product.id))


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


@app.route("/pricebooks/<int:pricebook_id>")
def show_pricebook(pricebook_id):
    pricebook = Pricebook.query.get_or_404(pricebook_id)
    tasks = Task.query.filter_by(model="pricebooks", record_id=pricebook_id).all()
    return render_template(
        "pricebook_detail.html",
        pricebook=pricebook,
        tasks=tasks,
        title="Pricebook Detail",
    )


@app.route("/pricebooks/<int:pricebook_id>/edit")
def edit_pricebook(pricebook_id):
    pricebook = Pricebook.query.get_or_404(pricebook_id)
    return render_template(
        "edit_pricebook.html", pricebook=pricebook, title="Edit Pricebook"
    )


@app.route("/pricebooks/<int:pricebook_id>/update", methods=["POST"])
def update_pricebook(pricebook_id):
    pricebook = Pricebook.query.get_or_404(pricebook_id)
    pricebook.name = request.form["name"]
    db.session.commit()
    return redirect(url_for("show_pricebook", pricebook_id=pricebook.id))


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


@app.route("/pricebook_entries/<int:entry_id>")
def show_pricebook_entry(entry_id):
    entry = PriceBookEntry.query.get_or_404(entry_id)
    tasks = Task.query.filter_by(model="pricebook_entries", record_id=entry_id).all()
    return render_template(
        "pricebook_entry_detail.html",
        entry=entry,
        tasks=tasks,
        title="Price Book Entry Detail",
    )


@app.route("/pricebook_entries/<int:entry_id>/edit")
def edit_pricebook_entry(entry_id):
    entry = PriceBookEntry.query.get_or_404(entry_id)
    products = Product.query.all()
    pricebooks = Pricebook.query.all()
    return render_template(
        "edit_pricebook_entry.html",
        entry=entry,
        products=products,
        pricebooks=pricebooks,
        title="Edit Price Book Entry",
    )


@app.route("/pricebook_entries/<int:entry_id>/update", methods=["POST"])
def update_pricebook_entry(entry_id):
    entry = PriceBookEntry.query.get_or_404(entry_id)
    entry.product_id = request.form.get("product_id")
    entry.pricebook_id = request.form.get("pricebook_id")
    entry.unit_price = request.form.get("unit_price")
    db.session.commit()
    return redirect(url_for("show_pricebook_entry", entry_id=entry.id))


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


@app.route("/quotes/<int:quote_id>")
def show_quote(quote_id):
    quote = Quote.query.get_or_404(quote_id)
    tasks = Task.query.filter_by(model="quotes", record_id=quote_id).all()
    return render_template(
        "quote_detail.html", quote=quote, tasks=tasks, title="Quote Detail"
    )


@app.route("/quotes/<int:quote_id>/edit")
def edit_quote(quote_id):
    quote = Quote.query.get_or_404(quote_id)
    deals = Deal.query.all()
    return render_template("edit_quote.html", quote=quote, deals=deals, title="Edit Quote")


@app.route("/quotes/<int:quote_id>/update", methods=["POST"])
def update_quote(quote_id):
    quote = Quote.query.get_or_404(quote_id)
    quote.deal_id = request.form.get("deal_id")
    quote.total = request.form.get("total")
    db.session.commit()
    return redirect(url_for("show_quote", quote_id=quote.id))


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


@app.route("/quote_line_items/<int:item_id>")
def show_quote_line_item(item_id):
    item = QuoteLineItem.query.get_or_404(item_id)
    tasks = Task.query.filter_by(model="quote_line_items", record_id=item_id).all()
    return render_template(
        "quote_line_item_detail.html",
        item=item,
        tasks=tasks,
        title="Quote Line Item Detail",
    )


@app.route("/quote_line_items/<int:item_id>/edit")
def edit_quote_line_item(item_id):
    item = QuoteLineItem.query.get_or_404(item_id)
    quotes = Quote.query.all()
    products = Product.query.all()
    return render_template(
        "edit_quote_line_item.html",
        item=item,
        quotes=quotes,
        products=products,
        title="Edit Quote Line Item",
    )


@app.route("/quote_line_items/<int:item_id>/update", methods=["POST"])
def update_quote_line_item(item_id):
    item = QuoteLineItem.query.get_or_404(item_id)
    item.quote_id = request.form.get("quote_id")
    item.product_id = request.form.get("product_id")
    item.quantity = request.form.get("quantity")
    item.price = request.form.get("price")
    db.session.commit()
    return redirect(url_for("show_quote_line_item", item_id=item.id))


@app.route("/tasks")
def list_tasks():
    tasks = Task.query.all()
    return render_template("tasks.html", tasks=tasks, title="Tasks")


@app.route("/tasks/new/<model>/<int:record_id>")
def new_task(model, record_id):
    return render_template(
        "new_task.html", model=model, record_id=record_id, title="New Task"
    )


@app.route("/tasks/create", methods=["POST"])
def create_task():
    task = Task(
        description=request.form["description"],
        due_date=request.form.get("due_date"),
        model=request.form.get("model"),
        record_id=request.form.get("record_id"),
    )
    db.session.add(task)
    db.session.commit()
    return redirect(url_for("list_tasks"))


with app.app_context():
    db.create_all()
