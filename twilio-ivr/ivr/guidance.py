"""Phase labels and phase-specific guidance from the `when-a-car-hits-you`
skill (Step 4). Shared by the IVR call flow (spoken back to the caller right
after the emergency check) and the emailed report (report.py).
"""

PHASE_LABELS = {"at_scene": "At the scene", "recent": "Within the last 24 hours", "later": "Days/weeks later"}

PHASE_GUIDANCE = {
    "at_scene": [
        "Call 911 and get a police report, no matter how minor this seems.",
        "Leave the scene undisturbed if you safely can.",
        "Don't say \"I'm fine\" — say \"I'm not sure yet, I need to be evaluated.\"",
        "Photograph everything: injuries, your bike or gear, the vehicle, plate, and the scene.",
        "Get witness names and phone numbers before they leave.",
        "Never negotiate with the driver. Get their information and stop there.",
        "When in doubt, go to the ER.",
        "Save GPS or fitness tracker data and any nearby camera footage before it's lost.",
    ],
    "recent": [
        "Get checked out at urgent care or the ER even if you feel fine — adrenaline masks injuries for 24 to 48 hours.",
        "Tell every provider you were struck by a motor vehicle, and when and where.",
        "Start a symptom and expense journal now.",
        "Notify your own insurance company and ask specifically about MedPay coverage.",
        "Make no statement to any insurance company until you've talked to a lawyer.",
        "Do not sign anything or accept any settlement offer.",
        "Stay off social media about this for the whole case.",
    ],
    "later": [
        "Don't accept an early settlement before reaching Maximum Medical Improvement.",
        "Personal injury attorneys work on contingency — a free consultation costs nothing.",
        "Track every expense: medical, transport, lost wages, repairs, and daily-life impact.",
        "Mental health treatment, including for PTSD, is legitimate and often reimbursable.",
        "MedPay and uninsured motorist coverage on your own auto policy protect you as a cyclist or pedestrian too.",
    ],
}
