from fastapi import FastAPI, Request, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from pathlib import Path
from datetime import datetime
import sqlite3
import hashlib
import secrets
import json
import os
import shutil

# =========================================================
# POCKETSMART AI - BACKEND
# =========================================================

app = FastAPI(title="PocketSmart AI")

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
UPLOAD_DIR = BASE_DIR / "uploads"
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"

DATA_DIR.mkdir(exist_ok=True)
UPLOAD_DIR.mkdir(exist_ok=True)

DATABASE_PATH = DATA_DIR / "pocketsmart.db"

# ---------------------------------------------------------
# Static files
# ---------------------------------------------------------

app.mount(
    "/static",
    StaticFiles(directory=STATIC_DIR),
    name="static"
)


# =========================================================
# DATABASE
# =========================================================

def get_db():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_database():
    conn = get_db()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            full_name TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            token TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
            created_at TEXT NOT NULL
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS recommendations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            kind TEXT NOT NULL,
            total_budget REAL NOT NULL,
            result TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)

    conn.commit()
    conn.close()


init_database()


# =========================================================
# PASSWORD FUNCTIONS
# =========================================================

def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)

    key = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        120000
    )

    return salt.hex() + ":" + key.hex()


def verify_password(password: str, stored_password: str) -> bool:
    try:
        salt_hex, key_hex = stored_password.split(":")

        salt = bytes.fromhex(salt_hex)

        key = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt,
            120000
        )

        return secrets.compare_digest(
            key.hex(),
            key_hex
        )

    except Exception:
        return False


# =========================================================
# AUTHENTICATION
# =========================================================

def get_current_user(request: Request):

    token = request.cookies.get("pocketsmart_session")

    if not token:
        return None

    conn = get_db()

    row = conn.execute("""
        SELECT users.*
        FROM sessions
        JOIN users ON users.id = sessions.user_id
        WHERE sessions.token = ?
    """, (token,)).fetchone()

    conn.close()

    return row


def require_user(request: Request):

    user = get_current_user(request)

    if not user:
        raise HTTPException(
            status_code=401,
            detail="Please login first."
        )

    return user


# =========================================================
# DATA MODELS
# =========================================================

class RegisterRequest(BaseModel):
    username: str
    email: str
    full_name: str
    password: str


class LoginRequest(BaseModel):
    username: str
    password: str


class HomeRequest(BaseModel):
    total_budget: float
    num_lights: int
    num_fans: int
    num_furniture: int
    num_dining_tables: int
    has_living_room: bool
    has_kitchen: bool
    has_bedroom: bool
    additional_requirements: str = ""


class PartyRequest(BaseModel):
    total_budget: float
    occasion: str
    num_guests: int
    party_type: str
    needs: list[str] = []
    additional_requirements: str = ""


# =========================================================
# HELPER FUNCTIONS
# =========================================================

def money(value):
    return round(float(value), 2)


def create_item(
    name,
    description,
    quantity,
    estimated_price,
    shopping_links=None
):
    return {
        "name": name,
        "description": description,
        "quantity": quantity,
        "estimated_price": money(estimated_price),
        "shopping_links": shopping_links or {}
    }


def create_result(
    total_budget,
    categories,
    source="PocketSmart AI",
    venue_suggestions=None,
    additional_suggestions=None
):

    used = sum(
        float(category["allocation"])
        for category in categories
    )

    remaining = max(
        0,
        float(total_budget) - used
    )

    return {
        "total_budget": money(total_budget),
        "remaining_budget": money(remaining),
        "source": source,
        "budget_breakdown": categories,
        "venue_suggestions": venue_suggestions or [],
        "additional_suggestions": additional_suggestions or []
    }


def save_recommendation(
    user_id,
    kind,
    total_budget,
    result
):

    conn = get_db()

    conn.execute("""
        INSERT INTO recommendations
        (
            user_id,
            kind,
            total_budget,
            result,
            created_at
        )
        VALUES (?, ?, ?, ?, ?)
    """, (
        user_id,
        kind,
        total_budget,
        json.dumps(result),
        datetime.now().isoformat()
    ))

    conn.commit()
    conn.close()


# =========================================================
# HOME PAGE
# =========================================================

@app.get("/")
def home():

    return FileResponse(
        TEMPLATES_DIR / "index.html"
    )


# =========================================================
# HEALTH CHECK
# =========================================================

@app.get("/health")
def health():

    return {
        "status": "ok",
        "message": "PocketSmart AI is running"
    }


# =========================================================
# REGISTER
# =========================================================

@app.post("/api/register")
def register(data: RegisterRequest):

    username = data.username.strip()
    email = data.email.strip()
    full_name = data.full_name.strip()
    password = data.password

    if not username or not email or not full_name:
        raise HTTPException(
            status_code=400,
            detail="All fields are required."
        )

    if len(password) < 4:
        raise HTTPException(
            status_code=400,
            detail="Password must contain at least 4 characters."
        )

    conn = get_db()

    existing = conn.execute("""
        SELECT id
        FROM users
        WHERE username = ? OR email = ?
    """, (username, email)).fetchone()

    if existing:
        conn.close()

        raise HTTPException(
            status_code=400,
            detail="Username or email already exists."
        )

    password_hash = hash_password(password)

    conn.execute("""
        INSERT INTO users
        (
            username,
            email,
            full_name,
            password_hash,
            created_at
        )
        VALUES (?, ?, ?, ?, ?)
    """, (
        username,
        email,
        full_name,
        password_hash,
        datetime.now().isoformat()
    ))

    conn.commit()
    conn.close()

    return {
        "success": True,
        "message": "Account created successfully!"
    }


# =========================================================
# LOGIN
# =========================================================

@app.post("/api/login")
def login(data: LoginRequest):

    conn = get_db()

    user = conn.execute("""
        SELECT *
        FROM users
        WHERE username = ?
    """, (data.username.strip(),)).fetchone()

    if not user:
        conn.close()

        raise HTTPException(
            status_code=401,
            detail="Invalid username or password."
        )

    if not verify_password(
        data.password,
        user["password_hash"]
    ):
        conn.close()

        raise HTTPException(
            status_code=401,
            detail="Invalid username or password."
        )

    token = secrets.token_urlsafe(32)

    conn.execute("""
        INSERT INTO sessions
        (
            token,
            user_id,
            created_at
        )
        VALUES (?, ?, ?)
    """, (
        token,
        user["id"],
        datetime.now().isoformat()
    ))

    conn.commit()
    conn.close()

    response = {
        "success": True,
        "message": "Login successful!"
    }

    from fastapi.responses import JSONResponse

    json_response = JSONResponse(content=response)

    json_response.set_cookie(
        key="pocketsmart_session",
        value=token,
        httponly=True,
        samesite="lax"
    )

    return json_response


# =========================================================
# LOGOUT
# =========================================================

@app.post("/api/logout")
def logout(request: Request):

    token = request.cookies.get(
        "pocketsmart_session"
    )

    if token:

        conn = get_db()

        conn.execute(
            "DELETE FROM sessions WHERE token = ?",
            (token,)
        )

        conn.commit()
        conn.close()

    from fastapi.responses import JSONResponse

    response = JSONResponse({
        "success": True,
        "message": "Logged out successfully."
    })

    response.delete_cookie(
        "pocketsmart_session"
    )

    return response


# =========================================================
# CURRENT USER
# =========================================================

@app.get("/api/me")
def me(request: Request):

    user = get_current_user(request)

    if not user:
        raise HTTPException(
            status_code=401,
            detail="Not logged in."
        )

    return {
        "id": user["id"],
        "username": user["username"],
        "email": user["email"],
        "full_name": user["full_name"]
    }


# =========================================================
# HOME BUDGET RECOMMENDATION
# =========================================================

@app.post("/api/home")
def home_budget(
    data: HomeRequest,
    request: Request
):

    user = require_user(request)

    budget = float(data.total_budget)

    if budget <= 0:
        raise HTTPException(
            status_code=400,
            detail="Budget must be greater than zero."
        )

    categories = []

    # Lights
    light_cost = data.num_lights * 800

    if light_cost > 0:

        categories.append({
            "category": "Lighting",
            "allocation": money(light_cost),
            "items": [
                create_item(
                    "LED Lights",
                    "Energy-efficient LED lights",
                    data.num_lights,
                    800,
                    {
                        "amazon": "https://www.amazon.in/s?k=LED+lights"
                    }
                )
            ]
        })

    # Fans
    fan_cost = data.num_fans * 2200

    if fan_cost > 0:

        categories.append({
            "category": "Fans",
            "allocation": money(fan_cost),
            "items": [
                create_item(
                    "Ceiling Fan",
                    "Energy-efficient ceiling fan",
                    data.num_fans,
                    2200,
                    {
                        "amazon": "https://www.amazon.in/s?k=ceiling+fan"
                    }
                )
            ]
        })

    # Furniture
    furniture_cost = data.num_furniture * 5000

    if furniture_cost > 0:

        categories.append({
            "category": "Furniture",
            "allocation": money(furniture_cost),
            "items": [
                create_item(
                    "Basic Furniture Set",
                    "Useful furniture for home",
                    data.num_furniture,
                    5000,
                    {
                        "amazon": "https://www.amazon.in/s?k=home+furniture"
                    }
                )
            ]
        })

    # Dining
    dining_cost = data.num_dining_tables * 8000

    if dining_cost > 0:

        categories.append({
            "category": "Dining",
            "allocation": money(dining_cost),
            "items": [
                create_item(
                    "Dining Table",
                    "Dining table suitable for home",
                    data.num_dining_tables,
                    8000,
                    {
                        "amazon": "https://www.amazon.in/s?k=dining+table"
                    }
                )
            ]
        })

    # Rooms
    room_items = []

    if data.has_living_room:
        room_items.append(
            create_item(
                "Living Room Setup",
                "Basic living room arrangement",
                1,
                12000,
                {
                    "amazon": "https://www.amazon.in/s?k=living+room+furniture"
                }
            )
        )

    if data.has_kitchen:
        room_items.append(
            create_item(
                "Kitchen Essentials",
                "Basic kitchen requirements",
                1,
                10000,
                {
                    "amazon": "https://www.amazon.in/s?k=kitchen+essentials"
                }
            )
        )

    if data.has_bedroom:
        room_items.append(
            create_item(
                "Bedroom Setup",
                "Basic bedroom requirements",
                1,
                15000,
                {
                    "amazon": "https://www.amazon.in/s?k=bedroom+furniture"
                }
            )
        )

    if room_items:

        room_cost = sum(
            item["estimated_price"]
            for item in room_items
        )

        categories.append({
            "category": "Rooms",
            "allocation": money(room_cost),
            "items": room_items
        })

    # If budget is smaller than calculated cost,
    # scale allocations.
    calculated = sum(
        category["allocation"]
        for category in categories
    )

    if calculated > budget and calculated > 0:

        ratio = budget / calculated

        for category in categories:

            category["allocation"] = money(
                category["allocation"] * ratio
            )

            for item in category["items"]:

                item["estimated_price"] = money(
                    item["estimated_price"] * ratio
                )

    suggestions = [
        "Compare prices before purchasing.",
        "Keep 5–10% of your budget for unexpected expenses.",
        "Choose energy-efficient appliances where possible."
    ]

    if data.additional_requirements:
        suggestions.append(
            "Additional requirement: "
            + data.additional_requirements
        )

    result = create_result(
        budget,
        categories,
        source="PocketSmart AI Budget Engine",
        additional_suggestions=suggestions
    )

    save_recommendation(
        user["id"],
        "home",
        budget,
        result
    )

    return result


# =========================================================
# PARTY BUDGET
# =========================================================

@app.post("/api/party")
def party_budget(
    data: PartyRequest,
    request: Request
):

    user = require_user(request)

    budget = float(data.total_budget)

    if budget <= 0:
        raise HTTPException(
            status_code=400,
            detail="Budget must be greater than zero."
        )

    guests = max(1, data.num_guests)

    food_cost = guests * 350

    decoration_cost = budget * 0.15

    music_cost = budget * 0.10

    invitation_cost = guests * 30

    categories = [

        {
            "category": "Food",
            "allocation": money(food_cost),
            "items": [
                create_item(
                    "Party Food",
                    f"Food arrangement for {guests} guests",
                    guests,
                    350,
                    {
                        "amazon": "https://www.amazon.in/s?k=party+food"
                    }
                )
            ]
        },

        {
            "category": "Decoration",
            "allocation": money(decoration_cost),
            "items": [
                create_item(
                    "Party Decoration",
                    "Balloons, lights and decoration items",
                    1,
                    decoration_cost,
                    {
                        "amazon": "https://www.amazon.in/s?k=party+decorations"
                    }
                )
            ]
        },

        {
            "category": "Music & Entertainment",
            "allocation": money(music_cost),
            "items": [
                create_item(
                    "Music Setup",
                    "Basic music and entertainment setup",
                    1,
                    music_cost,
                    {}
                )
            ]
        },

        {
            "category": "Invitations",
            "allocation": money(invitation_cost),
            "items": [
                create_item(
                    "Invitations",
                    "Digital or printed invitations",
                    guests,
                    30,
                    {}
                )
            ]
        }
    ]

    # Apply selected needs
    if data.needs:

        for need in data.needs:

            clean_need = need.strip()

            if clean_need:

                categories.append({
                    "category": clean_need,
                    "allocation": money(budget * 0.05),
                    "items": [
                        create_item(
                            clean_need,
                            f"Recommended requirement for {data.occasion}",
                            1,
                            budget * 0.05,
                            {}
                        )
                    ]
                })

    # Scale if necessary
    calculated = sum(
        category["allocation"]
        for category in categories
    )

    if calculated > budget:

        ratio = budget / calculated

        for category in categories:

            category["allocation"] = money(
                category["allocation"] * ratio
            )

            for item in category["items"]:

                item["estimated_price"] = money(
                    item["estimated_price"] * ratio
                )

    venues = [

        {
            "name": "Local Community Hall",
            "capacity": guests,
            "estimated_cost": money(budget * 0.20)
        },

        {
            "name": "Hotel Party Hall",
            "capacity": guests,
            "estimated_cost": money(budget * 0.30)
        },

        {
            "name": "Outdoor Event Space",
            "capacity": guests,
            "estimated_cost": money(budget * 0.15)
        }
    ]

    suggestions = [
        f"Occasion: {data.occasion}",
        f"Party type: {data.party_type}",
        "Book the venue early.",
        "Compare catering packages.",
        "Keep some money for unexpected expenses."
    ]

    if data.additional_requirements:

        suggestions.append(
            "Additional requirement: "
            + data.additional_requirements
        )

    result = create_result(
        budget,
        categories,
        source="PocketSmart AI Party Planner",
        venue_suggestions=venues,
        additional_suggestions=suggestions
    )

    save_recommendation(
        user["id"],
        "party",
        budget,
        result
    )

    return result


# =========================================================
# JEWELRY BUDGET
# =========================================================

@app.post("/api/jewelry")
async def jewelry_budget(
    request: Request,
    total_budget: float = Form(...),
    occasion: str = Form("General"),
    preferences: str = Form(""),
    image: UploadFile | None = File(None)
):

    user = require_user(request)

    if total_budget <= 0:
        raise HTTPException(
            status_code=400,
            detail="Budget must be greater than zero."
        )

    saved_image = None

    if image and image.filename:

        extension = Path(image.filename).suffix.lower()

        allowed = [
            ".jpg",
            ".jpeg",
            ".png",
            ".webp"
        ]

        if extension not in allowed:

            raise HTTPException(
                status_code=400,
                detail="Only JPG, JPEG, PNG and WEBP images are allowed."
            )

        safe_name = (
            secrets.token_hex(8)
            + extension
        )

        file_path = UPLOAD_DIR / safe_name

        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(
                image.file,
                buffer
            )

        saved_image = safe_name

    budget = float(total_budget)

    categories = [

        {
            "category": "Jewelry",
            "allocation": money(budget * 0.65),
            "items": [
                create_item(
                    "Gold Necklace",
                    "Simple jewelry recommendation",
                    1,
                    budget * 0.65,
                    {
                        "amazon": "https://www.amazon.in/s?k=gold+necklace"
                    }
                )
            ]
        },

        {
            "category": "Earrings",
            "allocation": money(budget * 0.15),
            "items": [
                create_item(
                    "Elegant Earrings",
                    "Suitable earrings for the occasion",
                    1,
                    budget * 0.15,
                    {
                        "amazon": "https://www.amazon.in/s?k=earrings"
                    }
                )
            ]
        },

        {
            "category": "Accessories",
            "allocation": money(budget * 0.10),
            "items": [
                create_item(
                    "Jewelry Accessories",
                    "Additional accessories",
                    1,
                    budget * 0.10,
                    {
                        "amazon": "https://www.amazon.in/s?k=jewelry+accessories"
                    }
                )
            ]
        }
    ]

    suggestions = [
        f"Occasion: {occasion}",
        "Compare making charges before buying.",
        "Check purity and certification.",
        "Keep the invoice and purchase documents safely."
    ]

    if preferences:

        suggestions.append(
            "Your preferences: "
            + preferences
        )

    if saved_image:

        suggestions.append(
            "Reference image uploaded successfully."
        )

    result = create_result(
        budget,
        categories,
        source="PocketSmart AI Jewelry Planner",
        additional_suggestions=suggestions
    )

    save_recommendation(
        user["id"],
        "jewelry",
        budget,
        result
    )

    return result


# =========================================================
# HISTORY
# =========================================================

@app.get("/api/history")
def history(request: Request):

    user = require_user(request)

    conn = get_db()

    rows = conn.execute("""
        SELECT
            id,
            kind,
            total_budget,
            created_at
        FROM recommendations
        WHERE user_id = ?
        ORDER BY id DESC
    """, (user["id"],)).fetchall()

    conn.close()

    return [
        {
            "id": row["id"],
            "kind": row["kind"],
            "total_budget": row["total_budget"],
            "created_at": row["created_at"]
        }
        for row in rows
    ]


# =========================================================
# HISTORY DETAILS
# =========================================================

@app.get("/api/history/{recommendation_id}")
def history_detail(
    recommendation_id: int,
    request: Request
):

    user = require_user(request)

    conn = get_db()

    row = conn.execute("""
        SELECT *
        FROM recommendations
        WHERE id = ?
        AND user_id = ?
    """, (
        recommendation_id,
        user["id"]
    )).fetchone()

    conn.close()

    if not row:

        raise HTTPException(
            status_code=404,
            detail="Recommendation not found."
        )

    return {
        "id": row["id"],
        "kind": row["kind"],
        "total_budget": row["total_budget"],
        "created_at": row["created_at"],
        "result": json.loads(row["result"])
    }


# =========================================================
# RUN SERVER
# =========================================================

if __name__ == "__main__":

    import uvicorn

    uvicorn.run(
        "app:app",
        host="127.0.0.1",
        port=8000,
        reload=True
    )