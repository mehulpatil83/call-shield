"""Editable word lists for the rule engine (English, Hinglish in Roman script, Hindi/Marathi in Devanagari).

DRAFT: written by an AI assistant and NOT yet reviewed by native speakers. Spelling variants are listed
explicitly because speech-to-text spells the same word differently ("केवायसी" / "के वाई सी" / "kyc").
Each phrase is matched fuzzily token by token, so small spelling differences are tolerated.
To extend: add a phrase to the right list. Run `python -m pytest tests` afterwards.
"""

# ---- sensitive things a scammer asks for ---------------------------------------------------------
OTP_TERMS = [
    "otp", "o t p", "saha anki code", "saha ankhi code", "one time password", "one time pin", "verification code", "security code",
    "six digit code", "6 digit code", "six digit otp", "6 digit otp", "six digit pin", "passcode",
    "ओटीपी", "ओ टी पी", "ओटिपी", "वन टाइम पासवर्ड", "सिक्स डिजिट कोड", "सिक्स डिजिट ओटीपी", "छह अंकों का कोड",
    "सहा अंकी कोड", "सहा अंकी ओटीपी", "वेरिफिकेशन कोड",
]
CREDENTIAL_TERMS = [
    "pin", "upi pin", "atm pin", "card pin", "password", "net banking password", "cvv", "card number",
    "card details", "expiry date", "aadhaar number", "aadhar number", "aadhaar", "aadhar", "pan number",
    "पिन", "यूपीआई पिन", "यूपीआय पिन", "पासवर्ड", "सीवीवी", "कार्ड नंबर", "कार्ड नंबर", "आधार नंबर", "आधार",
    "पिन नंबर", "कार्ड क्रमांक", "आधार क्रमांक",
]

# ---- verbs of handing something over (used with the terms above) -----------------------------------
DISCLOSE_VERBS = [
    "share", "tell", "give", "send", "read", "provide", "say", "confirm", "enter", "type", "forward",
    "need", "want", "required", "dictate",
    "bataiye", "bataiyega", "bataye", "batao", "bataiye", "bata", "dijiye", "dijiyega", "dena", "bhejiye",
    "bhejo", "bolo", "boliye", "share karo", "share kijiye", "share karein",
    "बताइए", "बताइये", "बताओ", "बता दीजिए", "दीजिए", "दीजिये", "भेजिए", "भेजो", "बोलिए", "शेयर", "बताएं",
    "बताना", "सांगा", "सांगावे", "द्या", "पाठवा", "टाका", "सांगितला", "सांगितलं", "मला सांगा",
    "sanga", "sang", "sangaa", "dya", "dyaa", "pathva", "pathav", "taka", "mala sanga",
    "daaliye", "daliye", "daaliyega", "dalo", "likhiye", "डालिए", "डालिये", "डालो", "दर्ज करें",
]
# "this" references: "don't tell anyone ABOUT THIS CALL" is a scammer's secrecy demand even when a PIN is mentioned nearby
SECRECY_THIS = ["about this call", "about this", "this call", "yeh baat", "ye baat", "is baat", "is call",
                "ये बात", "यह बात", "इस बात", "ही गोष्ट", "ही बाब", "हे"]

# ---- words that turn a mention into a warning ("never share your OTP") --------------------------------
WARNING_CUES = [
    "never", "not", "don't", "dont", "do not", "no one", "nobody", "hang up", "refuse", "beware",
    "fraud", "scam", "reminder", "never share", "doesn't ask", "does not ask", "will never ask",
    "nahi", "nahin", "nahi", "na karein", "na kijiye", "na kare", "mat", "kabhi nahi", "kabhi bhi nahi",
    "phone kaat", "kaat dijiye", "call kaat",
    "नहीं", "नही", "न करें", "न कीजिए", "मत", "कभी नहीं", "कभी भी नहीं", "फोन काट", "कॉल काट",
    "नका", "नकोस", "नाही", "कधीही", "कधीच", "कधी नाही", "कट करा", "फोन कट",
    "naka", "nako", "nakos", "kadhihi", "kadhich", "kadhi nahi", "kunalahi", "kat kara", "phone kat",
]

# ---- indicator categories --------------------------------------------------------------------------
# kind: request (asks you to hand over something), pressure (rushes or scares you), context (claims or pretexts)
CATEGORIES = {
    "payment_request": {
        "kind": "request",
        "explain": "Asks for money, a transfer or a payment link.",
        "phrases": [
            "link par bhejiye", "is link par", "rupaye bhejiye", "paise bhejiye",
            "paise bhara", "paise pathva", "link pathvto", "link pathva", "payment kara",
            "transfer of", "process a transfer", "process an urgent transfer", "transfer the money", "send the money",
            "send money", "make the payment", "make a payment", "pay the fine", "pay a fine", "pay the amount",
            "payment link", "click the link", "click on the link", "upi link", "gift card", "gift cards",
            "processing fee", "send the amount",
            "paise bhejiye", "paise bhejo", "paise transfer", "payment karo", "payment kijiye", "link par click",
            "link bhej raha", "amount bhejiye", "upi se bhejo",
            "पैसे भेजो", "पैसे भेजिए", "पेमेंट करो", "लिंक पर क्लिक", "पैसे ट्रांसफर", "पैसे ट्रांसफर करो",
            "पैसे भरा", "रुपये भरा", "पैसे पाठवा", "लिंक पाठवतो", "लिंक पाठवा", "पेमेंट करा", "ट्रान्सफर करा",
        ],
    },
    "remote_access": {
        "kind": "request",
        "explain": "Asks you to install a remote-control app or share your screen, which lets a stranger operate your device.",
        "phrases": [
            "app download kara", "app install kara", "screen share kara",
            "anydesk", "any desk", "teamviewer", "team viewer", "quicksupport", "quick support", "ultraviewer",
            "rustdesk", "screen sharing", "share your screen", "remote access", "remote desktop",
            "download the app", "install the app", "download an app", "install this app", "download this app",
            "download kijiye", "install kijiye", "app download", "app install", "remotely",
            "एनीडेस्क", "एनी डेस्क", "टीमव्यूअर", "टीम व्यूअर", "स्क्रीन शेयर", "ऐप डाउनलोड", "ऐप इंस्टॉल",
            "ॲप डाउनलोड", "अ‍ॅप डाउनलोड", "रिमोट", "स्क्रीन शेअर",
        ],
    },
    "urgency": {
        "kind": "pressure",
        "explain": "Pushes you to act immediately so you do not stop and think.",
        "phrases": [
            "lagech", "aattach", "atach", "tabadtob", "taabadtob", "tatkal", "aaj ratri paryant",
            "right now", "immediately", "urgent", "urgently", "as soon as possible", "asap", "tonight", "by tonight",
            "by midnight", "within an hour", "within one hour", "within ten minutes", "within 24 hours", "no time",
            "hurry", "quickly", "last chance", "by end of day",
            "abhi", "turant", "jaldi", "fauran", "foran", "aaj raat tak", "aaj hi", "jald se jald",
            "अभी", "तुरंत", "जल्दी", "आज रात तक", "आज ही", "फौरन",
            "लगेच", "आत्ताच", "आजच", "तात्काळ", "आज रात्री", "रात्रीपर्यंत", "आज रात्रीपर्यंत", "ताबडतोब",
        ],
    },
    "threat": {
        "kind": "pressure",
        "explain": "Threatens a bad consequence (blocked account, legal action, disconnection) to scare you into complying.",
        "phrases": [
            "kaat diya jayega", "kaat diya jaayega", "kat diya jayega", "connection kaat", "band kar diya jayega",
            "band hoil", "khate band hoil", "block hoil", "todle jail", "gothavle jail", "dand lagel", "karvai hoil",
            "will be blocked", "will be suspended", "will be frozen", "will be closed", "will be disconnected",
            "will be deactivated", "will be cancelled", "will be canceled", "legal action", "police case",
            "you will be arrested", "arrest warrant", "penalty will", "you will lose",
            "block ho jayega", "block ho jaayega", "band ho jayega", "band ho jaayega", "freeze ho jayega",
            "suspend ho jayega", "legal action", "arrest ho", "penalty lagegi",
            "ब्लॉक हो जाएगा", "बंद हो जाएगा", "फ्रीज हो जाएगा", "फ्रीज़ हो जाएगा", "गिरफ्तार", "जुर्माना लगेगा",
            "बंद होईल", "तोडले जाईल", "गोठवले जाईल", "ब्लॉक होईल", "दंड लागेल", "कारवाई होईल", "अटक होईल",
            "कनेक्शन तोडले जाईल", "खाते बंद होईल", "खाते गोठवले जाईल",
        ],
    },
    "secrecy": {
        "kind": "pressure",
        "explain": "Tells you to keep the call secret, which stops you from checking with anyone.",
        "phrases": [
            "kunalahi sangu naka", "kunala sangu naka", "kunalahi sangu nakos",
            "don't tell anyone", "do not tell anyone", "don't tell anybody", "keep this confidential",
            "keep it secret", "this is confidential", "between us", "don't share this with anyone",
            "kisi ko mat batana", "kisi ko mat bataiye", "kisi ko nahi batana", "kisi ko bhi mat batana",
            "yeh confidential hai", "किसी को मत बताना", "किसी को मत बताइए", "किसी को नहीं बताना", "गोपनीय",
            "कोणाला सांगू नका", "कोणालाही सांगू नका", "कुणाला सांगू नका", "गोपनीय आहे",
        ],
    },
    "verification_bypass": {
        "kind": "pressure",
        "explain": "Discourages you from verifying, hanging up or following the normal process.",
        "phrases": [
            "call kaatna mat", "kaatna mat", "call mat kaatna", "phone mat kaatna",
            "phone thevu naka", "phone thevu nakos",
            "skip the portal", "skip the verification", "skip approval", "bypass", "no need to verify",
            "don't call back", "don't hang up", "do not hang up", "don't disconnect", "stay on the line",
            "do not call the bank", "don't call the bank", "without approval", "just do it",
            "phone mat rakhiye", "call mat kaatiye", "line par bane rahiye", "verify karne ki zaroorat nahi",
            "फोन मत रखिए", "फोन मत रखना", "कॉल मत काटिए", "लाइन पर बने रहिए",
            "फोन ठेवू नका", "फोन कट करू नका", "लाईनवर रहा", "फोन बंद करू नका",
        ],
    },
    "authority": {
        "kind": "context",
        "explain": "Claims to be a bank, company, government body or senior colleague. Scammers use authority to gain trust.",
        "phrases": [
            "vibhag se bol raha", "vibhag se bol rahi", "bijli vibhag", "विभाग से बोल रहा", "विभाग से बोल रही",
            "bankentun bolatoy", "bankentun bolto", "bankentun bolte", "bankentun", "vij vitaran",
            "from your bank", "from the bank", "calling from your bank", "bank security department",
            "security department", "fraud department", "bank manager", "customer care executive", "rbi",
            "reserve bank of india", "cyber crime", "cyber cell", "income tax department", "customs department",
            "microsoft", "windows support", "technical support", "electricity board", "electricity office",
            "i am the cfo", "i'm the cfo", "this is the ceo", "i am the ceo", "i'm the ceo",
            "main aapke bank se", "bank se bol raha", "bank se bol rahi", "aapke bank se", "security department se",
            "fraud department se", "microsoft security team",
            "बैंक से बोल", "आपके बैंक से", "सिक्योरिटी डिपार्टमेंट", "माइक्रोसॉफ्ट",
            "बँकेतून बोलतोय", "बँकेतून बोलते", "बँकेतून", "वीज वितरण कार्यालयातून", "वीज वितरण", "बँक अधिकारी",
        ],
    },
    "kyc_pretext": {
        "kind": "context",
        "explain": "Uses a KYC (identity update) pretext, a very common opening in bank scams.",
        "phrases": [
            "kyc", "know your customer", "update your kyc", "kyc update", "kyc expired",
            "केवायसी", "केवाईसी", "के वाई सी", "के वाय सी", "के वायसी",
        ],
    },
}

# ---- how each request / warning is explained in the report ---------------------------------------------
REQUEST_EXPLAIN = {
    "otp_request": "Asks you to share a one-time code (OTP). Banks and genuine services never need you to read it out to them.",
    "credential_request": "Asks for a PIN, password, card or ID number.",
}
WARNING_EXPLAIN = "Cautionary wording near a sensitive item (for example 'never share your OTP'). Treated as a warning, not a request."
