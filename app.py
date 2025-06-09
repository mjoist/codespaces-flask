from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    session,
)
from flask_sqlalchemy import SQLAlchemy
from flask_login import (
    LoginManager,
    login_user,
    login_required,
    logout_user,
    current_user,
    UserMixin,
)
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import os
import re
from datetime import datetime

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///crm.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SECRET_KEY"] = "dev-secret"
db = SQLAlchemy(app)

login_manager = LoginManager(app)
login_manager.login_view = "login"

# --- Translation handling -------------------------------------------------
translations_cache = {}
AVAILABLE_LANGS = ["en", "de"]


def _parse_simple_yaml(path):
    data = {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if ":" in line:
                    k, v = line.split(":", 1)
                    data[k.strip()] = v.strip().strip('"').strip("'")
    except FileNotFoundError:
        pass
    return data


def get_translations():
    lang = (
        current_user.language
        if current_user.is_authenticated
        else session.get("lang", "en")
    )
    if lang not in translations_cache:
        fname = os.path.join(os.path.dirname(__file__), "locales", f"{lang}.yml")
        translations_cache[lang] = _parse_simple_yaml(fname)
    return translations_cache[lang]


@app.context_processor
def inject_translator():
    t = get_translations()

    def _(key):
        return t.get(key, key)

    return {"_": _}


@app.context_processor
def inject_notification_count():
    if current_user.is_authenticated:
        count = Notification.query.filter_by(user_id=current_user.id, is_read=False).count()
    else:
        count = 0
    return {"unread_notifications": count}


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    is_admin = db.Column(db.Boolean, default=False)
    language = db.Column(db.String(10), default="en")
    timezone = db.Column(db.String(50), default="UTC")
    country = db.Column(db.String(50))
    currency = db.Column(db.String(3), default="USD")
    profile_id = db.Column(db.Integer, db.ForeignKey("security_profile.id"))
    role_id = db.Column(db.Integer, db.ForeignKey("role.id"))
    profile = db.relationship("SecurityProfile")
    role = db.relationship("Role")


class Role(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True)
    parent_id = db.Column(db.Integer, db.ForeignKey("role.id"))
    parent = db.relationship("Role", remote_side=[id])


class SecurityProfile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True)


class ObjectPermission(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    profile_id = db.Column(db.Integer, db.ForeignKey("security_profile.id"))
    model = db.Column(db.String(50))
    can_create = db.Column(db.Boolean, default=True)
    can_read = db.Column(db.Boolean, default=True)
    can_update = db.Column(db.Boolean, default=True)
    can_delete = db.Column(db.Boolean, default=True)
    profile = db.relationship("SecurityProfile", backref="object_permissions")


class FieldPermission(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    profile_id = db.Column(db.Integer, db.ForeignKey("security_profile.id"))
    model = db.Column(db.String(50))
    field = db.Column(db.String(50))
    readable = db.Column(db.Boolean, default=True)
    editable = db.Column(db.Boolean, default=True)
    profile = db.relationship("SecurityProfile", backref="field_permissions")


class LeadShare(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    lead_id = db.Column(db.Integer, db.ForeignKey("lead.id"))
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    can_read = db.Column(db.Boolean, default=True)
    can_write = db.Column(db.Boolean, default=False)
    lead = db.relationship("Lead")
    user = db.relationship("User")


class AccountShare(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    account_id = db.Column(db.Integer, db.ForeignKey("account.id"))
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    can_read = db.Column(db.Boolean, default=True)
    can_write = db.Column(db.Boolean, default=False)
    account = db.relationship("Account")
    user = db.relationship("User")


class ContactShare(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    contact_id = db.Column(db.Integer, db.ForeignKey("contact.id"))
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    can_read = db.Column(db.Boolean, default=True)
    can_write = db.Column(db.Boolean, default=False)
    contact = db.relationship("Contact")
    user = db.relationship("User")


class DealShare(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    deal_id = db.Column(db.Integer, db.ForeignKey("deal.id"))
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    can_read = db.Column(db.Boolean, default=True)
    can_write = db.Column(db.Boolean, default=False)
    deal = db.relationship("Deal")
    user = db.relationship("User")


class StatusOption(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    model = db.Column(db.String(50))
    value = db.Column(db.String(50))


class Lead(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120))
    phone = db.Column(db.String(50))
    company = db.Column(db.String(120))
    notes = db.Column(db.Text)
    status = db.Column(db.String(50))
    owner_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    owner = db.relationship("User")


class Account(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    industry = db.Column(db.String(120))
    email = db.Column(db.String(120))
    phone = db.Column(db.String(50))
    address = db.Column(db.String(255))
    notes = db.Column(db.Text)
    owner_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    owner = db.relationship("User")


class Contact(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120))
    phone = db.Column(db.String(50))
    title = db.Column(db.String(120))
    account_id = db.Column(db.Integer, db.ForeignKey("account.id"))
    account = db.relationship("Account", backref=db.backref("contacts", lazy=True))
    owner_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    owner = db.relationship("User")


class Deal(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    amount = db.Column(db.Float)
    stage = db.Column(db.String(50))
    close_date = db.Column(db.String(50))
    account_id = db.Column(db.Integer, db.ForeignKey("account.id"))
    account = db.relationship("Account", backref=db.backref("deals", lazy=True))
    owner_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    owner = db.relationship("User")


class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    price = db.Column(db.Float)
    description = db.Column(db.Text)
    owner_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    owner = db.relationship("User")


class Pricebook(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text)
    owner_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    owner = db.relationship("User")


class PriceBookEntry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey("product.id"))
    pricebook_id = db.Column(db.Integer, db.ForeignKey("pricebook.id"))
    unit_price = db.Column(db.Float)
    product = db.relationship("Product")
    pricebook = db.relationship("Pricebook")
    owner_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    owner = db.relationship("User")


class Quote(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    deal_id = db.Column(db.Integer, db.ForeignKey("deal.id"))
    total = db.Column(db.Float)
    expiration_date = db.Column(db.String(50))
    deal = db.relationship("Deal")
    owner_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    owner = db.relationship("User")


class QuoteLineItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    quote_id = db.Column(db.Integer, db.ForeignKey("quote.id"))
    product_id = db.Column(db.Integer, db.ForeignKey("product.id"))
    quantity = db.Column(db.Integer)
    price = db.Column(db.Float)
    quote = db.relationship("Quote", backref=db.backref("line_items", lazy=True))
    product = db.relationship("Product")
    owner_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    owner = db.relationship("User")


class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(255))
    due_date = db.Column(db.String(50))
    status = db.Column(db.String(50))
    model = db.Column(db.String(50))
    record_id = db.Column(db.Integer)
    owner_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    owner = db.relationship("User")


class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    model = db.Column(db.String(50))
    record_id = db.Column(db.Integer)
    content = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user = db.relationship("User")


class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    message_id = db.Column(db.Integer, db.ForeignKey("message.id"))
    model = db.Column(db.String(50))
    record_id = db.Column(db.Integer)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user = db.relationship("User")
    message = db.relationship("Message")


def record_url(model, record_id):
    mapping = {
        "leads": ("show_lead", "lead_id"),
        "accounts": ("show_account", "account_id"),
        "contacts": ("show_contact", "contact_id"),
        "deals": ("show_deal", "deal_id"),
        "products": ("show_product", "product_id"),
        "pricebooks": ("show_pricebook", "pricebook_id"),
        "pricebook_entries": ("show_pricebook_entry", "entry_id"),
        "quotes": ("show_quote", "quote_id"),
        "quote_line_items": ("show_quote_line_item", "item_id"),
    }
    view, param = mapping.get(model, (None, None))
    if view:
        return url_for(view, **{param: record_id})
    return url_for("dashboard")


def _role_descendants(role):
    roles = []
    if not role:
        return roles
    stack = [role]
    while stack:
        r = stack.pop()
        roles.append(r.id)
        stack.extend(Role.query.filter_by(parent_id=r.id).all())
    return roles


def can_view_record(user, owner_id, shares):
    if user.is_admin:
        return True
    if owner_id == user.id:
        return True
    if owner_id and user.role:
        owner = User.query.get(owner_id)
        if owner and owner.role_id in _role_descendants(user.role):
            return True
    if any(s.user_id == user.id and s.can_read for s in shares):
        return True
    return False


@app.before_request
def require_login():
    if (
        request.endpoint not in ("login", "static")
        and not current_user.is_authenticated
    ):
        return redirect(url_for("login"))


@app.route("/")
def dashboard():
    q = request.args.get("q", "")
    counts = {
        "leads": Lead.query.count(),
        "accounts": Account.query.count(),
        "contacts": Contact.query.count(),
        "deals": Deal.query.count(),
        "products": Product.query.count(),
        "pricebooks": Pricebook.query.count(),
        "quotes": Quote.query.count(),
    }
    query = Task.query
    if q:
        query = query.filter(Task.description.ilike(f"%{q}%"))
    tasks = query.all()
    return render_template(
        "dashboard.html", counts=counts, tasks=tasks, q=q, title="Dashboard"
    )


@app.route("/leads")
def list_leads():
    q = request.args.get("q", "")
    query = Lead.query
    if q:
        query = query.filter(Lead.name.ilike(f"%{q}%"))
    leads = [
        l
        for l in query.all()
        if can_view_record(current_user, l.owner_id, LeadShare.query.filter_by(lead_id=l.id).all())
    ]
    return render_template(
        "leads.html",
        leads=leads,
        q=q,
        title=get_translations().get("leads", "Leads"),
    )


@app.route("/leads/kanban")
def leads_kanban():
    statuses = [s.value for s in StatusOption.query.filter_by(model="lead").all()]
    columns = {s: Lead.query.filter_by(status=s).all() for s in statuses}
    return render_template(
        "kanban.html", columns=columns, title="Leads Kanban", model="lead"
    )


@app.route("/leads/new")
def new_lead():
    statuses = StatusOption.query.filter_by(model="lead").all()
    return render_template("new_lead.html", statuses=statuses, title="New Lead")


@app.route("/leads/create", methods=["POST"])
def create_lead():
    lead = Lead(
        name=request.form["name"],
        email=request.form.get("email"),
        phone=request.form.get("phone"),
        company=request.form.get("company"),
        notes=request.form.get("notes"),
        status=request.form.get("status"),
        owner_id=current_user.id,
    )
    db.session.add(lead)
    db.session.commit()
    return redirect(url_for("list_leads"))


@app.route("/leads/<int:lead_id>")
def show_lead(lead_id):
    lead = Lead.query.get_or_404(lead_id)
    if not can_view_record(current_user, lead.owner_id, LeadShare.query.filter_by(lead_id=lead_id).all()):
        return redirect(url_for("list_leads"))
    tasks = Task.query.filter_by(model="leads", record_id=lead_id).all()
    messages = (
        Message.query.filter_by(model="leads", record_id=lead_id)
        .order_by(Message.created_at.desc())
        .all()
    )
    return render_template(
        "lead_detail.html",
        lead=lead,
        tasks=tasks,
        messages=messages,
        model="leads",
        record_id=lead_id,
        title="Lead Detail",
    )


@app.route("/leads/<int:lead_id>/edit")
def edit_lead(lead_id):
    lead = Lead.query.get_or_404(lead_id)
    statuses = StatusOption.query.filter_by(model="lead").all()
    return render_template(
        "edit_lead.html", lead=lead, statuses=statuses, title="Edit Lead"
    )


@app.route("/leads/<int:lead_id>/update", methods=["POST"])
def update_lead(lead_id):
    lead = Lead.query.get_or_404(lead_id)
    lead.name = request.form["name"]
    lead.email = request.form.get("email")
    lead.phone = request.form.get("phone")
    lead.company = request.form.get("company")
    lead.notes = request.form.get("notes")
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
    q = request.args.get("q", "")
    query = Account.query
    if q:
        query = query.filter(Account.name.ilike(f"%{q}%"))
    accounts = [
        a
        for a in query.all()
        if can_view_record(current_user, a.owner_id, AccountShare.query.filter_by(account_id=a.id).all())
    ]
    return render_template(
        "accounts.html",
        accounts=accounts,
        q=q,
        title=get_translations().get("accounts", "Accounts"),
    )


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
        address=request.form.get("address"),
        notes=request.form.get("notes"),
        owner_id=current_user.id,
    )
    db.session.add(account)
    db.session.commit()
    return redirect(url_for("list_accounts"))


@app.route("/accounts/<int:account_id>")
def show_account(account_id):
    account = Account.query.get_or_404(account_id)
    if not can_view_record(current_user, account.owner_id, AccountShare.query.filter_by(account_id=account_id).all()):
        return redirect(url_for("list_accounts"))
    tasks = Task.query.filter_by(model="accounts", record_id=account_id).all()
    messages = (
        Message.query.filter_by(model="accounts", record_id=account_id)
        .order_by(Message.created_at.desc())
        .all()
    )
    return render_template(
        "account_detail.html",
        account=account,
        tasks=tasks,
        messages=messages,
        model="accounts",
        record_id=account_id,
        title="Account Detail",
    )


@app.route("/accounts/<int:account_id>/edit")
def edit_account(account_id):
    account = Account.query.get_or_404(account_id)
    return render_template("edit_account.html", account=account, title="Edit Account")


@app.route("/accounts/<int:account_id>/update", methods=["POST"])
def update_account(account_id):
    account = Account.query.get_or_404(account_id)
    account.name = request.form["name"]
    account.industry = request.form.get("industry")
    account.email = request.form.get("email")
    account.phone = request.form.get("phone")
    account.address = request.form.get("address")
    account.notes = request.form.get("notes")
    db.session.commit()
    return redirect(url_for("show_account", account_id=account.id))


@app.route("/contacts")
def list_contacts():
    q = request.args.get("q", "")
    query = Contact.query
    if q:
        query = query.filter(Contact.name.ilike(f"%{q}%"))
    contacts = [
        c
        for c in query.all()
        if can_view_record(current_user, c.owner_id, ContactShare.query.filter_by(contact_id=c.id).all())
    ]
    return render_template(
        "contacts.html",
        contacts=contacts,
        q=q,
        title=get_translations().get("contacts", "Contacts"),
    )


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
        title=request.form.get("title"),
        account_id=request.form.get("account_id") or None,
        owner_id=current_user.id,
    )
    db.session.add(contact)
    db.session.commit()
    return redirect(url_for("list_contacts"))


@app.route("/contacts/<int:contact_id>")
def show_contact(contact_id):
    contact = Contact.query.get_or_404(contact_id)
    if not can_view_record(current_user, contact.owner_id, ContactShare.query.filter_by(contact_id=contact_id).all()):
        return redirect(url_for("list_contacts"))
    tasks = Task.query.filter_by(model="contacts", record_id=contact_id).all()
    messages = (
        Message.query.filter_by(model="contacts", record_id=contact_id)
        .order_by(Message.created_at.desc())
        .all()
    )
    return render_template(
        "contact_detail.html",
        contact=contact,
        tasks=tasks,
        messages=messages,
        model="contacts",
        record_id=contact_id,
        title="Contact Detail",
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
    contact.title = request.form.get("title")
    contact.account_id = request.form.get("account_id") or None
    db.session.commit()
    return redirect(url_for("show_contact", contact_id=contact.id))


@app.route("/deals")
def list_deals():
    q = request.args.get("q", "")
    query = Deal.query
    if q:
        query = query.filter(Deal.name.ilike(f"%{q}%"))
    deals = [
        d
        for d in query.all()
        if can_view_record(current_user, d.owner_id, DealShare.query.filter_by(deal_id=d.id).all())
    ]
    return render_template(
        "deals.html",
        deals=deals,
        q=q,
        title=get_translations().get("deals", "Deals"),
    )


@app.route("/deals/kanban")
def deals_kanban():
    statuses = [s.value for s in StatusOption.query.filter_by(model="deal").all()]
    columns = {s: Deal.query.filter_by(stage=s).all() for s in statuses}
    return render_template(
        "kanban.html", columns=columns, title="Deals Kanban", model="deal"
    )


@app.route("/deals/new")
def new_deal():
    accounts = Account.query.all()
    stages = StatusOption.query.filter_by(model="deal").all()
    return render_template(
        "new_deal.html", accounts=accounts, stages=stages, title="New Deal"
    )


@app.route("/deals/create", methods=["POST"])
def create_deal():
    deal = Deal(
        name=request.form["name"],
        amount=request.form.get("amount"),
        stage=request.form.get("stage"),
        close_date=request.form.get("close_date"),
        account_id=request.form.get("account_id") or None,
        owner_id=current_user.id,
    )
    db.session.add(deal)
    db.session.commit()
    return redirect(url_for("list_deals"))


@app.route("/deals/<int:deal_id>")
def show_deal(deal_id):
    deal = Deal.query.get_or_404(deal_id)
    if not can_view_record(current_user, deal.owner_id, DealShare.query.filter_by(deal_id=deal_id).all()):
        return redirect(url_for("list_deals"))
    tasks = Task.query.filter_by(model="deals", record_id=deal_id).all()
    messages = (
        Message.query.filter_by(model="deals", record_id=deal_id)
        .order_by(Message.created_at.desc())
        .all()
    )
    return render_template(
        "deal_detail.html",
        deal=deal,
        tasks=tasks,
        messages=messages,
        model="deals",
        record_id=deal_id,
        title="Deal Detail",
    )


@app.route("/deals/<int:deal_id>/edit")
def edit_deal(deal_id):
    deal = Deal.query.get_or_404(deal_id)
    accounts = Account.query.all()
    stages = StatusOption.query.filter_by(model="deal").all()
    return render_template(
        "edit_deal.html", deal=deal, accounts=accounts, stages=stages, title="Edit Deal"
    )


@app.route("/deals/<int:deal_id>/update", methods=["POST"])
def update_deal(deal_id):
    deal = Deal.query.get_or_404(deal_id)
    deal.name = request.form["name"]
    deal.amount = request.form.get("amount")
    deal.stage = request.form.get("stage")
    deal.close_date = request.form.get("close_date")
    deal.account_id = request.form.get("account_id") or None
    db.session.commit()
    return redirect(url_for("show_deal", deal_id=deal.id))


@app.route("/products")
def list_products():
    q = request.args.get("q", "")
    query = Product.query
    if q:
        query = query.filter(Product.name.ilike(f"%{q}%"))
    products = [
        p
        for p in query.all()
        if can_view_record(current_user, p.owner_id, [])
    ]
    return render_template(
        "products.html",
        products=products,
        q=q,
        title=get_translations().get("products", "Products"),
    )


@app.route("/products/new")
def new_product():
    return render_template("new_product.html", title="New Product")


@app.route("/products/create", methods=["POST"])
def create_product():
    product = Product(
        name=request.form["name"],
        price=request.form.get("price"),
        description=request.form.get("description"),
        owner_id=current_user.id,
    )
    db.session.add(product)
    db.session.commit()
    return redirect(url_for("list_products"))


@app.route("/products/<int:product_id>")
def show_product(product_id):
    product = Product.query.get_or_404(product_id)
    if not can_view_record(current_user, product.owner_id, []):
        return redirect(url_for("list_products"))
    tasks = Task.query.filter_by(model="products", record_id=product_id).all()
    messages = (
        Message.query.filter_by(model="products", record_id=product_id)
        .order_by(Message.created_at.desc())
        .all()
    )
    return render_template(
        "product_detail.html",
        product=product,
        tasks=tasks,
        messages=messages,
        model="products",
        record_id=product_id,
        title="Product Detail",
    )


@app.route("/products/<int:product_id>/edit")
def edit_product(product_id):
    product = Product.query.get_or_404(product_id)
    return render_template("edit_product.html", product=product, title="Edit Product")


@app.route("/products/<int:product_id>/update", methods=["POST"])
def update_product(product_id):
    product = Product.query.get_or_404(product_id)
    product.name = request.form["name"]
    product.price = request.form.get("price")
    product.description = request.form.get("description")
    db.session.commit()
    return redirect(url_for("show_product", product_id=product.id))


@app.route("/pricebooks")
def list_pricebooks():
    q = request.args.get("q", "")
    query = Pricebook.query
    if q:
        query = query.filter(Pricebook.name.ilike(f"%{q}%"))
    pricebooks = [
        pb
        for pb in query.all()
        if can_view_record(current_user, pb.owner_id, [])
    ]
    return render_template(
        "pricebooks.html",
        pricebooks=pricebooks,
        q=q,
        title=get_translations().get("pricebooks", "Pricebooks"),
    )


@app.route("/pricebooks/new")
def new_pricebook():
    return render_template("new_pricebook.html", title="New Pricebook")


@app.route("/pricebooks/create", methods=["POST"])
def create_pricebook():
    pricebook = Pricebook(
        name=request.form["name"],
        description=request.form.get("description"),
        owner_id=current_user.id,
    )
    db.session.add(pricebook)
    db.session.commit()
    return redirect(url_for("list_pricebooks"))


@app.route("/pricebooks/<int:pricebook_id>")
def show_pricebook(pricebook_id):
    pricebook = Pricebook.query.get_or_404(pricebook_id)
    if not can_view_record(current_user, pricebook.owner_id, []):
        return redirect(url_for("list_pricebooks"))
    tasks = Task.query.filter_by(model="pricebooks", record_id=pricebook_id).all()
    messages = (
        Message.query.filter_by(model="pricebooks", record_id=pricebook_id)
        .order_by(Message.created_at.desc())
        .all()
    )
    return render_template(
        "pricebook_detail.html",
        pricebook=pricebook,
        tasks=tasks,
        messages=messages,
        model="pricebooks",
        record_id=pricebook_id,
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
    pricebook.description = request.form.get("description")
    db.session.commit()
    return redirect(url_for("show_pricebook", pricebook_id=pricebook.id))


@app.route("/pricebook_entries")
def list_pricebook_entries():
    q = request.args.get("q", "")
    query = PriceBookEntry.query
    if q:
        try:
            entry_id = int(q)
            query = query.filter(PriceBookEntry.id == entry_id)
        except ValueError:
            query = query.filter(PriceBookEntry.id == -1)
    entries = query.all()
    return render_template(
        "pricebook_entries.html",
        entries=entries,
        q=q,
        title=get_translations().get("pricebook_entries", "Price Book Entries"),
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
        owner_id=current_user.id,
    )
    db.session.add(entry)
    db.session.commit()
    return redirect(url_for("list_pricebook_entries"))


@app.route("/pricebook_entries/<int:entry_id>")
def show_pricebook_entry(entry_id):
    entry = PriceBookEntry.query.get_or_404(entry_id)
    if not can_view_record(current_user, entry.owner_id, []):
        return redirect(url_for("list_pricebook_entries"))
    tasks = Task.query.filter_by(model="pricebook_entries", record_id=entry_id).all()
    messages = (
        Message.query.filter_by(model="pricebook_entries", record_id=entry_id)
        .order_by(Message.created_at.desc())
        .all()
    )
    return render_template(
        "pricebook_entry_detail.html",
        entry=entry,
        tasks=tasks,
        messages=messages,
        model="pricebook_entries",
        record_id=entry_id,
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
    q = request.args.get("q", "")
    query = Quote.query
    if q:
        query = query.filter(Quote.id == q)
    quotes = [
        q
        for q in query.all()
        if can_view_record(current_user, q.owner_id, [])
    ]
    return render_template(
        "quotes.html",
        quotes=quotes,
        q=q,
        title=get_translations().get("quotes", "Quotes"),
    )


@app.route("/quotes/new")
def new_quote():
    deals = Deal.query.all()
    return render_template("new_quote.html", deals=deals, title="New Quote")


@app.route("/quotes/create", methods=["POST"])
def create_quote():
    quote = Quote(
        deal_id=request.form.get("deal_id"),
        total=request.form.get("total"),
        expiration_date=request.form.get("expiration_date"),
        owner_id=current_user.id,
    )
    db.session.add(quote)
    db.session.commit()
    return redirect(url_for("list_quotes"))


@app.route("/quotes/<int:quote_id>")
def show_quote(quote_id):
    quote = Quote.query.get_or_404(quote_id)
    if not can_view_record(current_user, quote.owner_id, []):
        return redirect(url_for("list_quotes"))
    tasks = Task.query.filter_by(model="quotes", record_id=quote_id).all()
    messages = (
        Message.query.filter_by(model="quotes", record_id=quote_id)
        .order_by(Message.created_at.desc())
        .all()
    )
    return render_template(
        "quote_detail.html",
        quote=quote,
        tasks=tasks,
        messages=messages,
        model="quotes",
        record_id=quote_id,
        title="Quote Detail",
    )


@app.route("/quotes/<int:quote_id>/edit")
def edit_quote(quote_id):
    quote = Quote.query.get_or_404(quote_id)
    deals = Deal.query.all()
    return render_template(
        "edit_quote.html", quote=quote, deals=deals, title="Edit Quote"
    )


@app.route("/quotes/<int:quote_id>/update", methods=["POST"])
def update_quote(quote_id):
    quote = Quote.query.get_or_404(quote_id)
    quote.deal_id = request.form.get("deal_id")
    quote.total = request.form.get("total")
    quote.expiration_date = request.form.get("expiration_date")
    db.session.commit()
    return redirect(url_for("show_quote", quote_id=quote.id))


@app.route("/quote_line_items")
def list_quote_line_items():
    q = request.args.get("q", "")
    query = QuoteLineItem.query
    if q:
        query = query.filter(QuoteLineItem.id == q)
    items = [
        i
        for i in query.all()
        if can_view_record(current_user, i.owner_id, [])
    ]
    return render_template(
        "quote_line_items.html",
        items=items,
        q=q,
        title=get_translations().get("quote_line_items", "Quote Line Items"),
    )


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
        owner_id=current_user.id,
    )
    db.session.add(item)
    db.session.commit()
    return redirect(url_for("list_quote_line_items"))


@app.route("/quote_line_items/<int:item_id>")
def show_quote_line_item(item_id):
    item = QuoteLineItem.query.get_or_404(item_id)
    if not can_view_record(current_user, item.owner_id, []):
        return redirect(url_for("list_quote_line_items"))
    tasks = Task.query.filter_by(model="quote_line_items", record_id=item_id).all()
    messages = (
        Message.query.filter_by(model="quote_line_items", record_id=item_id)
        .order_by(Message.created_at.desc())
        .all()
    )
    return render_template(
        "quote_line_item_detail.html",
        item=item,
        tasks=tasks,
        messages=messages,
        model="quote_line_items",
        record_id=item_id,
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
    q = request.args.get("q", "")
    query = Task.query
    if q:
        query = query.filter(Task.description.ilike(f"%{q}%"))
    tasks = [
        t
        for t in query.all()
        if can_view_record(current_user, t.owner_id, [])
    ]
    return render_template(
        "tasks.html",
        tasks=tasks,
        q=q,
        title=get_translations().get("tasks", "Tasks"),
    )


@app.route("/tasks/kanban")
def tasks_kanban():
    statuses = [s.value for s in StatusOption.query.filter_by(model="task").all()]
    columns = {s: Task.query.filter_by(status=s).all() for s in statuses}
    return render_template(
        "kanban.html", columns=columns, title="Tasks Kanban", model="task"
    )


@app.route("/tasks/new/<model>/<int:record_id>")
def new_task(model, record_id):
    statuses = StatusOption.query.filter_by(model="task").all()
    return render_template(
        "new_task.html",
        model=model,
        record_id=record_id,
        statuses=statuses,
        title="New Task",
    )


@app.route("/tasks/create", methods=["POST"])
def create_task():
    task = Task(
        description=request.form["description"],
        due_date=request.form.get("due_date"),
        status=request.form.get("status"),
        model=request.form.get("model"),
        record_id=request.form.get("record_id"),
        owner_id=current_user.id,
    )
    db.session.add(task)
    db.session.commit()
    return redirect(url_for("list_tasks"))


@app.route("/messages/create", methods=["POST"])
@login_required
def create_message():
    content = request.form["content"]
    model = request.form.get("model")
    record_id = request.form.get("record_id")
    message = Message(
        user_id=current_user.id,
        model=model,
        record_id=record_id,
        content=content,
    )
    db.session.add(message)
    db.session.commit()

    mentioned = set(re.findall(r"@(\w+)", content))
    for username in mentioned:
        user = User.query.filter_by(username=username).first()
        if user:
            db.session.add(
                Notification(
                    user_id=user.id,
                    message=message,
                    model=model,
                    record_id=record_id,
                )
            )
    db.session.commit()
    return redirect(record_url(model, record_id))


@app.route("/notifications")
@login_required
def list_notifications():
    notes = (
        Notification.query.filter_by(user_id=current_user.id)
        .order_by(Notification.created_at.desc())
        .all()
    )
    return render_template("notifications.html", notifications=notes, title="Notifications")


@app.route("/notifications/<int:notif_id>")
@login_required
def view_notification(notif_id):
    note = Notification.query.get_or_404(notif_id)
    if note.user_id != current_user.id:
        return redirect(url_for("list_notifications"))
    note.is_read = True
    db.session.commit()
    return redirect(record_url(note.model, note.record_id))


@app.route("/search")
def global_search():
    q = request.args.get("q", "")
    like = f"%{q}%"
    results = {
        "leads": [
            (l.name, url_for("show_lead", lead_id=l.id))
            for l in Lead.query.filter(Lead.name.ilike(like)).all()
        ],
        "accounts": [
            (a.name, url_for("show_account", account_id=a.id))
            for a in Account.query.filter(Account.name.ilike(like)).all()
        ],
        "contacts": [
            (c.name, url_for("show_contact", contact_id=c.id))
            for c in Contact.query.filter(Contact.name.ilike(like)).all()
        ],
        "deals": [
            (d.name, url_for("show_deal", deal_id=d.id))
            for d in Deal.query.filter(Deal.name.ilike(like)).all()
        ],
    }
    return render_template(
        "search_results.html", q=q, results=results, title=f"Search: {q}"
    )


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = User.query.filter_by(username=request.form["username"]).first()
        if user and check_password_hash(user.password_hash, request.form["password"]):
            login_user(user)
            session["lang"] = user.language
            return redirect(url_for("dashboard"))
        flash("Invalid credentials")
    return render_template("login.html", title="Login")


@app.route("/settings", methods=["GET", "POST"])
def settings():
    if request.method == "POST":
        lang = request.form.get("lang", "en")
        tz = request.form.get("timezone", "UTC")
        country = request.form.get("country", "")
        currency = request.form.get("currency", "USD")
        if current_user.is_authenticated:
            if lang in AVAILABLE_LANGS:
                current_user.language = lang
                session["lang"] = lang
            current_user.timezone = tz
            current_user.country = country
            if currency in ("USD", "EUR"):
                current_user.currency = currency
            db.session.commit()
        else:
            if lang in AVAILABLE_LANGS:
                session["lang"] = lang
        return redirect(url_for("settings"))
    if current_user.is_authenticated:
        current = current_user.language
        tz = current_user.timezone
        country = current_user.country or ""
        currency = current_user.currency
    else:
        current = session.get("lang", "en")
        tz = "UTC"
        country = ""
        currency = "USD"
    return render_template(
        "settings.html",
        languages=AVAILABLE_LANGS,
        current=current,
        tz=tz,
        country=country,
        currency=currency,
        title=get_translations().get("settings", "Settings"),
    )


@app.route("/logout")
def logout():
    logout_user()
    session.pop("lang", None)
    return redirect(url_for("login"))


@app.route("/admin")
@login_required
def admin_overview():
    if not current_user.is_admin:
        return redirect(url_for("dashboard"))

    return render_template(
        "admin_overview.html",
        title=get_translations().get("admin_overview", "Admin Overview"),
    )


@app.route("/admin/users")
@login_required
def admin_users():
    if not current_user.is_admin:
        return redirect(url_for("dashboard"))
    users = User.query.all()
    roles = Role.query.all()
    profiles = SecurityProfile.query.all()

    return render_template(
        "admin.html",
        users=users,
        roles=roles,
        profiles=profiles,
        title=get_translations().get("user_management", "User Management"),
    )


@app.route("/admin/users/create", methods=["POST"])
@login_required
def create_user():
    if not current_user.is_admin:
        return redirect(url_for("dashboard"))
    username = request.form["username"]
    password = generate_password_hash(request.form["password"])
    user = User(
        username=username,
        password_hash=password,
        language="en",
        timezone="UTC",
        currency="USD",
        role_id=request.form.get("role_id") or None,
        profile_id=request.form.get("profile_id") or None,
    )
    db.session.add(user)
    db.session.commit()
    return redirect(url_for("admin_users"))

@app.route("/admin/users/<int:user_id>/update", methods=["POST"])
@login_required
def update_user(user_id):
    if not current_user.is_admin:
        return redirect(url_for("dashboard"))
    user = User.query.get_or_404(user_id)
    user.role_id = request.form.get("role_id") or None
    user.profile_id = request.form.get("profile_id") or None
    db.session.commit()
    return redirect(url_for("admin_users"))


@app.route("/admin/users/<int:user_id>/delete", methods=["POST"])
@login_required
def delete_user(user_id):
    if not current_user.is_admin:
        return redirect(url_for("dashboard"))
    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    return redirect(url_for("admin_users"))


@app.route("/admin/statuses")
@login_required
def manage_statuses():
    if not current_user.is_admin:
        return redirect(url_for("dashboard"))
    statuses = StatusOption.query.all()
    return render_template(
        "statuses.html",
        statuses=statuses,
        title=get_translations().get("manage_statuses", "Manage Statuses"),
    )


@app.route("/admin/statuses/create", methods=["POST"])
@login_required
def create_status():
    if not current_user.is_admin:
        return redirect(url_for("dashboard"))
    db.session.add(
        StatusOption(model=request.form["model"], value=request.form["value"])
    )
    db.session.commit()
    return redirect(url_for("manage_statuses"))


@app.route("/admin/statuses/<int:status_id>/update", methods=["POST"])
@login_required
def update_status(status_id):
    if not current_user.is_admin:
        return redirect(url_for("dashboard"))
    status = StatusOption.query.get_or_404(status_id)
    status.value = request.form["value"]
    db.session.commit()
    return redirect(url_for("manage_statuses"))


@app.route("/admin/statuses/<int:status_id>/delete", methods=["POST"])
@login_required
def delete_status(status_id):
    if not current_user.is_admin:
        return redirect(url_for("dashboard"))
    status = StatusOption.query.get_or_404(status_id)
    db.session.delete(status)
    db.session.commit()
    return redirect(url_for("manage_statuses"))


@app.route("/admin/roles")
@login_required
def manage_roles():
    if not current_user.is_admin:
        return redirect(url_for("dashboard"))
    roles = Role.query.all()
    return render_template(
        "roles.html",
        roles=roles,
        title=get_translations().get("manage_roles", "Manage Roles"),
    )

@app.route("/admin/roles/create", methods=["POST"])
@login_required
def create_role():
    if not current_user.is_admin:
        return redirect(url_for("dashboard"))
    role = Role(name=request.form["name"], parent_id=request.form.get("parent_id") or None)
    db.session.add(role)
    db.session.commit()
    return redirect(url_for("manage_roles"))

@app.route("/admin/roles/<int:role_id>/update", methods=["POST"])
@login_required
def update_role(role_id):
    if not current_user.is_admin:
        return redirect(url_for("dashboard"))
    role = Role.query.get_or_404(role_id)
    role.name = request.form["name"]
    role.parent_id = request.form.get("parent_id") or None
    db.session.commit()
    return redirect(url_for("manage_roles"))

@app.route("/admin/roles/<int:role_id>/delete", methods=["POST"])
@login_required
def delete_role(role_id):
    if not current_user.is_admin:
        return redirect(url_for("dashboard"))
    role = Role.query.get_or_404(role_id)
    db.session.delete(role)
    db.session.commit()
    return redirect(url_for("manage_roles"))

@app.route("/admin/profiles")
@login_required
def manage_profiles():
    if not current_user.is_admin:
        return redirect(url_for("dashboard"))
    profiles = SecurityProfile.query.all()
    return render_template(
        "profiles.html",
        profiles=profiles,
        title=get_translations().get("manage_profiles", "Manage Profiles"),
    )

@app.route("/admin/profiles/create", methods=["POST"])
@login_required
def create_profile():
    if not current_user.is_admin:
        return redirect(url_for("dashboard"))
    profile = SecurityProfile(name=request.form["name"])
    db.session.add(profile)
    db.session.commit()
    return redirect(url_for("manage_profiles"))

@app.route("/admin/profiles/<int:profile_id>/update", methods=["POST"])
@login_required
def update_profile(profile_id):
    if not current_user.is_admin:
        return redirect(url_for("dashboard"))
    profile = SecurityProfile.query.get_or_404(profile_id)
    profile.name = request.form["name"]
    db.session.commit()
    return redirect(url_for("manage_profiles"))

@app.route("/admin/profiles/<int:profile_id>/delete", methods=["POST"])
@login_required
def delete_profile(profile_id):
    if not current_user.is_admin:
        return redirect(url_for("dashboard"))
    profile = SecurityProfile.query.get_or_404(profile_id)
    db.session.delete(profile)
    db.session.commit()
    return redirect(url_for("manage_profiles"))


@app.route("/api/update_status", methods=["POST"])
def api_update_status():
    data = request.get_json()
    model = data.get("model")
    record_id = data.get("id")
    status = data.get("status")
    if model == "lead":
        record = Lead.query.get(record_id)
        if record:
            record.status = status
    elif model == "deal":
        record = Deal.query.get(record_id)
        if record:
            record.stage = status
    elif model == "task":
        record = Task.query.get(record_id)
        if record:
            record.status = status
    else:
        return {"success": False}, 400
    db.session.commit()
    return {"success": True}


@app.route("/api/record/<model>/<int:record_id>")
def api_get_record(model, record_id):
    if model == "lead":
        record = Lead.query.get_or_404(record_id)
    elif model == "account":
        record = Account.query.get_or_404(record_id)
    elif model == "contact":
        record = Contact.query.get_or_404(record_id)
    elif model == "deal":
        record = Deal.query.get_or_404(record_id)
    elif model == "product":
        record = Product.query.get_or_404(record_id)
    elif model == "pricebook":
        record = Pricebook.query.get_or_404(record_id)
    elif model == "quote":
        record = Quote.query.get_or_404(record_id)
    elif model == "task":
        record = Task.query.get_or_404(record_id)
    else:
        return {"error": "model"}, 404
    data = {k: v for k, v in record.__dict__.items() if k != "_sa_instance_state"}
    return data


with app.app_context():
    db.create_all()
    inspector = db.inspect(db.engine)
    cols = {c['name'] for c in inspector.get_columns('user')}
    added = False
    if 'language' not in cols:
        db.session.execute(db.text("ALTER TABLE user ADD COLUMN language VARCHAR(10) DEFAULT 'en'"))
        added = True
    if 'timezone' not in cols:
        db.session.execute(db.text("ALTER TABLE user ADD COLUMN timezone VARCHAR(50) DEFAULT 'UTC'"))
        added = True
    if 'country' not in cols:
        db.session.execute(db.text("ALTER TABLE user ADD COLUMN country VARCHAR(50)"))
        added = True
    if 'currency' not in cols:
        db.session.execute(db.text("ALTER TABLE user ADD COLUMN currency VARCHAR(3) DEFAULT 'USD'"))
        added = True
    if 'profile_id' not in cols:
        db.session.execute(db.text("ALTER TABLE user ADD COLUMN profile_id INTEGER"))
        added = True
    if 'role_id' not in cols:
        db.session.execute(db.text("ALTER TABLE user ADD COLUMN role_id INTEGER"))
        added = True
    tables = [
        'lead',
        'account',
        'contact',
        'deal',
        'product',
        'pricebook',
        'price_book_entry',
        'quote',
        'quote_line_item',
        'task',
    ]
    for table in tables:
        cols = {c['name'] for c in inspector.get_columns(table)}
        if 'owner_id' not in cols:
            db.session.execute(db.text(f"ALTER TABLE {table} ADD COLUMN owner_id INTEGER"))
            added = True
    if added:
        db.session.commit()
    if not User.query.filter_by(username="admin").first():
        admin_user = User(
            username="admin",
            password_hash=generate_password_hash("admin"),
            is_admin=True,
            language="en",
            timezone="UTC",
            country="",
            currency="USD",
        )
        db.session.add(admin_user)
        db.session.commit()

    if not StatusOption.query.first():
        defaults = {
            "lead": ["New", "Contacted", "Qualified"],
            "task": ["Open", "In Progress", "Closed"],
            "deal": ["Prospecting", "Negotiation", "Won", "Lost"],
        }
        for model, values in defaults.items():
            for v in values:
                db.session.add(StatusOption(model=model, value=v))
        db.session.commit()
