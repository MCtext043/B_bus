from fastapi import FastAPI, Request, Depends, HTTPException, Form, status, Query
from fastapi.responses import RedirectResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
import uvicorn
import random
from datetime import datetime, date, timedelta

from database import engine, get_db
from models import Base, Trip, Ticket, Dispatcher
from auth import authenticate_dispatcher, create_access_token, get_password_hash, get_current_dispatcher

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Bus Ticket System")

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Templates
templates = Jinja2Templates(directory="templates")

# Ticket number generator with collision check
def generate_ticket_number(db: Session) -> str:
    existing = set(n[0] for n in db.query(Ticket.ticket_number).all())
    for num in range(1, 1000):
        candidate = f"{num:03d}"
        if candidate not in existing:
            return candidate
    raise HTTPException(status_code=500, detail="Нет свободных номеров билетов")


def require_super(dispatcher: Dispatcher):
    if not dispatcher.is_super:
        raise HTTPException(status_code=403, detail="Требуются права главного диспетчера")
    return dispatcher

# Routes

# User routes (no authentication required)
@app.get("/", response_class=HTMLResponse)
async def role_choice(request: Request):
    return templates.TemplateResponse("role_choice.html", {"request": request})


@app.get("/user", response_class=HTMLResponse)
async def user_home(request: Request, selected_date: Optional[str] = None, db: Session = Depends(get_db)):
    today = date.today()
    selected = date.today()
    if selected_date:
        try:
            selected = date.fromisoformat(selected_date)
        except ValueError:
            selected = today

    # Get trips for today and tomorrow, or selected date
    if selected == today:
        trips = db.query(Trip).filter(
            Trip.departure_date.in_([today, today + timedelta(days=1)]),
            Trip.is_active == 1
        ).order_by(Trip.departure_date, Trip.departure_time).all()
    else:
        trips = db.query(Trip).filter(
            Trip.departure_date == selected,
            Trip.is_active == 1
        ).order_by(Trip.departure_time).all()

    return templates.TemplateResponse("user_home.html", {
        "request": request,
        "trips": trips,
        "today": today,
        "selected_date": selected,
        "tomorrow": today + timedelta(days=1)
    })

@app.get("/trip/{trip_id}", response_class=HTMLResponse)
async def trip_details(request: Request, trip_id: int, db: Session = Depends(get_db)):
    trip = db.query(Trip).filter(Trip.id == trip_id, Trip.is_active == 1).first()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")

    return templates.TemplateResponse("user_trip_details.html", {
        "request": request,
        "trip": trip
    })

@app.post("/trip/{trip_id}/book")
async def book_ticket(
    request: Request,
    trip_id: int,
    passenger_name: str = Form(...),
    passenger_phone: str = Form(...),
    boarding_point: str = Form(...),
    agree_privacy: str = Form(...),
    db: Session = Depends(get_db)
):
    # Check privacy agreement
    if not agree_privacy:
        return templates.TemplateResponse("error.html", {
            "request": request,
            "error": "Необходимо согласиться с обработкой персональных данных"
        })

    trip = db.query(Trip).filter(Trip.id == trip_id, Trip.is_active == 1).first()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")

    if trip.available_seats <= 0:
        return templates.TemplateResponse("error.html", {
            "request": request,
            "error": "Нет доступных мест на этот рейс"
        })

    # Create ticket with unique number
    ticket_number = generate_ticket_number(db)
    ticket = Ticket(
        ticket_number=ticket_number,
        trip_id=trip_id,
        passenger_name=passenger_name,
        passenger_phone=passenger_phone,
        boarding_point=boarding_point,
        payment_status="unpaid",
        payment_amount=trip.price
    )

    db.add(ticket)
    trip.available_seats -= 1
    try:
        db.commit()
        db.refresh(ticket)
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Ошибка при создании билета")

    return templates.TemplateResponse("user_payment.html", {
        "request": request,
        "ticket": ticket,
        "trip": trip
    })

@app.post("/ticket/{ticket_id}/pay")
async def pay_ticket(request: Request, ticket_id: int, db: Session = Depends(get_db)):
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    # Mark as paid (in real app, this would integrate with payment system)
    ticket.payment_status = "paid"
    ticket.status = "pending_confirmation"
    db.commit()

    return templates.TemplateResponse("user_success.html", {
        "request": request,
        "ticket": ticket
    })

@app.get("/tickets", response_class=HTMLResponse)
async def user_tickets(request: Request):
    return templates.TemplateResponse("user_tickets.html", {"request": request})

@app.get("/tickets/search")
async def search_tickets_get(request: Request):
    return RedirectResponse(url="/tickets", status_code=302)

@app.post("/tickets/search")
async def search_tickets(
    request: Request,
    phone: str = Form(...),
    db: Session = Depends(get_db)
):
    try:
        # Get current tickets (not expired)
        today = date.today()
        current_tickets = db.query(Ticket).join(Trip).filter(
            Ticket.passenger_phone == phone,
            Trip.departure_date >= today
        ).all()

        # Get archived tickets (expired)
        archived_tickets = db.query(Ticket).join(Trip).filter(
            Ticket.passenger_phone == phone,
            Trip.departure_date < today
        ).all()

        return templates.TemplateResponse("user_tickets.html", {
            "request": request,
            "current_tickets": current_tickets,
            "archived_tickets": archived_tickets,
            "searched": True,
            "search_phone": phone
        })
    except Exception as e:
        return templates.TemplateResponse("user_tickets.html", {
            "request": request,
            "error": f"Ошибка поиска: {str(e)}",
            "searched": False
        })

@app.get("/ticket/{ticket_id}", response_class=HTMLResponse)
async def ticket_details(request: Request, ticket_id: int, db: Session = Depends(get_db)):
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    return templates.TemplateResponse("user_ticket_details.html", {
        "request": request,
        "ticket": ticket
    })

# Dispatcher routes
@app.get("/dispatcher/login", response_class=HTMLResponse)
async def dispatcher_login_page(request: Request):
    return templates.TemplateResponse("dispatcher_login.html", {"request": request})

@app.post("/dispatcher/login")
async def dispatcher_login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    dispatcher = authenticate_dispatcher(db, username, password)
    if not dispatcher:
        return templates.TemplateResponse("dispatcher_login.html", {
            "request": request,
            "error": "Invalid username or password"
        })

    if not dispatcher.is_super and not dispatcher.is_approved:
        return templates.TemplateResponse("dispatcher_login.html", {
            "request": request,
            "error": "Аккаунт ожидает одобрения главным диспетчером"
        })

    access_token = create_access_token(
        data={"sub": dispatcher.username},
        expires_delta=timedelta(minutes=30)
    )

    response = RedirectResponse(url="/dispatcher/dashboard", status_code=302)
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        path="/",
        max_age=1800,
        samesite="lax"
    )
    return response

@app.get("/dispatcher/dashboard", response_class=HTMLResponse)
async def dispatcher_dashboard(
    request: Request,
    db: Session = Depends(get_db),
    current_dispatcher: Dispatcher = Depends(get_current_dispatcher)
):
    from datetime import datetime
    now = datetime.now()
    today = date.today()

    # Calculate statistics
    today_trips = db.query(Trip).filter(Trip.departure_date == today).count()

    today_tickets = db.query(Ticket).join(Trip).filter(
        Trip.departure_date == today,
        Ticket.payment_status == "paid"
    ).count()

    pending_tickets = db.query(Ticket).filter(
        Ticket.status == "pending_confirmation"
    ).count()

    today_revenue_result = db.query(func.sum(Ticket.payment_amount)).join(Trip).filter(
        Trip.departure_date == today,
        Ticket.payment_status == "paid"
    ).scalar()

    today_revenue = today_revenue_result if today_revenue_result else 0

    pending_dispatchers = []
    if current_dispatcher.is_super:
        pending_dispatchers = db.query(Dispatcher).filter(
            Dispatcher.is_super == 0,
            Dispatcher.is_approved == 0
        ).all()

    return templates.TemplateResponse("dispatcher_dashboard.html", {
        "request": request,
        "dispatcher": current_dispatcher,
        "now": now,
        "today": today,
        "today_trips": today_trips,
        "today_tickets": today_tickets,
        "pending_tickets": pending_tickets,
        "today_revenue": today_revenue,
        "pending_dispatchers": pending_dispatchers
    })

@app.get("/dispatcher/trips", response_class=HTMLResponse)
async def dispatcher_trips(request: Request, db: Session = Depends(get_db), current_dispatcher: Dispatcher = Depends(get_current_dispatcher)):
    today = date.today()
    tomorrow = today + timedelta(days=1)

    trips = db.query(Trip).filter(
        Trip.departure_date.in_([today, tomorrow])
    ).order_by(Trip.departure_date, Trip.departure_time).all()

    return templates.TemplateResponse("dispatcher_trips.html", {
        "request": request,
        "trips": trips,
        "today": today,
        "tomorrow": tomorrow
    })

@app.get("/dispatcher/trip/{trip_id}", response_class=HTMLResponse)
async def dispatcher_trip_details(
    request: Request,
    trip_id: int,
    db: Session = Depends(get_db),
    current_dispatcher: Dispatcher = Depends(get_current_dispatcher)
):
    trip = db.query(Trip).filter(Trip.id == trip_id).first()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")

    tickets = db.query(Ticket).filter(
        Ticket.trip_id == trip_id,
        Ticket.payment_status == "paid"
    ).order_by(Ticket.created_at).all()

    return templates.TemplateResponse("dispatcher_trip_details.html", {
        "request": request,
        "trip": trip,
        "tickets": tickets
    })


@app.get("/dispatcher/trip/{trip_id}/edit", response_class=HTMLResponse)
async def edit_trip_page(
    request: Request,
    trip_id: int,
    db: Session = Depends(get_db),
    current_dispatcher: Dispatcher = Depends(get_current_dispatcher)
):
    trip = db.query(Trip).filter(Trip.id == trip_id).first()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")

    today = date.today()
    return templates.TemplateResponse("dispatcher_edit_trip.html", {
        "request": request,
        "trip": trip,
        "today": today
    })


@app.post("/dispatcher/trip/{trip_id}/edit")
async def edit_trip(
    request: Request,
    trip_id: int,
    departure_city: str = Form(...),
    arrival_city: str = Form(...),
    departure_date: str = Form(...),
    departure_time: str = Form(...),
    arrival_time: str = Form(...),
    bus_number: str = Form(...),
    bus_name: str = Form(...),
    bus_color: str = Form(...),
    total_seats: int = Form(...),
    price: float = Form(0.0),
    db: Session = Depends(get_db),
    current_dispatcher: Dispatcher = Depends(get_current_dispatcher)
):
    trip = db.query(Trip).filter(Trip.id == trip_id).first()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")

    sold = trip.total_seats - trip.available_seats
    new_available = max(0, total_seats - sold)

    trip.departure_city = departure_city
    trip.arrival_city = arrival_city
    trip.departure_date = date.fromisoformat(departure_date)
    trip.departure_time = departure_time
    trip.arrival_time = arrival_time
    trip.bus_number = bus_number
    trip.bus_name = bus_name
    trip.bus_color = bus_color
    trip.total_seats = total_seats
    trip.available_seats = new_available
    trip.price = price

    db.commit()

    return RedirectResponse(url=f"/dispatcher/trip/{trip_id}", status_code=302)


@app.post("/dispatcher/trip/{trip_id}/delete")
async def delete_trip(
    request: Request,
    trip_id: int,
    db: Session = Depends(get_db),
    current_dispatcher: Dispatcher = Depends(get_current_dispatcher)
):
    trip = db.query(Trip).filter(Trip.id == trip_id).first()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")

    # Remove tickets first
    db.query(Ticket).filter(Ticket.trip_id == trip_id).delete()
    db.delete(trip)
    db.commit()

    return {"success": True}

@app.post("/dispatcher/ticket/{ticket_id}/status")
async def update_ticket_status(
    request: Request,
    ticket_id: int,
    status: str = Form(...),
    reason: str = Form(""),
    db: Session = Depends(get_db),
    current_dispatcher: Dispatcher = Depends(get_current_dispatcher)
):
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    ticket.status = status
    if reason:
        ticket.status_reason = reason

    db.commit()

    return RedirectResponse(url=f"/dispatcher/trip/{ticket.trip_id}", status_code=302)

@app.get("/dispatcher/create-trip", response_class=HTMLResponse)
async def create_trip_page(request: Request, current_dispatcher: Dispatcher = Depends(get_current_dispatcher)):
    from datetime import datetime
    now = datetime.now()
    today = date.today()

    return templates.TemplateResponse("dispatcher_create_trip.html", {
        "request": request,
        "now": now,
        "today": today
    })

@app.post("/dispatcher/create-trip")
async def create_trip(
    request: Request,
    departure_city: str = Form(...),
    arrival_city: str = Form(...),
    departure_date: str = Form(...),
    departure_time: str = Form(...),
    arrival_time: str = Form(...),
    bus_number: str = Form(...),
    bus_name: str = Form(...),
    bus_color: str = Form(...),
    total_seats: int = Form(...),
    price: float = Form(0.0),
    db: Session = Depends(get_db),
    current_dispatcher: Dispatcher = Depends(get_current_dispatcher)
):
    trip = Trip(
        departure_city=departure_city,
        arrival_city=arrival_city,
        departure_date=date.fromisoformat(departure_date),
        departure_time=departure_time,
        arrival_time=arrival_time,
        bus_number=bus_number,
        bus_name=bus_name,
        bus_color=bus_color,
        total_seats=total_seats,
        available_seats=total_seats,
        price=price
    )

    db.add(trip)
    db.commit()

    return RedirectResponse(url="/dispatcher/trips", status_code=302)


@app.get("/dispatcher/register", response_class=HTMLResponse)
async def dispatcher_register_page(request: Request):
    return templates.TemplateResponse("dispatcher_register.html", {"request": request})


@app.post("/dispatcher/register")
async def dispatcher_register(
    request: Request,
    username: str = Form(...),
    email: str = Form(...),
    phone: str = Form(""),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    existing = db.query(Dispatcher).filter(
        (Dispatcher.username == username) | (Dispatcher.email == email)
    ).first()
    if existing:
        return templates.TemplateResponse("dispatcher_register.html", {
            "request": request,
            "error": "Пользователь с таким логином или email уже существует"
        })

    new_disp = Dispatcher(
        username=username,
        email=email,
        phone=phone,
        hashed_password=get_password_hash(password),
        is_super=0,
        is_approved=0
    )
    db.add(new_disp)
    db.commit()

    return templates.TemplateResponse("dispatcher_register.html", {
        "request": request,
        "success": "Заявка отправлена. Ожидайте одобрения главным диспетчером."
    })


@app.post("/dispatcher/approve/{dispatcher_id}")
async def approve_dispatcher(
    dispatcher_id: int,
    db: Session = Depends(get_db),
    current_dispatcher: Dispatcher = Depends(get_current_dispatcher)
):
    require_super(current_dispatcher)
    disp = db.query(Dispatcher).filter(Dispatcher.id == dispatcher_id).first()
    if not disp:
        raise HTTPException(status_code=404, detail="Dispatcher not found")
    disp.is_approved = 1
    db.commit()
    return RedirectResponse(url="/dispatcher/dashboard", status_code=302)


@app.post("/dispatcher/reject/{dispatcher_id}")
async def reject_dispatcher(
    dispatcher_id: int,
    db: Session = Depends(get_db),
    current_dispatcher: Dispatcher = Depends(get_current_dispatcher)
):
    require_super(current_dispatcher)
    disp = db.query(Dispatcher).filter(Dispatcher.id == dispatcher_id).first()
    if not disp:
        raise HTTPException(status_code=404, detail="Dispatcher not found")
    db.delete(disp)
    db.commit()
    return RedirectResponse(url="/dispatcher/dashboard", status_code=302)

@app.post("/dispatcher/logout")
async def dispatcher_logout():
    response = RedirectResponse(url="/", status_code=302)
    response.delete_cookie(key="access_token")
    return response

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)
