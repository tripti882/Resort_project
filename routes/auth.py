import re
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from models import db, User

auth_bp = Blueprint("auth", __name__)

EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
ALLOWED_ROLES = {"admin", "frontdesk", "kitchen", "housekeeping", "guest"}
STAFF_ROLES   = {"frontdesk", "kitchen", "housekeeping", "admin"}


def _normalize_email(raw_email):
    return (raw_email or "").strip().lower()


def _is_valid_email(email):
    return bool(EMAIL_PATTERN.match(email))


def _validate_password(password):
    if len(password or "") < 6:
        return "Password must be at least 6 characters."
    return None


def _post_login_redirect(user):
    if user.role == "guest":
        return redirect(url_for("main.dashboard"))
    if user.role in STAFF_ROLES:
        return redirect(url_for("staff.dashboard"))
    logout_user()
    flash("Role is not allowed to sign in.", "error")
    return redirect(url_for("auth.login"))


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return _post_login_redirect(current_user)
    if request.method == "POST":
        name     = request.form.get("name", "").strip()
        email    = _normalize_email(request.form.get("email"))
        phone    = request.form.get("phone", "").strip()
        password = request.form.get("password", "")
        confirm  = request.form.get("confirm_password", "")
        if not name or not email or not password:
            flash("All fields are required.", "error")
            return render_template("pages/public/register.html")
        if not _is_valid_email(email):
            flash("Please enter a valid email address.", "error")
            return render_template("pages/public/register.html")
        if password != confirm:
            flash("Passwords do not match.", "error")
            return render_template("pages/public/register.html")
        err = _validate_password(password)
        if err:
            flash(err, "error")
            return render_template("pages/public/register.html")
        if User.query.filter_by(email=email).first():
            flash("Email already registered.", "error")
            return render_template("pages/public/register.html")
        user = User(name=name, email=email, phone=phone, role="guest", is_approved=True)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        flash("Account created successfully! Please log in.", "success")
        return redirect(url_for("auth.login"))
    return render_template("pages/public/register.html")


@auth_bp.route("/staff-register", methods=["GET", "POST"])
def staff_register():
    """Staff self-registration — account is created with is_approved=False
    and requires admin approval before the user can log in."""
    if current_user.is_authenticated:
        return _post_login_redirect(current_user)
    if request.method == "POST":
        name         = request.form.get("name", "").strip()
        email        = _normalize_email(request.form.get("email"))
        phone        = request.form.get("phone", "").strip()
        password     = request.form.get("password", "")
        confirm      = request.form.get("confirm_password", "")
        desired_role = request.form.get("desired_role", "").strip()

        if not name or not email or not password or not desired_role:
            flash("All fields are required.", "error")
            return render_template("pages/public/staff_register.html",
                                   staff_roles=list(STAFF_ROLES - {"admin"}))
        if desired_role not in (STAFF_ROLES - {"admin"}):
            flash("Please select a valid staff role.", "error")
            return render_template("pages/public/staff_register.html",
                                   staff_roles=list(STAFF_ROLES - {"admin"}))
        if not _is_valid_email(email):
            flash("Please enter a valid email address.", "error")
            return render_template("pages/public/staff_register.html",
                                   staff_roles=list(STAFF_ROLES - {"admin"}))
        if password != confirm:
            flash("Passwords do not match.", "error")
            return render_template("pages/public/staff_register.html",
                                   staff_roles=list(STAFF_ROLES - {"admin"}))
        err = _validate_password(password)
        if err:
            flash(err, "error")
            return render_template("pages/public/staff_register.html",
                                   staff_roles=list(STAFF_ROLES - {"admin"}))
        if User.query.filter_by(email=email).first():
            flash("Email already registered.", "error")
            return render_template("pages/public/staff_register.html",
                                   staff_roles=list(STAFF_ROLES - {"admin"}))

        # Create account locked until admin approves
        user = User(
            name=name,
            email=email,
            phone=phone,
            role="guest",           # stays guest until approved
            pending_role=desired_role,
            is_approved=False,
        )
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        flash(
            "Registration submitted! You can log in once an admin approves your account.",
            "success",
        )
        return redirect(url_for("auth.login"))
    return render_template("pages/public/staff_register.html",
                           staff_roles=sorted(STAFF_ROLES - {"admin"}))


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return _post_login_redirect(current_user)

    if request.method == "POST":
        email    = _normalize_email(request.form.get("email"))
        password = request.form.get("password", "")
        remember = request.form.get("remember") == "on"

        if not email or not password:
            flash("Email and password are required.", "error")
            return render_template("pages/public/login.html")
        if not _is_valid_email(email):
            flash("Please enter a valid email address.", "error")
            return render_template("pages/public/login.html")

        account = User.query.filter_by(email=email).first()
        if not account or not account.check_password(password):
            flash("Invalid email or password.", "error")
            return render_template("pages/public/login.html")
        if account.role not in ALLOWED_ROLES:
            flash("This account role is not allowed.", "error")
            return render_template("pages/public/login.html")

        # Block unapproved staff applicants
        if not account.is_approved:
            flash(
                "Your account is pending admin approval. "
                "You will be able to log in once it is approved.",
                "warning",
            )
            return render_template("pages/public/login.html")

        login_user(account, remember=remember)
        flash(f"Welcome back, {account.name}!", "success")
        return _post_login_redirect(account)

    return render_template("pages/public/login.html")


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("main.index"))
