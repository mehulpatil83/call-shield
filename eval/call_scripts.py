"""Acted English call scripts for the phone-to-laptop demo (20 scripts: 10 dev, 10 test). All texts are fictional.

HONEST EVALUATION: the same author wrote these scripts and the word lists, so the numbers are optimistic. They show
that the lists behave sensibly on varied wording, not how they behave on strangers' real calls. Rules for use:
  * Tune the word lists on DEV scripts (and on real transcripts) only.
  * TEST scripts are for the final numbers: run them once with --i-am-done-tuning.
"scam" = a fraud attempt; "benign" = an ordinary call; hard=True = a legitimate call that sounds suspicious.
Read each aloud once at normal speed. Never add real names, numbers or accounts."""
from __future__ import annotations

CALLS: dict[str, dict] = {}


def add(id: str, label: str, scenario: str, split: str, text: str, hard: bool = False) -> None:
    CALLS[id] = {"id": id, "label": label, "scenario": scenario, "split": split, "hard": hard, "text": text}


# ------------------------------------------------------------------------------------------------ DEV
add("c-s1", "scam", "fake fraud department: suspicious activity, token read-back", "dev",
    "Good afternoon, I am calling from the fraud prevention team. We have detected suspicious activity on your debit card "
    "ending four four one nine. Two unauthorised charges were flagged less than ten minutes ago. I need to verify your "
    "identity before I can stop them. I am sending a secure authorisation token to your phone right now, please read that "
    "six digit code back to me so I can cancel the payment.")
add("c-s2", "scam", "RBI safe account transfer", "dev",
    "This is an officer from the Reserve Bank cyber cell. Your savings account has been compromised and hackers are trying "
    "to withdraw your money tonight. To protect your funds you must move your money to a safe account that I will give you. "
    "Do not tell your family or the bank staff about this call.")
add("c-s3", "scam", "remote access refund", "dev",
    "Hello sir, we are processing your refund for the mobile plan. To complete it please install the QuickSupport app and "
    "share your screen with me. Once the app opens, read me the code on the screen so I can start the remote session.")
add("c-s4", "scam", "courier customs fee", "dev",
    "Your courier parcel is held at customs. To release it you need to pay the clearance fee today. I am sending a payment "
    "link, click the link and pay the amount, otherwise legal action will be taken and the parcel will be destroyed.")
add("c-s5", "scam", "lottery processing fee", "dev",
    "Congratulations, you have won the national mobile lottery. To receive your prize you only need to send the processing "
    "fee by UPI right now. Keep this confidential until the money reaches your account.")
add("c-b1", "benign", "friends planning lunch", "dev",
    "Hi, are we still meeting for lunch at one? I will bring the notes from class. Let me know if the cafe is too crowded "
    "and we can go somewhere else. See you soon.")
add("c-b2", "benign", "bank awareness message", "dev",
    "This is a reminder from your bank. Never share your OTP, PIN or password with anyone, even if they say they are "
    "calling from the bank. If someone asks, hang up and call the number on your card.")
add("c-b3", "benign", "doctor appointment", "dev",
    "Hello, this is the clinic. Your appointment is tomorrow at four in the afternoon. Please bring your earlier reports. "
    "If you need to move it, call us back on the clinic number.")
add("c-h1", "benign", "courier at the door asks for the delivery code", "dev",
    "Hello, I am the delivery executive and I am outside your building with your order. Please share the delivery code "
    "from your order app so that I can hand over the parcel.", hard=True)
add("c-h2", "benign", "genuine bank call, customer calls back", "dev",
    "Hello sir, this is your bank. We saw a payment on your card that looks unusual. Was it you? If not, please call the "
    "number printed on the back of your card. We will never ask for your OTP or PIN.", hard=True)

# ------------------------------------------------------------------------------------------------ TEST (run once at the end)
add("c-s6", "scam", "bank impersonation: card blocked and OTP", "test",
    "Hello, I am calling from your bank's security desk. Your card has been used for an unauthorised payment and it will be "
    "blocked today. To keep it active, tell me the verification code that just arrived on your phone.")
add("c-s7", "scam", "tax department threat", "test",
    "This is the income tax department. There is a case against you for unpaid tax and you will be arrested tonight. To "
    "settle it immediately, transfer the amount to the account number I give you and do not speak to anyone about this.")
add("c-s8", "scam", "tech support virus alert", "test",
    "I am calling from Windows support. Your computer is sending out a virus alert and your bank details are at risk. Please "
    "download AnyDesk right now so that I can connect to your computer and remove it.")
add("c-s9", "scam", "relative in trouble", "test",
    "Hello uncle, it is me. I am in trouble and I need money urgently, please send two thousand rupees to this number right "
    "now. Do not tell anyone in the family.")
add("c-s10", "scam", "KYC expiry", "test",
    "Dear customer, your KYC has expired and your account will be suspended within one hour. To update it, please confirm "
    "your card number and the six digit OTP you will receive.")
add("c-b4", "benign", "family dinner plans", "test",
    "Hi mom, I will reach home by eight. Can you keep the dinner warm? I also need to pick up the books from the shop on "
    "the way, so do not wait for me.")
add("c-b5", "benign", "colleagues about a meeting", "test",
    "Hey, can we move the project meeting to Thursday? The client wants to see the demo before the weekend. I will send the "
    "slides tonight so you can go through them.")
add("c-b6", "benign", "telecom plan information", "test",
    "Hello, this is a call about your mobile plan. Your current pack ends on Sunday and a new pack with more data is "
    "available. You can recharge from the app whenever you like. Thank you.")
add("c-h3", "benign", "real bank officer asks the customer to visit the branch", "test",
    "Good morning, I am calling from your bank branch. Your debit card is ready for collection. Please visit the branch with "
    "your identity proof and the receipt. We do not ask for any codes over the phone.", hard=True)
add("c-h4", "benign", "friend asks to read back the lock code", "test",
    "Hey, I forgot the door code for the guest room. Can you tell me the four digit code you set last week? I am standing "
    "outside and my hands are full.", hard=True)


def by_split(split: str) -> list[dict]:
    return [s for s in CALLS.values() if s["split"] == split]
