---
title: "Airline GDS and Inventory Systems: Technical Architecture, Data Structures, and APIs"
description: "Deep technical guide to GDS systems (Sabre, Amadeus), inventory control algorithms, PNR data structures, and real-world API examples. For systems engineers, data analysts, and IT roles in airlines and GDS providers."
date: 2026-10-11
---

This guide explains the technical architecture behind airline reservation systems, inventory databases, and GDS APIs. It's written for IT and systems roles who need to understand how booking data flows through Sabre, Amadeus, or proprietary airline systems—and the algorithms that manage seat allocation in real time.

## Overview: The GDS Architecture

A Global Distribution System (GDS) is a massive distributed database and API layer that connects airlines, travel agents, and online booking systems.

### High-Level System Flow

```
[Traveler / Web Booking] 
         ↓
[Travel Agent Terminal / GDS API Client]
         ↓
[GDS Query Engine (Sabre / Amadeus)]
         ↓
[Airline Inventory Servers]
         ↓
[Flight Availability Response]
         ↓
[Booking Engine]
         ↓
[PNR Storage (Airline Database)]
         ↓
[Ticket Issuing System]
```

Each step involves real-time communication, database consistency, and concurrency management.

---

## GDS Architecture: The Three Layers

### Layer 1: Distribution & Search

**Responsibility**: Distribute flight availability to millions of agents and systems.

**Components**:
- **Host System** (Sabre Central, Amadeus Central) — Central GDS database in secure data centers
- **Agency Agents** — Terminals used by travel agents
- **NDC APIs** (New Distribution Capability) — Direct airline APIs that bypass traditional GDS (modern alternative)
- **Aggregators** — Meta-search platforms (Google Flights, Skyscanner) that query multiple GDS

**Data Flow**:
1. Travel agent / booking system sends a search query (origin, destination, date, passengers)
2. GDS queries multiple airlines simultaneously for availability
3. Each airline's inventory server returns flights + pricing (based on current seat availability)
4. GDS aggregates, ranks, and returns results in microseconds

**Scale**: A major GDS handles 1M+ searches per minute globally. Sabre processes ~$200 billion in airline bookings annually.

### Layer 2: Booking & PNR Management

**Responsibility**: Create, store, and modify bookings in real time.

**Components**:
- **Booking Engine** — Transactional system that allocates seats and creates PNRs
- **PNR Database** — Distributed storage (often replicated across data centers for redundancy)
- **Concurrency Control** — Ensures two agents don't sell the same seat twice
- **Payment Processing** — Integration with credit card networks and airline payment gateways

**Data Flow**:
1. Agent selects a flight and passenger details
2. Booking engine reserves a seat (inventory -1)
3. PNR record created with passenger name, itinerary, contact info
4. Payment authorization (if paying now)
5. Ticket number assigned
6. PNR written to distributed database (replicated)

**Concurrency Challenge**: If two agents book the last seat simultaneously, the system must guarantee only ONE gets it. This is solved using:
- **Optimistic locking** — Each PNR has a version number; booking increments it; if another agent modified it, the booking fails
- **Database transactions** (ACID guarantees) — Either all steps succeed or all roll back

### Layer 3: Operational Systems

**Responsibility**: Delivery of bookings to airlines for operations (check-in, boarding, baggage, crew).

**Components**:
- **Check-in Systems** — Kiosks, web, agents that verify passengers and assign final seats
- **Baggage Systems** — Weight, special handling, through-baggage rules
- **Crew Scheduling** — Integration with crew management systems
- **Catering** — Special meals, beverage orders from PNR

**Data Flow**:
1. Passenger checks in (24–48 hours before departure)
2. System retrieves PNR from database
3. Assigns final seat, verifies documents
4. Uploads passenger to airline's departure control system (DCS)
5. Crew and operations see final passenger list

---

## Inventory Control: The Database Model

### Inventory Storage

Airlines store inventory in a **multi-dimensional array** organized by:
- **Flight leg** (e.g., UA100 SFO-ORD on 15-DEC-2026)
- **Booking class** (Y, M, L, K for Economy; J, Z for Business; F, A for First)
- **Availability count** (number of open seats per class)

**Example Schema** (simplified):

```sql
CREATE TABLE flight_inventory (
  flight_id VARCHAR(6),           -- UA100
  flight_date DATE,               -- 2026-12-15
  cabin VARCHAR(1),               -- Y (Economy), J (Business), F (First)
  booking_class CHAR(1),          -- Y, M, L, K (sub-classes of cabin)
  open_seats INT,                 -- Number of open seats
  sold_seats INT,                 -- Number of sold seats
  oversell_limit INT,             -- Max seats allowed (physical + overbooking factor)
  last_updated TIMESTAMP,
  PRIMARY KEY (flight_id, flight_date, cabin, booking_class)
);
```

**Example Data**:

```
| flight_id | flight_date | cabin | booking_class | open_seats | sold_seats | oversell_limit |
|-----------|------------|-------|---------------|------------|------------|----------------|
| UA100     | 2026-12-15 | Y     | Y             | 20         | 50         | 80            |
| UA100     | 2026-12-15 | Y     | M             | 25         | 45         | 70            |
| UA100     | 2026-12-15 | Y     | L             | 15         | 60         | 75            |
| UA100     | 2026-12-15 | Y     | K             | 17         | 30         | 47            |
| UA100     | 2026-12-15 | J     | J             | 4          | 8          | 12            |
| UA100     | 2026-12-15 | F     | F             | 6          | 2          | 8             |
```

Total open: 87 seats
Total sold: 185 seats
Total oversell limit: 372 seats (on a 350-seat aircraft)

### Real-Time Inventory Updates

When a passenger books:

```
UPDATE flight_inventory 
SET open_seats = open_seats - 1,
    sold_seats = sold_seats + 1,
    last_updated = NOW()
WHERE flight_id = 'UA100'
  AND flight_date = '2026-12-15'
  AND cabin = 'Y'
  AND booking_class = 'Y';
```

This must be **atomic** — if two agents execute simultaneously, only one wins. This is handled by the database transaction layer (SQL ACID guarantees).

---

## Seat Allocation Algorithm: The Yield Management Engine

Airlines use sophisticated algorithms to decide:
1. How many seats to allocate per booking class
2. When to stop selling a lower class to save seats for higher-paying classes
3. How much overbooking to allow

### The Classic Algorithm: Littlewood's Rule

Developed in 1972, this algorithm is still used. It calculates a **protection level** — how many seats to protect for higher-fare classes.

**Logic**:
- Economy fare: $200
- Business fare: $500
- Aircraft has 100 Economy seats, 20 Business seats

**Question**: If an Economy passenger wants the last seat, should we sell it? Or protect it hoping a Business passenger books?

**Littlewood's Rule**:
```
Protection level = Expected_number_of_business_passengers
                   × Business_fare
                   ÷ Economy_fare
```

Example:
- Expected 5 Business passengers to book at $500
- Expected 40 Economy passengers to book at $200
- Protection level = 5 × $500 ÷ $200 = 12.5 seats

**Decision**: Protect at least 13 seats for Business. Only sell the remaining 87 Economy seats.

### Modern Algorithm: EMSR (Expected Marginal Seat Revenue)

Most airlines use EMSR (or variants) because it considers multiple cabin classes, not just two.

**Concept**: For each seat remaining, calculate the expected revenue if sold to each cabin class. Sell to the highest.

**Pseudocode** (simplified):

```
available_seats = 100
classes = [("Economy", $200, 40_expected_bookings),
           ("Business", $500, 5_expected_bookings),
           ("First", $1000, 2_expected_bookings)]

for each_seat in range(1, available_seats + 1):
    expected_revenue_per_class = [
        $200 × probability_economy_books,
        $500 × probability_business_books,
        $1000 × probability_first_books
    ]
    
    winning_class = argmax(expected_revenue_per_class)
    allocate_seat_to(winning_class)
```

This runs continuously as bookings come in and demand forecasts update.

[Research on Dynamic Seat Allocation](https://business.columbia.edu/sites/default/files-efs/pubfiles/3925/vanryzin_revenue.pdf) shows EMSR can increase revenue by 3–5% vs. static allocations.

---

## PNR Data Structure: The Full Technical Spec

### PNR Record Format (IATA Simplification)

A complete PNR record in a real system can be 10KB+. Here's a simplified technical structure:

```
PNR_HEADER
├─ PNR_ID: String (8 chars, e.g., ABC123XY)
├─ CREATION_DATE: DateTime
├─ LAST_MODIFIED: DateTime
├─ AGENCY_ID: String (travel agent code)
├─ AIRLINE_ID: String (owning airline)

PASSENGER_SEGMENT (repeated per passenger)
├─ PASSENGER_NAME: String (as-per-ID format)
├─ PASSENGER_TYPE: Enum (ADT=Adult, CHD=Child, INF=Infant, SRC=Senior)
├─ DATE_OF_BIRTH: Date
├─ PHONE: String
├─ EMAIL: String
├─ LOYALTY_PROGRAM_ID: String (frequent flyer number)

ITINERARY_SEGMENT (repeated per flight leg)
├─ SEGMENT_NUMBER: Int
├─ AIRLINE_CODE: String (operating carrier)
├─ FLIGHT_NUMBER: String
├─ DEPARTURE_DATE: Date
├─ DEPARTURE_TIME: Time (UTC)
├─ DEPARTURE_AIRPORT: IATA code
├─ ARRIVAL_AIRPORT: IATA code
├─ CABIN_CLASS: Enum (F, J, Y, etc.)
├─ BOOKING_CLASS: String (Y, M, L, K, Z, etc.)
├─ SEAT_NUMBER: String (or NULL if not assigned)
├─ SEAT_STATUS: Enum (HK=Held Confirmed, HL=Held Waitlist, XL=Cancelled)
├─ EQUIPMENT: String (aircraft type, e.g., 77W for 777-300ER)

PRICING_SEGMENT
├─ FARE_BASIS: String (specifies pricing rules, e.g., YLEEUS)
├─ PRICE_PER_PERSON: Money
├─ TOTAL_PASSENGERS: Int
├─ TOTAL_PRICE: Money
├─ CURRENCY: String (USD, EUR, GBP)
├─ TAX_BREAKDOWN: List of {TAX_CODE, AMOUNT}

REMARKS_SEGMENT (free-text notes)
├─ REMARK_TYPE: Enum (OSI=Other Service Info, SSR=Special Service Request)
├─ REMARK_TEXT: String (e.g., "VEGAN MEAL REQUIRED", "WHEELCHAIR ASSISTANCE")

PAYMENT_SEGMENT
├─ PAYMENT_TYPE: Enum (CC=Credit Card, CASH, CHECK, EMD=Electronic Misc Document)
├─ PAYMENT_METHOD: String or Card Token
├─ PAYMENT_DATE: Date
├─ AUTHORIZATION_CODE: String

TICKETING_SEGMENT
├─ TICKET_NUMBER: String (13 digits, format: AIRLINE_CODE + SERIAL)
├─ TICKET_STATUS: Enum (ISSUED, VOID, REFUNDED, EXCHANGED)
├─ TICKET_DATE: Date
├─ TICKET_AMOUNT: Money

BAGGAGE_SEGMENT
├─ BAGGAGE_ALLOWANCE: Int (number of pieces)
├─ BAGGAGE_WEIGHT_LIMIT: Int (kg)
├─ BAGGAGE_HEIGHT_LIMIT: Int (cm)
├─ BAGGAGE_SPECIAL_ITEMS: List of {ITEM_TYPE, QUANTITY, RESTRICTIONS}
    └─ Examples: GOLF_CLUBS, BICYCLE, MUSICAL_INSTRUMENT, HAZMAT
```

### PNR Storage: Distributed Database

A production GDS stores billions of PNRs. Storage strategy:

1. **Hot Storage** (recent bookings, last 7 days) → In-memory cache + primary database (Sabre/Amadeus data centers)
2. **Warm Storage** (7 days – 1 year) → Distributed database (replicated across regions)
3. **Cold Storage** (archived bookings) → Long-term archive (S3-like storage)

**Concurrency Handling**:
```
OPTIMISTIC LOCKING on PNR:

1. Agent A retrieves PNR (version=5)
2. Agent B retrieves same PNR (version=5)
3. Agent A modifies seat, saves (version→6)
4. Agent B tries to save, checks version=5, but database has version=6
5. Agent B gets error: "PNR has been modified; please retrieve again"
6. Agent B retrieves updated PNR (version=6)
7. Agent B re-applies their modification and tries again
```

This prevents lost updates and race conditions.

---

## API Examples: How Systems Communicate

### Amadeus Availability Search API

Modern GDS providers (Amadeus, Sabre) expose REST APIs for search and booking. Here's a simplified example:

**Search Request**:

```json
POST /v2/amadeus/shopping/flight-offers

{
  "originLocationCode": "SFO",
  "destinationLocationCode": "LHR",
  "departureDate": "2026-12-15",
  "adults": 1,
  "children": 0,
  "infants": 0,
  "travelClass": "ECONOMY",
  "nonStop": false,
  "max": 10
}
```

**Search Response** (abbreviated):

```json
{
  "data": [
    {
      "id": "1",
      "source": "GDS",
      "instantTicketingRequired": false,
      "nonHomogeneous": false,
      "oneWay": false,
      "lastTicketingDate": "2026-11-25",
      "numberOfBookableSeats": 4,
      "itineraries": [
        {
          "duration": "PT10H30M",
          "segments": [
            {
              "departure": {
                "iataCode": "SFO",
                "at": "2026-12-15T14:30:00"
              },
              "arrival": {
                "iataCode": "ORD",
                "at": "2026-12-15T21:45:00"
              },
              "carrierCode": "UA",
              "number": "100",
              "aircraft": {
                "code": "77W"
              },
              "operating": {
                "carrierCode": "UA"
              },
              "stops": 0,
              "class": "Y"
            }
          ]
        }
      ],
      "price": {
        "currency": "USD",
        "total": "850.00",
        "base": "650.00",
        "fees": [
          {
            "amount": "0.00",
            "type": "SUPPLIER"
          }
        ],
        "grandTotal": "850.00"
      },
      "pricingOptions": {
        "fareType": [
          "PUBLISHED"
        ]
      }
    }
  ]
}
```

**Key fields**:
- `numberOfBookableSeats`: Current available seats (pulled from airline inventory in real time)
- `price.total`: Calculated based on current fare rules and inventory level

### Booking API

Once a passenger selects a flight:

**Booking Request**:

```json
POST /v1/booking/flight-orders

{
  "type": "flight-order",
  "flightOffers": [
    {
      "id": "1",
      "source": "GDS"
    }
  ],
  "travelers": [
    {
      "id": "1",
      "dateOfBirth": "1980-06-14",
      "name": {
        "firstName": "JOHN",
        "lastName": "SMITH"
      },
      "gender": "MALE",
      "contact": {
        "emailAddress": "john.smith@example.com",
        "phones": [
          {
            "deviceType": "MOBILE",
            "countryCallingCode": "1",
            "number": "4155551234"
          }
        ]
      },
      "documents": [
        {
          "documentType": "PASSPORT",
          "birthPlace": "Madrid",
          "issuanceLocation": "Madrid",
          "issuanceDate": "2015-04-14",
          "number": "00000000",
          "expiryDate": "2025-04-14",
          "issuanceCountry": "ES",
          "validityCountry": "US",
          "nationality": "ES",
          "holder": true
        }
      ]
    }
  ],
  "remarks": {
    "general": [
      {
        "subType": "GENERAL_REMARK",
        "text": "VEGAN MEAL REQUIRED"
      }
    ]
  }
}
```

**Booking Response** (PNR created):

```json
{
  "id": "ABC123XY",
  "associatedRecords": [
    {
      "reference": "ABC123XY",
      "creationDate": "2026-10-11",
      "creationOffice": "SFO123456"
    }
  ],
  "flightOffers": [
    {
      "id": "1",
      "source": "GDS",
      "instantTicketingRequired": false,
      "nonHomogeneous": false,
      "oneWay": false,
      "lastTicketingDate": "2026-11-25",
      "numberOfBookableSeats": 3,
      "itineraries": [
        {
          "duration": "PT10H30M",
          "segments": [
            {
              "departure": {
                "iataCode": "SFO",
                "at": "2026-12-15T14:30:00"
              },
              "arrival": {
                "iataCode": "LHR",
                "at": "2026-12-16T09:45:00"
              },
              "carrierCode": "UA",
              "number": "100",
              "aircraft": {
                "code": "77W"
              },
              "operating": {
                "carrierCode": "UA"
              },
              "class": "Y",
              "class_of_service": "Y"
            }
          ]
        }
      ],
      "price": {
        "currency": "USD",
        "total": "850.00",
        "base": "650.00",
        "grandTotal": "850.00"
      }
    }
  ],
  "travelerPricings": [
    {
      "travelerId": "1",
      "fareDetailsBySegment": [
        {
          "segmentId": "1",
          "cabin": "ECONOMY",
          "fareBasis": "YLEEUS",
          "class": "Y",
          "includedCheckedBags": {
            "weight": 23,
            "weightUnit": "KG"
          }
        }
      ],
      "price": {
        "currency": "USD",
        "total": "850.00",
        "base": "650.00",
        "grandTotal": "850.00"
      },
      "fareDetailsBySegment": []
    }
  ],
  "type": "flight-order",
  "ticketingAgreement": {
    "option": "CONFIRM_FOR_TICKETING",
    "delay": "6D"
  }
}
```

**What happened**:
1. GDS allocated a seat from inventory (inventory -1)
2. PNR created with ID `ABC123XY`
3. Booking held for 6 days (must issue ticket within 6 days or booking expires)
4. `numberOfBookableSeats` decreased from 4 to 3

### Inventory Update API

Behind the scenes, the airline's inventory server updates in real time:

**Update Message** (published to all agents/APIs):

```json
{
  "event": "inventory_update",
  "flight": {
    "airline": "UA",
    "flight_number": "100",
    "departure_date": "2026-12-15"
  },
  "cabin_class": "Y",
  "booking_class": "Y",
  "open_seats_before": 20,
  "open_seats_after": 19,
  "reason": "booking_created",
  "pnr_id": "ABC123XY",
  "timestamp": "2026-10-11T14:32:45Z"
}
```

All other agents receive this in real time and update their displays. This is why seat counts change as you're booking—the inventory is live.

---

## Concurrency & Consistency: The Challenge

### Problem: Overselling

Two agents book the last Economy seat simultaneously:

```
Time 1:  Agent A queries: open_seats = 1
Time 2:  Agent B queries: open_seats = 1
Time 3:  Agent A books: open_seats = 0, sells to Smith
Time 4:  Agent B books: open_seats = -1, sells to Jones  ← PROBLEM
```

Result: Aircraft is oversold by 1 seat, passenger gets denied boarding.

### Solution 1: Pessimistic Locking

```sql
-- Agent A locks the seat
SELECT open_seats FROM flight_inventory 
WHERE flight_id='UA100' AND booking_class='Y'
FOR UPDATE;  -- Lock it, no one else can read until unlocked

UPDATE flight_inventory SET open_seats = open_seats - 1
WHERE flight_id='UA100' AND booking_class='Y';

COMMIT;  -- Release lock
```

Downside: Slow (locks wait for each other). Used for low-concurrency systems.

### Solution 2: Optimistic Locking with Retries (Modern Standard)

```sql
-- Read PNR with version number
SELECT open_seats, version FROM flight_inventory 
WHERE flight_id='UA100' AND booking_class='Y';
-- Returns: open_seats=1, version=42

-- Try to update (only if version hasn't changed)
UPDATE flight_inventory 
SET open_seats = open_seats - 1, version = version + 1
WHERE flight_id='UA100' AND booking_class='Y' AND version=42;

-- If no rows updated, version changed; retry
IF @@ROWCOUNT = 0 THEN
  GOTO RETRY;
ENDIF;
```

Modern GDS (Sabre, Amadeus) use optimistic locking + exponential backoff retry logic.

---

## Overbooking: The Math

Airlines overbook because of no-shows. The **no-show rate** varies by route and season:
- Domestic leisure routes: 5–10% no-show rate
- Long-haul business routes: 2–5% no-show rate
- Last-minute bookings: 15–25% no-show rate

**Overbooking Formula**:

```
Seats to sell = Physical seats × (1 + No_show_rate)

Example:
Boeing 777 = 350 Economy seats
No-show rate = 10%
Seats to sell = 350 × 1.10 = 385
```

**Inventory rule**:
- Open 385 seats for economy booking class
- If no-shows don't materialize, 35 passengers are denied boarding (managed with volunteers + compensation)
- If enough no-shows occur, all 350 seats are filled

Airlines use historical no-show data to calculate overbooking per route per season. This is dynamically updated in the inventory system.

[Research on overbooking optimization](https://iaorifors.com/paper/63772) shows a 2–3% margin is optimal (minimizes both denied boardings and unsold seats).

---

## Real-World System: Booking Flow Diagram

```
User Search Request
        ↓
┌──────────────────────────────────┐
│ GDS Query Engine (Sabre Central) │
│ - Check all participating airlines│
│ - Read inventory in parallel      │
└──────────────────────────────────┘
        ↓
┌──────────────────────────────────┐
│ Airline Inventory Servers (x10)   │
│ - UA inventory → 1 open Y seat    │
│ - LH inventory → 5 open Y seats   │
│ - BA inventory → 0 open Y seats   │
└──────────────────────────────────┘
        ↓
┌──────────────────────────────────┐
│ Rank & Aggregate Results          │
│ - Price sorting (lowest first)    │
│ - Stops (nonstop preferred)       │
│ - Brand preference (home airline) │
└──────────────────────────────────┘
        ↓
Results displayed (microseconds elapsed)

Agent selects UA100
        ↓
┌──────────────────────────────────┐
│ Booking Engine                    │
│ 1. Check seat available (again)   │
│ 2. Lock PNR version (optimistic)  │
│ 3. Decrement inventory: 1 → 0     │
│ 4. Create PNR record              │
│ 5. Assign seat number             │
│ 6. Process payment                │
│ 7. Unlock PNR (commit)            │
└──────────────────────────────────┘
        ↓
┌──────────────────────────────────┐
│ PNR Database (Replicated)         │
│ - Master: Data Center A           │
│ - Replica: Data Center B          │
│ - Replica: Data Center C          │
└──────────────────────────────────┘
        ↓
┌──────────────────────────────────┐
│ Event Stream (Kafka / Pub-Sub)    │
│ Publish: "Inventory update UA100" │
│ Subscribers: Travel agents,       │
│             GDS portals,          │
│             Airlines              │
└──────────────────────────────────┘
        ↓
All agents refresh; seat count decreases
Ticket issued; PNR confirmed
```

---

## Key Technologies in Production Systems

| Component | Technology | Example |
| --- | --- | --- |
| **Primary Database** | Distributed relational DB | Oracle, Sybase (legacy); PostgreSQL, MySQL (modern) |
| **Cache Layer** | In-memory key-value store | Redis, Memcached (for hot inventory) |
| **Message Queue** | Event streaming | Kafka, RabbitMQ (inventory updates to agents) |
| **Search Engine** | Indexed query engine | Elasticsearch, Solr (search flights by date/route) |
| **API Gateway** | REST/GraphQL server | AWS API Gateway, Kong, Tyk |
| **Load Balancer** | Distribute requests | NGINX, HAProxy (across multiple inventory servers) |
| **Replication** | Master-slave or multi-master | Streaming replication (inventory replicas in multiple regions) |

---

## Performance Metrics to Know

If you're supporting or building a GDS:

| Metric | Target | Why It Matters |
| --- | --- | --- |
| **Search latency** | <500ms | Users won't wait for search results |
| **Booking latency** | <2s | Agent productivity; every second costs money |
| **Inventory update latency** | <1s | Agents see real-time availability |
| **PNR retrieval** | <100ms | Agents modify bookings instantly |
| **Booking concurrency** | 10K+ simultaneous bookings | Peak times (holiday sales) hit thousands/sec |
| **Database replication lag** | <100ms | Backup DC can take over seamlessly |
| **API availability** | 99.99% (4 nines) | Airlines cannot afford downtime |

---

## Where to Learn More

- **IATA Airline Coding Manual**: [IATA Standards](https://www.iata.org) (covers PNR structure, Resolution 722/723)
- **Seat Inventory Control Algorithms**: [US Patent 5255184A](https://patents.google.com/patent/US5255184A) — foundational work still used today
- **Yield Management Research**: [Van Ryzin & Talluri, "Revenue Management"](https://business.columbia.edu/sites/default/files-efs/pubfiles/3925/vanryzin_revenue.pdf) — Columbia Business School
- **Amadeus API Documentation**: [Amadeus for Developers](https://amadeus.com/en) (public sandbox for testing)
- **Sabre API Documentation**: [Sabre Dev Studio](https://developer.sabre.com) (similar public APIs)
- **GDS Architecture Deep Dive**: Most GDS vendors offer white papers to technical customers (request from your sales contact)

---

## Interview Questions You Might Get

1. **"Explain how inventory decreases when a seat is booked."**
   - Atomic database update, concurrency handling, replication across data centers

2. **"How do we prevent overbooking a flight?"**
   - Pessimistic locking (slow but safe) vs. optimistic locking with retries (fast, standard)
   - No-show rate calculations built into oversell limits

3. **"What happens if a PNR is modified by two agents simultaneously?"**
   - Optimistic locking: version numbers; second agent gets "conflict" error and retries

4. **"How does a search query return results in <500ms across 10 airlines?"**
   - Parallel queries to all airline inventory servers + cached results + indexing

5. **"What's the difference between inventory control and seat allocation?"**
   - **Inventory control**: Real-time seat availability tracking
   - **Seat allocation**: Algorithm (EMSR, Littlewood's Rule) to decide how many seats per fare class

---

*Last updated: October 2026. GDS technologies evolve; consult current Sabre, Amadeus, and airline documentation for production details.*
