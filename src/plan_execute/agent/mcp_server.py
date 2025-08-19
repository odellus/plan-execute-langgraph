import random
import string
import logging

from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel

# Configure logging for the MCP server
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mcp_server")

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
    # Add Boston flights for testing
    "DA201": Flight(
        flight_id="DA201",
        origin="SFO",
        destination="BOS",
        date_time=Date(year=2024, month=12, day=19, hour=14),
        duration=5.5,
        price=350,
    ),
    "DA203": Flight(
        flight_id="DA203",
        origin="SFO",
        destination="BOS",
        date_time=Date(year=2024, month=12, day=19, hour=18),
        duration=5.5,
        price=420,
    ),
    "DA205": Flight(
        flight_id="DA205",
        origin="SFO",
        destination="BOS",
        date_time=Date(year=2024, month=12, day=20, hour=8),
        duration=5.5,
        price=380,
    ),
}

itinerary_database = {}  # Will be populated as bookings are made


@mcp.tool()
def fetch_flight_info(date: Date, origin: str, destination: str):
    """Fetch flight information from origin to destination on the given date"""
    logger.info(f"🔍 Searching flights: {origin} → {destination} on {date.year}-{date.month:02d}-{date.day:02d}")
    
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
    
    logger.info(f"✈️ Found {len(flights)} flights matching criteria")
    return flights


@mcp.tool()
def fetch_itinerary(confirmation_number: str):
    """Fetch itinerary information using confirmation number"""
    logger.info(f"🎫 Looking up itinerary: {confirmation_number}")
    
    if confirmation_number in itinerary_database:
        itinerary = itinerary_database[confirmation_number]
        logger.info(f"✅ Found itinerary for {itinerary.user_profile.name}")
        return itinerary
    else:
        logger.warning(f"❌ Itinerary not found: {confirmation_number}")
        return None


@mcp.tool()
def book_itinerary(user_name: str, flight_id: str):
    """Book a flight for a user"""
    logger.info(f"📝 Booking flight {flight_id} for {user_name}")
    
    if user_name not in user_database:
        logger.error(f"❌ User not found: {user_name}")
        return f"User {user_name} not found in database"

    if flight_id not in flight_database:
        logger.error(f"❌ Flight not found: {flight_id}")
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
    
    logger.info(f"✅ Successfully booked flight {flight_id} for {user_name}, confirmation: {confirmation_number}")
    return itinerary


@mcp.tool()
def modify_itinerary(confirmation_number: str, new_flight_id: str = None, cancel: bool = False):
    """Modify an existing itinerary - either change flight or cancel"""
    logger.info(f"✏️ Modifying itinerary {confirmation_number}, cancel={cancel}, new_flight={new_flight_id}")
    
    if confirmation_number not in itinerary_database:
        logger.error(f"❌ Confirmation number not found: {confirmation_number}")
        return f"Confirmation number {confirmation_number} not found"

    if cancel:
        # Cancel the booking
        cancelled_itinerary = itinerary_database.pop(confirmation_number)
        logger.info(f"🗑️ Cancelled booking {confirmation_number} for {cancelled_itinerary.user_profile.name}")
        return f"Booking {confirmation_number} has been cancelled"

    if new_flight_id:
        if new_flight_id not in flight_database:
            logger.error(f"❌ New flight not found: {new_flight_id}")
            return f"Flight {new_flight_id} not found"

        # Update the flight
        itinerary = itinerary_database[confirmation_number]
        old_flight = itinerary.flight.flight_id
        itinerary.flight = flight_database[new_flight_id]
        logger.info(f"🔄 Updated itinerary {confirmation_number}: {old_flight} → {new_flight_id}")
        return itinerary

    logger.warning(f"⚠️ No modification specified for {confirmation_number}")
    return "No modification specified"


@mcp.tool()
def get_user_info(user_name: str):
    """Get user profile information"""
    logger.info(f"👤 Looking up user: {user_name}")
    
    if user_name in user_database:
        user = user_database[user_name]
        logger.info(f"✅ Found user: {user.name} ({user.email})")
        return user
    else:
        logger.warning(f"❌ User not found: {user_name}")
        return f"User {user_name} not found"


@mcp.tool()
def file_ticket(user_name: str, user_request: str):
    """File a support ticket for complex requests that need human assistance"""
    logger.info(f"🎟️ Filing support ticket for {user_name}")
    
    if user_name not in user_database:
        logger.error(f"❌ User not found: {user_name}")
        return f"User {user_name} not found in database"

    user_profile = user_database[user_name]
    ticket = Ticket(user_request=user_request, user_profile=user_profile)

    # In a real system, this would be stored in a ticketing system
    ticket_id = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
    
    logger.info(f"✅ Created support ticket {ticket_id} for {user_name}")
    return f"Support ticket {ticket_id} has been created for {user_name}. A human agent will contact you at {user_profile.email} within 24 hours."


if __name__ == "__main__":
    logger.info("🚀 Starting MCP Airline Server...")
    mcp.run()