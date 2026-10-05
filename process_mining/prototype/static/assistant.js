// In-page assistant. Written against the portal's DOM grammar ({pfx}-table rows, {pfx}-note, btn-{pfx}-ok),
// so the same script can be packaged as a browser extension for the real portal.
(function () {
  const $ = (s) => document.querySelector(s);
  const tbody = $("#pi-table tbody"), note = $("#pi-note"), ok = $("#btn-pi-ok"), panel = $("#panel");
  let queue = [], current = null, draft = null, chosen = null;
  const TEXT = { approve: "差異なし承認", hold: "差異あり要確認" };
  const LABEL = { approve: "承認 approve", hold: "保留・要確認 hold for review", human: "担当者判断 human decision" };

  const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

  async function loadQueue() {
    queue = await (await fetch("/api/queue")).json();
    tbody.innerHTML = queue.map((r, i) =>
      `<tr data-i="${i}"><td>${esc(r.case_no)}</td><td>${esc(r.vendor_id)}</td><td>${esc(r.vendor)}</td>` +
      `<td>請求書承認 ${esc(r.invoice_no)}</td><td>${esc(r.amount)}</td><td>${esc(r.kind)}</td>` +
      `<td class="st-${esc(r.status)}">${esc(r.status)}</td></tr>`).join("");
    const open = queue.filter((r) => r.status === "未処理").length;
    $("#count").textContent = `${queue.length} 件 · ${open} 件未処理`;
  }

  function noteFor(outcome) {
    return `請求書照合完了。${current.invoice_no} 金額：${current.amount}。${TEXT[outcome]}。`;
  }

  function render() {
    const d = draft, rc = d.reference_check || {};
    panel.className = "";
    panel.innerHTML =
      `<div class="kv"><b>案件</b>${esc(d.case_no)} — ${esc(current.vendor)}</div>` +
      `<div class="kv"><b>提案</b><span class="badge ${d.outcome}">${LABEL[d.outcome]}</span></div>` +
      `<div class="kv"><b>根拠</b>${esc(d.reason)}</div>` +
      `<div class="kv"><b>照合表</b>${esc(rc.doc || "")}<br>${esc(rc.finding || "")}</div>` +
      (d.rule_conflict ? `<div class="warn"><b>Rule conflict.</b> The practised rule says approve, but the written procedure ` +
        `cannot confirm this vendor/amount. Check before approving; the business owner must decide which rule is authoritative.</div>` : "") +
      `<div class="override">最終判断 (final): ` +
      `<label><input type="radio" name="o" value="approve" ${chosen === "approve" ? "checked" : ""}> 承認</label>` +
      `<label><input type="radio" name="o" value="hold" ${chosen === "hold" ? "checked" : ""}> 保留・要確認</label></div>` +
      `<div class="muted" style="margin-top:8px">Manual steps removed per case: re-typing the note, opening the Word reference list, ` +
      `appending the memo line. Remaining: read, decide, click OK.</div>`;
    panel.querySelectorAll('input[name="o"]').forEach((el) => el.addEventListener("change", (e) => {
      chosen = e.target.value; note.value = noteFor(chosen); render();
    }));
  }

  async function select(i) {
    current = queue[i];
    tbody.querySelectorAll("tr").forEach((tr) => tr.classList.toggle("sel", tr.dataset.i === String(i)));
    $("#detail-title").textContent = `${current.case_no}  ${current.vendor}  ${current.invoice_no}  ${current.amount}  (${current.kind})`;
    draft = await (await fetch(`/api/draft?case=${encodeURIComponent(current.case_no)}`)).json();
    chosen = draft.outcome === "human" ? null : draft.outcome;
    note.value = draft.note || "";
    ok.disabled = current.status !== "未処理";
    render();
  }

  async function submit() {
    if (!current || !chosen) { alert("最終判断を選択してください (choose approve or hold)"); return; }
    ok.disabled = true;
    await fetch("/api/commit", { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ case_no: current.case_no, outcome: chosen, note: note.value, user: "demo-user" }) });
    await loadQueue(); await loadAudit();
    const next = queue.findIndex((r) => r.status === "未処理");
    if (next >= 0) select(next); else { panel.textContent = "Queue done."; note.value = ""; }
  }

  async function loadAudit() {
    const rows = await (await fetch("/api/audit")).json();
    $("#audit").innerHTML = "<b>監査ログ (audit log)</b>" + (rows.length ? rows.slice().reverse().map((r) =>
      `<div>${esc(r.ts_utc.slice(11, 19))} ${esc(r.case_no)} → <b>${esc(r.final_outcome)}</b>` +
      `${r.overridden === "True" ? " <span style='color:#b91c1c'>(overrode draft)</span>" : ""}` +
      `${r.rule_conflict === "True" ? " ⚠" : ""}</div>`).join("") : "<div class='muted'>empty</div>");
  }

  tbody.addEventListener("click", (e) => { const tr = e.target.closest("tr"); if (tr) select(Number(tr.dataset.i)); });
  ok.addEventListener("click", submit);
  loadQueue().then(() => { loadAudit(); const i = queue.findIndex((r) => r.status === "未処理"); if (i >= 0) select(i); });
})();
