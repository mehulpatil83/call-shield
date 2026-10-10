# Seed call scenarios (Phase 0 draft, 6 of the planned ~30)

All people, numbers and amounts are fictional. **Marathi and Hinglish lines need review by a native speaker before
we record or use them for evaluation.** "Hard negative" = a legitimate call that contains scam-like words, which is
exactly what a naive keyword detector gets wrong.

Each scenario is a two-person call. Record the two roles on separate channels or separate files when possible.

---
## EN-1 Executive impersonation (scam)
Tactics: authority claim, urgency, bypass verification, secrecy, payment.
- Caller: Hi Rahul, it's Anil. I'm in a board meeting and can't talk. I need you to process an urgent transfer of two lakh rupees to a vendor, right now.
- Employee: Sure sir, should I raise it through the finance portal?
- Caller: No, skip the portal, there's no time. Don't tell anyone, this is confidential. I'll send the account number on WhatsApp.
- Employee: Okay, but the policy says transfers need a second approval.
- Caller: I'm the CFO. Just do it and confirm back in ten minutes.

## EN-2 Delivery OTP at the door (hard negative)
Why it is hard: a real person legitimately asks for an OTP.
- Agent: Hello ma'am, I'm the delivery executive with your parcel, I'm at your gate.
- Customer: Oh good. Is that the grocery order?
- Agent: Yes ma'am. The delivery OTP is on your app, please share it so I can hand over the parcel.
- Customer: It's four four one seven.
- Agent: Thank you ma'am, have a nice day.

## HI-1 Remote-access tech support (scam)
Tactics: authority claim, fear, remote-access install, code request, secrecy, threat.
- Caller: Hello sir, main Microsoft security team se bol raha hoon. Aapke laptop mein virus aa gaya hai.
- Victim: Kya? Mujhe toh kuch dikha nahi.
- Caller: Sir, aapka bank account bhi risk mein hai. Aap abhi AnyDesk app download kijiye, main remotely fix kar dunga.
- Victim: Lekin yeh safe hai?
- Caller: Bilkul safe hai sir. Bas jo nine digit code screen par aaye woh mujhe bataiye. Aur kisi ko mat batana, warna account freeze ho jayega.

## HI-2 Genuine bank fraud alert (hard negative)
Why it is hard: mentions blocking, OTP and PIN, but the agent refuses to ask for them.
- Agent: Namaste sir, main aapke bank ke fraud monitoring desk se bol rahi hoon. Aapke card se chaar hazaar paanch sau rupaye ka transaction hua hai, kya yeh aapne kiya?
- Customer: Nahi, maine toh nahi kiya.
- Agent: Theek hai sir, hum card abhi block kar dete hain. Main aapse koi OTP ya PIN nahi maangungi. Naya card teen din mein aapke ghar aa jayega.
- Customer: Thank you. Kya main branch jaake bhi confirm kar sakta hoon?
- Agent: Ji bilkul, aap card ke peeche likhe number par call karke ya branch jaakar confirm kar sakte hain.

## MR-1 Electricity disconnection + UPI PIN (scam)
Tactics: authority claim, urgency, threat, payment link, PIN request, do-not-hang-up.
- Caller: नमस्कार, मी वीज वितरण कार्यालयातून बोलतोय. तुमचे मागील महिन्याचे बिल थकले आहे.
- Victim: अरे, मी तर बिल भरले आहे.
- Caller: नाही साहेब, आमच्याकडे नोंद नाही. आज रात्री नऊ वाजेपर्यंत पैसे भरले नाहीत तर तुमचे वीज कनेक्शन तोडले जाईल.
- Victim: मग आता काय करू?
- Caller: मी तुम्हाला एक लिंक पाठवतो. त्यावर तुमचा यूपीआय पिन टाका आणि दोन हजार रुपये भरा.
- Victim: पिन कशाला?
- Caller: ही फक्त पडताळणी आहे. आणि फोन ठेवू नका, लगेच करा, नाहीतर दंड लागेल.

## MR-2 Son warns mother about OTP (hard negative)
Why it is hard: discusses an OTP that was received and a suspicious caller, but nobody is being scammed on this call.
- Son: आई, मी बोलतोय. आत्ताच बँकेचा मेसेज आला का?
- Mother: हो, ओटीपी आला आहे. कोणीतरी फोन करून तो विचारत होता.
- Son: आई, तो कोणालाही सांगू नकोस. बँक कधीच ओटीपी विचारत नाही.
- Mother: ठीक आहे, मी फोन कट केला.
- Son: छान. मी संध्याकाळी घरी येऊन तुझ्या फोनमध्ये सगळं तपासतो.
- Mother: बरं बाळा, ये.
