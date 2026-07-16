#!/usr/bin/env python3
"""Regenerate board-dev/board-test.html — the war-room test build — from board.html.

DEMO=true + an in-memory seed + the saved live SC board sample (so the parser and
proximity overlay run against real board HTML without touching the SC site).
The seeded day sheet is crafted to exercise every proximity tier: NOW, soon,
watch (mentioning), later, idle (court not sitting), passed, unknown.
Run after editing board.html:  python3 make-board-test.py
Written into board-dev/ so the relative board-sample fetch resolves.
"""
html = open("board.html").read()

SEED = '''function seedDemo(db){
  const n=db.now;
  const people=[
    ["u_senior","Shyam Divan","senior","sd@chamber.in"],
    ["u_admin","Adith Deshmukh","admin","adithdeshmukh@gmail.com"],
    ["u_clerk","Staff","clerk","clerk@chamber.in"],
    ["u_yash","Yashvardhan S.","junior","yash@chamber.in"],
    ["u_shaishir","Shaishir","junior","shaishir@chamber.in"],
    ["u_anshula","Anshula L.","junior","anshula@chamber.in"],
    ["u_rishit","Rishit V.","junior","rishit@chamber.in"],
  ];
  people.forEach(([uid,name,role,email])=>db.set("users/"+uid,{name,email,role,active:true}));

  const D=todayISO();
  // Items chosen to hit each tier against the saved board sample (2026-07-13):
  //  Ct6 on item 3 (seq present) · Ct3 on 3 · Ct10 on 4 · Ct7 on 1506 · Ct13 not sitting · Ct14 on 3
  const entries=[
    {courtNo:"6", itemNo:"4",  caseTitle:"Mahabanoo & Anr. vs Kalikund Developers & Ors.", time:"10:30", bench:"J.B. Pardiwala, K.V. Chandran", counsel:"Somiran Sharma", juniorUids:["u_yash","u_shaishir"], confTime:"6:30 pm"},
    {courtNo:"3", itemNo:"6",  caseTitle:"Test Soon Matter vs State (sample)", time:"10:30", bench:"Vikram Nath, Sandeep Mehta", counsel:"Karanjawala & Co.", juniorUids:["u_anshula"]},
    {courtNo:"5", itemNo:"6",  caseTitle:"Test Adjacent Matter vs Union (sample)", time:"10:30", bench:"", counsel:"", juniorUids:["u_rishit"]},
    {courtNo:"6", itemNo:"49", caseTitle:"Jyoti Builders vs Chief Executive Officer & Ors.", time:"10:30", bench:"J.B. Pardiwala, K.V. Chandran", counsel:"Anish Agarwal", juniorUids:["u_yash"], confTime:"5:00 pm"},
    {courtNo:"7", itemNo:"MM", caseTitle:"Kotak Mahindra Trustee Co. Ltd. vs SEBI", time:"10:30", bench:"Dipankar Datta, Sheel Nagu", counsel:"Mahesh Agarwal", juniorUids:["u_anshula"]},
    {courtNo:"13",itemNo:"48", caseTitle:"M/s Chandler & Price India vs M.Z.S. Da Piedade Vas & Ors.", time:"10:30", bench:"P.K. Mishra, Chandrasekhar", counsel:"Wadia Ghandy", juniorUids:["u_rishit"]},
    {courtNo:"14",itemNo:"2",  caseTitle:"Test Passed Matter vs State (sample)", time:"10:30", bench:"", counsel:"", juniorUids:["u_shaishir"]},
    {courtNo:"1", itemNo:"12", caseTitle:"Sugandha Hiemath & Ors. vs Babasaheb N. Kalyani & Ors.", time:"10:30", bench:"C.J.I., Joymala Bagchi, V. Mohana", counsel:"Karanjawala & Co.", juniorUids:["u_yash"]},
    {courtNo:"2", itemNo:"101", listType:"Regular", caseTitle:"Test Regular Matter vs Union of India (regular list)", time:"10:30", bench:"Surya Kant, N.K. Singh", counsel:"AZB & Partners", juniorUids:["u_rishit"]},
  ];
  db.set("daysheets/"+D,{date:D,updatedAt:n(),updatedBy:"u_clerk",entries,conferences:[]});

  // Senior last marked in Court 6 40 min ago -> stale -> the app should INFER.
  db.set("config/live",{court:{court:"6",at:{_t:Date.now()-40*60000},by:"u_yash"},conf:null});

  db.set("messages/m1",{by:"u_yash",name:"Yashvardhan S.",text:"Court 6 is moving slowly, still on item 3.",at:{_t:Date.now()-9*60000}});
  db.set("messages/m2",{by:"u_anshula",name:"Anshula L.",text:"I'm outside Court 3, will signal when our item is called.",at:{_t:Date.now()-4*60000}});
}'''

# swap the empty stub for the real seed
stub = "function seedDemo(db){}"
assert stub in html, "seed stub not found"
html = html.replace(stub, SEED, 1)

html = html.replace("const DEMO = false;", "const DEMO = true;", 1)
html = html.replace('const BOARD_SAMPLE = null;',
                    'const BOARD_SAMPLE = "./get_board_sample_2026-07-13.html";', 1)

open("board-dev/board-test.html", "w").write(html)
print("board-dev/board-test.html regenerated:", len(html), "bytes")
