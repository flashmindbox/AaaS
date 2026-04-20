# Booth & Day-Of Checklist

Print this page. Tick every box. Do not improvise anything on this list — improvisation is what makes demos fail.

---

## T-minus 48 hours (two days before)

- [ ] Final commit merged to `main`. No half-built features on the demo branch.
- [ ] `pnpm install && pnpm dev` works from a clean clone on a machine that is **not** the presenter's laptop.
- [ ] Full-Vision demo rehearsed end-to-end, with a timer, twice.
- [ ] Foundation demo rehearsed end-to-end, with a timer, once.
- [ ] **Odia Scene 2 rehearsed with a native Odia speaker.** If the presenter is not a native speaker, the native speaker must sign off on the pronunciation of every demo phrase. Record a fallback audio clip.
- [ ] Screen-capture recording made of a successful Full-Vision run. Saved locally, not in the cloud.
- [ ] Backup laptop identified. Repo cloned onto it. `pnpm dev` confirmed working.
- [ ] QR code generated pointing to the repo. Printed. Three copies.
- [ ] Business cards / one-page flyers printed. **English + Odia bilingual.** Minimum 50 copies.
- [ ] Odia cue card printed (Scene 2 phrases in Odia script with transliteration).
- [ ] `PRESENTER_BRIEF.md` printed. Folded. In the presenter's pocket.

## T-minus 24 hours (day before)

- [ ] Laptop fully charged. Charger in the bag. Spare charger if available.
- [ ] External mic tested. Spare mic or headset in the bag.
- [ ] Laptop stand / riser if the booth surface is low — eye-level demos win.
- [ ] Two HDMI adapters. One USB-C to HDMI. One USB-C to VGA as legacy backup.
- [ ] Extension cord or power strip — booths never have enough outlets.
- [ ] Water bottle. Throat lozenges. Energy bars.
- [ ] Team t-shirts / branded clothing laid out, ironed.
- [ ] Route to venue confirmed. Backup route confirmed.
- [ ] Sleep. Seriously. A tired presenter loses every Q&A.

## T-minus 2 hours (arriving at venue)

- [ ] Setup booth. Laptop on stand, mic plugged in, power connected.
- [ ] Join venue Wi-Fi. Run a speed test. If < 5 Mbps, plan to demo on localhost.
- [ ] Start `pnpm dev` and leave it running. Do *not* restart it for demos.
- [ ] Open all required browser tabs in order. Pin them. Close every other tab.
- [ ] Open one terminal window, one code window, one browser window. Hide the dock / taskbar.
- [ ] Turn notifications OFF system-wide. Slack, email, calendar, iMessage, Discord, everything.
- [ ] Silence the phone. Put it face-down.
- [ ] Disable OS updates, screen-saver, screen-lock during the demo period.
- [ ] Set display scaling so the demo is readable from 2 metres away.
- [ ] Open the hidden recording tab — confirm it plays with sound.

## T-minus 30 minutes

- [ ] Final dry run of the full demo. If anything breaks, fall back to the Foundation track for the rest of the day.
- [ ] Test sound output at booth volume. Too quiet and judges lean in with strained faces; too loud and you annoy the neighbouring booth.
- [ ] Position QR code / flyers at the front edge of the table, angled toward approaching judges.
- [ ] Presenter drinks water, stretches, does three breaths.
- [ ] Team decides speaking order if multiple presenters.

## During each demo

- [ ] Stand up when a judge approaches.
- [ ] Hand them a card / point at the QR code within 20 seconds.
- [ ] Start with the hook, not the problem. Curiosity first, sermon second.
- [ ] Watch for boredom signs — crossed arms, looking past you. If they appear at 30 seconds, skip to the demo *immediately*.
- [ ] Never say "this is buggy" or "this didn't work earlier" even if it's true.
- [ ] End with an explicit ask. Always.
- [ ] Write down the judge's name + question in a notebook as soon as they walk away.

## Between demos

- [ ] Close any modal dialogs, stray windows, debug consoles.
- [ ] Reset the demo tabs to the opening state. Don't let a judge watch you scroll back up.
- [ ] Drink water. One sip, not a gulp.
- [ ] If you've repeated the demo five times, ask a teammate to swap in. Energy matters.

## End of day

- [ ] Collect every business card / note from every judge interaction.
- [ ] Type up the Q&A notebook into a shared team doc, same evening, before sleep.
- [ ] Patch the single most embarrassing demo hiccup before tomorrow.
- [ ] Charge the laptop to 100% overnight.

---

## What to pack — the physical list

Tick each item into a bag the night before.

**Electronics**
- [ ] Primary laptop + charger
- [ ] Backup laptop + charger (if available)
- [ ] Phone + charger + power bank
- [ ] External mic + USB adapter
- [ ] In-ear headphones
- [ ] HDMI cable + USB-C to HDMI adapter + VGA adapter
- [ ] Extension cord / 4-way power strip
- [ ] Laptop stand or riser
- [ ] Mouse (booth surfaces are often too small for trackpad)

**Paper**
- [ ] 50× flyers / one-pagers (English + Odia, back-to-back)
- [ ] 50× business cards
- [ ] 3× printed `PRESENTER_BRIEF.md`
- [ ] 3× printed QR codes on stiff card
- [ ] 1× Odia cue card (Scene 2 phrases + transliteration)
- [ ] 1× notebook + 2× pens for capturing judge questions

**Human supplies**
- [ ] Water bottle (refillable)
- [ ] Energy bars
- [ ] Throat lozenges / spray
- [ ] Deodorant (long day, hot room)
- [ ] Tissues / handkerchief
- [ ] Team t-shirts / branded attire
- [ ] Jacket (venues over-AC)
- [ ] Comfortable shoes

**Boring but critical**
- [ ] Venue entry pass / registration confirmation
- [ ] Photo ID
- [ ] Printed schedule with session times highlighted

---

## Fallback plans — decide the trigger in advance

| If this happens | Trigger immediately |
|---|---|
| Wi-Fi flaky | Switch to localhost. Announce: *"We're running on-prem — which is the point."* |
| Demo crashes mid-scene | Switch to recorded tab. One sentence: *"Let me show you the scripted run."* |
| AI service slow / timing out | Same as above. Do not debug. |
| Laptop crashes | Hand out one-pager. Pitch verbally. Pivot to backup laptop. |
| Mic fails | Type Odia input instead. Say "Odia typed input works the same way." |
| Native Odia speaker absent | Play pre-recorded Odia sample during Scene 2. Never attempt unfamiliar Odia pronunciation live. |
| Judge interrupts with a tough question | Pause the demo. Answer briefly. Ask *"shall I continue the demo or go deeper here?"* |
| You blank on a number | Flip open the printed brief. Say *"I want to be precise — one second."* |
| You blank on the next scene | Stop. Take a breath. *"Let me reset — the next thing to show is…"* Judges forgive this. |
| Someone asks for something we haven't built | *"That's in Phase [X]. Let me walk you through the plan."* Pull up PLAN.md. |

---

## What judges remember

After a day of 40 booths, judges remember three things from a good booth:

1. **A specific user story.** "The blind Odia-speaking student filling the Utkal admission form" sticks. "An AI accessibility platform" does not.
2. **A visible, honest demo.** One thing that works, shown confidently, beats five things that sort-of-work. Odia working live trumps Hindi working live, at an Odisha event.
3. **A specific ask.** "Can you introduce us to OCAC or the 5T cell?" is memorable. "We'd love feedback" is not.

Design every interaction around planting those three things.

---

## After the hackathon

- [ ] Email every judge who left a card within 48 hours. Reference a specific thing they said.
- [ ] Public thank-you on the repo to any organisation / mentor who gave time.
- [ ] Write up lessons learned — what worked in the demo, what didn't.
- [ ] Update `DEMO_SCRIPT.md` with the real timings observed in the field.
- [ ] Keep shipping. The hackathon is a milestone, not the finish line.
