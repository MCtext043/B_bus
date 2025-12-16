from sqlalchemy.orm import Session
from database import SessionLocal, engine
from models import Base, Route, Schedule, Admin
from auth import get_password_hash

def create_sample_data():
    # Create database tables
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()

    try:
        # Check if data already exists
        if db.query(Route).first():
            print("Sample data already exists!")
            return

        # Create sample admin
        admin = Admin(
            username="admin",
            email="admin@example.com",
            hashed_password=get_password_hash("admin123")
        )
        db.add(admin)

        # Create sample routes
        routes_data = [
            {
                "route_number": "1",
                "route_name": "Автовокзал - Центр",
                "description": "Основной маршрут через центр города"
            },
            {
                "route_number": "5A",
                "route_name": "Железнодорожный вокзал - Аэропорт",
                "description": "Экспресс маршрут до аэропорта"
            },
            {
                "route_number": "12Б",
                "route_name": "Южный район - Северный район",
                "description": "Кольцевой маршрут между районами"
            },
            {
                "route_number": "7",
                "route_name": "Университет - Торговый центр",
                "description": "Студенческий маршрут"
            }
        ]

        routes = []
        for route_data in routes_data:
            route = Route(**route_data)
            db.add(route)
            routes.append(route)

        db.flush()  # Get IDs for routes

        # Create sample schedules
        schedules_data = [
            # Route 1: Автовокзал - Центр
            {"route_id": routes[0].id, "departure_time": "06:00", "arrival_time": "06:30", "departure_stop": "Автовокзал", "arrival_stop": "Центр", "days_of_week": "mon,tue,wed,thu,fri"},
            {"route_id": routes[0].id, "departure_time": "07:15", "arrival_time": "07:45", "departure_stop": "Автовокзал", "arrival_stop": "Центр", "days_of_week": "mon,tue,wed,thu,fri"},
            {"route_id": routes[0].id, "departure_time": "08:30", "arrival_time": "09:00", "departure_stop": "Автовокзал", "arrival_stop": "Центр", "days_of_week": "mon,tue,wed,thu,fri,sat,sun"},
            {"route_id": routes[0].id, "departure_time": "12:00", "arrival_time": "12:30", "departure_stop": "Автовокзал", "arrival_stop": "Центр", "days_of_week": "mon,tue,wed,thu,fri,sat,sun"},
            {"route_id": routes[0].id, "departure_time": "17:45", "arrival_time": "18:15", "departure_stop": "Автовокзал", "arrival_stop": "Центр", "days_of_week": "mon,tue,wed,thu,fri"},
            {"route_id": routes[0].id, "departure_time": "19:30", "arrival_time": "20:00", "departure_stop": "Автовокзал", "arrival_stop": "Центр", "days_of_week": "mon,tue,wed,thu,fri,sat,sun"},

            # Route 5A: Железнодорожный вокзал - Аэропорт
            {"route_id": routes[1].id, "departure_time": "05:30", "arrival_time": "06:45", "departure_stop": "Железнодорожный вокзал", "arrival_stop": "Аэропорт", "days_of_week": "mon,tue,wed,thu,fri,sat,sun"},
            {"route_id": routes[1].id, "departure_time": "14:20", "arrival_time": "15:35", "departure_stop": "Железнодорожный вокзал", "arrival_stop": "Аэропорт", "days_of_week": "mon,tue,wed,thu,fri,sat,sun"},
            {"route_id": routes[1].id, "departure_time": "18:10", "arrival_time": "19:25", "departure_stop": "Железнодорожный вокзал", "arrival_stop": "Аэропорт", "days_of_week": "mon,tue,wed,thu,fri,sat,sun"},

            # Route 12Б: Южный район - Северный район
            {"route_id": routes[2].id, "departure_time": "06:45", "arrival_time": "07:30", "departure_stop": "Южный район", "arrival_stop": "Северный район", "days_of_week": "mon,tue,wed,thu,fri"},
            {"route_id": routes[2].id, "departure_time": "09:15", "arrival_time": "10:00", "departure_stop": "Южный район", "arrival_stop": "Северный район", "days_of_week": "mon,tue,wed,thu,fri,sat"},
            {"route_id": routes[2].id, "departure_time": "13:30", "arrival_time": "14:15", "departure_stop": "Южный район", "arrival_stop": "Северный район", "days_of_week": "mon,tue,wed,thu,fri,sat,sun"},
            {"route_id": routes[2].id, "departure_time": "16:45", "arrival_time": "17:30", "departure_stop": "Южный район", "arrival_stop": "Северный район", "days_of_week": "mon,tue,wed,thu,fri,sat"},

            # Route 7: Университет - Торговый центр
            {"route_id": routes[3].id, "departure_time": "08:00", "arrival_time": "08:25", "departure_stop": "Университет", "arrival_stop": "Торговый центр", "days_of_week": "mon,tue,wed,thu,fri"},
            {"route_id": routes[3].id, "departure_time": "08:30", "arrival_time": "08:55", "departure_stop": "Университет", "arrival_stop": "Торговый центр", "days_of_week": "mon,tue,wed,thu,fri"},
            {"route_id": routes[3].id, "departure_time": "12:15", "arrival_time": "12:40", "departure_stop": "Университет", "arrival_stop": "Торговый центр", "days_of_week": "mon,tue,wed,thu,fri"},
            {"route_id": routes[3].id, "departure_time": "15:00", "arrival_time": "15:25", "departure_stop": "Университет", "arrival_stop": "Торговый центр", "days_of_week": "mon,tue,wed,thu,fri"},
            {"route_id": routes[3].id, "departure_time": "17:30", "arrival_time": "17:55", "departure_stop": "Университет", "arrival_stop": "Торговый центр", "days_of_week": "mon,tue,wed,thu,fri"},
        ]

        for schedule_data in schedules_data:
            schedule = Schedule(**schedule_data, is_active=1)
            db.add(schedule)

        db.commit()
        print("Sample data created successfully!")
        print("Admin credentials:")
        print("Username: admin")
        print("Password: admin123")

    except Exception as e:
        db.rollback()
        print(f"Error creating sample data: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    create_sample_data()
