/** Acted, fictional English scripts for the live demo. Read aloud at a normal speed; never add real details. */
export const DEMO_SCRIPTS: { id: 'scam' | 'scamShort' | 'friendly' | 'warning'; text: string }[] = [
  { id: 'scam', text: 'Good afternoon, I am calling from the fraud prevention team. We have detected suspicious activity on your debit card ending four four one nine. Two unauthorised charges were flagged less than ten minutes ago. I need to verify your identity before I can stop them. I am sending a secure authorisation token to your phone right now, please read that six digit code back to me so I can cancel the payment.' },
  { id: 'scamShort', text: "Hello sir, I am calling from your bank's security department. Your account will be blocked today unless you verify right now. Please share the six digit OTP that you just received." },
  { id: 'friendly', text: 'Hi, are we still meeting for lunch at one? I will bring the notes from class. Let me know if the cafe is too crowded and we can go somewhere else. See you soon.' },
  { id: 'warning', text: 'This is a reminder from your bank. Never share your OTP, PIN or password with anyone, even if they say they are calling from the bank. If someone asks, hang up and call the number on your card.' },
]
