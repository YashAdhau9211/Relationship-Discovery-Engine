import argparse
from collections import Counter
from datetime import date
from itertools import combinations

from app.core.config import get_settings
from app.db.neo4j import Neo4jClient
from app.db.schema import bootstrap_schema


def slug(value: str) -> str:
    return value.lower().replace(" ", "-").replace(".", "").replace("'", "")


PEOPLE_BLUEPRINTS = [
    ("Alice Chen", "US", "intelligence_analyst", "person:alice-chen"),
    ("Ben Ortiz", "US", "data_engineer", "person:ben-ortiz"),
    ("Carla Singh", "IN", "ngo_advisor", "person:carla-singh"),
    ("David Kim", "KR", "security_researcher", "person:david-kim"),
    ("Elena Petrova", "BG", "finance_ops", None),
    ("Farah Al Mansour", "AE", "logistics_manager", None),
    ("Grace Okafor", "NG", "compliance_officer", None),
    ("Hugo Martinez", "MX", "platform_engineer", None),
    ("Iris Novak", "CZ", "policy_researcher", None),
    ("Jonah Reed", "US", "founder", None),
    ("Kavya Raman", "IN", "ml_engineer", None),
    ("Liam O'Connor", "IE", "investigator", None),
    ("Maya Hassan", "EG", "field_coordinator", None),
    ("Nora Fischer", "DE", "academic", None),
    ("Omar Haddad", "JO", "vendor_manager", None),
    ("Priya Nair", "IN", "risk_manager", None),
    ("Quinn Walker", "US", "journalist", None),
    ("Rafael Costa", "BR", "payments_specialist", None),
    ("Sara Lind", "SE", "research_director", None),
    ("Tariq Saleh", "SA", "procurement_lead", None),
    ("Uma Iyer", "IN", "data_scientist", None),
    ("Victor Sokolov", "UA", "systems_admin", None),
    ("Wendy Brooks", "US", "legal_counsel", None),
    ("Xavier Laurent", "FR", "community_manager", None),
    ("Yara Haddad", "LB", "social_researcher", None),
    ("Zane Murphy", "AU", "devops_engineer", None),
    ("Amina Diallo", "SN", "program_manager", None),
    ("Boris Volkov", "RU", "broker", None),
    ("Camila Torres", "CO", "regional_lead", None),
    ("Dev Patel", "IN", "product_manager", None),
    ("Eva Novak", "SK", "analyst", None),
    ("Felix Meyer", "DE", "infrastructure_lead", None),
    ("Gita Rao", "IN", "education_admin", None),
    ("Harper Stone", "US", "forensics_specialist", None),
    ("Isla Morgan", "GB", "operations_lead", None),
    ("Jae Park", "KR", "growth_manager", None),
    ("Kofi Mensah", "GH", "community_liaison", None),
    ("Leila Haddad", "MA", "field_researcher", None),
    ("Mateo Silva", "CL", "network_admin", None),
    ("Nikhil Shah", "IN", "backend_engineer", None),
    ("Olivia Grant", "CA", "audit_lead", None),
    ("Pavel Orlov", "KZ", "vendor_operator", None),
    ("Rina Sato", "JP", "ai_researcher", None),
    ("Samir Khan", "PK", "logistics_analyst", None),
    ("Tessa Young", "NZ", "program_director", None),
    ("Uri Cohen", "IL", "security_architect", None),
    ("Valeria Rossi", "IT", "finance_controller", None),
    ("Wei Zhang", "CN", "data_platform_lead", None),
]

ORGANIZATIONS = [
    {"canonical_id": "org:novus-labs", "org_name": "Novus Labs", "org_type": "company", "jurisdiction": "US-DE", "pagerank_score": 0.91},
    {"canonical_id": "org:civic-data-trust", "org_name": "Civic Data Trust", "org_type": "ngo", "jurisdiction": "US-NY", "pagerank_score": 0.74},
    {"canonical_id": "org:helix-foundation", "org_name": "Helix Foundation", "org_type": "foundation", "jurisdiction": "CH-ZH", "pagerank_score": 0.69},
    {"canonical_id": "org:atlas-logistics", "org_name": "Atlas Logistics", "org_type": "logistics", "jurisdiction": "AE-DU", "pagerank_score": 0.63},
    {"canonical_id": "org:quantum-bridge-capital", "org_name": "Quantum Bridge Capital", "org_type": "investment_firm", "jurisdiction": "GB-LND", "pagerank_score": 0.81},
    {"canonical_id": "org:open-cities-lab", "org_name": "Open Cities Lab", "org_type": "research_lab", "jurisdiction": "DE-BE", "pagerank_score": 0.66},
    {"canonical_id": "org:blue-river-consulting", "org_name": "Blue River Consulting", "org_type": "consulting", "jurisdiction": "CA-ON", "pagerank_score": 0.58},
    {"canonical_id": "org:meridian-aid-network", "org_name": "Meridian Aid Network", "org_type": "aid_network", "jurisdiction": "NG-LA", "pagerank_score": 0.62},
    {"canonical_id": "org:pacific-signal-group", "org_name": "Pacific Signal Group", "org_type": "telecom", "jurisdiction": "SG-01", "pagerank_score": 0.77},
    {"canonical_id": "org:northstar-analytics", "org_name": "Northstar Analytics", "org_type": "analytics_vendor", "jurisdiction": "US-CA", "pagerank_score": 0.71},
    {"canonical_id": "org:vector-security", "org_name": "Vector Security", "org_type": "security_vendor", "jurisdiction": "IL-TA", "pagerank_score": 0.73},
    {"canonical_id": "org:solstice-holdings", "org_name": "Solstice Holdings", "org_type": "holding_company", "jurisdiction": "LU-LU", "pagerank_score": 0.55},
]

EDUCATION_INSTITUTIONS = [
    {"institution_id": "edu:stanford", "name": "Stanford University", "type": "university", "country": "US", "field_taxonomy": ["computer_science", "data_science"]},
    {"institution_id": "edu:mit", "name": "Massachusetts Institute of Technology", "type": "university", "country": "US", "field_taxonomy": ["systems", "ai"]},
    {"institution_id": "edu:oxford", "name": "University of Oxford", "type": "university", "country": "GB", "field_taxonomy": ["policy", "law"]},
    {"institution_id": "edu:iit-delhi", "name": "Indian Institute of Technology Delhi", "type": "university", "country": "IN", "field_taxonomy": ["engineering", "data_science"]},
    {"institution_id": "edu:sciences-po", "name": "Sciences Po", "type": "university", "country": "FR", "field_taxonomy": ["international_relations", "policy"]},
    {"institution_id": "edu:eth-zurich", "name": "ETH Zurich", "type": "university", "country": "CH", "field_taxonomy": ["security", "networks"]},
    {"institution_id": "edu:university-of-cape-town", "name": "University of Cape Town", "type": "university", "country": "ZA", "field_taxonomy": ["urban_systems", "public_policy"]},
    {"institution_id": "edu:nus", "name": "National University of Singapore", "type": "university", "country": "SG", "field_taxonomy": ["telecom", "ai"]},
]

LOCATIONS = [
    {"location_id": "loc:san-francisco", "location_name": "San Francisco", "type": "city", "country_code": "US", "latitude": 37.7749, "longitude": -122.4194},
    {"location_id": "loc:new-york", "location_name": "New York", "type": "city", "country_code": "US", "latitude": 40.7128, "longitude": -74.0060},
    {"location_id": "loc:london", "location_name": "London", "type": "city", "country_code": "GB", "latitude": 51.5072, "longitude": -0.1276},
    {"location_id": "loc:dubai", "location_name": "Dubai", "type": "city", "country_code": "AE", "latitude": 25.2048, "longitude": 55.2708},
    {"location_id": "loc:berlin", "location_name": "Berlin", "type": "city", "country_code": "DE", "latitude": 52.5200, "longitude": 13.4050},
    {"location_id": "loc:singapore", "location_name": "Singapore", "type": "city", "country_code": "SG", "latitude": 1.3521, "longitude": 103.8198},
    {"location_id": "loc:lagos", "location_name": "Lagos", "type": "city", "country_code": "NG", "latitude": 6.5244, "longitude": 3.3792},
    {"location_id": "loc:mumbai", "location_name": "Mumbai", "type": "city", "country_code": "IN", "latitude": 19.0760, "longitude": 72.8777},
    {"location_id": "loc:geneva", "location_name": "Geneva", "type": "city", "country_code": "CH", "latitude": 46.2044, "longitude": 6.1432},
    {"location_id": "loc:asn-64512", "location_name": "ASN 64512 Cloud Relay", "type": "ip_asn", "country_code": "ZZ", "latitude": 0.0, "longitude": 0.0, "ip_range": "10.48.0.0/16"},
    {"location_id": "loc:sf-mission-workspace", "location_name": "Mission Street Workspace", "type": "venue", "country_code": "US", "latitude": 37.7601, "longitude": -122.4194},
    {"location_id": "loc:dubai-freezone-warehouse", "location_name": "Dubai Free Zone Warehouse", "type": "venue", "country_code": "AE", "latitude": 25.1100, "longitude": 55.3800},
]

EVENTS = [
    {"event_id": "event:graph-summit-2026", "type": "conference", "timestamp": "2026-02-12T10:00:00Z", "platform": "offline", "location_id": "loc:san-francisco"},
    {"event_id": "event:aid-procurement-roundtable", "type": "roundtable", "timestamp": "2026-01-18T14:00:00Z", "platform": "offline", "location_id": "loc:dubai"},
    {"event_id": "event:encrypted-call-alpha", "type": "call", "timestamp": "2026-03-04T21:30:00Z", "platform": "signal", "location_id": "loc:asn-64512"},
    {"event_id": "event:open-data-hacknight", "type": "meetup", "timestamp": "2026-02-20T18:00:00Z", "platform": "offline", "location_id": "loc:berlin"},
    {"event_id": "event:vendor-demo-northstar", "type": "demo", "timestamp": "2026-03-11T16:00:00Z", "platform": "zoom", "location_id": "loc:new-york"},
    {"event_id": "event:geneva-policy-forum", "type": "forum", "timestamp": "2026-04-02T09:00:00Z", "platform": "offline", "location_id": "loc:geneva"},
    {"event_id": "event:singapore-signal-review", "type": "workshop", "timestamp": "2026-02-27T11:00:00Z", "platform": "offline", "location_id": "loc:singapore"},
    {"event_id": "event:lagos-community-briefing", "type": "briefing", "timestamp": "2026-01-29T15:00:00Z", "platform": "offline", "location_id": "loc:lagos"},
    {"event_id": "event:mumbai-payments-audit", "type": "audit", "timestamp": "2026-03-19T12:00:00Z", "platform": "offline", "location_id": "loc:mumbai"},
    {"event_id": "event:sf-warehouse-review", "type": "site_visit", "timestamp": "2026-04-08T13:00:00Z", "platform": "offline", "location_id": "loc:sf-mission-workspace"},
    {"event_id": "event:dubai-shipment-exception", "type": "shipment", "timestamp": "2026-04-14T06:00:00Z", "platform": "logistics", "location_id": "loc:dubai-freezone-warehouse"},
    {"event_id": "event:case-sync-bridge", "type": "case_sync", "timestamp": "2026-05-02T17:00:00Z", "platform": "teams", "location_id": "loc:asn-64512"},
]

COMMUNITIES = [
    {"community_id": "community:graph-intelligence", "name": "Graph Intelligence Cohort", "platform": "synthetic", "visibility": "private", "algorithm_source": "seed", "modularity_contribution": 0.31},
    {"community_id": "community:aid-procurement", "name": "Aid Procurement Network", "platform": "synthetic", "visibility": "private", "algorithm_source": "seed", "modularity_contribution": 0.27},
    {"community_id": "community:open-cities", "name": "Open Cities Research Circle", "platform": "synthetic", "visibility": "public", "algorithm_source": "seed", "modularity_contribution": 0.22},
    {"community_id": "community:telecom-signal", "name": "Telecom Signal Review Group", "platform": "synthetic", "visibility": "private", "algorithm_source": "seed", "modularity_contribution": 0.25},
    {"community_id": "community:payments-risk", "name": "Payments Risk Cluster", "platform": "synthetic", "visibility": "private", "algorithm_source": "seed", "modularity_contribution": 0.24},
    {"community_id": "community:policy-forum", "name": "Policy Forum Alumni", "platform": "synthetic", "visibility": "public", "algorithm_source": "seed", "modularity_contribution": 0.19},
    {"community_id": "community:hidden-brokers", "name": "Hidden Broker Candidates", "platform": "synthetic", "visibility": "restricted", "algorithm_source": "seed", "modularity_contribution": 0.37},
]

COMMUNITY_GROUPS = {
    "community:graph-intelligence": ["person:alice-chen", "person:ben-ortiz", "person:kavya-raman", "person:uma-iyer", "person:nikhil-shah", "person:wei-zhang", "person:rina-sato"],
    "community:aid-procurement": ["person:farah-al-mansour", "person:omar-haddad", "person:tariq-saleh", "person:samir-khan", "person:amina-diallo", "person:pavel-orlov"],
    "community:open-cities": ["person:carla-singh", "person:iris-novak", "person:sara-lind", "person:xavier-laurent", "person:kofi-mensah", "person:leila-haddad"],
    "community:telecom-signal": ["person:hugo-martinez", "person:zane-murphy", "person:mateo-silva", "person:uri-cohen", "person:jae-park", "person:felix-meyer"],
    "community:payments-risk": ["person:elena-petrova", "person:rafael-costa", "person:priya-nair", "person:valeria-rossi", "person:olivia-grant", "person:grace-okafor"],
    "community:policy-forum": ["person:liam-oconnor", "person:nora-fischer", "person:wendy-brooks", "person:quinn-walker", "person:tessa-young", "person:yara-haddad"],
    "community:hidden-brokers": ["person:david-kim", "person:boris-volkov", "person:maya-hassan", "person:jonah-reed", "person:camila-torres", "person:isla-morgan", "person:dev-patel", "person:gita-rao"],
}


def build_people() -> list[dict]:
    people = []
    for idx, (name, nationality, role, explicit_id) in enumerate(PEOPLE_BLUEPRINTS, start=1):
        canonical_id = explicit_id or f"person:{slug(name)}"
        people.append(
            {
                "canonical_id": canonical_id,
                "name": name,
                "aliases": [name.split()[0][0] + ". " + name.split()[-1], name.replace(" ", "_").lower()],
                "date_of_birth": date(1978 + (idx % 18), ((idx * 3) % 12) + 1, ((idx * 7) % 27) + 1).isoformat(),
                "nationality": nationality,
                "role_hint": role,
                "source_ids": [f"crm:{1000 + idx}", f"social:{slug(name)}", f"hris:{5000 + idx}"],
                "er_confidence": round(0.91 + ((idx % 9) * 0.01), 2),
                "classification": "synthetic_complex",
                "risk_segment": ["low", "medium", "watchlist", "sensitive"][idx % 4],
            }
        )
    return people


def edge(source: str, rel_type: str, target: str, props: dict) -> tuple[str, str, str, dict]:
    return source, rel_type, target, props


def node_identity_cypher(alias: str) -> str:
    return (
        "CASE "
        f"WHEN {alias}:Person THEN {alias}.canonical_id "
        f"WHEN {alias}:Organization THEN {alias}.canonical_id "
        f"WHEN {alias}:EducationInstitution THEN {alias}.institution_id "
        f"WHEN {alias}:Location THEN {alias}.location_id "
        f"WHEN {alias}:Event THEN {alias}.event_id "
        f"WHEN {alias}:Community THEN {alias}.community_id "
        f"ELSE coalesce({alias}.canonical_id, {alias}.institution_id, {alias}.location_id, {alias}.event_id, {alias}.community_id) "
        "END"
    )


def build_relationships() -> list[tuple[str, str, str, dict]]:
    relationships: list[tuple[str, str, str, dict]] = []
    people_ids = [person["canonical_id"] for person in build_people()]

    # Community memberships and dense local friend/follow graphs.
    for community_id, members in COMMUNITY_GROUPS.items():
        for order, member in enumerate(members):
            relationships.append(edge(member, "MEMBER_OF", community_id, {"role": "member", "start_date": f"2025-{(order % 9) + 1:02d}-01", "membership_type": "detected_seed"}))
        for left, right in zip(members, members[1:]):
            relationships.append(edge(left, "FOLLOWS", right, {"weight": 0.55 + (len(left) % 4) * 0.08, "timestamp": "2026-01-05T00:00:00Z", "platform": "synthetic-social"}))
            if len(relationships) % 3 == 0:
                relationships.append(edge(right, "FOLLOWS", left, {"weight": 0.49, "timestamp": "2026-01-06T00:00:00Z", "platform": "synthetic-social"}))
        for left, right in combinations(members[:4], 2):
            relationships.append(edge(left, "FRIENDS_WITH", right, {"weight": 0.72, "timestamp": "2026-01-10T00:00:00Z", "platform": "synthetic-social", "mutual": True}))

    # Explicit hidden path scenarios:
    # Alice -> Ben -> Carla -> David gives a clean third-degree chain.
    # Alice and David also share education, but no direct social edge.
    bridge_edges = [
        ("person:alice-chen", "person:ben-ortiz", 0.88),
        ("person:ben-ortiz", "person:carla-singh", 0.83),
        ("person:carla-singh", "person:david-kim", 0.79),
        ("person:david-kim", "person:boris-volkov", 0.76),
        ("person:boris-volkov", "person:farah-al-mansour", 0.71),
        ("person:farah-al-mansour", "person:omar-haddad", 0.74),
        ("person:rafael-costa", "person:elena-petrova", 0.78),
        ("person:elena-petrova", "person:valeria-rossi", 0.69),
        ("person:uri-cohen", "person:hugo-martinez", 0.81),
        ("person:hugo-martinez", "person:zane-murphy", 0.67),
    ]
    for source, target, weight in bridge_edges:
        relationships.append(edge(source, "FOLLOWS", target, {"weight": weight, "timestamp": "2026-02-01T00:00:00Z", "platform": "bridge-follow"}))

    org_cycles = [org["canonical_id"] for org in ORGANIZATIONS]
    for idx, person_id in enumerate(people_ids):
        primary_org = org_cycles[idx % len(org_cycles)]
        secondary_org = org_cycles[(idx + 3) % len(org_cycles)]
        relationships.append(edge(person_id, "WORKS_AT", primary_org, {"role": "staff", "start_date": f"{2020 + (idx % 5)}-01-01", "end_date": None if idx % 5 else "2024-12-31", "source": "synthetic_hr", "confidence": 0.86 + (idx % 8) * 0.01}))
        if idx % 3 == 0:
            relationships.append(edge(person_id, "MEMBER_OF", secondary_org, {"role": "advisor", "start_date": f"{2021 + (idx % 4)}-06-01", "end_date": None, "membership_type": "affiliate"}))

    # High-value shared organization overlap scenarios.
    shared_org_edges = [
        ("person:alice-chen", "org:novus-labs", "Research Lead", "2023-01-01", None),
        ("person:ben-ortiz", "org:novus-labs", "Data Engineer", "2022-06-01", None),
        ("person:carla-singh", "org:civic-data-trust", "Advisor", "2024-01-01", None),
        ("person:maya-hassan", "org:civic-data-trust", "Field Coordinator", "2023-09-01", None),
        ("person:farah-al-mansour", "org:atlas-logistics", "Regional Manager", "2021-03-01", None),
        ("person:boris-volkov", "org:atlas-logistics", "External Broker", "2022-11-01", None),
        ("person:elena-petrova", "org:quantum-bridge-capital", "Finance Ops", "2020-04-01", None),
        ("person:rafael-costa", "org:quantum-bridge-capital", "Payments Specialist", "2023-07-01", None),
    ]
    for person_id, org_id, role, start_date, end_date in shared_org_edges:
        relationships.append(edge(person_id, "WORKS_AT", org_id, {"role": role, "start_date": start_date, "end_date": end_date, "source": "synthetic_case_file", "confidence": 0.97}))

    edu_cycles = [school["institution_id"] for school in EDUCATION_INSTITUTIONS]
    fields = ["Computer Science", "Data Science", "Policy", "Security", "International Relations", "Finance"]
    degrees = ["BS", "MS", "PhD", "Certificate"]
    for idx, person_id in enumerate(people_ids):
        school = edu_cycles[idx % len(edu_cycles)]
        start_year = 2004 + (idx % 14)
        relationships.append(edge(person_id, "STUDIED_AT", school, {"degree": degrees[idx % len(degrees)], "field": fields[idx % len(fields)], "start_year": start_year, "end_year": start_year + 2, "overlap_score": round(0.45 + (idx % 5) * 0.1, 2)}))
    relationships.extend(
        [
            edge("person:alice-chen", "STUDIED_AT", "edu:stanford", {"degree": "MS", "field": "Computer Science", "start_year": 2010, "end_year": 2012, "overlap_score": 1.0}),
            edge("person:david-kim", "STUDIED_AT", "edu:stanford", {"degree": "MS", "field": "Data Science", "start_year": 2011, "end_year": 2013, "overlap_score": 0.82}),
            edge("person:kavya-raman", "STUDIED_AT", "edu:iit-delhi", {"degree": "MS", "field": "Data Science", "start_year": 2012, "end_year": 2014, "overlap_score": 0.9}),
            edge("person:nikhil-shah", "STUDIED_AT", "edu:iit-delhi", {"degree": "BS", "field": "Engineering", "start_year": 2011, "end_year": 2015, "overlap_score": 0.76}),
        ]
    )

    loc_cycles = [loc["location_id"] for loc in LOCATIONS]
    for idx, person_id in enumerate(people_ids):
        location = loc_cycles[idx % len(loc_cycles)]
        relationships.append(edge(person_id, "LOCATED_AT", location, {"location_type": "activity_cluster", "start_ts": f"2026-0{(idx % 5) + 1}-01T08:00:00Z", "end_ts": None, "frequency": 3 + (idx % 11), "recency": round(0.35 + (idx % 7) * 0.08, 2)}))
        if idx % 4 == 0:
            relationships.append(edge(person_id, "LOCATED_AT", "loc:asn-64512", {"location_type": "ip_login", "start_ts": "2026-03-04T21:00:00Z", "end_ts": "2026-03-04T23:00:00Z", "frequency": 2, "recency": 0.93}))

    event_attendees = {
        "event:graph-summit-2026": ["person:alice-chen", "person:ben-ortiz", "person:kavya-raman", "person:wei-zhang", "person:rina-sato", "person:david-kim"],
        "event:aid-procurement-roundtable": ["person:farah-al-mansour", "person:omar-haddad", "person:tariq-saleh", "person:boris-volkov", "person:amina-diallo"],
        "event:encrypted-call-alpha": ["person:alice-chen", "person:david-kim", "person:boris-volkov", "person:farah-al-mansour"],
        "event:open-data-hacknight": ["person:carla-singh", "person:iris-novak", "person:sara-lind", "person:xavier-laurent", "person:felix-meyer"],
        "event:vendor-demo-northstar": ["person:jonah-reed", "person:dev-patel", "person:nora-fischer", "person:olivia-grant"],
        "event:geneva-policy-forum": ["person:liam-oconnor", "person:nora-fischer", "person:wendy-brooks", "person:tessa-young", "person:yara-haddad"],
        "event:singapore-signal-review": ["person:hugo-martinez", "person:uri-cohen", "person:jae-park", "person:mateo-silva", "person:wei-zhang"],
        "event:lagos-community-briefing": ["person:amina-diallo", "person:kofi-mensah", "person:leila-haddad", "person:maya-hassan"],
        "event:mumbai-payments-audit": ["person:priya-nair", "person:rafael-costa", "person:valeria-rossi", "person:grace-okafor"],
        "event:dubai-shipment-exception": ["person:farah-al-mansour", "person:boris-volkov", "person:pavel-orlov", "person:samir-khan"],
        "event:case-sync-bridge": ["person:alice-chen", "person:liam-oconnor", "person:maya-hassan", "person:olivia-grant", "person:uri-cohen"],
    }
    event_lookup = {event["event_id"]: event for event in EVENTS}
    for event_id, attendees in event_attendees.items():
        event_props = event_lookup[event_id]
        for attendee in attendees:
            relationships.append(edge(attendee, "CO_OCCURRED_IN", event_id, {"event_type": event_props["type"], "timestamp": event_props["timestamp"], "location_id": event_props["location_id"]}))

    # Direct and indirect interaction evidence.
    interaction_pairs = [
        ("person:alice-chen", "person:ben-ortiz", "message", 12, 0.94),
        ("person:ben-ortiz", "person:carla-singh", "comment", 7, 0.88),
        ("person:carla-singh", "person:david-kim", "call", 3, 0.81),
        ("person:farah-al-mansour", "person:boris-volkov", "transaction", 5, 0.89),
        ("person:elena-petrova", "person:rafael-costa", "payment_review", 9, 0.86),
        ("person:hugo-martinez", "person:uri-cohen", "ticket", 6, 0.79),
        ("person:liam-oconnor", "person:nora-fischer", "document_review", 4, 0.72),
        ("person:maya-hassan", "person:amina-diallo", "field_note", 8, 0.83),
        ("person:jonah-reed", "person:dev-patel", "vendor_email", 11, 0.77),
    ]
    for source, target, interaction_type, count, recency in interaction_pairs:
        relationships.append(edge(source, "INTERACTED_WITH", target, {"interaction_type": interaction_type, "count": count, "timestamps": ["2026-04-20T10:00:00Z", "2026-04-21T11:30:00Z"], "platform": "synthetic-logs", "recency_score": recency}))
    for event_id, attendees in event_attendees.items():
        for attendee in attendees[:3]:
            relationships.append(edge(attendee, "INTERACTED_WITH", event_id, {"interaction_type": "event_engagement", "count": 1 + len(attendee) % 4, "timestamps": [event_lookup[event_id]["timestamp"]], "platform": event_lookup[event_id]["platform"], "recency_score": 0.68}))

    predicted_links = [
        ("person:alice-chen", "person:david-kim", 0.84, "third_degree_plus_shared_education"),
        ("person:farah-al-mansour", "person:david-kim", 0.78, "broker_path_and_common_call"),
        ("person:elena-petrova", "person:boris-volkov", 0.73, "finance_logistics_bridge"),
        ("person:hugo-martinez", "person:wei-zhang", 0.71, "shared_signal_review"),
        ("person:maya-hassan", "person:carla-singh", 0.76, "shared_ngo_and_field_events"),
    ]
    for source, target, score, reason in predicted_links:
        relationships.append(edge(source, "PREDICTED_LINK", target, {"score": score, "algorithm": "synthetic_seed_ground_truth", "confidence_interval": [round(score - 0.07, 2), round(score + 0.05, 2)], "model_version": "seed-v1", "reason": reason}))

    # De-duplicate exact relationship triples while preserving the latest properties.
    deduped: dict[tuple[str, str, str], tuple[str, str, str, dict]] = {}
    for source, rel_type, target, props in relationships:
        deduped[(source, rel_type, target)] = (source, rel_type, target, props)
    return list(deduped.values())


PEOPLE = build_people()
RELATIONSHIPS = build_relationships()


def seed_summary() -> dict[str, int]:
    edge_counts = Counter(rel_type for _, rel_type, _, _ in RELATIONSHIPS)
    return {
        "people": len(PEOPLE),
        "organizations": len(ORGANIZATIONS),
        "education_institutions": len(EDUCATION_INSTITUTIONS),
        "locations": len(LOCATIONS),
        "events": len(EVENTS),
        "communities": len(COMMUNITIES),
        "relationships": len(RELATIONSHIPS),
        **{f"edge_{edge_type.lower()}": count for edge_type, count in sorted(edge_counts.items())},
    }


def seed(reset: bool = False) -> dict[str, int]:
    settings = get_settings()
    bootstrap_schema(settings)
    client = Neo4jClient(settings)
    try:
        with client.session() as session:
            if reset:
                session.run("MATCH (n) DETACH DELETE n").consume()
            for row in PEOPLE:
                session.run("MERGE (n:Person {canonical_id: $canonical_id}) SET n += $props", canonical_id=row["canonical_id"], props=row).consume()
            for row in ORGANIZATIONS:
                session.run("MERGE (n:Organization {canonical_id: $canonical_id}) SET n += $props", canonical_id=row["canonical_id"], props=row).consume()
            for row in EDUCATION_INSTITUTIONS:
                session.run("MERGE (n:EducationInstitution {institution_id: $institution_id}) SET n += $props", institution_id=row["institution_id"], props=row).consume()
            for row in LOCATIONS:
                session.run("MERGE (n:Location {location_id: $location_id}) SET n += $props", location_id=row["location_id"], props=row).consume()
            for row in EVENTS:
                session.run("MERGE (n:Event {event_id: $event_id}) SET n += $props", event_id=row["event_id"], props=row).consume()
            for row in COMMUNITIES:
                session.run("MERGE (n:Community {community_id: $community_id}) SET n += $props", community_id=row["community_id"], props=row).consume()
            for source, rel_type, target, props in RELATIONSHIPS:
                session.run(
                    f"""
                    MATCH (source), (target)
                    WHERE {node_identity_cypher("source")} = $source
                      AND {node_identity_cypher("target")} = $target
                    MERGE (source)-[r:{rel_type}]->(target)
                    SET r += $props
                    """,
                    source=source,
                    target=target,
                    props=props,
                ).consume()
    finally:
        client.close()
    return seed_summary()


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed deterministic RDNAE synthetic data.")
    parser.add_argument("--reset", action="store_true", help="Delete all graph data before seeding.")
    parser.add_argument("--summary", action="store_true", help="Print seed summary without writing to Neo4j.")
    args = parser.parse_args()
    summary = seed_summary() if args.summary else seed(reset=args.reset)
    print("RDNAE synthetic seed data summary:")
    for key, value in summary.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()
