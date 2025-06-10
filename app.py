import string

from flask import Flask, request, make_response, jsonify, render_template, redirect, url_for
from pony import orm
from datetime import datetime, timezone

DB = orm.Database()
app = Flask(__name__)

class Trip(DB.Entity):
    id = orm.PrimaryKey(int, auto=True)
    destination = orm.Required(str)
    price = orm.Required(float)
    length_in_days = orm.Required(int)
    departure_date = orm.Required(datetime)
    return_date  = orm.Required(datetime)
    isFull = orm.Required(bool)
    created_at = orm.Required(datetime)
    updated_at = orm.Required(datetime)
    travellers = orm.Set('Traveller')

class Traveller(DB.Entity):
    id = orm.PrimaryKey(int, auto=True)
    trip = orm.Required(Trip)
    name = orm.Required(str)
    nationality = orm.Required(str)
    email = orm.Required(str)
    phone = orm.Required(str)
    hasPaid = orm.Required(bool)
    created_at = orm.Required(datetime)
    updated_at = orm.Required(datetime)

DB.bind(provider='sqlite', filename='database.sqlite', create_db=True)
DB.generate_mapping(create_tables=True)
@app.route("/")
def home():
    return redirect(url_for("get_trips"))

@app.route("/trips", methods=["POST"])
@orm.db_session
def create_trip():
    data = request.get_json()
    trip = Trip(
        destination=data["destination"],
        price=data["price"],
        length_in_days=data["length_in_days"],
        departure_date=datetime.fromisoformat(data["departure_date"]),
        return_date=datetime.fromisoformat(data["return_date"]),
        isFull=data["isFull"],
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    return jsonify({
        "id": trip.id,
        "destination": trip.destination,
        "price": trip.price,
        "length_in_days": trip.length_in_days,
        "departure_date": trip.departure_date.strftime("%Y-%m-%d %H:%M"),
        "return_date": trip.return_date.strftime("%Y-%m-%d %H:%M"),
        "isFull": trip.isFull,
        "created_at": trip.created_at.strftime("%Y-%m-%d %H:%M"),
        "updated_at": trip.updated_at.strftime("%Y-%m-%d %H:%M")
    }), 201

@app.route("/trips/new", methods=["GET", "POST"])
@orm.db_session
def new_trip():
    if request.method == "POST":
        destination = request.form["destination"]
        price = float(request.form["price"])
        length_in_days = int(request.form["length_in_days"])
        departure_date = datetime.fromisoformat(request.form["departure_date"])
        return_date = datetime.fromisoformat(request.form["return_date"])
        isFull = False

        trip = Trip(
            destination=destination,
            price=price,
            length_in_days=length_in_days,
            departure_date=departure_date,
            return_date=return_date,
            isFull=isFull,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )

        return redirect("/trips")
        # after successful creation
    return render_template("add_trip.html")

@app.route("/trips", methods=["GET"])
@orm.db_session
def get_trips():
    trip_id = request.args.get("id")

    def format_traveller(t):
        return {
            "id": t.id,
            "name": t.name,
            "nationality": t.nationality,
            "email": t.email,
            "phone": t.phone,
            "hasPaid": t.hasPaid,
            "created_at": t.created_at.strftime("%Y-%m-%d %H:%M"),
            "updated_at": t.updated_at.strftime("%Y-%m-%d %H:%M")
        }

    def format_trip(t):
        return {
            "id": t.id,
            "destination": t.destination,
            "price": t.price,
            "length_in_days": t.length_in_days,
            "departure_date": t.departure_date.strftime("%Y-%m-%d %H:%M"),
            "return_date": t.return_date.strftime("%Y-%m-%d %H:%M"),
            "isFull": t.isFull,
            "created_at": t.created_at.strftime("%Y-%m-%d %H:%M"),
            "updated_at": t.updated_at.strftime("%Y-%m-%d %H:%M"),
            "travellers": [format_traveller(tr) for tr in t.travellers]
        }

    if trip_id:
        trip = Trip.get(id=int(trip_id))
        if trip:
            return jsonify(format_trip(trip))
        else:
            return jsonify({"message": f"Trip with id {trip_id} not found"}), 404

    # No trip ID passed — render HTML view
    trips = orm.select(t for t in Trip)[:]
    trip_data = [
        {
            "id": t.id,
            "destination": t.destination,
            "price": t.price,
            "length_in_days": t.length_in_days,
            "departure_date": t.departure_date.strftime("%Y-%m-%d"),
            "return_date": t.return_date.strftime("%Y-%m-%d"),
            "isFull": t.isFull
        }
        for t in trips
    ]
    return render_template("index.html", trips=trip_data)

@app.route("/trips/delete/<int:trip_id>", methods=["GET", "POST"])
@orm.db_session
def delete_trip(trip_id):
    trip = Trip.get(id=trip_id)
    if trip:
        for traveller in trip.travellers:
            traveller.delete()
        trip.delete()
        return redirect(url_for("get_trips"))  # or whatever method renders your trip list
    else:
        return jsonify({"message": f"Trip {trip_id} not found"}), 404

@app.route("/travellers", methods=["POST"])
@orm.db_session
def add_traveller():
    data = request.get_json()
    traveller = Traveller(
        trip=Trip[data["trip_id"]],
        name=data["name"],
        nationality=data["nationality"],
        email=data["email"],
        phone=data["phone"],
        hasPaid=data["hasPaid"],
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    return jsonify({
        "id": traveller.id,
        "trip_id": traveller.trip.id,
        "name": traveller.name,
        "nationality": traveller.nationality,
        "email": traveller.email,
        "phone": traveller.phone,
        "hasPaid": traveller.hasPaid,
        "created_at": traveller.created_at.strftime("%Y-%m-%d %H:%M"),
        "updated_at": traveller.updated_at.strftime("%Y-%m-%d %H:%M")
    }), 201

@app.route("/trips/<int:trip_id>/travellers/new", methods=["GET", "POST"])
@orm.db_session
def add_traveller_form(trip_id):
    trip = Trip.get(id=trip_id)
    if not trip:
        return "Trip not found", 404

    if request.method == "POST":
        traveller = Traveller(
            trip=trip,
            name=request.form["name"],
            nationality=request.form["nationality"],
            email=request.form["email"],
            phone=request.form["phone"],
            hasPaid=request.form["hasPaid"] == "true",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        return redirect(url_for("view_travellers", trip_id=trip.id))

    return render_template("add_traveller.html", trip_id=trip.id)


@app.route("/travellers", methods=["GET"])
@orm.db_session
def get_all_travellers():
    travellers = orm.select(t for t in Traveller)[:]
    return jsonify([
        {
            "id": t.id,
            "trip_id": t.trip.id,
            "name": t.name,
            "nationality": t.nationality,
            "email": t.email,
            "phone": t.phone,
            "hasPaid": t.hasPaid,
            "created_at": t.created_at.strftime("%Y-%m-%d %H:%M"),
            "updated_at": t.updated_at.strftime("%Y-%m-%d %H:%M")
        } for t in travellers
    ])

@app.route("/trips/<int:trip_id>/travellers", methods=["GET"])
@orm.db_session
def get_travellers_by_trip(trip_id):
    trip = Trip.get(id=trip_id)
    if not trip:
        return jsonify({"message": f"Trip {trip_id} not found"}), 404

    travellers = trip.travellers
    return jsonify([
        {
            "id": t.id,
            "trip_id": t.trip.id,
            "name": t.name,
            "nationality": t.nationality,
            "email": t.email,
            "phone": t.phone,
            "hasPaid": t.hasPaid,
            "created_at": t.created_at.strftime("%Y-%m-%d %H:%M"),
            "updated_at": t.updated_at.strftime("%Y-%m-%d %H:%M")
        } for t in travellers
    ])

@app.route("/trips/<int:trip_id>/travellers/view", methods=["GET"])
@orm.db_session
def view_travellers(trip_id):
    trip = Trip.get(id=trip_id)
    if not trip:
        return "Trip not found", 404

    travellers = trip.travellers
    return render_template("travellers.html", trip=trip, travellers=travellers)


@app.route("/travellers/<int:traveller_id>", methods=["DELETE"])
@orm.db_session
def delete_traveller(traveller_id):
    traveller = Traveller.get(id=traveller_id)
    if traveller:
        traveller.delete()
        return jsonify({"message": f"Traveller {traveller_id} deleted successfully"}), 200
    else:
        return jsonify({"message": f"Traveller {traveller_id} not found"}), 404

@app.route("/travellers/<int:traveller_id>/delete", methods=["GET", "POST"])
@orm.db_session
def delete_traveller_form(traveller_id):
    traveller = Traveller.get(id=traveller_id)
    if not traveller:
        return "Traveller not found", 404
    trip_id = traveller.trip.id
    traveller.delete()
    return redirect(url_for('view_travellers', trip_id=trip_id))


@app.route("/travellers/<int:traveller_id>", methods=["PUT"])
@orm.db_session
def update_traveller(traveller_id):
    data = request.get_json()
    traveller = Traveller.get(id=traveller_id)

    if not traveller:
        return jsonify({"message": f"Traveller {traveller_id} not found"}), 404

    if "name" in data:
        traveller.name = data["name"]
    if "nationality" in data:
        traveller.nationality = data["nationality"]
    if "email" in data:
        traveller.email = data["email"]
    if "phone" in data:
        traveller.phone = data["phone"]
    if "hasPaid" in data:
        traveller.hasPaid = data["hasPaid"]
    if "trip_id" in data:
        traveller.trip = Trip[data["trip_id"]]

    traveller.updated_at = datetime.now(timezone.utc)

    orm.flush()

    return jsonify({
        "id": traveller.id,
        "trip_id": traveller.trip.id,
        "name": traveller.name,
        "nationality": traveller.nationality,
        "email": traveller.email,
        "phone": traveller.phone,
        "hasPaid": traveller.hasPaid,
        "created_at": traveller.created_at.strftime("%Y-%m-%d %H:%M"),
        "updated_at": traveller.updated_at.strftime("%Y-%m-%d %H:%M")
    })

# Show edit form
@app.route("/travellers/<int:traveller_id>/edit", methods=["GET"])
@orm.db_session
def edit_traveller(traveller_id):
    traveller = Traveller.get(id=traveller_id)
    if not traveller:
        return "Traveller not found", 404
    return render_template("edit_traveller.html", traveller=traveller)

# Handle form submission
@app.route("/travellers/<int:traveller_id>/edit", methods=["POST"])
@orm.db_session
def update_traveller_form(traveller_id):
    traveller = Traveller.get(id=traveller_id)
    if not traveller:
        return "Traveller not found", 404

    traveller.name = request.form["name"]
    traveller.nationality = request.form["nationality"]
    traveller.email = request.form["email"]
    traveller.phone = request.form["phone"]
    traveller.hasPaid = request.form.get("hasPaid") == "true"
    traveller.updated_at = datetime.now(timezone.utc)

    return redirect(url_for('view_travellers', trip_id=traveller.trip.id))

@app.route("/trips/<int:trip_id>", methods=["PUT"])
@orm.db_session
def update_trip(trip_id):
    data = request.get_json()
    trip = Trip.get(id=trip_id)

    if not trip:
        return jsonify({"message": f"Trip {trip_id} not found"}), 404

    if "destination" in data:
        trip.destination = data["destination"]
    if "price" in data:
        trip.price = data["price"]
    if "length_in_days" in data:
        trip.length_in_days = data["length_in_days"]
    if "departure_date" in data:
        trip.departure_date = datetime.fromisoformat(data["departure_date"])
    if "return_date" in data:
        trip.return_date = datetime.fromisoformat(data["return_date"])
    if "isFull" in data:
        trip.isFull = data["isFull"]

    trip.updated_at = datetime.now(timezone.utc)

    orm.flush()

    return jsonify({
        "id": trip.id,
        "destination": trip.destination,
        "price": trip.price,
        "length_in_days": trip.length_in_days,
        "departure_date": trip.departure_date.strftime("%Y-%m-%d %H:%M"),
        "return_date": trip.return_date.strftime("%Y-%m-%d %H:%M"),
        "isFull": trip.isFull,
        "created_at": trip.created_at.strftime("%Y-%m-%d %H:%M"),
        "updated_at": trip.updated_at.strftime("%Y-%m-%d %H:%M")
    })

@app.route("/trips/<int:trip_id>/edit", methods=["GET", "POST"])
@orm.db_session
def edit_trip(trip_id):
    trip = Trip.get(id=trip_id)
    if not trip:
        return "Trip not found", 404

    if request.method == "POST":
        trip.destination = request.form["destination"]
        trip.price = float(request.form["price"])
        trip.length_in_days = int(request.form["length_in_days"])
        trip.departure_date = datetime.fromisoformat(request.form["departure_date"])
        trip.return_date = datetime.fromisoformat(request.form["return_date"])
        trip.isFull = request.form["isFull"] == "true"
        trip.updated_at = datetime.utcnow()
        orm.flush()
        return redirect(url_for("get_trips"))

    return render_template("edit_trip.html", trip=trip)

if (__name__ == "__main__"):
    app.run(host="0.0.0.0", port=8080, debug=True)