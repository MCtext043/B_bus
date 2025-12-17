from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Date, Float, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base
import enum

class TicketStatus(enum.Enum):
    PENDING_CONFIRMATION = "pending_confirmation"
    CONFIRMED = "confirmed"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class Dispatcher(Base):
    __tablename__ = "dispatchers"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    phone = Column(String, nullable=True)
    is_super = Column(Integer, default=0)     # 1 - главный диспетчер
    is_approved = Column(Integer, default=0)  # 1 - одобрен главным
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Trip(Base):
    __tablename__ = "trips"

    id = Column(Integer, primary_key=True, index=True)
    departure_city = Column(String, nullable=False)
    arrival_city = Column(String, nullable=False)
    departure_date = Column(Date, nullable=False)
    departure_time = Column(String, nullable=False)  # Format: HH:MM
    arrival_time = Column(String, nullable=False)    # Format: HH:MM
    bus_number = Column(String, nullable=False)      # Гос. номер автобуса
    bus_name = Column(String, nullable=False)        # Название автобуса
    bus_color = Column(String, nullable=False)       # Цвет автобуса
    total_seats = Column(Integer, nullable=False)
    available_seats = Column(Integer, nullable=False)
    price = Column(Float, default=0.0)
    is_active = Column(Integer, default=1)  # 1 = active, 0 = inactive
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    tickets = relationship("Ticket", back_populates="trip")

class Ticket(Base):
    __tablename__ = "tickets"

    id = Column(Integer, primary_key=True, index=True)
    ticket_number = Column(String, unique=True, index=True)  # 001-999
    trip_id = Column(Integer, ForeignKey("trips.id"))
    passenger_name = Column(String, nullable=False)
    passenger_phone = Column(String, nullable=False)
    boarding_point = Column(String, nullable=False)
    status = Column(String, default="pending_confirmation")  # pending_confirmation, confirmed, completed, cancelled
    status_reason = Column(Text, nullable=True)
    payment_status = Column(String, default="unpaid")  # unpaid, paid, refunded
    payment_amount = Column(Float, default=0.0)
    is_open_date = Column(Integer, default=0)  # 1 = open date ticket
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    trip = relationship("Trip", back_populates="tickets")
