"""Seed fact-checks for Jubilee 2017 and Kenya Kwanza 2022 manifestos.

Safe to re-run — skips rows that already exist (matched by
promise_keyword + party + year).
"""
from src.db import execute_many, fetch_one


SQL = """
INSERT INTO promise_evidence
  (promise_keyword, party, year, original_promise, action_taken, status,
   source_url, source_title, verified_by, verified_date, confidence)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
"""


# =====================================================================
# Jubilee Party — 2017 Manifesto
# =====================================================================
JUBILEE_ROWS = [
    # 1. HEALTH
    (
        "health",
        "Jubilee Party",
        2017,
        "Provide free, quality primary healthcare for all Kenyans. "
        "Expand free maternity care to include government-funded NHIF cover "
        "for every expectant mother for one year.",
        "The Linda Mama free maternity programme was implemented and later "
        "folded into the Universal Health Coverage (UHC) pilot in Kisumu, "
        "Nyeri, Machakos and Isiolo. Jubilee publicly claimed it was effective, "
        "but the programme's continuity became complex after the 2022 transition "
        "when NHIF was replaced by the Social Health Authority (SHA). Coverage "
        "of the full 'primary healthcare for all' pledge remained incomplete by "
        "the end of the term.",
        "PARTIALLY FULFILLED",
        "https://mzalendo.com/promise2implementation/",
        "Mzalendo Trust — Promise to Implementation Report (Jubilee 2017 Scorecard)",
        "Mzalendo Trust",
        "2020-12-15",
        "HIGH",
    ),
    # 2. INFRASTRUCTURE
    (
        "infrastructure",
        "Jubilee Party",
        2017,
        "Connect every Kenyan to reliable and affordable electricity (on or "
        "off-grid) by 2020, and double the number of tarmacked roads.",
        "Electricity access rose from roughly 35% in 2013 to over 70–75% of the "
        "population by 2022 — the strongest performance of the Jubilee manifesto. "
        "On roads, the government claimed to have doubled the tarmacked network, "
        "but independent auditors and the Auditor-General flagged cost overruns, "
        "incomplete sections and disputed mileage on flagship projects such as "
        "the Nairobi Expressway and various bypass roads.",
        "PARTIALLY FULFILLED",
        "https://www.africacheck.org/fact-checks/reports",
        "Africa Check / Auditor-General reports on Jubilee infrastructure pledges",
        "Africa Check",
        "2022-08-01",
        "MEDIUM",
    ),
    # 3. EDUCATION
    (
        "education",
        "Jubilee Party",
        2017,
        "Expand the free primary school programme to include free day public "
        "secondary schools, and provide laptops to all Class One pupils.",
        "Free day secondary education was implemented starting January 2018, "
        "delivering on the headline pledge. However, the flagship 'one laptop "
        "per child' project — carried over from the 2013 manifesto — was widely "
        "described as slow in implementation, with rollout described as 'low key' "
        "and coverage far below plan.",
        "PARTIALLY FULFILLED",
        "https://mzalendo.com/promise2implementation/",
        "Mzalendo Trust — Promise to Implementation Report (Jubilee 2017 Scorecard)",
        "Mzalendo Trust",
        "2020-12-15",
        "HIGH",
    ),
    # 4. JOBS
    (
        "jobs",
        "Jubilee Party",
        2017,
        "Create 1.3 million jobs every year for Kenyan youth.",
        "This promise was largely unfulfilled. The Mzalendo Trust scorecard found "
        "that the Jubilee administration failed to implement most of its 2017 "
        "manifesto pledges despite holding a parliamentary majority, and "
        "independent estimates of new formal jobs fell far short of the 1.3 "
        "million-per-year target. Youth unemployment remained a top voter concern "
        "going into 2022.",
        "BROKEN",
        "https://mzalendo.com/promise2implementation/",
        "Mzalendo Trust — Promise to Implementation Report (Jubilee 2017 Scorecard)",
        "Mzalendo Trust",
        "2020-12-15",
        "HIGH",
    ),
    # 5. WATER
    (
        "water",
        "Jubilee Party",
        2017,
        "Ensure every Kenyan has access to clean, safe running water by 2020.",
        "Access to clean water remained an 'elusive dream' for many Kenyans, "
        "particularly in coastal regions such as Mombasa, well past the 2020 "
        "deadline and into 2025. Multiple news reports and civil-society "
        "assessments described the 2017 water pledge as unfulfilled, with chronic "
        "rationing and aging infrastructure still dominant in many counties.",
        "BROKEN",
        "https://www.the-star.co.ke/",
        "The Star Kenya — Mombasa water access reporting, 2024–2025",
        "Author (news archive)",
        "2025-01-10",
        "MEDIUM",
    ),
]


# =====================================================================
# Kenya Kwanza — 2022 Manifesto (BETA)
# =====================================================================
KENYA_KWANZA_ROWS = [
    # 1. HEALTH (UHC → SHA/SHIF)
    (
        "health",
        "Kenya Kwanza",
        2022,
        "Achieve Universal Health Coverage (UHC) by 2030 by establishing the "
        "Social Health Authority (SHA) — replacing NHIF — with a Primary "
        "Healthcare Fund, Emergency Chronic and Critical Illness Fund, and "
        "Social Health Insurance Fund (SHIF).",
        "The Social Health Authority and SHIF were launched on 1 October 2024, "
        "after extended court challenges; NHIF was formally dissolved. Rollout "
        "has been marred by registration problems, hospital payment delays and "
        "public confusion about the new contribution formula. Full UHC by 2030 "
        "remains far off, and the transition is still in progress.",
        "PARTIALLY FULFILLED",
        "https://www.africacheck.org/fact-checks/reports",
        "Africa Check — SHA/SHIF rollout fact-checks (2024–2025)",
        "Africa Check",
        "2025-01-20",
        "HIGH",
    ),
    # 2. HOUSING (AHP + Housing Fund)
    (
        "housing",
        "Kenya Kwanza",
        2022,
        "Deliver 200,000 affordable housing units every year under the "
        "Affordable Housing Programme (AHP), financed by a 3% employee and 3% "
        "employer Housing Fund levy.",
        "Multiple AHP sites are under construction — Mukuru, Bondeni, Pangani, "
        "Shauri Moyo, and others. The Housing Fund levy was introduced in 2024 "
        "(later revised after youth-led protests). Some completed units have "
        "been allocated, but output is far below the 200,000-units-per-year "
        "target. Programme continues under the State Department for Housing.",
        "IN PROGRESS",
        "https://mzalendo.com/promise2implementation/",
        "Mzalendo Trust — Kenya Kwanza Promise Tracker",
        "Mzalendo Trust",
        "2024-11-15",
        "MEDIUM",
    ),
    # 3. AGRICULTURE (Fertilizer subsidy)
    (
        "agriculture",
        "Kenya Kwanza",
        2022,
        "Reduce the cost of fertilizer from Ksh 6,500 to Ksh 2,500 per 50kg bag, "
        "and raise annual maize production to 60 million bags under the BETA "
        "agriculture pillar.",
        "A subsidized fertilizer programme was rolled out at the promised "
        "Ksh 2,500 per 50kg bag in 2022–2024, though distribution gaps were "
        "reported in some counties and farmers' access varied by region. The "
        "60-million-bag maize production target has not been consistently met. "
        "Kiswahili term: 'mbolea' (fertilizer).",
        "PARTIALLY FULFILLED",
        "https://www.the-star.co.ke/",
        "The Star Kenya — Fertilizer subsidy distribution reporting (2023–2024)",
        "Author (news archive)",
        "2024-09-01",
        "MEDIUM",
    ),
    # 4. JOBS & HUSTLER FUND
    (
        "jobs",
        "Kenya Kwanza",
        2022,
        "Create at least 1 million jobs per year for Kenyan youth through the "
        "Bottom-up Economic Transformation Agenda (BETA), and launch a Financial "
        "Inclusion (Hustler) Fund to provide affordable credit.",
        "The Hustler Fund was launched on 30 November 2022 and has disbursed "
        "billions of shillings in small loans (average Ksh 500–1,000 per "
        "borrower). The 1-million-jobs-per-year target remains disputed — "
        "independent economists and Mzalendo Trust note that formal job creation "
        "fell well short of the pledge, and youth unemployment remains a "
        "top-of-mind concern.",
        "PARTIALLY FULFILLED",
        "https://mzalendo.com/promise2implementation/",
        "Mzalendo Trust — Kenya Kwanza Promise Tracker",
        "Mzalendo Trust",
        "2024-11-15",
        "MEDIUM",
    ),
    # 5. MANUFACTURING
    (
        "manufacturing",
        "Kenya Kwanza",
        2022,
        "Raise manufacturing's contribution to GDP to 30% and promote 'Made in "
        "Kenya' products through County Aggregation and Industrial Parks.",
        "Manufacturing's share of GDP remained around 7–8% as of 2024–2025 — "
        "unchanged from the pre-2022 baseline. County Aggregation and Industrial "
        "Parks are still in planning or early-construction phases. The 30% GDP "
        "target is not measurable progress yet.",
        "NOT STARTED",
        "https://www.africacheck.org/fact-checks/reports",
        "Africa Check / Business Daily — Manufacturing share of GDP analysis",
        "Africa Check",
        "2025-01-15",
        "MEDIUM",
    ),
]


def _insert_if_new(row):
    keyword, party, year = row[0], row[1], row[2]
    exists = fetch_one(
        "SELECT 1 FROM promise_evidence "
        "WHERE promise_keyword=? AND party=? AND year=?",
        (keyword, party, year),
    )
    if exists:
        print(f"[SKIP] {party} / {keyword} ({year}) — already exists")
        return False
    execute_many(SQL, [row])
    print(f"[OK]   inserted {party} / {keyword} ({year})")
    return True


def main():
    print("=" * 60)
    print("Seeding fact-checks")
    print("=" * 60)

    inserted = 0
    for row in JUBILEE_ROWS:
        if _insert_if_new(row):
            inserted += 1

    print()
    for row in KENYA_KWANZA_ROWS:
        if _insert_if_new(row):
            inserted += 1

    print()
    print(f"Done. {inserted} new row(s) added.")


if __name__ == "__main__":
    main()