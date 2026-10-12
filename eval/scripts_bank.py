"""Reading scripts for evaluation recordings (single speaker reads one script aloud, 20-40 seconds).

IMPORTANT (honest evaluation): scripts are split into DEV and TEST. Look at failures and improve the word lists using DEV
recordings only. TEST scripts are for the final numbers; do not tune on them. All texts are fictional (no real names or
numbers). Marathi and Hinglish texts are drafts and need a native speaker's review before recording.

Script ids: <language>-<s|b><n>  (s = scam, b = benign; hard = a legitimate call that sounds suspicious)"""
from __future__ import annotations

SCRIPTS: dict[str, dict] = {}


def add(id: str, language: str, label: str, scenario: str, split: str, text: str, hard: bool = False) -> None:
    SCRIPTS[id] = {"id": id, "language": language, "label": label, "scenario": scenario, "split": split,
                   "hard": hard, "text": text}


# ----------------------------------------------------------------------------------------- English
add("en-s1", "en", "scam", "bank KYC and OTP", "dev",
    "Good afternoon sir, I am calling from the State Bank customer security team. Your KYC has expired and your account will be blocked within one hour. To avoid this, please tell me the six digit code that was just sent to your mobile phone. Do not disconnect the call, it is urgent.")
add("en-s2", "en", "scam", "electricity disconnection and UPI", "dev",
    "Hello, this is the electricity board billing office. Your last bill is unpaid and your power connection will be disconnected tonight at nine. Please pay two thousand rupees immediately using the payment link I am sending you. Enter your UPI PIN on that page to confirm. Do not tell anyone about this call.")
add("en-s3", "en", "scam", "tech support remote access", "test",
    "Hello, I am from Microsoft technical support. Your computer has sent us a virus alert and your bank details are at risk. Please download the AnyDesk app right now so that I can connect to your screen and fix it. Once it is installed, read out the nine digit code to me.")
add("en-s4", "en", "scam", "digital arrest and transfer", "test",
    "This is the cyber crime branch. A parcel in your name has been found with illegal items and there is an arrest warrant against you. Stay on this video call and do not speak to anyone. To close the case you must transfer the verification amount to the government account today, otherwise you will be arrested.")
add("en-b1", "en", "benign", "bank reminder", "dev",
    "Hello, this is a message from your bank. For your safety, we will never ask for your OTP, PIN or password on a call. If anyone asks you for these details, hang up and call the number on the back of your card. Thank you for banking with us.")
add("en-b2", "en", "benign", "delivery code at the door", "dev",
    "Hello ma'am, I am the delivery executive with your grocery order and I am at your gate. For delivery confirmation, please share the code shown in your order app so that I can hand over the parcel. Thank you.", hard=True)
add("en-b3", "en", "benign", "genuine bank fraud alert", "test",
    "Hello sir, this is the fraud monitoring team of your bank. We noticed a payment of four thousand five hundred rupees on your card. Was this you? If not, we will block the card now. We will not ask for your OTP or PIN. You can confirm by calling the number on your card.", hard=True)
add("en-b4", "en", "benign", "clinic appointment reminder", "test",
    "Hi, this is a reminder from the clinic that your appointment is tomorrow at ten thirty in the morning. Please bring your previous reports. If you need to change the time, call us back on the clinic number. Thank you and have a good day.")

# ----------------------------------------------------------------------------------------- Hinglish (Roman script)
add("hinglish-s1", "hinglish", "scam", "bank KYC and OTP", "dev",
    "Namaste sir, main aapke bank ke security department se bol raha hoon. Aapka KYC update pending hai aur aaj raat tak aapka account block ho jayega. Abhi aapke phone par jo six digit OTP aaya hai woh mujhe bataiye. Call kaatna mat, bahut urgent hai.")
add("hinglish-s2", "hinglish", "scam", "electricity disconnection and UPI", "dev",
    "Hello, main bijli vibhag se bol raha hoon. Aapka pichla bill baaki hai aur aaj raat nau baje aapka connection kaat diya jayega. Abhi do hazaar rupaye is link par bhejiye aur apna UPI PIN daaliye. Yeh baat kisi ko mat batana.")
add("hinglish-s3", "hinglish", "scam", "tech support remote access", "test",
    "Hello sir, main Microsoft technical support se bol raha hoon. Aapke computer mein virus aa gaya hai aur aapke bank details khatre mein hain. Abhi AnyDesk app download kijiye taaki main aapki screen dekh kar fix kar sakun. Phir jo nine digit code aaye woh mujhe bataiye.")
add("hinglish-s4", "hinglish", "scam", "digital arrest and transfer", "test",
    "Yeh cyber crime branch se call hai. Aapke naam ke parcel mein illegal saaman mila hai aur aapke khilaaf arrest warrant nikla hai. Is video call par bane rahiye aur kisi se baat mat kijiye. Case band karne ke liye aaj hi verification amount transfer kijiye, warna aapko arrest kar liya jayega.")
add("hinglish-b1", "hinglish", "benign", "bank reminder", "dev",
    "Namaste, yeh aapke bank ki taraf se ek reminder hai. Hum kabhi bhi phone par aapka OTP, PIN ya password nahi maangte. Agar koi aisa maange toh call kaat dijiye aur card ke peeche likhe number par call kijiye. Dhanyavaad.")
add("hinglish-b2", "hinglish", "benign", "delivery code at the door", "dev",
    "Hello madam, main delivery wala bol raha hoon, aapka order lekar gate par khada hoon. Delivery confirm karne ke liye aapke order app mein jo code dikh raha hai woh bata dijiye, taaki main parcel de sakun. Dhanyavaad.", hard=True)
add("hinglish-b3", "hinglish", "benign", "genuine bank fraud alert", "test",
    "Namaste sir, main aapke bank ke fraud monitoring team se bol raha hoon. Aapke card se chaar hazaar paanch sau rupaye ka transaction hua hai, kya yeh aapne kiya? Agar nahi, toh hum card abhi block kar denge. Hum aapse OTP ya PIN nahi maangte. Aap card ke peeche likhe number par call karke confirm kar sakte hain.", hard=True)
add("hinglish-b4", "hinglish", "benign", "clinic appointment reminder", "test",
    "Hello, yeh clinic ki taraf se reminder hai ki kal subah saade das baje aapka appointment hai. Kripya apni pichli reports saath layein. Agar time badalna ho toh clinic ke number par call kijiye. Dhanyavaad.")

# ----------------------------------------------------------------------------------------- Marathi (Devanagari)
add("mr-s1", "mr", "scam", "bank KYC and OTP", "dev",
    "नमस्कार साहेब, मी तुमच्या बँकेच्या सुरक्षा विभागातून बोलतोय. तुमचे केवायसी अपडेट बाकी आहे आणि आज रात्रीपर्यंत तुमचे खाते बंद होईल. कृपया तुमच्या फोनवर आलेला सहा अंकी ओटीपी मला आत्ताच सांगा. फोन कट करू नका, खूप तातडीचे आहे.")
add("mr-s2", "mr", "scam", "electricity disconnection and UPI", "dev",
    "नमस्कार, मी वीज वितरण कार्यालयातून बोलतोय. तुमचे मागील बिल थकले आहे आणि आज रात्री नऊ वाजता तुमचे वीज कनेक्शन तोडले जाईल. मी पाठवलेल्या लिंकवर लगेच दोन हजार रुपये भरा आणि तुमचा यूपीआय पिन टाका. हे कोणालाही सांगू नका.")
add("mr-s3", "mr", "scam", "tech support remote access", "test",
    "नमस्कार, मी मायक्रोसॉफ्ट तांत्रिक सहाय्यातून बोलतोय. तुमच्या संगणकात व्हायरस आला आहे आणि तुमची बँक माहिती धोक्यात आहे. आत्ताच एनीडेस्क अ‍ॅप डाउनलोड करा, म्हणजे मी तुमची स्क्रीन पाहून ते ठीक करू शकतो. मग तुम्हाला येणारा नऊ अंकी कोड मला सांगा.")
add("mr-s4", "mr", "scam", "digital arrest and transfer", "test",
    "हा सायबर क्राइम विभागाचा कॉल आहे. तुमच्या नावाच्या पार्सलमध्ये बेकायदेशीर वस्तू सापडल्या आहेत आणि तुमच्याविरुद्ध अटक वॉरंट निघाले आहे. या व्हिडिओ कॉलवर रहा आणि कोणाशीही बोलू नका. प्रकरण बंद करण्यासाठी आजच पडताळणी रक्कम ट्रान्सफर करा, नाहीतर तुम्हाला अटक होईल.")
add("mr-b1", "mr", "benign", "bank reminder", "dev",
    "नमस्कार, ही तुमच्या बँकेकडून एक आठवण आहे. आम्ही फोनवर तुमचा ओटीपी, पिन किंवा पासवर्ड कधीही विचारत नाही. कोणी असे विचारल्यास कॉल कट करा आणि कार्डच्या मागे दिलेल्या क्रमांकावर कॉल करा. धन्यवाद.")
add("mr-b2", "mr", "benign", "delivery code at the door", "dev",
    "नमस्कार ताई, मी तुमची ऑर्डर घेऊन आलो आहे आणि गेटवर उभा आहे. डिलिव्हरी निश्चित करण्यासाठी तुमच्या ऑर्डर अ‍ॅपमध्ये दिसणारा कोड मला सांगा, म्हणजे मी पार्सल देऊ शकतो. धन्यवाद.", hard=True)
add("mr-b3", "mr", "benign", "genuine bank fraud alert", "test",
    "नमस्कार साहेब, मी तुमच्या बँकेच्या फसवणूक निरीक्षण विभागातून बोलतोय. तुमच्या कार्डवरून चार हजार पाचशे रुपयांचा व्यवहार झाला आहे, तो तुम्ही केला का? नसेल तर आम्ही कार्ड आत्ता ब्लॉक करतो. आम्ही तुमचा ओटीपी किंवा पिन कधीही विचारत नाही. तुम्ही कार्डच्या मागील क्रमांकावर कॉल करून खात्री करू शकता.", hard=True)
add("mr-b4", "mr", "benign", "clinic appointment reminder", "test",
    "नमस्कार, ही दवाखान्याकडून आठवण आहे की उद्या सकाळी साडेदहा वाजता तुमची भेट ठरलेली आहे. कृपया तुमचे जुने रिपोर्ट सोबत आणा. वेळ बदलायची असल्यास दवाखान्याच्या क्रमांकावर कॉल करा. धन्यवाद.")


def write_sheets(folder) -> None:
    """Write printable reading sheets, one per language."""
    from pathlib import Path

    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    names = {"en": "English", "hinglish": "Hinglish", "mr": "Marathi"}
    for lang, title in names.items():
        lines = [f"# Reading sheet: {title}", "",
                 "Read each script aloud once, in your normal voice, at normal speed, 20 to 40 seconds each.",
                 "Name the file `<speaker>_<script id>.wav`, for example `p1_en-s1.wav`. These are fictional scripts.", ""]
        for s in (v for v in SCRIPTS.values() if v["language"] == lang):
            lines += [f"## {s['id']}  ({s['label']}: {s['scenario']}{', hard case' if s['hard'] else ''}; {s['split']})", "", s["text"], ""]
        (folder / f"{lang}.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    import sys

    out = sys.argv[1] if len(sys.argv) > 1 else "eval/scripts"
    write_sheets(out)
    print(f"Wrote reading sheets to {out}")
