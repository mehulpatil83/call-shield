"""Transcripts used by the tests. SCAM cases must reach 'high', BENIGN cases must stay 'low',
HARD cases are legitimate calls that look suspicious: they document a known limitation."""

SCAM = {
    "en_scam": "Hello sir, I am calling from your bank's security department. Your account will be blocked today unless you verify your details right now. Please share the six digit OTP that you just received on your phone. My employee ID is four seven two nine one zero, and the reference number is two zero five eight.",
    "hinglish_scam": "Hello sir, main aapke bank se bol raha hoon. Aapka KYC update pending hai, isliye aapka account aaj raat tak block ho jayega. Please apne phone par jo OTP aaya hai woh mujhe abhi bataiye, six digit code, ek do teen char paanch chhe. Agar verify nahi kiya toh account freeze ho jayega.",
    "hinglish_scam_deva": "हेलो सर मैं आपके बैंक से बोल रहा हूँ आपका के वाई सी अपडेट पेंडिंग है इसलिए आपका अकाउंट आज रात तक ब्लॉक हो जाएगा प्लीज़ अपने फ़ोन पर जो ओटीपी आया है वह मुझे अभी बताइए सिक्स डिजिट कोड एक दो तीन चार पाँच छह",
    "mr_scam": "नमस्कार मी तुमच्या बँकेतून बोलतोय तुमचे केवायसी अपडेट बाकी आहे त्यामुळे आज रात्रीपर्यंत तुमचे खाते बंद होईल कृपया तुमच्या फोनवर आलेला ओटीपी मला सांगा सहा अंकी कोड एक दोन तीन चार पाच सहा जर तुम्ही आत्ताच पडताळणी केली नाही तर खाते गोठवले जाईल",
    "en_exec": "Hi Rahul, it's Anil. I'm in a board meeting and can't talk. I need you to process an urgent transfer of two lakh rupees to a vendor, right now. No, skip the portal, there's no time. Don't tell anyone, this is confidential. I'm the CFO. Just do it and confirm back in ten minutes.",
    "hinglish_remote": "Hello sir, main Microsoft security team se bol raha hoon. Aapke laptop mein virus aa gaya hai. Aap abhi AnyDesk app download kijiye, main remotely fix kar dunga. Jo nine digit code screen par aaye woh mujhe bataiye. Aur kisi ko mat batana, warna account freeze ho jayega.",
    "mr_electricity": "नमस्कार मी वीज वितरण कार्यालयातून बोलतोय तुमचे मागील महिन्याचे बिल थकले आहे आज रात्री नऊ वाजेपर्यंत पैसे भरले नाहीत तर तुमचे वीज कनेक्शन तोडले जाईल मी तुम्हाला एक लिंक पाठवतो त्यावर तुमचा यूपीआय पिन टाका आणि दोन हजार रुपये भरा फोन ठेवू नका लगेच करा",
}
BENIGN = {
    "en_benign": "Hello, this is a reminder from your bank. For your safety, please never share your OTP, PIN or password with anyone, including bank staff. If you receive a call asking for these details, hang up and call the number printed on the back of your card. Your complaint reference number is three eight one five.",
    "hinglish_benign": "Namaste, yeh aapke bank ki taraf se ek reminder hai. Kripya apna OTP, PIN ya password kisi ke saath share na karein, bank kabhi phone par OTP nahi maangta. Agar koi aisa call kare toh phone kaat dijiye aur card ke peeche likhe number par call kijiye.",
    "mr_benign": "नमस्कार ही तुमच्या बँकेकडून एक आठवण आहे कृपया तुमचा ओटीपी पिन किंवा पासवर्ड कोणालाही सांगू नका बँक कधीही फोनवर ओटीपी विचारत नाही असा कोणताही फोन आला तर तो कट करा आणि कार्डच्या मागे दिलेल्या क्रमांकावर कॉल करा",
    "hi_genuine_alert": "Namaste sir, main aapke bank ke fraud monitoring desk se bol rahi hoon. Aapke card se chaar hazaar paanch sau rupaye ka transaction hua hai, kya yeh aapne kiya? Nahi, maine toh nahi kiya. Theek hai sir, hum card abhi block kar dete hain. Main aapse koi OTP ya PIN nahi maangungi. Naya card teen din mein aapke ghar aa jayega.",
    "mr_son_warns": "आई मी बोलतोय आत्ताच बँकेचा मेसेज आला का हो ओटीपी आला आहे कोणीतरी फोन करून तो विचारत होता आई तो कोणालाही सांगू नकोस बँक कधीच ओटीपी विचारत नाही ठीक आहे मी फोन कट केला",
    "mr_clinic": "डॉक्टर मला खूप थकवा जाणवतो आणि कधी कधी डोकेदुखी होते ठीक आहे आत्ता काळजी करू नका हा साधारण त्रास आहे रक्ताची तपासणी करू या रिपोर्ट आल्यावर पुढे काय करायचं ते सांगतो धन्यवाद डॉक्टर",
    "small_talk": "Hello, how are you? I wanted to ask whether you are free for dinner on Sunday. Let me know and I will book a table for four people.",
}
HARD = {
    # legitimate, but an OTP is requested: the engine should say 'elevated' (check who is asking), never 'high'
    "en_delivery_otp": "Hello ma'am, I'm the delivery executive with your parcel, I'm at your gate. The delivery OTP is on your app, please share it so I can hand over the parcel. It's four four one seven.",
}
