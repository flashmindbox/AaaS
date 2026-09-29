"""Simulate 'Translate page' on a real site: many uncached fragments, 16 in flight."""
import json
import sys
import time
import urllib.request
import uuid
from concurrent.futures import ThreadPoolExecutor

BASE = sys.argv[1] if len(sys.argv) > 1 else "https://168-144-216-83.sslip.io"
KEY = "aaas_live_33333333333333333333333333333333"
TAG = uuid.uuid4().hex[:6]  # makes every string new, so nothing is cached

FRAGMENTS = [
    "Home", "About Us", "Contact Us", "Screen Reader Access", "Skip to main content",
    "Right to Information", "Tenders", "Recruitment", "Notices", "Photo Gallery",
    "Citizen Services", "Downloads", "Important Links", "Feedback", "Sitemap",
    "Last updated on", "Terms and Conditions", "Privacy Policy", "Help", "Disclaimer",
    "Admission notice for the academic session",
    "Online application for the post of Junior Assistant is now open.",
    "Candidates must upload a scanned copy of their caste certificate.",
    "The last date for payment of examination fees has been extended.",
    "Results of the annual examination will be published on the website.",
    "Hall tickets can be downloaded from the candidate login page.",
    "The Collector reviewed the progress of welfare schemes in the district.",
    "Farmers can register for crop insurance at the nearest common service centre.",
    "Applications are invited from eligible students for the post-matric scholarship.",
    "The hospital outpatient department will remain closed on public holidays.",
    "Patients are requested to carry their health card during every visit.",
    "The university will conduct a workshop on research methodology next week.",
    "Grievances can be submitted online through the public grievance portal.",
    "A special camp will be organised for issuing disability certificates.",
    "The helpline number is available from ten in the morning to six in the evening.",
    "All government offices will follow the revised working hours from Monday.",
    "Beneficiaries must link their bank account with their Aadhaar number.",
    "The district administration has issued an advisory for the heatwave.",
    "Students who have failed in one subject may apply for the supplementary examination.",
    "Mid-day meal will be served in all primary schools during the summer camp.",
    "The notice regarding transfer of teachers has been withdrawn.",
    "Copies of the gazette notification are available at the district office.",
    "Tender documents can be downloaded free of cost from this website.",
    "The pension will be credited directly to the beneficiary's bank account.",
    "Voters can check their name in the electoral roll online.",
    "The road will remain closed for repair work till further orders.",
    "Senior citizens are exempted from standing in the queue.",
    "The committee will submit its report within thirty days.",
]
POSTER = ("4 INTERNATIONAL CONFERENCE ON MICROWAVE, OPTICAL AND COMMUNICATION ENGINEERING "
          "TECHNICAL CO-SPONSORS IEEE BHUBANESWAR SECTION [UNDER PROCESS] MAY 2027 "
          "ORGANIZED BY SCHOOL OF ELECTRICAL AND COMPUTER SCIENCES IIT BHUBANESWAR, "
          "ODISHA, INDIA CONTACT US")


def translate(text: str, timeout: float = 60) -> tuple[float, str]:
    body = json.dumps({"text": text, "src_lang": "en", "tgt_lang": "or"}).encode()
    req = urllib.request.Request(
        f"{BASE}/translate/translate", data=body,
        headers={"X-API-Key": KEY, "Content-Type": "application/json"},
    )
    t = time.perf_counter()
    with urllib.request.urlopen(req, timeout=timeout) as r:
        out = json.loads(r.read())["text"]
    return time.perf_counter() - t, out


texts = [f"{f} ({TAG}{i})" if len(f) < 25 else f"{f} Ref {TAG}{i}." for i, f in enumerate(FRAGMENTS)]
start = time.perf_counter()
with ThreadPoolExecutor(max_workers=16) as pool:
    results = list(pool.map(translate, texts))
total = time.perf_counter() - start
lat = sorted(r[0] for r in results)
print(f"{len(texts)} uncached fragments, 16 in flight: total {total:.1f}s, "
      f"median {lat[len(lat)//2]:.1f}s, slowest {lat[-1]:.1f}s")
print("  sample:", texts[21], "->", results[21][1])

t, out = translate(POSTER + f" {TAG}")
print(f"poster ALL-CAPS text: {t:.1f}s ->", out[:200])
