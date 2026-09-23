"""Validate ERP-shaped CSV exports and produce a dated, reproducible report.

No SAP connector, credentials, third-party packages, or email transmission.
Exit 2 means quality failures; latest.json is only advanced on a clean run.
"""
import argparse, csv, hashlib, html, json, tempfile, os
from pathlib import Path
from datetime import date, datetime, timezone

ROOT=Path(__file__).resolve().parents[1]
def read(path):
    with Path(path).open(encoding='utf-8-sig',newline='') as f: return list(csv.DictReader(f))
def csvout(path, rows, fields):
    with path.open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(rows)
def validate(orders,items,suppliers,bom):
    issues=[]; good=[]; seen=set(); itemmap={r['ItemID']:r for r in items}; supplierids={r['SupplierID'] for r in suppliers}
    def issue(entity,key,rule): issues.append(dict(entity=entity,key=key,rule=rule))
    for entity,records,keyfield in [('items',items,'ItemID'),('suppliers',suppliers,'SupplierID')]:
        masterseen=set()
        for r in records:
            key=r.get(keyfield,'')
            if not key or key in masterseen: issue(entity,key,'missing_or_duplicate_master_key')
            masterseen.add(key)
    for r in items:
        if r.get('SupplierID') not in supplierids: issue('items',r['ItemID'],'unknown_supplier')
        if not r.get('Unit'): issue('items',r['ItemID'],'missing_unit')
    for row in orders:
        key=row.get('OrderLine',''); rules=[]
        if not key or key in seen: rules.append('missing_or_duplicate_order_key')
        seen.add(key)
        if row.get('ItemID') not in itemmap: rules.append('unknown_item')
        if row.get('SupplierID') not in supplierids: rules.append('unknown_supplier')
        if row.get('ItemID') in itemmap and row.get('SupplierID')!=itemmap[row['ItemID']]['SupplierID']: rules.append('supplier_item_mismatch')
        try:
            q=int(row['OrderedQty']); r=int(row['ReceivedQty']); cost=float(row['UnitCost'])
            if q<=0 or r<0 or r>q or not 0<cost<1000000: rules.append('invalid_quantity_or_cost')
        except (ValueError,KeyError): rules.append('invalid_number')
        try:
            od=date.fromisoformat(row['OrderDate']); dd=date.fromisoformat(row['DueDate']); rd=date.fromisoformat(row['ReceiptDate']) if row.get('ReceiptDate') else None
            if dd<od or (rd and rd<od): rules.append('date_sequence')
            if bool(rd)!=(int(row['ReceivedQty'])>0): rules.append('receipt_date_quantity_mismatch')
        except (ValueError,KeyError): rules.append('invalid_date_or_receipt')
        for rule in rules: issue('orders',key,rule)
        if not rules: good.append(row)
    seen=set(); graph={}
    for r in bom:
        key=(r.get('ParentID',''),r.get('ComponentID','')); sk='/'.join(key)
        if not all(key) or key in seen: issue('bom',sk,'missing_or_duplicate_bom_key')
        seen.add(key); graph.setdefault(key[0],[]).append(key[1])
        if key[1] not in itemmap and not key[1].startswith('KIT'): issue('bom',sk,'unknown_component')
        if key[1].startswith('KIT') and key[1] not in {b.get('ParentID') for b in bom}: issue('bom',sk,'unknown_assembly')
        try:
            if float(r['Quantity'])<=0: issue('bom',sk,'nonpositive_bom_quantity')
        except (ValueError,KeyError): issue('bom',sk,'invalid_bom_quantity')
        if key[1] in itemmap and r.get('Unit')!=itemmap[key[1]]['Unit']: issue('bom',sk,'unit_mismatch')
    def cycle(node,trail):
        if node in trail: return True
        return any(cycle(c,trail|{node}) for c in graph.get(node,[]))
    for parent in graph:
        if cycle(parent,set()): issue('bom',parent,'bom_cycle')
    return good,issues

def metrics(rows,asof):
    rows=[r for r in rows if date.fromisoformat(r['OrderDate'])<=asof]
    due=[r for r in rows if date.fromisoformat(r['DueDate'])<=asof]
    received=[r for r in rows if r['ReceiptDate'] and date.fromisoformat(r['ReceiptDate'])<=asof]
    otif=[r for r in due if r['ReceiptDate'] and date.fromisoformat(r['ReceiptDate'])<=date.fromisoformat(r['DueDate']) and int(r['ReceivedQty'])>=int(r['OrderedQty'])]
    late=[r for r in due if not r['ReceiptDate'] or date.fromisoformat(r['ReceiptDate'])>asof]
    return dict(order_lines=len(rows),due_lines=len(due),otif_lines=len(otif),otif_rate=len(otif)/len(due) if due else None,overdue_open_lines=len(late),ordered_value=round(sum(int(r['OrderedQty'])*float(r['UnitCost']) for r in rows),2),mean_received_lead_days=sum((date.fromisoformat(r['ReceiptDate'])-date.fromisoformat(r['OrderDate'])).days for r in received)/len(received) if received else None)

def run(inputdir,output,asof):
    orders=read(inputdir/'orders.csv'); bom=read(inputdir/'bom.csv'); items=read(ROOT/'data/clean/items.csv'); suppliers=read(ROOT/'data/clean/suppliers.csv')
    good,issues=validate(orders,items,suppliers,bom)
    digest=hashlib.sha256(b''.join(p.read_bytes() for p in [inputdir/'orders.csv',inputdir/'bom.csv',ROOT/'data/clean/items.csv',ROOT/'data/clean/suppliers.csv'])+asof.isoformat().encode()).hexdigest()[:12]
    runid=f'{asof}_{digest}'; dest=output/runid; dest.mkdir(parents=True,exist_ok=True)
    summary=dict(as_of=str(asof),run_id=runid,status='BLOCKED' if issues else 'PASS',input_rows=len(orders),accepted_rows=len(good),rejected_rows=len(orders)-len(good),quality_issues=len(issues),metrics=metrics(good,asof),synthetic=True)
    csvout(dest/'quality_issues.csv',issues,['entity','key','rule'])
    csvout(dest/'accepted_orders.csv',good,list(orders[0]))
    (dest/'summary.json').write_text(json.dumps(summary,indent=2))
    label='Diagnostic only: quality failures block publication.' if issues else 'Validated report ready for review.'
    body=''.join(f'<tr><td>{html.escape(k)}</td><td>{html.escape(str(v))}</td></tr>' for k,v in summary['metrics'].items())
    (dest/'report.html').write_text(f'<!doctype html><html lang="en"><meta charset="utf-8"><title>Supply chain report</title><style>body{{font:16px Arial;max-width:900px;margin:50px auto;color:#183044}}td{{padding:12px;border-bottom:1px solid #ddd}}h1{{color:#183044}}</style><h1>Supply chain reporting</h1><p>Synthetic demonstration · {asof} · {summary["status"]}</p><p>{label}</p><table>{body}</table><p>OTIF denominator: all order lines due by the reporting date, including open overdue orders. No email has been sent.</p></html>',encoding='utf-8')
    if not issues:
        tmp=output/'latest.tmp'; tmp.write_text(json.dumps(dict(run_id=runid,report=f'{runid}/report.html'))); os.replace(tmp,output/'latest.json')
    print(json.dumps(summary,indent=2)); return 2 if issues else 0

if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('--input',type=Path,default=ROOT/'data/raw'); p.add_argument('--output',type=Path,default=ROOT/'03_Automation/runs'); p.add_argument('--as-of',type=date.fromisoformat,default=date(2026,9,21)); a=p.parse_args()
    raise SystemExit(run(a.input,a.output,a.as_of))
