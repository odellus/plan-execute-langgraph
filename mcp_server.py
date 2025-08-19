import random
import string

from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel

# Create an MCP server
mcp = FastMCP("Airline Agent")


class Date(BaseModel):
    # Somehow LLM is bad at specifying `datetime.datetime`
    year: int
    month: int
    day: int
    hour: int


class UserProfile(BaseModel):
    user_id: str
    name: str
    email: str


class Flight(BaseModel):
    flight_id: str
    date_time: Date
    origin: str
    destination: str
    duration: float
    price: float


class Itinerary(BaseModel):
    confirmation_number: str
    user_profile: UserProfile
    flight: Flight


class Ticket(BaseModel):
    user_request: str
    user_profile: UserProfile


user_database = {
    "Adam": UserProfile(user_id="1", name="Adam", email="adam@gmail.com"),
    "Bob": UserProfile(user_id="2", name="Bob", email="bob@gmail.com"),
    "Chelsie": UserProfile(user_id="3", name="Chelsie", email="chelsie@gmail.com"),
    "David": UserProfile(user_id="4", name="David", email="david@gmail.com"),
}

flight_database = {
    "DA123": Flight(
        flight_id="DA123",
        origin="SFO",
        destination="JFK",
        date_time=Date(year=2025, month=9, day=1, hour=1),
        duration=3,
        price=200,
    ),
    "DA125": Flight(
        flight_id="DA125",
        origin="SFO",
        destination="JFK",
        date_time=Date(year=2025, month=9, day=1, hour=7),
        duration=9,
        price=500,
    ),
    "DA127": Flight(
        flight_id="DA127",
        origin="SFO",
        destination="JFK",
        date_time=Date(year=2025, month=9, day=1, hour=19),
        duration=5,
        price=300,
    ),
    "DA129": Flight(
        flight_id="DA129",
        origin="JFK",
        destination="SFO",
        date_time=Date(year=2025, month=9, day=2, hour=1),
        duration=6,
        price=250,
    ),
    "DA131": Flight(
        flight_id="DA131",
        origin="JFK",
        destination="SFO",
        date_time=Date(year=2025, month=9, day=2, hour=7),
        duration=6,
        price=350,
    ),
    "DA133": Flight(
        flight_id="DA133",
        origin="JFK",
        destination="SFO",
        date_time=Date(year=2025, month=9, day=2, hour=19),
        duration=6,
        price=400,
    ),
    "DA135": Flight(
        flight_id="DA135",
        origin="LAX",
        destination="JFK",
        date_time=Date(year=2025, month=9, day=1, hour=10),
        duration=5,
        price=275,
    ),
    "DA137": Flight(
        flight_id="DA137",
        origin="JFK",
        destination="LAX",
        date_time=Date(year=2025, month=9, day=2, hour=15),
        duration=6,
        price=325,
    ),
}

itinerary_database = {}  # Will be populated as bookings are made


@mcp.tool()
def fetch_flight_info(date: Date, origin: str, destination: str):
    """Fetch flight information from origin to destination on the given date"""
    flights = []

    for flight_id, flight in flight_database.items():
        if (
            flight.date_time.year == date.year
            and flight.date_time.month == date.month
            and flight.date_time.day == date.day
            and flight.origin == origin
            and flight.destination == destination
        ):
            flights.append(flight)
    return flights


@mcp.tool()
def fetch_itinerary(confirmation_number: str):
    """Fetch itinerary information using confirmation number"""
    if confirmation_number in itinerary_database:
        return itinerary_database[confirmation_number]
    else:
        return None


@mcp.tool()
def book_itinerary(user_name: str, flight_id: str):
    """Book a flight for a user"""
    if user_name not in user_database:
        return f"User {user_name} not found in database"

    if flight_id not in flight_database:
        return f"Flight {flight_id} not found"

    user_profile = user_database[user_name]
    flight = flight_database[flight_id]

    # Generate confirmation number
    confirmation_number = "".join(random.choices(string.ascii_lowercase + string.digits, k=8))

    # Create itinerary
    itinerary = Itinerary(
        confirmation_number=confirmation_number,
        user_profile=user_profile,
        flight=flight
    )

    # Store in database
    itinerary_database[confirmation_number] = itinerary

    return itinerary


@mcp.tool()
def modify_itinerary(confirmation_number: str, new_flight_id: str = None, cancel: bool = False):
    """Modify an existing itinerary - either change flight or cancel"""
    if confirmation_number not in itinerary_database:
        return f"Confirmation number {confirmation_number} not found"

    if cancel:
        # Cancel the booking
        cancelled_itinerary = itinerary_database.pop(confirmation_number)
        return f"Booking {confirmation_number} has been cancelled"

    if new_flight_id:
        if new_flight_id not in flight_database:
            return f"Flight {new_flight_id} not found"

        # Update the flight
        itinerary = itinerary_database[confirmation_number]
        itinerary.flight = flight_database[new_flight_id]
        return itinerary

    return "No modification specified"


@mcp.tool()
def get_user_info(user_name: str):
    """Get user profile information"""
    if user_name in user_database:
        return user_database[user_name]
    else:
        return f"User {user_name} not found"


@mcp.tool()
def file_ticket(user_name: str, user_request: str):
    """File a support ticket for complex requests that need human assistance"""
    if user_name not in user_database:
        return f"User {user_name} not found in database"

    user_profile = user_database[user_name]
    ticket = Ticket(user_request=user_request, user_profile=user_profile)

    # In a real system, this would be stored in a ticketing system
    ticket_id = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
    
    return f"Support ticket {ticket_id} has been created for {user_name}. A human agent will contact you at {user_profile.email} within 24 hours."


if __name__ == "__main__":
    mcp.run()
