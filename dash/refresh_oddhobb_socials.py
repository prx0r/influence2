"""Refresh oddhobb passport from the objective social onboarding registry.

Preserves done flags (otp-test). Claim priorities/order come from
data/social_onboarding.v1.json. Safe to re-run.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from core.cmail import models as M
from core.cmail.engine import reconcile_project, project_summary
from core.cmail.influencer import influencer_passport
from dash.store import DB_PATH

DONE = {
    "otp-test": True,  # proven inbound SMS 2026-10-06
    "name": True,
}


def refresh(db_path: str = DB_PATH) -> dict:
    eng = create_engine(f"sqlite:///{db_path}")
    M.Base.metadata.create_all(bind=eng)
    s = sessionmaker(bind=eng)()
    try:
        p = s.scalar(select(M.Project).where(M.Project.slug == "oddhobb"))
        if p is None:
            raise SystemExit("oddhobb project not in dash DB")
        passport = influencer_passport(
            "oddhobbstudio",
            "oddhobb.com",
            DONE,
            display_name="OddHobb",
            email="hello@oddhobb.com",
            phone="+447822000802",
            website="https://oddhobb.com",
        )
        # Brand-specific pre-step: OTP proof (not in generic registry).
        if not any(r["key"] == "otp-test" for r in passport["resources"]):
            passport["resources"].insert(0, {
                "key": "otp-test",
                "kind": "static",
                "label": "OTP test",
                "desired": {
                    "label": "OTP test",
                    "done": True,
                    "executor": "HUMAN",
                    "human_title": "Prove inbound SMS reaches the brand phone",
                    "instructions": (
                        "Text the brand number from your personal mobile with the word TEST. "
                        "Open https://phone.agentcom.org/app SMS tab and confirm it landed. "
                        "Social OTPs depend on this. If nothing arrives: Telnyx portal → "
                        "number → Messaging profile must be attached."
                    ),
                    "url": "https://phone.agentcom.org/app",
                    "priority": 85,
                },
            })
        # Pinterest is covered by the existing Shopify sales channel — no separate claim.
        # Mark claim-pin done so the queue doesn't ask for a signup we already have.
        pin = next((r for r in passport["resources"] if r.get("key") == "claim-pin"), None)
        if pin is not None:
            pin["desired"]["done"] = True
            pin["desired"]["instructions"] = (
                "SKIPPED — Pinterest runs through the Shopify sales channel "
                "(OddHobb store byg8sv-p6.myshopify.com). No separate @oddhobbstudio "
                "Pinterest signup. Later: claim oddhobb.com domain on the existing "
                "Pinterest business account if verification is needed."
            )
            pin["desired"]["priority"] = 5
            kit = dict(pin["desired"].get("kit") or {})
            kit["skipped_reason"] = "shopify_sales_channel"
            kit["note"] = "Linked via Shopify — do not create a second Pinterest account"
            pin["desired"]["kit"] = kit
        # Preserve prior done on any claim-* / verify-report if already True
        old = p.passport or {}
        old_done = {}
        for r in old.get("resources", []):
            d = (r.get("desired") or {})
            if d.get("done"):
                old_done[r.get("key")] = True
        # Merge: old done wins over defaults except we keep otp-test True
        for r in passport["resources"]:
            k = r["key"]
            if old_done.get(k) or DONE.get(k):
                r["desired"]["done"] = True
        p.passport = passport
        s.commit()
        rep = reconcile_project(s, p)
        summ = project_summary(p)
        statuses = {r["key"]: r["status"] for r in summ["resources"]}
        tasks = [{"key": a["resource_key"], "title": a["title"], "done": a["done"],
                  "priority": a["priority"]} for a in summ["actions"]]
        print("OK oddhobb passport refreshed from social_onboarding.v1.json")
        print("counts:", rep["counts"], "progress:", rep.get("progress"))
        print("resources:")
        for r in passport["resources"]:
            print(f"  {r['key']:16} {r['kind']:8} done={r['desired'].get('done')} "
                  f"status={statuses.get(r['key'], '?')}")
        print("open tasks:")
        for t in sorted(tasks, key=lambda x: -x["priority"]):
            if not t["done"]:
                print(f"  p={t['priority']:3} {t['key']:16} {t['title'][:70]}")
        return {"statuses": statuses, "tasks": tasks, "counts": rep["counts"]}
    finally:
        s.close()


if __name__ == "__main__":
    refresh()
