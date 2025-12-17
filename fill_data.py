from sqlalchemy.orm import Session
from database import SessionLocal, engine
from models import Base, Trip, Ticket, Dispatcher
from auth import get_password_hash
from datetime import date, timedelta

def create_sample_data():
    # Recreate database tables to match current models
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()

    try:
        # Check if data already exists
        if db.query(Dispatcher).first():
            print("Sample data already exists!")
            return

        # Create main dispatcher (approved, super)
        dispatcher = Dispatcher(
            username="dispatcher",
            email="dispatcher@udmurtbus.ru",
            phone="+7 (3412) 123-456",
            hashed_password=get_password_hash("dispatcher123"),
            is_super=1,
            is_approved=1
        )
        db.add(dispatcher)

        # Get current date
        today = date.today()

        # Create sample trips
        trips_data = [
            {
                "departure_city": "Ижевск",
                "arrival_city": "Балезино",
                "departure_date": today,
                "departure_time": "08:00",
                "arrival_time": "09:30",
                "bus_number": "У123АА18",
                "bus_name": "ПАЗ-3205",
                "bus_color": "Черный",
                "total_seats": 45,
                "available_seats": 35,
                "price": 150.0
            },
            {
                "departure_city": "Ижевск",
                "arrival_city": "Глазов",
                "departure_date": today,
                "departure_time": "10:00",
                "arrival_time": "11:45",
                "bus_number": "У456ББ18",
                "bus_name": "ЛИАЗ-5256",
                "bus_color": "Красный",
                "total_seats": 50,
                "available_seats": 42,
                "price": 200.0
            },
            {
                "departure_city": "Балезино",
                "arrival_city": "Ижевск",
                "departure_date": today,
                "departure_time": "14:00",
                "arrival_time": "15:30",
                "bus_number": "У789ВВ18",
                "bus_name": "ПАЗ-3205",
                "bus_color": "Красный",
                "total_seats": 45,
                "available_seats": 0,
                "price": 150.0
            },
            {
                "departure_city": "Ижевск",
                "arrival_city": "Сарапул",
                "departure_date": today + timedelta(days=1),
                "departure_time": "09:00",
                "arrival_time": "10:45",
                "bus_number": "У111ГГ18",
                "bus_name": "ЛИАЗ-5256",
                "bus_color": "Белый",
                "total_seats": 50,
                "available_seats": 50,
                "price": 180.0
            },
            {
                "departure_city": "Глазов",
                "arrival_city": "Ижевск",
                "departure_date": today + timedelta(days=1),
                "departure_time": "16:00",
                "arrival_time": "17:45",
                "bus_number": "У222ДД18",
                "bus_name": "ПАЗ-3205",
                "bus_color": "Желтый",
                "total_seats": 45,
                "available_seats": 28,
                "price": 200.0
            }
        ]

        trips = []
        for trip_data in trips_data:
            trip = Trip(**trip_data)
            db.add(trip)
            trips.append(trip)

        db.flush()  # Get IDs for trips

        # Create sample tickets
        tickets_data = [
            {
                "trip_id": trips[0].id,
                "ticket_number": "001",
                "passenger_name": "Иванов Иван Иванович",
                "passenger_phone": "+7 (912) 345-67-89",
                "boarding_point": "Автовокзал Ижевск",
                "status": "confirmed",
                "payment_status": "paid",
                "payment_amount": 150.0
            },
            {
                "trip_id": trips[1].id,
                "ticket_number": "002",
                "passenger_name": "Петрова Мария Сергеевна",
                "passenger_phone": "+7 (922) 123-45-67",
                "boarding_point": "Центральный автовокзал",
                "status": "pending_confirmation",
                "payment_status": "paid",
                "payment_amount": 200.0
            },
            {
                "trip_id": trips[4].id,
                "ticket_number": "003",
                "passenger_name": "Сидоров Алексей Петрович",
                "passenger_phone": "+7 (951) 987-65-43",
                "boarding_point": "Автовокзал Глазов",
                "status": "completed",
                "payment_status": "paid",
                "payment_amount": 200.0,
                "status_reason": "Рейс выполнен успешно"
            }
        ]

        for ticket_data in tickets_data:
            ticket = Ticket(**ticket_data)
            db.add(ticket)

        db.commit()
        print("Sample data created successfully!")
        print("Dispatcher credentials:")
        print("Username: dispatcher")
        print("Password: dispatcher123")
        print("Phone: +7 (3412) 123-456")

    except Exception as e:
        db.rollback()
        print(f"Error creating sample data: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    create_sample_data()
