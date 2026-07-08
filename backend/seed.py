"""
backend/seed.py
──────────────────────────────────────────────────────────────────────────────
Seed script for the hcp_crm database.

Usage (from /backend directory with venv activated):
    python seed.py

What it does:
  1. Creates all tables via SQLAlchemy (idempotent — uses checkfirst=True).
  2. Inserts 10 realistic pharma HCPs if they don't already exist.
  3. Inserts 6 interactions with real materials/samples/outcomes.
  4. Inserts follow-up suggestions per interaction.
──────────────────────────────────────────────────────────────────────────────
"""

import sys
import os

# Ensure backend/ is on the path when running from that directory
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from datetime import date, time, datetime, timedelta
from sqlalchemy.orm import Session

from app.core.database import engine, SessionLocal, Base
from app.models import HCP, Interaction, FollowUp, SentimentEnum, InteractionTypeEnum, FollowUpStatusEnum


# ─── Create tables ────────────────────────────────────────────────────────────
def create_tables():
    print("[INFO] Creating tables (if not exist)...")
    Base.metadata.create_all(bind=engine, checkfirst=True)
    print("[OK] Tables ready.")


# ─── Seed HCPs ────────────────────────────────────────────────────────────────
HCP_DATA = [
    {
        "name": "Dr. Anil Sharma",
        "specialty": "Oncology",
        "hospital": "Apollo Hospitals, Delhi",
        "contact_info": '{"email": "a.sharma@apollo.in", "phone": "+91-98110-11223"}',
    },
    {
        "name": "Dr. Priya Mehta",
        "specialty": "Cardiology",
        "hospital": "Fortis Heart Institute, Mumbai",
        "contact_info": '{"email": "p.mehta@fortis.in", "phone": "+91-98220-33441"}',
    },
    {
        "name": "Dr. Rajesh Iyer",
        "specialty": "Neurology",
        "hospital": "NIMHANS, Bengaluru",
        "contact_info": '{"email": "r.iyer@nimhans.ac.in", "phone": "+91-80-4699-0000"}',
    },
    {
        "name": "Dr. Sunita Rao",
        "specialty": "Endocrinology",
        "hospital": "Narayana Health, Hyderabad",
        "contact_info": '{"email": "s.rao@narayana.in", "phone": "+91-40-2771-2222"}',
    },
    {
        "name": "Dr. Vikram Patel",
        "specialty": "Pulmonology",
        "hospital": "PD Hinduja Hospital, Mumbai",
        "contact_info": '{"email": "v.patel@hinduja.in", "phone": "+91-22-6766-8484"}',
    },
    {
        "name": "Dr. Kavitha Nair",
        "specialty": "Rheumatology",
        "hospital": "Amrita Institute, Kochi",
        "contact_info": '{"email": "k.nair@amrita.edu", "phone": "+91-484-2801-234"}',
    },
    {
        "name": "Dr. Suresh Bansal",
        "specialty": "Gastroenterology",
        "hospital": "Max Super Speciality, Gurugram",
        "contact_info": '{"email": "s.bansal@maxhealthcare.in", "phone": "+91-98301-55671"}',
    },
    {
        "name": "Dr. Ananya Desai",
        "specialty": "Hematology",
        "hospital": "Tata Memorial Centre, Mumbai",
        "contact_info": '{"email": "a.desai@tmc.gov.in", "phone": "+91-22-2417-7000"}',
    },
    {
        "name": "Dr. Mohan Krishna",
        "specialty": "Nephrology",
        "hospital": "AIIMS, New Delhi",
        "contact_info": '{"email": "m.krishna@aiims.edu", "phone": "+91-11-2658-8500"}',
    },
    {
        "name": "Dr. Lalitha Subramanian",
        "specialty": "Oncology",
        "hospital": "Christian Medical College, Vellore",
        "contact_info": '{"email": "l.subramanian@cmcvellore.ac.in", "phone": "+91-416-228-1000"}',
    },
]


# ─── Seed Interactions ────────────────────────────────────────────────────────
# Built after HCPs are inserted so we can reference their IDs by index
INTERACTION_DATA = [
    # --- Interaction 1: Dr. Anil Sharma (Oncology) ---
    {
        "hcp_index": 0,   # Dr. Anil Sharma
        "interaction_type": InteractionTypeEnum.meeting,
        "date": date(2026, 6, 12),
        "time": time(10, 30),
        "attendees": "Rohan Verma (MSL), Deepa Singh (Area Sales Manager)",
        "topics_discussed": (
            "Discussed OncoBoost Phase III trial results showing 34% improvement in "
            "progression-free survival vs. standard of care. Dr. Sharma expressed interest "
            "in initiating OncoBoost for newly diagnosed NSCLC patients. Reviewed biomarker "
            "eligibility criteria (EGFR+, ALK–). Addressed concerns about Grade 3 "
            "hepatotoxicity — clarified monitoring protocol from the BOOST-301 trial."
        ),
        "materials_shared": [
            {"name": "OncoBoost Phase III BOOST-301 Clinical Summary", "type": "Clinical Brochure"},
            {"name": "EGFR Biomarker Eligibility Flowchart", "type": "Reference Card"},
            {"name": "Patient Support Program Enrollment Form", "type": "Form"},
        ],
        "samples_distributed": [
            {"drug": "OncoBoost 150mg", "quantity": 10, "lot_number": "OB-2026-0412", "expiry": "2027-03"},
            {"drug": "OncoBoost 300mg", "quantity": 5, "lot_number": "OB-2026-0413", "expiry": "2027-03"},
        ],
        "sentiment": SentimentEnum.positive,
        "outcomes": (
            "Dr. Sharma agreed to enroll 3 eligible NSCLC patients in the OncoBoost "
            "compassionate use program. Requested a follow-up MSL-led scientific exchange "
            "session with his resident team. Expressed intent to present OncoBoost data "
            "at the upcoming ICON oncology grand rounds."
        ),
        "follow_up_actions": (
            "Schedule MSL scientific exchange session with Dr. Sharma's resident team by 30 June. "
            "Send BOOST-301 full publication PDF. Register Dr. Sharma for OncoBoost Advisory "
            "Board meeting in August."
        ),
    },
    # --- Interaction 2: Dr. Priya Mehta (Cardiology) ---
    {
        "hcp_index": 1,   # Dr. Priya Mehta
        "interaction_type": InteractionTypeEnum.call,
        "date": date(2026, 6, 18),
        "time": time(14, 0),
        "attendees": "Self (Field Rep)",
        "topics_discussed": (
            "Phone follow-up after last in-clinic visit. Discussed CardioShield 10mg "
            "reimbursement status update — confirmed CGHS listing approved. "
            "Dr. Mehta raised a query on QTc prolongation risk when co-administered with "
            "amiodarone. Shared the DDI (Drug-Drug Interaction) data from the label."
        ),
        "materials_shared": [
            {"name": "CardioShield CGHS Reimbursement Approval Letter", "type": "Regulatory Document"},
            {"name": "CardioShield DDI Reference — Amiodarone Co-administration", "type": "Medical Insert"},
        ],
        "samples_distributed": [],
        "sentiment": SentimentEnum.neutral,
        "outcomes": (
            "Dr. Mehta satisfied with reimbursement news. Will initiate CardioShield for "
            "3 high-risk AF patients pending latest ECG review. "
            "Requested written DDI summary to share with pharmacy."
        ),
        "follow_up_actions": (
            "Email CardioShield DDI PDF to Dr. Mehta's secretary. "
            "Follow up in 2 weeks to check on patient initiations."
        ),
    },
    # --- Interaction 3: Dr. Sunita Rao (Endocrinology) ---
    {
        "hcp_index": 3,   # Dr. Sunita Rao
        "interaction_type": InteractionTypeEnum.meeting,
        "date": date(2026, 6, 25),
        "time": time(9, 0),
        "attendees": "Neeraj Kulkarni (KAM), Dr. Sunita Rao, Resident Dr. Pooja Tiwari",
        "topics_discussed": (
            "Detailed product discussion on GlucoNorm XR for T2DM patients with CKD Stage 3. "
            "Reviewed the RENALGUARD sub-study data demonstrating eGFR stability over 52 weeks. "
            "Discussed dosing adjustments (GlucoNorm XR 500mg BD for eGFR 30–60 mL/min). "
            "Dr. Rao is skeptical about SGLT2 combination — shared head-to-head PK data."
        ),
        "materials_shared": [
            {"name": "GlucoNorm XR RENALGUARD Sub-study Reprint", "type": "Journal Reprint"},
            {"name": "GlucoNorm XR Dosing Guide for CKD", "type": "Clinical Brochure"},
            {"name": "Patient Diary — GlucoNorm XR", "type": "Patient Education Material"},
        ],
        "samples_distributed": [
            {"drug": "GlucoNorm XR 500mg", "quantity": 14, "lot_number": "GN-2026-0601", "expiry": "2027-06"},
        ],
        "sentiment": SentimentEnum.neutral,
        "outcomes": (
            "Dr. Rao agreed to trial GlucoNorm XR in 5 CKD-T2DM patients over 3 months. "
            "Resident Dr. Tiwari requested CME credit information for the RENALGUARD data webinar."
        ),
        "follow_up_actions": (
            "Register Dr. Tiwari for RENALGUARD webinar (July 15). "
            "Send GlucoNorm XR CME certificate template to Dr. Rao's clinic. "
            "Schedule 3-month review call."
        ),
    },
    # --- Interaction 4: Dr. Ananya Desai (Hematology) ---
    {
        "hcp_index": 7,   # Dr. Ananya Desai
        "interaction_type": InteractionTypeEnum.conference,
        "date": date(2026, 7, 2),
        "time": time(11, 0),
        "attendees": (
            "Dr. Ananya Desai, Dr. Rajeev Joshi (CMC Vellore), "
            "Sangeeta Pillai (Medical Affairs), Ravi Agarwal (Field Rep)"
        ),
        "topics_discussed": (
            "Met Dr. Desai at the Indian Society of Hematology annual conference. "
            "Presented HemaFlex (eltrombopag biosimilar) data from the FLEX-301 study "
            "in ITP patients — 72% platelet response at week 6. "
            "Advisory board discussion on real-world dosing challenges. "
            "Explored compassionate use pathway for relapsed/refractory ITP patients "
            "who failed rituximab."
        ),
        "materials_shared": [
            {"name": "HemaFlex FLEX-301 Study Abstract", "type": "Conference Abstract"},
            {"name": "HemaFlex Real-World Evidence Monograph", "type": "Monograph"},
            {"name": "ITP Patient Support Programme Brochure", "type": "Patient Brochure"},
        ],
        "samples_distributed": [],
        "sentiment": SentimentEnum.positive,
        "outcomes": (
            "Dr. Desai expressed strong interest in HemaFlex for 2nd-line ITP. "
            "Agreed to participate in HemaFlex advisory board panel in September. "
            "Requested full FLEX-301 publication and Indian pricing data."
        ),
        "follow_up_actions": (
            "Send FLEX-301 full publication PDF by July 10. "
            "Share Indian market pricing and reimbursement sheet. "
            "Add Dr. Desai to advisory board participant list for September event. "
            "Send advisory board logistics and honorarium details by July 20."
        ),
    },
    # --- Interaction 5: Dr. Rajesh Iyer (Neurology) ---
    {
        "hcp_index": 2,   # Dr. Rajesh Iyer
        "interaction_type": InteractionTypeEnum.email,
        "date": date(2026, 7, 4),
        "time": time(16, 0),
        "attendees": "Self (Field Rep) via email",
        "topics_discussed": (
            "Email follow-up sharing NeuroCalm (levetiracetam extended-release) updated "
            "prescribing information following DCGI label revision for pediatric indication (4–16 yrs). "
            "Attached revised SmPC and updated patient information leaflet."
        ),
        "materials_shared": [
            {"name": "NeuroCalm XR Revised SmPC — Pediatric Indication", "type": "Regulatory Document"},
            {"name": "NeuroCalm XR Patient Information Leaflet (PIL)", "type": "Patient Education Material"},
        ],
        "samples_distributed": [],
        "sentiment": SentimentEnum.neutral,
        "outcomes": (
            "Awaiting acknowledgement from Dr. Iyer. "
            "Expected to update hospital formulary for pediatric epilepsy ward."
        ),
        "follow_up_actions": (
            "Follow up by phone if no reply within 5 business days. "
            "Schedule in-person detail visit for Q3."
        ),
    },
    # --- Interaction 6: Dr. Lalitha Subramanian (Oncology) ---
    {
        "hcp_index": 9,   # Dr. Lalitha Subramanian
        "interaction_type": InteractionTypeEnum.meeting,
        "date": date(2026, 7, 7),
        "time": time(15, 30),
        "attendees": "Self (Field Rep), MSL Dr. Kiran Bose",
        "topics_discussed": (
            "In-depth discussion on OncoPrime (pembrolizumab biosimilar candidate) — "
            "bridging study design under CDSCO biosimilar guidelines. "
            "Discussed PD-L1 testing protocols at CMC pathology lab. "
            "Reviewed immune-related adverse event (irAE) management algorithm. "
            "Dr. Subramanian currently treating 12 advanced TNBC patients — interested "
            "in OncoPrime as a cost-effective IO option vs. originator."
        ),
        "materials_shared": [
            {"name": "OncoPrime Bridging Study Design Overview", "type": "Clinical Brochure"},
            {"name": "irAE Management Algorithm — Grade 1-4 Toxicity", "type": "Reference Card"},
            {"name": "PD-L1 Testing Protocol for TNBC", "type": "Lab Guide"},
            {"name": "OncoPrime vs. Originator Cost Analysis", "type": "Health Economics Dossier"},
        ],
        "samples_distributed": [],
        "sentiment": SentimentEnum.positive,
        "outcomes": (
            "Dr. Subramanian agreed to include OncoPrime in the hospital's biosimilar "
            "evaluation committee submission (next meeting: Aug 5). "
            "MSL Dr. Bose to provide regulatory dossier to CMC formulary committee. "
            "Strong KOL potential identified — will explore scientific publication collaboration."
        ),
        "follow_up_actions": (
            "Deliver OncoPrime regulatory dossier to CMC formulary committee by July 15. "
            "Schedule KOL advisory board nomination call with Medical Affairs. "
            "Send publication collaboration proposal by July 25. "
            "Follow up on formulary committee decision post Aug 5 meeting."
        ),
    },
]


# ─── Follow-up suggestions per interaction ────────────────────────────────────
FOLLOWUP_DATA = {
    0: [  # for interaction index 0 (Dr. Sharma)
        "Schedule MSL-led scientific exchange with Dr. Sharma's resident team by June 30",
        "Send OncoBoost BOOST-301 full publication PDF via secure email",
        "Add Dr. Sharma to OncoBoost Advisory Board August invite list",
    ],
    1: [  # Dr. Priya Mehta
        "Email CardioShield DDI (amiodarone) PDF to Dr. Mehta's pharmacy team",
        "Follow up in 2 weeks on CardioShield patient initiations for AF",
    ],
    2: [  # Dr. Sunita Rao
        "Register Dr. Tiwari for RENALGUARD CME webinar on July 15",
        "Send GlucoNorm XR 3-month patient monitoring form",
        "Schedule 3-month review call for CKD-T2DM patient cohort",
    ],
    3: [  # Dr. Ananya Desai
        "Send HemaFlex FLEX-301 full publication PDF by July 10",
        "Add Dr. Desai to HemaFlex September Advisory Board panel",
        "Share Indian HemaFlex pricing and CGHS reimbursement sheet",
    ],
    4: [  # Dr. Rajesh Iyer
        "Call Dr. Iyer's office to confirm receipt of NeuroCalm XR revised SmPC",
        "Schedule Q3 in-person detail visit for NeuroCalm pediatric indication",
    ],
    5: [  # Dr. Lalitha Subramanian
        "Deliver OncoPrime regulatory dossier to CMC formulary committee by July 15",
        "Schedule KOL advisory board nomination call with Medical Affairs team",
        "Follow up on formulary committee decision after August 5 meeting",
    ],
}


# ─── Main seeding function ─────────────────────────────────────────────────────
def seed(db: Session):
    # ── HCPs ──────────────────────────────────────────────────────────────────
    existing_hcp_count = db.query(HCP).count()
    if existing_hcp_count >= len(HCP_DATA):
        print(f"[SKIP] HCPs already seeded ({existing_hcp_count} records found) - skipping HCP insert.")
        hcps = db.query(HCP).order_by(HCP.id).all()
    else:
        print(f"[INFO] Seeding {len(HCP_DATA)} HCPs...")
        hcps = []
        for data in HCP_DATA:
            hcp = HCP(**data)
            db.add(hcp)
            hcps.append(hcp)
        db.commit()
        # Refresh to get DB-assigned IDs
        for hcp in hcps:
            db.refresh(hcp)
        print(f"[OK] {len(hcps)} HCPs inserted.")

    # ── Interactions ──────────────────────────────────────────────────────────
    existing_interaction_count = db.query(Interaction).count()
    if existing_interaction_count >= len(INTERACTION_DATA):
        print(f"[SKIP] Interactions already seeded ({existing_interaction_count} records found) - skipping.")
        interactions = db.query(Interaction).order_by(Interaction.id).all()
    else:
        print(f"[INFO] Seeding {len(INTERACTION_DATA)} interactions...")
        interactions = []
        for idx, data in enumerate(INTERACTION_DATA):
            hcp = hcps[data["hcp_index"]]
            interaction = Interaction(
                hcp_id=hcp.id,
                interaction_type=data["interaction_type"],
                date=data["date"],
                time=data["time"],
                attendees=data["attendees"],
                topics_discussed=data["topics_discussed"],
                materials_shared=data["materials_shared"],
                samples_distributed=data["samples_distributed"],
                sentiment=data["sentiment"],
                outcomes=data["outcomes"],
                follow_up_actions=data["follow_up_actions"],
            )
            db.add(interaction)
            interactions.append(interaction)
        db.commit()
        for interaction in interactions:
            db.refresh(interaction)
        print(f"[OK] {len(interactions)} interactions inserted.")

    # ── Follow-ups ────────────────────────────────────────────────────────────
    existing_followup_count = db.query(FollowUp).count()
    if existing_followup_count > 0:
        print(f"[SKIP] Follow-ups already seeded ({existing_followup_count} records found) - skipping.")
    else:
        print("[INFO] Seeding follow-up suggestions...")
        followup_count = 0
        for interaction_idx, suggestions in FOLLOWUP_DATA.items():
            if interaction_idx < len(interactions):
                interaction = interactions[interaction_idx]
                for suggestion_text in suggestions:
                    followup = FollowUp(
                        interaction_id=interaction.id,
                        suggested_action=suggestion_text,
                        status=FollowUpStatusEnum.pending,
                    )
                    db.add(followup)
                    followup_count += 1
        db.commit()
        print(f"[OK] {followup_count} follow-up suggestions inserted.")


def main():
    print("\n" + "=" * 60)
    print("  AI-CRM HCP Module - Database Seed Script")
    print("=" * 60 + "\n")

    create_tables()

    db = SessionLocal()
    try:
        seed(db)
        print("\n[OK] Seeding complete. Database is ready.\n")
    except Exception as e:
        db.rollback()
        print(f"\n[ERROR] Seeding failed: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
