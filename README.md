# When a Car Hits You — Claude Agent Skill

[![Agent Skills](https://img.shields.io/badge/Agent%20Skills-Claude%20%2F%20Codex-6366f1)](https://agentskills.io)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![The White Line](https://img.shields.io/badge/Source-The%20White%20Line-black)](https://www.thewhiteline.org/pages/tools)

A trauma-informed, AI-powered guide for cyclists, pedestrians, and vulnerable road users after being hit by a car. Based on [*When a Car Hits You*](https://www.thewhiteline.org/pages/tools) by The White Line (Jill & Michael White).

---

## What It Does

When activated, Claude becomes a calm, knowledgeable guide that:

- **Detects the user's phase** — at the crash scene, within 24 hours, or days/weeks later — and tailors guidance accordingly
- **Asks focused questions** one or two at a time to understand the user's specific situation
- **Flags emergencies** immediately if serious symptoms are mentioned (loss of consciousness, confusion, vomiting, severe headache)
- **Provides actionable, phase-appropriate steps** grounded in the source guide
- **Builds a structured crash summary report** including completed steps, urgent flags, next steps, expenses to track, and ready-to-use word-for-word scripts
- **Sends the summary by email** on request via Gmail integration

---

## Example Trigger Phrases

Claude will load this skill automatically when context matches. Example phrases that trigger it:

- *"I was just hit by a car while cycling"*
- *"A car hit me while I was walking — what do I do?"*
- *"I was in a bike crash yesterday, what should I do now?"*
- *"What do I do after being hit by a car?"*
- *"A driver hit me and drove off"*

---

## Installation

### Claude.ai (Pro, Max, Team, or Enterprise)

1. Download this repository as a ZIP (`Code → Download ZIP`)
2. Go to **Settings → Features → Skills** in Claude.ai
3. Upload the ZIP file
4. Skills are enabled — start a new conversation and describe your crash

> Requires code execution to be enabled on your plan.

### Claude Code

Copy the skill folder to your personal skills directory:

```bash
# Personal (available across all projects)
cp -r skills/when-a-car-hits-you ~/.claude/skills/

# Or project-scoped (shared via git)
cp -r skills/when-a-car-hits-you .claude/skills/
```

Then restart Claude Code. Invoke with `/when-a-car-hits-you` or just describe the situation.

### Claude API

```python
import anthropic
import base64, zipfile, io

client = anthropic.Anthropic()

# Zip the skill folder
buf = io.BytesIO()
with zipfile.ZipFile(buf, 'w') as zf:
    zf.write('skills/when-a-car-hits-you/SKILL.md',
             'when-a-car-hits-you/SKILL.md')
buf.seek(0)

# Upload the skill
skill = client.beta.skills.upload(
    name="when-a-car-hits-you",
    file=("when-a-car-hits-you.zip", buf, "application/zip")
)

# Use it in a message
response = client.beta.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=1024,
    skill_ids=[skill.id],
    messages=[{"role": "user", "content": "I was hit by a car while biking. What do I do?"}]
)
```

---

## Instructions for usage

1. Install the Claude app on your phone
2. Use the Claude Voice Conversation once to allow permission to the microphone
3. Open the Shortcuts app on iPhone (or similar on Android):
  1. Create a Shortcut to the Claude Voice Conversation
  2. Name this Shortcut “A Car Hit Me”
  3. Make a duplicate and name it “I Was Hit By a Car”
  4. Create an Automation inside the Shortcuts app
    1. Select “Run Immediately”
    2. Use the condition “When a NFC tag is detected”. (I named my tag “Collision”)
    3. Make it Do one of the shortcuts defined above
  5. Stick the NFC tag to your helmet or bike frame
4. Launch the Voice Conversation mode of Claude:
  1. Either touch the top back of your phone to the NFC tag
  2. Or use Siri:
    1. You can hold down the Siri button (power button) or say *“Hey Siri”*
    2. Then say either shortcut name: “*A Car Hit Me”* or “*I Was Hit By a Car”*
5. Once in the Claude Voice Conversation say something like:
  1. *"I was just hit by a car while cycling, can you help me prepare a report?"*
  2. *"A car hit me while I was walking; what do I do?"*
  3. *"I was in a bike crash yesterday, what should I do now?"*
  4. *"What do I do after being hit by a car?"*
6. When you are done, ask for a draft of the report. If you have Gmail connected it will end up in your drafts folder.

---

## Skill Output: Crash Summary Report

After gathering information, Claude produces a structured report including:

| Section | Contents |
|---|---|
| Crash Details | Date, location, mode of travel, driver insurance status |
| Scene Checklist | Police report, photos, driver info, witnesses, medical care |
| Injuries & Symptoms | All reported symptoms with notes on delayed presentation |
| 🔴 Urgent Flags | Critical steps not yet taken, in priority order |
| Next Steps | 2–3 specific, personalized actions to take right now |
| Completed Steps | What the user has already done |
| Expenses to Track | Medical, transport, lost income, property, daily life |
| Scripts | Exact words to use with police, insurance, employer, family |

---

## Key Guidance Encoded in This Skill

All guidance is drawn directly from the [White Line source guide](https://www.thewhiteline.org/pages/tools):

- **Never say "I'm fine"** — say *"I'm not sure yet. I need to be evaluated."*
- **Always say "crash," never "accident"** — crashes have causes; accidents don't
- **Call 911 after every crash** — even if it seems minor; no report = no record
- **Adrenaline masks injuries for 24–48 hours** — get checked out even if you feel fine
- **MedPay and UM/UIM on your auto policy cover you as a cyclist or pedestrian**, not just as a driver
- **Don't give recorded statements** to the other driver's insurance company
- **Don't accept early settlement** before reaching Maximum Medical Improvement (MMI)
- **Social media silence** starts immediately and lasts the entire case
- **PTSD affects 17–30% of crash survivors** — mental health treatment is legitimate and often reimbursable
- **Personal injury attorneys work on contingency** — free consult, no upfront cost

---

## Source & Citation

This skill is based on:

> White, Jill and Michael. *When a Car Hits You: A guide for cyclists, pedestrians, and vulnerable road users after a "minor" crash.* The White Line, April 2026. https://www.thewhiteline.org/pages/tools

The White Line was founded by Jill and Michael White after their son Magnus was killed by a driver while cycling in July 2023. This guide and this skill are dedicated to his memory.

**This skill is not legal, medical, or financial advice.** Laws vary by state and jurisdiction. Always consult qualified professionals for guidance specific to your situation.

---

## Additional Resources

| Resource | Link |
|---|---|
| The White Line (source guide) | https://www.thewhiteline.org/pages/tools |
| Anthropic Agent Skills docs | https://docs.claude.com/en/agents-and-tools/agent-skills/overview |
| Agent Skills open standard | https://agentskills.io |
| Agent Skills marketplace | https://skillsmp.com |
| Official Anthropic skills repo | https://github.com/anthropics/skills |
| Crisis support (988 Lifeline) | https://988lifeline.org |
| Crisis Text Line | Text HOME to 741741 |
| CounterForce Health (insurance appeals) | https://counterforcehealth.com |

---

## License

Apache 2.0 — see [LICENSE](LICENSE).

Skill content is based on the White Line guide, shared here for public benefit with attribution. The White Line guide itself is © Jill & Michael White / The White Line.

---

## Contributing

Issues and pull requests welcome. If you have suggestions for improving the guidance, phrasing, or structure — especially from lived experience as a crash survivor — please open an issue.
