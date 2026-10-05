"""Demo: the invoice-matching screen (P6) with the assistant panel, served locally.

The real portal is an internal test system we cannot reach, so this page reproduces its list screen with the
same DOM grammar seen in the logs (#pi-table rows, #pi-note, #btn-pi-ok) and the REAL invoice rows captured in
dataset B.  The assistant drafts; a person submits.  Every submission is appended to data/audit_log.csv with the
draft, the final decision and whether the person overrode the draft.

    python server.py            ->  http://127.0.0.1:8765/
"""
import csv
import json
import os
import sys
import threading
import webbrowser
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from assistant import Assistant

HERE = os.path.dirname(os.path.abspath(__file__))
PORT = int(os.environ.get("PORT", "8765"))
AUDIT = os.path.join(HERE, "data", "audit_log.csv")
A = Assistant()
LOCK = threading.Lock()


def load_queue():
    seen, q = set(), []
    for line in open(os.path.join(HERE, "data", "b_cases.jsonl"), encoding="utf-8"):
        c = json.loads(line)
        if c["type"] != "P6" or not c["case_no"] or c["case_no"] in seen:
            continue
        f = A.parse_row("P6", c["row_text"])
        if not f:
            continue
        seen.add(c["case_no"])
        q.append({"case_no": c["case_no"], **f, "status": "未処理", "human_note_in_log": c["human_note"]})
    q.sort(key=lambda r: r["case_no"])
    return q[:24]


QUEUE = load_queue()


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, code, body, ctype="application/json; charset=utf-8"):
        data = body if isinstance(body, bytes) else json.dumps(body, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        u = urlparse(self.path)
        if u.path == "/api/queue":
            return self._send(200, QUEUE)
        if u.path == "/api/draft":
            cno = parse_qs(u.query).get("case", [""])[0]
            row = next((r for r in QUEUE if r["case_no"] == cno), None)
            return self._send(404, {"error": "unknown case"}) if not row else self._send(200, A.draft("P6", row, cno))
        if u.path == "/api/audit":
            rows = list(csv.DictReader(open(AUDIT, encoding="utf-8"))) if os.path.exists(AUDIT) else []
            return self._send(200, rows[-50:])
        name = "portal.html" if u.path in ("/", "/index.html") else u.path.lstrip("/")
        path = os.path.join(HERE, "static", os.path.basename(name))
        if not os.path.isfile(path):
            return self._send(404, {"error": "not found"})
        ctype = "text/html; charset=utf-8" if path.endswith(".html") else "application/javascript; charset=utf-8" \
            if path.endswith(".js") else "text/css; charset=utf-8"
        return self._send(200, open(path, "rb").read(), ctype)

    def do_POST(self):
        if urlparse(self.path).path != "/api/commit":
            return self._send(404, {"error": "unknown"})
        body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
        row = next((r for r in QUEUE if r["case_no"] == body.get("case_no")), None)
        if not row:
            return self._send(404, {"error": "unknown case"})
        draft = A.draft("P6", row, row["case_no"])
        rec = {"ts_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"), "user": body.get("user") or "demo-user",
               "case_no": row["case_no"], "vendor": row["vendor"], "invoice_no": row["invoice_no"], "amount": row["amount"],
               "draft_outcome": draft["outcome"], "final_outcome": body.get("outcome"),
               "overridden": str(body.get("outcome") != draft["outcome"]), "note_edited": str(body.get("note") != draft["note"]),
               "rule_conflict": str(draft["rule_conflict"]), "note": body.get("note", "")}
        with LOCK:
            new = not os.path.exists(AUDIT)
            with open(AUDIT, "a", newline="", encoding="utf-8") as fh:
                w = csv.DictWriter(fh, fieldnames=list(rec.keys()))
                if new:
                    w.writeheader()
                w.writerow(rec)
            row["status"] = "登録済み" if body.get("outcome") == "approve" else "要確認"
        return self._send(200, {"ok": True, "status": row["status"]})


def main():
    srv = ThreadingHTTPServer(("127.0.0.1", PORT), H)
    print(f"demo portal: http://127.0.0.1:{PORT}/  ({len(QUEUE)} real invoice cases from dataset B)")
    if "--no-browser" not in sys.argv:
        threading.Timer(0.8, lambda: webbrowser.open(f"http://127.0.0.1:{PORT}/")).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
