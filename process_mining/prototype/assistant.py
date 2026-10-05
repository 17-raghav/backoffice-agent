"""Case-queue assistant: one small engine, per-process behaviour in definitions.json.

For a case row it returns a draft: decision (approve / hold / human), the note text in the exact wording the
team already uses, the audit-memo line, the reason, and reference checks.  It never submits anything:
a person confirms (or edits) and clicks the portal's own OK button.
"""
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))


def _num(s):
    return int(re.sub(r"[^\d]", "", s)) if s and re.search(r"\d", s) else None


class Assistant:
    def __init__(self, path=os.path.join(HERE, "definitions.json")):
        with open(path, encoding="utf-8") as fh:
            self.defs = {k: v for k, v in json.load(fh).items() if not k.startswith("_")}
        self.rx = {k: re.compile(v["row_regex"]) for k, v in self.defs.items()}

    def supports(self, ptype):
        return ptype in self.defs

    def parse_row(self, ptype, row_text):
        m = self.rx[ptype].match(re.sub(r"\s+", " ", row_text or "").strip())
        return m.groupdict() if m else None

    def decide(self, ptype, fields):
        for rule in self.defs[ptype]["decision"]:
            cond = rule["if"]
            if cond.get("always") or fields.get(cond.get("field")) == cond.get("equals"):
                return rule["outcome"], rule["text"], rule["reason"]
        return "human", "", "no rule matched"

    def reference_check(self, ptype, fields):
        ref = self.defs[ptype].get("reference_check")
        if not ref:
            return None
        vendor, amount = fields.get("vendor"), _num(fields.get("amount"))
        fixed = ref["fixed_monthly"].get(vendor)
        if fixed is None:
            return {"doc": ref["doc"], "on_list": False,
                    "finding": "vendor not on the fixed-amount list — the written procedure cannot confirm this invoice"}
        dev = (amount - fixed) / fixed if amount else None
        ok = dev is not None and abs(dev) <= ref["tolerance"]
        return {"doc": ref["doc"], "on_list": True, "fixed_monthly": fixed, "deviation": round(dev, 4) if dev is not None else None,
                "finding": f"{dev:+.1%} vs fixed monthly amount" + ("" if ok else " (outside tolerance)")}

    def draft(self, ptype, fields, case_no=""):
        d = self.defs[ptype]
        outcome, text, reason = self.decide(ptype, fields)
        values = {**fields, "decision_text": text, "case_no": case_no}
        note = d["note_template"].format(**values) if text else ""
        memo = d.get("memo_template", "{case_no}\t{decision_text}").format(**values)
        checks = self.reference_check(ptype, fields)
        conflict = bool(checks) and outcome == "approve" and not (checks.get("on_list") and abs(checks.get("deviation") or 1) <= self.defs[ptype]["reference_check"]["tolerance"])
        return {"type": ptype, "case_no": case_no, "outcome": outcome, "note": note, "memo": memo, "reason": reason,
                "reference_check": checks, "rule_conflict": conflict, "status": d["status"]}
