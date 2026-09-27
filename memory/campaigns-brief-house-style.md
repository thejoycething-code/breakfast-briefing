---
name: campaigns-brief-house-style
description: How Christopher fills the CitizenGO Campaigns Brief sheet (learned 17 Sept 2026 from his 2024-25 assisted suicide and Aug 2026 Ofcom briefs); what the template's cells actually do
metadata:
  type: feedback
---

Christopher's briefs, not the generated ones, are the style to match. Read from
"2024-25 Combined EN GB Brief: No to Assisted Suicide" (his fullest) and the
Aug 2026 Caroline Farrow/Ofcom brief.

**Style (from 21 of his EN GB briefs, read 17 Sept 2026):** the Background
opens with the actor and the threat in one concrete sentence ("Labour MP Kim
Leadbeater is advancing a Private Member's Bill that would legalise assisted
suicide"; "The NHS has applied to the Court of Protection to remove life-saving
treatment"), then the process facts with dates and margins, then why it matters
and the numeric target ("we need just 28 MPs"). Moral framing is woven into the
description, never appended: "one of the most serious threats to the sanctity
of life since the Abortion Act 1967"; "effectively the NHS signing the young
person's death warrant". It is descriptive in shape but never neutral, and it
does NOT lead with a quote or overstate what a politician said. Never write as
though the other side's premise were legitimate: it is always "assisted
suicide" in our voice ("assisted dying" only inside a Bill or committee name),
and care is "the compassionate answer", never a step towards anything. For a
keep-your-promise campaign, describe what is happening first, then quote the
promise, then cite CitizenGO's standing (previous petition numbers), as in the
Paul Givan brief. Arguments and the injustice are numbered with short headings
and name the vulnerable people harmed; betrayal is a recurring motif ("That
betrayal of safeguarding is the heart of the injustice"). Dates read "21
September 2026". Language field: "English (United Kingdom). Use British
spelling and UK institutional terminology." Signers may differ per email.
Sources as "- Title [Outlet, date]: URL". Image spec starts "Text-free 16:9
editorial photograph" with an avoid-list. Notes carries "Draft for content
review" plus a calendar/duplicate check.

**Timeline uses the EN GB email codes:** L, L RT, RL1, RL1 RT, Nurture, Report
Back; parliamentary events get links; comments explain decisions. His run to
30+ rows, so insert rows (insertDimension, inheritFromBefore) rather than
squeeze into the template's 8.

**RF4:** he scores at Plan with paragraph comments; RF#4/2 is 0 unless losing
accelerates harm; 2024-25 Bill brief scored 1/3/4/3/0 = 11 win / 8 lose. The
TOTAL rows are formulas (=C32+C33+C34+C35 and ...+C36): write scores in C, never
the totals.

**Corrections he gave on 17 Sept:** never overstate a politician's position;
quote their own words ("he simply noted palliative care needed fixing").
Arguments need ideological as well as factual points. Injustice sections
should say the pro-life movement fights FOR families (end-of-life care,
babies), not only against assisted suicide and abortion. RF#1 is scored on the
nearest comparable campaigns with an asterisk for a new ask type; RF#4/2 is 0
whenever losing means the status quo resumes. He likes two-phase deliveries
(conference, then pre-Budget if it performs).

**Correction on 24 Sept (NCID brief):** a "reject/drop" campaign has ONE ask: drop it. Don't add fallback safeguards ("if you go ahead, then..."). They weaken the demand and read as accepting the premise.

**Template traps:** the timeline's Action is merged B:C and Comment D:G, so a
three-column write puts the comment in hidden C; write [date, action, "",
comment]. The label-driven publisher skips fields whose CSV value is empty, so
the RF#1 expectation rows never reach the sheet.

**Why:** "the same template we usually use" means his filled Sheets, not the
markdown or the generator's skeleton. **How to apply:** before writing a brief,
read one of his recent EN GB Brief sheets from Drive and mirror it.
See [[uk-campaign-calendar]], [[parl-monitor-drive-publish]].
