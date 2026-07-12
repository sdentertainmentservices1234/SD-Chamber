#!/usr/bin/env python3
"""Regenerate test.html — the real-chamber test build — from index.html.

test.html is index.html with DEMO=true and seedDemo() replaced by the actual
chamber as transcribed from the clerk's paper cause list for Monday 13.07.2026.
Run after any edit to index.html:  python3 make-test.py
In-memory only; a browser reload resets all test state.
"""
import re

html = open("index.html").read()

SEED = '''function seedDemo(db){
  const n=db.now;
  // REAL-CHAMBER TEST SEED — transcribed from the clerk's paper cause list
  // for Monday 13.07.2026. In-memory only; reload resets everything.
  // joinedOn dates are placeholders in paper order — edit via Chamber tab.
  const people=[
    ["u_admin","Adith Deshmukh","admin",null,"adithdeshmukh@gmail.com"],
    ["u_clerk","Clerk","clerk",null,"clerk@chamber.in"],
    ["u_adith","Adith D.","junior","2019-07-01","adithd@chamber.in"],["u_ankur","Ankur S.","junior","2020-07-01","ankur@chamber.in"],
    ["u_yash","Yashvardhan S.","junior","2021-07-01","yash@chamber.in"],["u_shaishir","Shaishir","junior","2022-07-01","shaishir@chamber.in"],
    ["u_anshula","Anshula L.","junior","2023-07-01","anshula@chamber.in"],["u_rongong","Rongong","junior","2024-07-01","rongong@chamber.in"],
    ["u_rishit","Rishit V.","junior","2025-07-01","rishit@chamber.in"],
  ];
  people.forEach(([uid,name,role,joinedOn,email])=>db.set("users/"+uid,{name,email,role,active:true,phone:"",joinedOn,createdAt:n()}));
  db.set("config/roster",{pointer:0});
  // a pending email invite so the admin's onboarding panel is populated
  db.set("approvals/"+emailKey("newjunior@gmail.com"),{email:"newjunior@gmail.com",name:"New Junior (sample invite)",role:"junior",phone:"9820000000",joinedOn:"2026-07-01",by:"u_admin",at:n()});

  const D="2026-07-13"; // Monday, as on the paper
  // [id, title, bench, court, item, briefing counsel, appearing for, juniors, conference time]
  const M=[
    ["m1","Sugandha Hiemath & Ors. vs Babasaheb Neelkanth Kalyani & Ors.","C.J.I., Joymala Bagchi, V. Mohana","1","30","Karanjawala & Co.","",["u_adith","u_ankur"],"4.00"],
    ["m2","Mahabanoo & Anr. vs Kalikund Developers & Ors.","J.B. Pardiwala, K.V. Chandran","6","46","Somiran Sharma","Petitioner",["u_yash","u_shaishir"],"6.30"],
    ["m3","Jyoti Builders vs Chief Executive Officer & Ors.","J.B. Pardiwala, K.V. Chandran","6","49","Anish Agarwal","Petitioner",["u_yash"],"5.00"],
    ["m4","Kotak Mahindra Trustee Co. Ltd. vs SEBI","Dipankar Datta, Sheel Nagu","7","MM","Mahesh Agarwal","Petitioner",["u_anshula","u_ankur"],"3.00"],
    ["m5","Bhudarbhai D Patel vs Jayesh T Kotak & Ors.","Sanjay Karol, A.G. Masih","8","21","Rishabh Parekh","Respondent",["u_shaishir","u_rongong"],"3.30"],
    ["m6","Pareshbhai Anandbhai & Ors vs Maheshbhai Rambhai Patel & Ors.","Arvind Kumar, Vipul Pancholi","12","37","S. Sanjanwala","Petitioner",["u_yash"],"7.00"],
    ["m7","M/s Chandler & Price India vs Maria Zoraida Sarojini Da Piedade Vas & Ors.","P.K. Mishra, Chandrasekhar","13","48","Wadia Ghandy","Petitioner",["u_rishit"],"6.00"],
  ];
  M.forEach(([id,title,bench,court,item,counsel,af,jrs],i)=>{
    // diary/case numbers are not on the paper — left blank, flagged "details awaited"
    // matterType "Other court / tribunal" (weight 2) until the clerk corrects it
    const acked = i<4; // m5–m7 left unacknowledged so the unseen-ageing + nudge flow is visible
    db.set("briefs/"+id,{caseTitle:title,chamberNo:String(104-i),diaryNo:"",caseNo:"",matterType:"Other court / tribunal",
      appearingFor:af,aor:counsel,assignedTo:jrs.slice(),everAssigned:jrs.slice(),
      assignHistory:jrs.map(u=>({uid:u,at:Date.now()-(7-i)*864e5,by:"u_clerk",mode:"manual"})),
      declinedBy:[],ackBy:acked?jrs.slice():[],assignedAt:Date.now()-(7-i)*864e5,
      status:"listed",priority:false,nextDate:D,conferenceAt:D,detailsAwaited:true,
      createdAt:n(),updatedAt:{_t:Date.now()-i*60000}});
  });

  // three clearly synthetic unassigned briefs so auto-assign / rostering can be exercised
  const T=[["t1","Test Matter A vs State (sample)","Civil Appeal","11111/2026","2026-07-15"],
    ["t2","Test Matter B vs Union of India (sample)","SLP (Civil)","22222/2026","2026-07-21"],
    ["t3","Test Matter C vs Registrar (sample)","MA / IA","33333/2026",null]];
  T.forEach(([id,title,mt,dy,nx])=>db.set("briefs/"+id,{caseTitle:title,diaryNo:dy,caseNo:"",matterType:mt,
    appearingFor:"Petitioner",aor:"",assignedTo:[],everAssigned:[],assignHistory:[],declinedBy:[],ackBy:[],
    status:"received",priority:false,nextDate:nx,conferenceAt:null,createdAt:n(),updatedAt:{_t:Date.now()}}));

  // calendar: real SC 2026 summer vacation (partial court, ends 12 Jul) + a
  // senior-away day, so the demo shows the actual shading (no fake clutter).
  db.set("config/vacation",{ranges:[["2026-06-01","2026-07-12","Summer vacation — partial court working days"]]});
  db.set("config/senioravail",{"2026-07-15":"Travelling (sample)"});
  // live "Now" tracker — Senior currently in Court 6 (marked a few minutes ago)
  db.set("config/live",{court:{court:"6",at:Date.now()-7*60000,by:"u_yash"},conf:null});
  // a couple of sample leave-log entries (this month, so the counters show)
  db.set("leaves/lv1",{uid:"u_yash",from:"2026-07-04",to:"2026-07-06",reason:"Family function",by:"u_admin",at:n()});
  db.set("leaves/lv2",{uid:"u_ankur",from:"2026-07-09",to:"2026-07-09",reason:"",by:"u_admin",at:n()});
  db.set("leaves/lv3",{uid:"u_yash",from:"2026-02-11",to:"2026-02-14",reason:"Medical",by:"u_admin",at:n()});

  // everyone available today and on the 13th
  ["u_adith","u_ankur","u_yash","u_shaishir","u_anshula","u_rongong","u_rishit"].forEach(u=>
    [D,todayISO()].forEach(dt=>db.set("availability/"+u+"_"+dt,{uid:u,date:dt,status:"available",note:"",at:n()})));
  // the paper itself: one day-sheet doc for Monday, mirrored onto today so the tab isn't empty on open
  const entries=M.map(([id,title,bench,court,item,counsel,af,jrs,ct])=>({briefId:id,caseTitle:title,
    courtNo:court,itemNo:item,listType:"Miscellaneous",appearingFor:af||"Petitioner",time:"10.30",confTime:ct,confDate:D,bench,counsel,juniorUids:jrs.slice(),juniorUid:jrs[0],remarks:"",done:false}));
  [D,todayISO()].forEach(dt=>db.set("daysheets/"+dt,{date:dt,updatedAt:n(),updatedBy:"u_clerk",
    // today's copy carries the conferences dated TODAY so the Now tracker has live conferences
    entries:entries.map(e=>({...e, confDate:dt})),conferences:[]}));
}
'''

start = html.index("function seedDemo(db){")
end = html.index("/* ============================================================\n   APP STATE + BOOT")
html = html[:start] + SEED + "\n" + html[end:]
html = html.replace("const DEMO = false;", "const DEMO = true;", 1)

# demo bar: real names in the role switcher, honest banner text
opts = re.search(r'(<select id="demoRole">)(.*?)(</select>)', html, re.S)
new_opts = """
      <option value="u_admin">Adith · Admin</option>
      <option value="u_clerk">Staff</option>
      <option value="u_adith">Adith D. · Colleague</option>
      <option value="u_ankur">Ankur S. · Colleague</option>
      <option value="u_yash">Yashvardhan S. · Colleague</option>
      <option value="u_shaishir">Shaishir · Colleague</option>
      <option value="u_anshula">Anshula L. · Colleague</option>
      <option value="u_rongong">Rongong · Colleague</option>
      <option value="u_rishit">Rishit V. · Colleague</option>
    """
html = html[:opts.start(2)] + new_opts + html[opts.end(2):]
html = html.replace("Preview — sample chamber, nothing is saved",
                    "Test — real chamber list of 13.07.2026, nothing is saved", 1)

open("test.html", "w").write(html)
print("test.html regenerated:", len(html), "bytes")
