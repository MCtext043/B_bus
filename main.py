from fastapi import FastAPI, Request, Depends, HTTPException, Form, status
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import List
import uvicorn

from database import engine, get_db
from models import Base, Route, Schedule, Admin
from auth import authenticate_admin, create_access_token, get_password_hash, get_current_admin
from datetime import timedelta

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Bus Schedule System")

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Templates
templates = Jinja2Templates(directory="templates")

# Routes
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/schedule", response_class=HTMLResponse)
async def view_schedule(request: Request, db: Session = Depends(get_db)):
    routes = db.query(Route).all()
    schedules = db.query(Schedule).filter(Schedule.is_active == 1).all()

    # Group schedules by route
    route_schedules = {}
    for route in routes:
        route_schedules[route.id] = {
            "route": route,
            "schedules": [s for s in schedules if s.route_id == route.id]
        }

    return templates.TemplateResponse("schedule.html", {
        "request": request,
        "route_schedules": route_schedules
    })

@app.get("/admin/login", response_class=HTMLResponse)
async def admin_login_page(request: Request):
    return templates.TemplateResponse("admin_login.html", {"request": request})

@app.post("/admin/login")
async def admin_login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    admin = authenticate_admin(db, username, password)
    if not admin:
        return templates.TemplateResponse("admin_login.html", {
            "request": request,
            "error": "Invalid username or password"
        })

    access_token = create_access_token(
        data={"sub": admin.username},
        expires_delta=timedelta(minutes=30)
    )

    response = RedirectResponse(url="/admin/dashboard", status_code=302)
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        path="/",
        max_age=1800,  # 30 minutes
        samesite="lax"
    )
    return response

@app.get("/admin/register", response_class=HTMLResponse)
async def admin_register_page(request: Request):
    return templates.TemplateResponse("admin_register.html", {"request": request})

@app.post("/admin/register")
async def admin_register(
    request: Request,
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    agree_privacy: str = Form(...),
    db: Session = Depends(get_db)
):
    # Check privacy agreement
    if not agree_privacy:
        return templates.TemplateResponse("admin_register.html", {
            "request": request,
            "error": "Необходимо согласиться с обработкой персональных данных"
        })

    # Check if admin already exists
    existing_admin = db.query(Admin).filter(
        (Admin.username == username) | (Admin.email == email)
    ).first()

    if existing_admin:
        return templates.TemplateResponse("admin_register.html", {
            "request": request,
            "error": "Username or email already registered"
        })

    # Create new admin
    hashed_password = get_password_hash(password)
    new_admin = Admin(
        username=username,
        email=email,
        hashed_password=hashed_password
    )

    db.add(new_admin)
    db.commit()
    db.refresh(new_admin)

    return RedirectResponse(url="/admin/login", status_code=302)

@app.get("/admin/dashboard", response_class=HTMLResponse)
async def admin_dashboard(request: Request, current_admin: Admin = Depends(get_current_admin)):
    return templates.TemplateResponse("admin_dashboard.html", {
        "request": request,
        "admin": current_admin
    })

@app.get("/admin/routes", response_class=HTMLResponse)
async def admin_routes(request: Request, db: Session = Depends(get_db), current_admin: Admin = Depends(get_current_admin)):
    routes = db.query(Route).all()
    return templates.TemplateResponse("admin_routes.html", {
        "request": request,
        "routes": routes
    })

@app.get("/admin/route/add", response_class=HTMLResponse)
async def add_route_page(request: Request, current_admin: Admin = Depends(get_current_admin)):
    return templates.TemplateResponse("admin_route_form.html", {"request": request})

@app.post("/admin/route/add")
async def add_route(
    request: Request,
    route_number: str = Form(...),
    route_name: str = Form(...),
    description: str = Form(""),
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    # Check if route number already exists
    existing_route = db.query(Route).filter(Route.route_number == route_number).first()
    if existing_route:
        return templates.TemplateResponse("admin_route_form.html", {
            "request": request,
            "error": "Route number already exists"
        })

    new_route = Route(
        route_number=route_number,
        route_name=route_name,
        description=description
    )

    db.add(new_route)
    db.commit()
    db.refresh(new_route)

    return RedirectResponse(url="/admin/routes", status_code=302)

@app.get("/admin/route/{route_id}/edit", response_class=HTMLResponse)
async def edit_route_page(
    request: Request,
    route_id: int,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    route = db.query(Route).filter(Route.id == route_id).first()
    if not route:
        raise HTTPException(status_code=404, detail="Route not found")

    return templates.TemplateResponse("admin_route_edit.html", {
        "request": request,
        "route": route
    })

@app.post("/admin/route/{route_id}/edit")
async def edit_route(
    request: Request,
    route_id: int,
    route_number: str = Form(...),
    route_name: str = Form(...),
    description: str = Form(""),
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    route = db.query(Route).filter(Route.id == route_id).first()
    if not route:
        raise HTTPException(status_code=404, detail="Route not found")

    # Check if route number already exists (excluding current route)
    existing_route = db.query(Route).filter(
        Route.route_number == route_number,
        Route.id != route_id
    ).first()
    if existing_route:
        return templates.TemplateResponse("admin_route_edit.html", {
            "request": request,
            "route": route,
            "error": "Номер маршрута уже существует"
        })

    route.route_number = route_number
    route.route_name = route_name
    route.description = description

    db.commit()

    return RedirectResponse(url="/admin/routes", status_code=302)

@app.post("/admin/route/{route_id}/delete")
async def delete_route(
    request: Request,
    route_id: int,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    route = db.query(Route).filter(Route.id == route_id).first()
    if not route:
        raise HTTPException(status_code=404, detail="Route not found")

    # Delete all schedules for this route first
    db.query(Schedule).filter(Schedule.route_id == route_id).delete()

    # Delete the route
    db.delete(route)
    db.commit()

    return {"success": True}

@app.get("/admin/route/{route_id}/schedules", response_class=HTMLResponse)
async def admin_route_schedules(
    request: Request,
    route_id: int,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    route = db.query(Route).filter(Route.id == route_id).first()
    if not route:
        raise HTTPException(status_code=404, detail="Route not found")

    schedules = db.query(Schedule).filter(Schedule.route_id == route_id).all()

    return templates.TemplateResponse("admin_schedules.html", {
        "request": request,
        "route": route,
        "schedules": schedules
    })

@app.get("/admin/route/{route_id}/schedule/add", response_class=HTMLResponse)
async def add_schedule_page(
    request: Request,
    route_id: int,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    route = db.query(Route).filter(Route.id == route_id).first()
    if not route:
        raise HTTPException(status_code=404, detail="Route not found")

    return templates.TemplateResponse("admin_schedule_form.html", {
        "request": request,
        "route": route
    })

@app.post("/admin/route/{route_id}/schedule/add")
async def add_schedule(
    request: Request,
    route_id: int,
    departure_time: str = Form(...),
    arrival_time: str = Form(...),
    departure_stop: str = Form(...),
    arrival_stop: str = Form(...),
    days_of_week: List[str] = Form(...),
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    route = db.query(Route).filter(Route.id == route_id).first()
    if not route:
        raise HTTPException(status_code=404, detail="Route not found")

    days_str = ",".join(days_of_week)

    new_schedule = Schedule(
        route_id=route_id,
        departure_time=departure_time,
        arrival_time=arrival_time,
        departure_stop=departure_stop,
        arrival_stop=arrival_stop,
        days_of_week=days_str,
        is_active=1
    )

    db.add(new_schedule)
    db.commit()
    db.refresh(new_schedule)

    return RedirectResponse(url=f"/admin/route/{route_id}/schedules", status_code=302)

@app.get("/admin/route/{route_id}/schedule/{schedule_id}/edit", response_class=HTMLResponse)
async def edit_schedule_page(
    request: Request,
    route_id: int,
    schedule_id: int,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    route = db.query(Route).filter(Route.id == route_id).first()
    if not route:
        raise HTTPException(status_code=404, detail="Route not found")

    schedule = db.query(Schedule).filter(Schedule.id == schedule_id, Schedule.route_id == route_id).first()
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")

    return templates.TemplateResponse("admin_schedule_edit.html", {
        "request": request,
        "route": route,
        "schedule": schedule
    })

@app.post("/admin/route/{route_id}/schedule/{schedule_id}/edit")
async def edit_schedule(
    request: Request,
    route_id: int,
    schedule_id: int,
    departure_time: str = Form(...),
    arrival_time: str = Form(...),
    departure_stop: str = Form(...),
    arrival_stop: str = Form(...),
    days_of_week: List[str] = Form(...),
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    route = db.query(Route).filter(Route.id == route_id).first()
    if not route:
        raise HTTPException(status_code=404, detail="Route not found")

    schedule = db.query(Schedule).filter(Schedule.id == schedule_id, Schedule.route_id == route_id).first()
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")

    days_str = ",".join(days_of_week)

    schedule.departure_time = departure_time
    schedule.arrival_time = arrival_time
    schedule.departure_stop = departure_stop
    schedule.arrival_stop = arrival_stop
    schedule.days_of_week = days_str

    db.commit()

    return RedirectResponse(url=f"/admin/route/{route_id}/schedules", status_code=302)

@app.post("/admin/route/{route_id}/schedule/{schedule_id}/delete")
async def delete_schedule(
    request: Request,
    route_id: int,
    schedule_id: int,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin)
):
    route = db.query(Route).filter(Route.id == route_id).first()
    if not route:
        raise HTTPException(status_code=404, detail="Route not found")

    schedule = db.query(Schedule).filter(Schedule.id == schedule_id, Schedule.route_id == route_id).first()
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")

    db.delete(schedule)
    db.commit()

    return {"success": True}

@app.post("/admin/logout")
async def admin_logout():
    response = RedirectResponse(url="/", status_code=302)
    response.delete_cookie(key="access_token")
    return response

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)
