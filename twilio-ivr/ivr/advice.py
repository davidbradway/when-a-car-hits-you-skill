"""Spoken guidance for callers, based on Ann Groninger's guidance for what to
do after a car hits you while biking, walking, or running.
"""

NC_ADVICE = (
    "North Carolina is special. It is one of only four states with pure contributory negligence, "
    "which means that if you are found even one percent at fault, you may not be able to recover "
    "anything. Because of this, rule number one is: do not speak with any insurance company before "
    "first speaking with an experienced bicycle lawyer. That includes the driver's insurance and "
    "your own insurance representative. "
    "A few other important rules. Use your health insurance at the hospital. "
    "Do not give your motor vehicle insurance information to any medical providers. "
    "Do not give motor vehicle liability information to your health insurance or disability "
    "provider without checking with your lawyer first, since some plans require it and it can be "
    "tricky. And if you have auto insurance, your policy likely has med pay coverage. Use that "
    "after your health insurance processes the bills."
)

GENERAL_ADVICE = (
    "Here is some general guidance for after a crash. There are very few rules that apply "
    "everywhere, and advice you find online may not match the law where you are, so it's important "
    "to speak with an experienced bicycle lawyer licensed in your state. "
    "Report the crash, wait for police, and insist on a crash report. "
    "Gather information if you can, including witness contact information and photos of the "
    "vehicles and the scene. If possible, do not move vehicles or debris until police document the "
    "scene. If you get the chance to talk with police, tell them what happened, but don't try to "
    "give precise times and distances, because you will likely get them wrong. "
    "Get immediate medical attention for your injuries. "
    "Avoid posting on any social media. "
    "Preserve any recordings of your ride, such as Strava, Garmin, or video. "
    "Do not speak with any insurance adjuster without first speaking with an experienced bicycle "
    "lawyer. "
    "Do not repair or dispose of your bike, or any other damaged property, until your lawyer says "
    "it's okay to. "
    "Take photos of all of your injuries, even minor ones — sometimes a bruise is not just a "
    "bruise. "
    "And track your losses, including lost income, lost business opportunities, and trips you paid "
    "for but couldn't take."
)

GOODBYE = "Take care of yourself. Goodbye."

TRANSFER_NUMBER = "+19198994078"
TRANSFER_SAY = "Connecting you now to the Law Office of Johnson and Groninger, P L L C."


def advice_for(in_nc: bool) -> str:
    if in_nc:
        return NC_ADVICE + " " + GENERAL_ADVICE
    return GENERAL_ADVICE
