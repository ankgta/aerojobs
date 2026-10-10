---
title: "Airline Operations Basics: Interline, Codeshare, Inventory, and Passenger Journey"
description: "Essential terminology for airline operations roles—interline agreements, codeshare mechanics, seat inventory control, and how passengers move through the system. A beginner's guide for new hires at airlines, GDS providers, and reservations companies."
date: 2026-10-11
---

If you're starting a job at an airline, a reservations center, or a GDS (Global Distribution System) company like Sabre or Amadeus, you'll hear terms like "interline," "codeshare," "inventory control," and "passenger name record" on your first day. This guide explains what they mean, how they work in practice, and why they matter to your role.

## The Passenger Journey: Where These Terms Matter

Before diving into definitions, here's the flow:

1. **Passenger searches** for a flight on a website or through a travel agent (powered by a GDS)
2. **Inventory system** checks seat availability
3. **Booking is created** — a Passenger Name Record (PNR) is generated
4. **Ticket is issued** — either on a single airline or shared via codeshare/interline
5. **Passenger checks in** — system assigns seat, tags baggage
6. **Flight operates** — airlines cooperate (interline) or share flights (codeshare)
7. **Passenger arrives** — baggage transferred if needed (interline only)

Most of your daily work involves steps 2–4. Understanding the full journey helps you troubleshoot when things break.

## Interline: When Two Different Airlines Work Together

**Interline** is an agreement between two airlines to honor each other's tickets and transfer passengers and baggage.

### What Interline Actually Means

An interline agreement lets an airline accept a ticket issued by another airline. For example:
- Passenger buys a ticket from **United Airlines** for a United flight to Chicago, then a **Lufthansa** flight to Berlin
- United's ticket covers both legs
- At Chicago, Lufthansa takes the passenger (and baggage) even though Lufthansa didn't issue the ticket
- The two airlines settle money later

### Why Interline Exists

Before codeshare and GDS systems, interline was the *only* way to sell connecting flights on multiple airlines. Today it's less common but still critical for:
- **Missed connections** — if a passenger misses their second flight, the next available flight on any airline honors the ticket
- **Irregular operations** (flight cancellations) — passenger can be rebooked on any interline partner
- **International routes** — some routes are operated by airline partnerships under interline rules

### The Interline Rules (IATA Resolution 722)

The rules are set by [IATA Resolution 722](https://www.iata.org/contentassets/e7a533819be440edbb1e49da96e0f2a8/industry-restart-new-partnerships-in-interline-framework.pdf), which covers:
- Which airlines can honor which tickets
- Baggage allowances and handling
- Liability and refund rules
- Settlement procedures

### Real Example

A passenger booked on:
- **United Flight UA123** departing San Francisco at 10:00 AM, arriving Chicago at 4:00 PM
- **Lufthansa Flight LH401** departing Chicago at 6:00 PM, arriving Berlin at 8:00 AM (next day)

If UA123 is delayed and the passenger misses LH401:
- The United ticket is still valid (interline agreement)
- Lufthansa rebooking desk accepts the ticket and rebooks the passenger on the next available Lufthansa flight to Berlin
- United and Lufthansa later settle the cost of the new flight through their interline clearing house

**Job impact**: If you work at an airline rebooking desk, you need to know which airlines have interline agreements with you so you can confidently rebook passengers on competitors' flights without calling for approval.

---

## Codeshare: One Flight, Two Airline Names

**Codeshare** is an agreement where two airlines use the same flight but sell seats under their own airline code.

### What Codeshare Actually Means

On a codeshare flight:
- **One airline operates the flight** (the "operating carrier" or "actual flight operator")
- **Other airlines sell seats under their own code** (the "marketing carriers")

Example:
- **United Airlines operates** a daily flight from San Francisco to London (UA950)
- **British Airways also sells seats** on the same plane under **BA8950**
- **American Airlines also sells seats** under **AA6950**

Passengers on all three flights are on the *same plane* but booked under different codes.

### Why Airlines Do Codeshare

Codeshare benefits both airlines:

| Benefit | Operating Airline | Marketing Airline |
| --- | --- | --- |
| Revenue | Fills more seats on the actual flight | Sells a London flight without operating one |
| Cost | Shares risk with partners | Lower cost — no aircraft, crew, fuel needed |
| Network | Grows partnerships | Expands route network without investment |
| Customer | Loyalty program miles | Access to partner's frequent-flyer benefits |

### The Codeshare Agreement (IATA Resolution 723)

Rules are set by [IATA Resolution 723](https://www.iata.org), covering:
- Revenue sharing (how much each airline gets from ticket sales)
- Seat allocation (how many seats each airline can sell)
- Fare coordination (pricing rules)
- Liability (who is responsible if the flight is delayed)

### Real Example: United + Brussels Airlines + Air France

United, Brussels Airlines, and Air France operate a codeshare on the Newark-Brussels route:
- **Brussels Airlines actually operates** a Boeing 777 from Newark to Brussels
- **United sells 100 of 350 seats** as United flight UA 956
- **Air France sells 80 seats** as AF 6956
- **Brussels Airlines sells 170 seats** as SN 500

A passenger can buy on any of the three codes. All three codes take them on the same physical flight.

**Job impact**: When you search for flights in a GDS, codeshare flights appear. You need to understand that a "United" flight from Newark to Brussels might actually be Brussels Airlines operating it. This matters for:
- **Ground operations** — which airline's crew and catering handles the flight
- **Frequent flyer miles** — a United passenger on a Brussels Airlines flight gets United miles but Brussels Airlines operates the flight
- **Customer service** — if the flight is delayed, which airline is responsible?

---

## Inventory: The Seat Management System

**Inventory** is the airline's real-time database of seat availability, grouped by fare class and flight.

### How Inventory Works

Each flight has a fixed number of seats (e.g., 350 on a Boeing 777). Those seats are divided into:
- **Cabin classes** — First, Business, Economy
- **Booking classes** — fare levels within each cabin (Economy has Y, B, M, L classes at different prices)
- **Open inventory** — seats available to sell
- **Sold inventory** — seats already booked

### Example: A Single Flight's Inventory

```
Flight: UA456, San Francisco to New York
Aircraft: Boeing 787, Total Seats: 242

First Class (Business/First cabin):
- F class (Full fare): 2 sold, 6 open
- A class (Upgrade/Discount): 0 sold, 4 open
- Subtotal First: 2 sold, 10 open

Business Class:
- J class (Full): 8 sold, 4 open
- Z class (Discounted): 10 sold, 8 open
- Subtotal Business: 18 sold, 12 open

Economy:
- Y class (Full): 50 sold, 20 open
- M class (Mid): 45 sold, 25 open
- L class (Low): 60 sold, 15 open
- K class (Ultra-low): 30 sold, 17 open
- Subtotal Economy: 185 sold, 77 open

Total: 205 sold, 99 open
```

### Seat Inventory Control: The Math Behind Overbooking

Airlines overbook flights because passengers don't always show up. But they can't oversell too much.

**Overbooking factor** = No-show rate (typically 5–15% depending on route and season)

If the no-show rate is 10%:
- 350-seat flight
- 10% no-show = 35 passengers expected to not show
- **Airline books 385 seats** to fill 350 actual seats

The inventory system automatically calculates how many seats to open per class based on:
- Historical no-show rates
- Demand forecasts
- Cargo capacity (some flights carry cargo in empty seats)
- Airline overbooking policy

[Research shows airline seat inventory control uses complex algorithms](https://patents.google.com/patent/US5255184A) to maximize revenue while managing the risk of too many oversells (and therefore denied boardings).

### Yield Management: Dynamic Pricing Tied to Inventory

Airlines adjust prices based on how many seats are left:
- **High inventory** (lots of empty seats) → Lower fares
- **Low inventory** (few seats left) → Higher fares

This is why the same flight costs $150 a month in advance but $600 two days before departure—the inventory system shows fewer seats open, so the GDS raises fares.

**Job impact**: If you work in reservations or pricing, you need to understand that every time you book a seat, the inventory goes down by one, and the system may automatically raise the price of remaining seats. If a customer complains about a price quote that changed in 2 hours, it's because inventory changed (not always because the airline is being greedy).

---

## Passenger Name Record (PNR): The Complete Booking Record

**PNR** is a single record that holds all the information about a passenger's booking: name, flight, seat, baggage, special requests, and payment.

### What's Inside a PNR

A typical PNR includes:
- **Passenger names** (usually as they appear on passport)
- **Itinerary** — flights, dates, seat numbers
- **Contact details** — phone, email, address
- **Special requests** — dietary needs (VEGAN, LOWFAT), seat preference (aisle, window), mobility assistance
- **Baggage** — number of bags, weight, special items
- **Payment** — credit card, ticket number, price paid
- **Ticketing status** — issued, pending, waitlisted
- **Remarks** — notes from agent (e.g., "customer called to confirm")

A typical PNR record might look like (simplified):

```
PNR: ABC123
Created: 11 OCT 26
Last modified: 11 OCT 26 14:32

NAME: SMITH/JOHN MR
      SMITH/JANE MS

ITINERARY:
1. 15DEC SFO-LHR UA100 Y 14:00 CONFIRMED
   Seat: 45A/45B
2. 22DEC LHR-SFO UA101 Y 11:00 CONFIRMED
   Seat: 45A/45B

CONTACT:
Address: 123 Main St, San Francisco, CA 94102
Phone: (415) 555-1234
Email: john.smith@email.com

REMARKS:
- Requested aisle seats for both
- Traveling with child (DOB 05JAN24)
- Notes: Celebrating 25th anniversary

BAGGAGE:
2 checked bags per passenger (baseline)
Special baggage: None

PAYMENT:
Ticket number: 0011234567890
Price: $2,450.00 (2 adult Economy, roundtrip)
Payment: VISA ending 4242
```

### PNR in the Real System

In actual GDS systems ([like Amadeus](https://amadeus.com/en/travel-glossary/passenger-name-record) or Sabre), a PNR is stored centrally and accessed by:
- Travel agents (to modify the booking)
- Airline reservations (to issue the ticket)
- Check-in (to verify the passenger)
- Ground operations (to handle baggage)
- Crew (on some systems, to know about special needs)

**Job impact**: As a reservations agent, you spend most of your day in PNRs. You:
- Create PNRs when booking
- Modify PNRs to add seats, meals, or baggage
- Manage waitlisted PNRs (converting them to CONFIRMED when space opens)
- Read PNRs to troubleshoot customer issues
- Cancel PNRs (which refunds the ticket)

Understanding the structure helps you work faster and avoid mistakes like forgetting to add a special meal or missing a contact detail.

---

## How These Systems Work Together: A Real Scenario

You're a reservations agent at United Airlines. A customer calls:

> "I want to book San Francisco to Berlin. I'll fly United to Chicago, then Lufthansa to Berlin."

**Step 1: Search**
- You search the GDS (Sabre or Amadeus) for flights
- GDS checks inventory on both airlines
- Result: UA123 SFO-ORD (Economy seats open), LH401 ORD-BER (codeshare marketed as United, inventory available)

**Step 2: Check Codeshare Terms**
- LH401 is a **Lufthansa-operated codeshare** sold by United
- You confirm with the customer: "The Berlin leg is operated by Lufthansa, but you'll be on a United ticket"

**Step 3: Check Interline Rules**
- United and Lufthansa have an **interline agreement**
- If the passenger misses the Lufthansa connection due to a delay, Lufthansa will honor the ticket

**Step 4: Create the PNR**
- You create a PNR with both flights
- System allocates seats: 15A (SFO-ORD), 32B (ORD-BER)
- Inventory decreases by 1 on UA123 and LH401

**Step 5: Issue Ticket**
- One ticket covers both flights
- Ticket number: 0011234567890 (United's numbering)
- Cost: $1,200

**Step 6: Passenger Travels**
- Arrives in Chicago on time for the Lufthansa flight
- Lufthansa agent scans the United ticket (interline agreement in action)
- Baggage auto-transfers to Berlin (interline baggage handling)
- Passenger arrives in Berlin

This entire flow depends on inventory systems, codeshare partnerships, and interline agreements working together seamlessly.

---

## Key Takeaways for Your Role

| Term | What It Means | Why It Matters to You |
| --- | --- | --- |
| **Interline** | Two airlines accept each other's tickets and transfer passengers/baggage | Understand which airlines can rebook passengers on competitors' flights |
| **Codeshare** | Two airlines sell seats on the same flight under different codes | Know which airline actually operates the flight (affects crew, liability, service) |
| **Inventory** | Real-time seat availability database | Every booking decreases inventory; low inventory triggers higher prices |
| **Overbooking** | Airlines sell more seats than available, betting on no-shows | Understand why denied boardings happen and how to handle them |
| **PNR** | The complete booking record for a passenger | Master PNR structure to modify bookings, troubleshoot issues, and serve customers faster |

---

## Where to Learn More

- **IATA Resolution 722** (Interline): [industry-restart-new-partnerships-in-interline-framework.pdf](https://www.iata.org/contentassets/e7a533819be440edbb1e49da96e0f2a8/industry-restart-new-partnerships-in-interline-framework.pdf)
- **IATA Resolution 723** (Codeshare): Covered in IATA Airline Coding Manual (available through IATA)
- **Passenger Name Record standards**: [ICAO FALP Document](https://www.icao.int:443/Meetings/FALP/Documents/falp6_2010/FALP6_WP05_en.pdf)
- **Seat inventory control research**: [US Patent 5255184](https://patents.google.com/patent/US5255184A) — early formalization of algorithms used in modern systems
- **Airline operations guides**: Consult your employer's internal training (most airlines have orientation docs on these topics)

Your first week, your trainer will dive deep into your airline's specific interline partners, codeshare routes, and overbooking policy. This guide is the foundation.

*Last updated: October 2026. Standards and specific airline policies are subject to change; always verify with your employer's documentation.*
