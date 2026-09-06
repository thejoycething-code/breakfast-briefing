#!/usr/bin/env python3
"""Group a sweep's candidates into the seven briefing sections.

fetch_feeds.py emits 450-650 candidates grouped by *source*, which is expensive to read
and organised the wrong way round for curation. This assigns each item to a briefing
section and prints them section by section, numbered, so the digest step can pick items
by index and compose.py can copy the fields verbatim.

Assignment is by priority, not by first match:
  - the five specific sections win first (persecution, speech, family, gender, life)
  - Church & Society is the residual faith bucket
  - Other is the residual interest bucket - matched nothing, survived chaff suppression

Usage:
    python3 fetch_feeds.py --json today.json > sweep.txt
    python3 shortlist.py today.json                 # all candidates
    python3 shortlist.py today.json --per-section 40 # cap each section
    python3 shortlist.py today.json --show-chaff     # audit what was suppressed
"""

import argparse
import collections
import json
import math
import os
import re
import sys
import unicodedata  # fold accents before tokenising - see _deaccent()

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import regions
import fetch_feeds   # url_key + fetch_lede, for the sheet's bounded lede fetch
import textsignals   # report-vs-comment and friends, read off the article opening
import history      # what actually appeared in recent editions, for the cross-day repeat check

HERE = os.path.dirname(os.path.abspath(__file__))

# Hours the sweep looked back - 36 normally, 84 on Mondays. importance() scales its age
# thresholds by this, so set it from the sweep JSON's "window_hours" before scoring
# (main() here and compose.py both do). The default keeps synthetic tests on 36h behaviour.
SWEEP_WINDOW_H = 36

# ---------------------------------------------------------------------------
# Sections, in the order they appear in the briefing.
# Each entry: (weight, pattern). Weights let a strong signal beat a weak one when an
# item matches more than one section - "puberty blockers" is Gender, not Family, even
# though it mentions children.
# ---------------------------------------------------------------------------
SECTIONS = [
    ("Religious Freedom & Persecution", [
        (5, r"persecut|martyr|anti-conversion|forced conversion|apostas"
            r"|blasphem|religious (freedom|liberty|hatred|discrimination|persecution|test)"
            # "religious test" added 25.08.2026: National Review's "Virginia's 'Religious Test'
            # for College Students Is Unconstitutional" scored nothing here and fell to the
            # Church & Religion catch-all on the word "religious" alone - landing it in a
            # different section from the ADF release it was arguing about, which is what made
            # pairing the two by hand hard. A religious test is a liberty question by
            # definition; the phrase has no other use.
            r"|freedom of religion|\bFoRB\b|conscientious objection"),
        (4, r"church (attack|burn|bomb|raid|demolish|clos)|attack on (a )?church"
            r"|christians? (killed|kidnapp|abduct|jailed|imprison|arrest|detain|shot)"
            r"|(kill|murder|massacr|abduct|kidnap|behead|slaughter)\w*\b.{0,30}"
            r"(christian|catholic|worshipper|churchgoer|believer)s?"
            r"|(pastor|priest|bishop|nun|imam|convert)s? (jailed|arrested|sentenced|killed|abducted|detained)"),
        # "Islamic/sharia/morality police" and "hisbah" are what these forces are actually
        # called in the reporting; only "religious police" was listed. And the arrest verbs
        # were written one way round - "convert arrested" matched, "arresting a convert" did
        # not - so CNA's Nigerian Hisbah story scored 2 for Religious Freedom and landed in
        # Marriage, Family & Education on the words "marriage refusal" (found 17.08.2026).
        # Sabbath observance and religious-accommodation cases had no vocabulary at all: a
        # Forest Service officer winning an exemption from Sunday working reached no section
        # on 19.08.2026, though it is a textbook religious-liberty win.
        (5, r"sabbath|(religious|sunday|sabbath) (exemption|accommodation|observance)"
            r"|exemption from working|refus\w+ to work on (sunday|the sabbath)"),
        # Chris, 27.08.2026: four persecution stories filed as Church & Religion. Each was a
        # shape the vocabulary above did not have.
        #
        # 1. A believer already in custody, waiting on the court. The verbs at (4) are all
        #    about the MOMENT of arrest - jailed, detained, sentenced - so a story about
        #    what happens next scored nothing ("China's 'Zion 8' church leaders awaiting
        #    verdicts"). "Underground church" is added alongside it: the word exists in
        #    English almost solely to describe a church the state has driven out of sight.
        (5, r"underground church|house church(es)? raid"
            r"|(church|christian|pastor|priest|bishop|nun|convert|believer)\w*\b.{0,40}"
            r"(awaiting|await|face[sd]?) (a )?(verdict|verdicts|trial|sentencing|retrial)"
            r"|(verdict|sentencing|trial) .{0,30}(pastor|priest|bishop|church leaders?)"),
        # 2. A named group attacking a religious community. (4) covers killing and kidnapping
        #    but not the slower kind - Word&Way's "Settler Attacks Threaten the West Bank's
        #    Final Christian Village" is intimidation and land seizure, and read as ordinary
        #    church news. Anchored to the ATTACKER, not to the bare word "attack", which is
        #    far too common to key a section on.
        (5, r"(settler|mob|militant|extremist|gunmen|jihadist|islamist|insurgent|vigilante"
            r"|hardline|nationalist|bajrang dal|boko haram|fulani)\w*\s+"
            r"(attack|attacks|violence|raid|raids|mob)"
            r"|attacks?\b.{0,40}(christian|catholic|worshipper|churchgoer|believer|convert)"
            r"s?\s+(village|community|town|quarter|neighbourhood|neighborhood)"),
        # 3. A state refusing a believer entry. The Rasanen visa story ("the UK bars Christian
        #    MP") is a government acting against someone for their faith, which is this beat
        #    exactly, but no pattern here described a border rather than a jail.
        (5, r"(bar|bars|barred|ban|bans|banned|refus\w+|denie[sd]|revok\w+|cancel\w+)"
            r"\b.{0,30}(christian|catholic|muslim|jewish|pastor|priest|bishop|imam|rabbi"
            r"|missionary|evangelist)\w*\b.{0,30}\b(visa|entry|\bETA\b|conference|from entering)"
            r"|(bars?|barred|denie[sd]|refus\w+)\s+(a\s+|the\s+)?(christian|catholic|muslim"
            r"|jewish)\s+(mp|senator|lawmaker|politician|pastor|priest|bishop|speaker)"),
        # Chris, 20.08.2026: "the ADF release should be in religious freedom". A
        # religious-liberty CASE carries none of the persecution vocabulary above - nobody is
        # killed, jailed or attacked - so "Christian employers free to conduct business
        # consistent with their faith" scored 0 here and lost to Church & Religion on the bare
        # word "Christian". Persecution and religious liberty are one beat; only the forum
        # differs. These are the case SHAPES, so a newsroom write-up lands with the release.
        (5, r"(consistent with|in accordance with|in line with|according to)\s+"
            r"(their|his|her|its)\s+(faith|belief|beliefs|conscience|religion)"
            r"|free to (operate|conduct business|practi[cs]e|serve)"
            r"|(denied|refused|excluded|barred|disqualified|penalis\w+|penaliz\w+)"
            r"\w*\b.{0,30}(for|over|because of)\b.{0,24}(religio|faith|belief)"
            r"|(religious|faith-based) (employer|business|charity|school|hiring|college)"
            r"|houses? of worship|place of worship"
            r"|ministerial exception|church autonomy"),
        (5, r"chaplain\w*\b.{0,40}(denied|discriminat|barred|excluded|refused|removed)"
            r"|(denied|discriminat|barred|excluded|refused)\w*\b.{0,40}chaplain"
            r"|religious (harassment|discrimination|coercion|intimidation)"
            r"|(harass|assault|spit|attack)\w*\b.{0,25}(nuns?|monks?|clergy|priests?|imams?)"
            # Chris, 17.08.2026: "This harassment is more of a persecution / freedom story."
            # A whole community living under harassment is the persecution beat even when no
            # single incident is reported and no cleric is named.
            r"|(christians?|believers?|worshipp\w+|minority|minorities)\b.{0,40}"
            r"(harassment|harassed|intimidat\w+|under (attack|siege|pressure))"
            r"|(rising|growing|increasing) (harassment|hostility|intimidation|persecution)"
            r"|freedom from religion|first amendment.{0,30}religio"
            r"|conscience (clause|protection)|religious (test|litmus test) for"
            # Military chaplaincy is a religious-liberty beat almost by definition. The
            # Washington Post ran "Virginia is putting military chaplains in an impossible
            # position", which carries no discrimination verb for the rule above to catch.
            r"|military chaplain|chaplaincy"),
        (3, r"(religious|islamic|sharia|morality) police|\bhisbah\b"
            r"|(arrest|detain|jail|imprison|sentenc|convict)\w*\b.{0,25}"
            r"(christian|convert|pastor|priest|worshipp|churchgoer|believer)"
            r"|convert\w*\b.{0,20}from islam|left islam"
            r"|religious (police|minorit)|conversion (ban|law)|worship ban|underground church"
            r"|house church|bible (ban|smuggl)|missionar"
            r"|religious exemption|(fired|sacked|dismissed|disciplin)\w*.{0,40}"
            r"(refus\w+|conscience|belief|religio|faith)"),
        (2, r"^(?=.*(christ|church|catholic|priest|pastor|bishop|missionar|convert|believer"
            r"|muslim|islam|hindu|sikh|jewish|faith|religio|worship|blasphem|persecut"
            r"|martyr|chapel|mosque|temple|monk|nun\b|preacher|gospel|bible))"
            r"(?=.*(nigeria|pakistan|india|china|sudan|iran|iraq|syria|afghanistan|vietnam"
            r"|north korea|eritrea|algeria|egypt|bangladesh|myanmar|nicaragua|cuba"
            r"|west bank|indonesia|turkey|belarus))"),
    ]),
    ("Free Speech & Civil Liberties", [
        # free[- ]speech: the space-only form missed "Free-Speech Concerns", which is how a
        # South Korean internet-law story reached no section on 19.08.2026 - a free speech
        # item that failed the free speech pattern on a hyphen.
        (5, r"free[- ]speech|freedom of (speech|expression)|censor|deplatform|no.platform"
            r"|hate speech|non-crime hate|speech police|online safety act|\bOfcom\b"
            r"|academic freedom|press freedom|chilling effect|prior restraint"
            # The French Constitutional Council struck the under-15 social media ban down on
            # free-expression grounds. Jurist's headline says "free speech" so it classified;
            # POLITICO's says only "French court blocks social media ban for under 15s" and
            # fell to Other. Chris, 17.08.2026: the ruling "should have stood as a free speech
            # issue" - so the subject matter has to carry it, not the wording of one headline.
            r"|social media ban|age verification|online safety|digital id"
            r"|(block|strike|struck|overturn)\w*\b.{0,24}(ban on|ban for|speech|expression)"),
        # Verbs and objects both widened 20.08.2026. Chris moved The Federalist's UK
        # speech-ban story to Free Speech; the Daily Wire's version of the same story
        # ("Politician Punished For Christian Beliefs Targeted Again") scored nothing here
        # because "punished" was not a verb and "beliefs" not an object, so it sat in Church
        # & Religion. The object may now be preceded by up to three words, since the real
        # phrasing is "for CHRISTIAN beliefs", not "for beliefs".
        #
        # This does not swallow persecution: a headline naming one of the countries in the
        # Religious Freedom block scores 8 there against 4 here, and classify takes the
        # highest-scoring specific section.
        (4, r"(arrest|question|visit|charg|convict|sack|fir|punish|ban|barr|prosecut"
            r"|fine|silenc)\w*( \w+){0,3} (over|for)( \w+){0,3} "
            r"(post|tweet|comment|joke|remark|sermon|placard|prayer|leaflet"
            r"|belief|view|opinion|speech|preaching)s?\b"
            r"|debank|silenc\w+ (critic|journalist)|gagging|super.?injunction"
            r"|cancel culture|cancelled for|misgendering (arrest|conviction|case)"),
        (6, r"^(?=.*blasphem)(?=.*(fined|convict|prosecut|charged|arrest|posts?\b|tweet"
            r"|comments?\b|offensive|social media|free speech|policeman|police officer))"
            r".*blasphem"),
        # Satire is only a free speech signal when someone is suing or banning over it -
        # bare "satire" is an arts tag (see CATEGORY_DROP), so both directions are anchored
        # to a legal verb. The Babylon Bee's suit over New Mexico's satire disclaimer had no
        # section on 19.08.2026.
        (3, r"satir\w+.{0,25}(disclaimer|lawsuit|sues?\b|ban\b|law\b|prosecut|fine)"
            r"|(sues?|suing|lawsuit|banned?|prosecut\w+).{0,25}satir"
            r"|speech (law|bill|code|ban)|blasphemy law|libel|defamation|thought crime"
            r"|buffer zone (arrest|conviction)|silent prayer|street preacher"
            r"|banned from|investigat\w+ (by|over) (Ofcom|the regulator)"),
        (5, r"digital id|digital identity|\bCBDC\b|central bank digital"
            r"|online safety act|age verification|age assurance|encryption backdoor"
            r"|facial recognition|live facial|biometric|(mass|total|state) surveillance"
            r"|surveillance state|snoopers'? charter"
            r"|investigatory powers|debank|de-?bank|payment (processor|denial)"
            r"|social credit|vaccine passport|covid pass|\bID cards?\b"),
        (2, r"\bwoke\b|free expression|open debate|intellectual"),
    ]),
    ("Marriage, Family & Education", [
        # "political marriage" and "unholy marriage" are figures of speech about an alliance,
        # not stories about marriage. Chris, 20.08.2026, on the Belfast News Letter's "The
        # 'Dear Jon' letter which brought an end to an awkward and ultimately short-lived
        # political marriage" leaving Politics: the subject is two Stormont ministers falling
        # out. Guarded here rather than by weakening the tag-override rule in classify, which
        # would have given back the Rasanen fix from the same day's markup - and guarded
        # NARROWLY, because child, forced, sham and same-sex marriage are all real subjects
        # (the sham-marriage family was ruled in scope on 13.08.2026).
        (5, r"(?<!political )(?<!unholy )marriage"
            r"|married|marry|wedding|divorce|cohabit|civil partnership"
            r"|polyamor|polygam|annulment"),
        (5, r"birth ?rate|fertility rate|demograph|depopulat|motherhood|fatherhood"
            r"|childless|family breakdown|family court|parental rights|parents'? rights"),
        (4, r"sex education|relationships education|\bRSE\b|curriculum|school librar"
            r"|faith school|home ?school|ofsted|school (policy|uniform|prayer)"
            r"|parental (consent|notification|opt.out)"),
        (2, r"famil(y|ies)|parent|mother|father|adoption|foster|childcare|nurser"
            r"|school|pupil|teacher|university|student|childhood|toddler|teen"),
    ]),
    ("Gender, Identity & Sexuality", [
        (6, r"trans(gender|sexual)?\b|puberty blocker|cross-sex hormone|gender dysphoria"
            r"|gender clinic|tavistock|detrans|sex change|misgender|deadnam"
            # The movement goes by several names and only "ideology" was listed, so The
            # Australian's "Covert gender activism wags the care watchdog" reached no section
            # at all (Chris, 20.08.2026 - a story he had asked for). Every addition here names
            # the MOVEMENT or the DOCTRINE. A bare "gender" is deliberately NOT enough: it is
            # demographic, statistical or biological far more often than ideological, and the
            # guards in testcases.txt - a zoo giraffe, a pay gap, a gender reveal, shift-work
            # health data - are all real headlines this would otherwise have swept in.
            r"|gender[- ]?(transition|affirming|reassignment|identity|ideology"
            r"|activis|lobby|agenda|orthodoxy|theory|extremis)"
            r"|trans (youth|kids|child|care|health|women|men|athlete)|youth gender|child gender"),
        (5, r"single.sex|women.only|gender recognition|\bGRC\b|\bEHRC\b|changing room"
            # "biological (sex|male|female)" never covered the PLURAL: "biological male"
            # catches "males" by substring, but "biological men" and "biological women"
            # both missed entirely. Separate defect from the apostrophe one, same headline
            # found both (Telegraph, 31.08.2026).
            r"|strip.search|gender.critical|self-?id\b|biological (sex|male|female|m[ae]n|women)"
            r"|women'?s (sport|football|rugby|swimming|boxing|cricket|league|spa)"
            r"|female categor|male athlete"),
        (3, r"\bLGBT|\bpride\b|\bqueer\b|lesbian|\bgay\b|bisexual|non-?binary|stonewall"
            r"|drag queen|conversion therapy|chestfeed|intersex|same-sex attract"
            r"|sexual orientation|\bWNBA\b|women'?s (basketball|team|categor)"),
        (4, r"\bDEI\b|\bEDI\b|diversity, equity|equity and inclusion|identity politics"
            r"|critical race theory|\bCRT\b|decolonis|unconscious bias|positive action"
            r"|diversity officer|inclusion officer|affirmative action"),
        (2, r"\bsex\b|sexualit|rowling"),
    ]),
    ("Life", [
        (6, r"march for life|life march|pro-?life (march|rally|walk|vigil|chain)"
            r"|abortion|pro-?life|pro-?choice|mifepristone|abortion pill|unborn|preborn|foetus"
            r"|fetus|foetal|buffer zone|\bBPAS\b|marie stopes|planned parenthood"
            r"|gendercide|sex-selective|down'?s syndrome|heartbeat (bill|law)"
            # "born alive" matched nothing at all, so the Daily Telegraph's "10,000 booties on
            # lawn in 'born alive' bill push" fell into NO SECTION MATCHED (Chris, 17.08.2026).
            r"|born.?alive|infanticide|viability (limit|threshold)|late-?term"
            r"|conscientious objection|foeticide|feticide"),
        (6, r"assisted (dying|suicide|death)|euthanas|\bMAiD\b|\bMAID\b|right to die"
            r"|dignity in dying|end of life|palliative|hospice|lethal (drug|prescription)"),
        (6, r"surrogac|surrogate|\bIVF\b|embryo|egg freezing|fertility (treatment|clinic|doctor)"
            r"|designer bab|gene edit|three.parent|artificial womb|sperm donor"),
        # Three gaps found 19.08.2026, all in NO SECTION MATCHED:
        #  - "preborn" (added above) is Live Action's house term, so an Oklahoma law taking
        #    effect to save "preborn children" matched nothing;
        #  - organ-donation consent is bioethics and had no vocabulary at all;
        #  - "voice for life" is anchored to those nouns deliberately. Bare "for life" would
        #    have swallowed "jailed for life" and "sentenced to life in prison", both of
        #    which ran in Religious Freedom the same morning.
        (5, r"organ don(or|ation)|presumed consent|opt-?out (organ|donor)|donor register"
            r"|(voice|vigil|rally|march|stand|witness|speaking|advocate)s?\s+for life\b"),
        (3, r"micro-?preemie|premature (baby|birth|infant)|extremely preterm|\bNICU\b"),
        (2, r"suicide|terminally ill|life support|withdraw treatment|disabilit|eugenic"),
    ]),
    ("Church & Religion", [
        (4, r"church of england|\bCofE\b|\bC of E\b|anglican|archbishop|synod|diocese"
            r"|cathedral|parish|vicar|curate|lambeth|canterbury|york minster"),
        (4, r"\bpope\b|vatican|papal|leo xiv|cardinal|conclave|holy see|encyclical"
            r"|canon law|catholic (church|bishops|conference)|magisterium"),
        (3, r"\bchurch(es|goer|going)?\b|christian|catholic|evangelical|protestant"
            r"|orthodox|baptist"
            r"|methodist|presbyterian|congregation|pastor|priest|clergy|chaplain"
            # "Mass" but NOT "Mass." — the abbreviation for Massachusetts. Found 28.08.2026
            # while measuring the sue|lawsuit widening: \bmass\b matched the state in every
            # WBUR, Boston.com and NBC Boston headline, and two items in that day's sweep sat
            # in the Church & Religion candidate list on the strength of it. A trailing period
            # is the whole tell — the liturgy is written "Mass at the cathedral", "Red Mass",
            # never "Mass." unless a sentence ends there, which headlines do not do.
            r"|sermon|liturg|\bmass\b(?!\.)|worship|discipleship|evangeli|missional"),
        # faith[- ]: the space-only form silently dropped every hyphenated compound, so the
        # State Department's $2bn in grants to "Faith-Based Charities" reached no section at
        # all (found 19.08.2026). Same class of bug as law/laws below.
        (3, r"faith[- ](leader|group|school|community|based)|religion|religious"
            r"|secular|atheis|humanist|islam|muslim|jewish|judaism|hindu|sikh"
            r"|church attendance|churchgoing|belief"),
        # Marian vocabulary was absent entirely: Poland unveiling Europe's tallest statue of
        # the Virgin Mary matched nothing (19.08.2026), and three outlets carried it.
        (2, r"bishop|theolog|scripture|\bbible\b|gospel|prayer|\bchrist\b|jesus|god\b"
            # Bare "shrine" was too broad: it moved "Japanese PM and ministers honour
            # war-criminals at imperial shrine" out of Politics on 19.08.2026. Yasukuni is a
            # diplomatic story, so the shrine forms are anchored to a Christian referent.
            r"|virgin mary|our lady\b|marian\b|pilgrimage"
            r"|shrine of (our lady|st\.?|saint)|(marian|catholic|christian) shrine"),
    ]),
]
COMPILED = [(name, [(w, re.compile(p, re.I)) for w, p in pats]) for name, pats in SECTIONS]

# ---------------------------------------------------------------------------
# Spanish and Italian vocabulary.
#
# CitizenGO works in 30+ countries and Spanish is a primary language, but every pattern
# above is English, so ACI Prensa, Actuall, InfoCatolica, La Nuova Bussola and Le Salon Beige
# would parse perfectly and then vanish: classify() returned None and the item was dropped
# without trace. Added 13.08.2026 at Chris's request - this was the single biggest cap on
# coverage, larger than the RSS truncation loss.
#
# Merged into COMPILED rather than edited into SECTIONS so the English tables are untouched
# and a mistake here cannot change existing behaviour. Weights mirror their English
# counterparts so an item scores the same whichever language it arrives in.
# ---------------------------------------------------------------------------
ML_SECTIONS = {
    "Religious Freedom & Persecution": [
        (5, r"persecuci[oó]n|perseguid|libertad religiosa|libertad de culto|blasfemia"
            r"|apostas[ií]a|m[aá]rtir|conversi[oó]n forzada|cristianofobia"
            r"|persecuzione|perseguitat|libert[aà] religiosa|libert[aà] di culto|bestemmia"
            r"|apostasia|martire|cristianofobia|cristiani perseguitati"),
        (4, r"(iglesia|templo|capilla)s? (atacad|incendiad|profanad|destruid|demolid)"
            r"|(sacerdote|obispo|p[aá]rroco|monja|religiosa|pastor)s? (asesinad|detenid|secuestrad|encarcelad)"
            r"|cristianos (asesinad|detenid|secuestrad|encarcelad|matad)"
            # Spanish and Italian invert this: "Detenido un sacerdote", not "sacerdote detenido"
            r"|(detenid|arrestad|encarcelad|asesinad|secuestrad|expulsad|condenad)\w*\s+"
            r"(a\s+)?(un|una|el|la|los|las)?\s*(sacerdote|obispo|p[aá]rroco|monja|religiosa"
            r"|pastor|seminarista|misioner|cristian)"
            r"|(arrestat|uccis|rapit|incarcerat|espuls|condannat)\w*\s+"
            r"(un|una|il|lo|la|i|gli)?\s*(sacerdote|vescovo|parroco|suora|religiosa"
            r"|pastore|seminarista|missionar|cristian)"
            r"|(chiesa|cappella) (attaccat|incendiat|profanat|distrutt)"
            r"|(sacerdote|vescovo|parroco|suora|religiosa) (uccis|arrestat|rapit|incarcerat)"
            r"|cristiani (uccis|arrestat|rapit|incarcerat)"),
        (3, r"polic[ií]a religiosa|ley anticonversi[oó]n|minor[ií]as religiosas"
            r"|objeci[oó]n de conciencia|polizia religiosa|minoranze religiose"
            r"|obiezione di coscienza|legge anti-conversione"),
    ],
    "Free Speech & Civil Liberties": [
        (5, r"libertad de expresi[oó]n|libertad de prensa|censura|censurad|delito de odio"
            r"|ley mordaza|cancelaci[oó]n|autocensura"
            r"|libert[aà] di espressione|libert[aà] di stampa|censur|reato d'odio"
            r"|legge bavaglio|autocensura"),
        (3, r"detenid\w* por (un )?(tuit|mensaje|comentario|publicaci[oó]n)"
            r"|arrestat\w* per (un )?(tweet|messaggio|commento|post)|querella|querelat"),
    ],
    "Marriage, Family & Education": [
        (5, r"matrimonio|matrimonial|divorcio|c[oó]nyuge|uniones civiles"
            r"|divorzio|coniug|unioni civili"),
        (5, r"natalidad|fecundidad|demograf|maternidad|paternidad|patria potestad"
            r"|invierno demogr[aá]fico|natalit[aà]|fecondit[aà]|demograf|maternit[aà]"
            r"|paternit[aà]|inverno demografico|denatalit[aà]"),
        (4, r"educaci[oó]n sexual|adoctrinamiento|curr[ií]culo|libertad educativa"
            r"|pin parental|colegio concertado|educazione sessuale|indottrinamento"
            r"|programma scolastico|libert[aà] educativa"),
        (2, r"familia|familiar|padres|madre|padre|hijos|adopci[oó]n|acogida|escuela|colegio"
            r"|alumno|profesor|universidad|infancia|adolescent"
            r"|famiglia|famigliar|genitori|madre|padre|figli|adozione|affido|scuola|scolastic"
            r"|alunno|insegnante|universit[aà]|infanzia|adolescen"),
    ],
    "Gender, Identity & Sexuality": [
        (6, r"transg[eé]nero|transexual|ideolog[ií]a de g[eé]nero|cambio de sexo"
            r"|bloqueadores de (la )?pubertad|disforia de g[eé]nero|autodeterminaci[oó]n de g[eé]nero"
            r"|ley trans|detransici[oó]n|hormonaci[oó]n"
            r"|transessual|ideologia (del )?gender|cambio di sesso|bloccanti della pubert[aà]"
            r"|disforia di genere|carriera alias|detransizione"),
        (5, r"espacios? (solo )?para mujeres|deporte femenino|categor[ií]a femenina"
            r"|sexo biol[oó]gico|vestuarios?|spazi per (sole )?donne|sport femminile"
            r"|categoria femminile|sesso biologico|spogliatoi"),
        (3, r"LGTB\w*|LGBT\w*|homosexual|lesbiana|bisexual|no binari|orgullo gay"
            r"|terapia de conversi[oó]n|omosessual|lesbica|bisessual|non binari|gay pride"
            r"|terapia di conversione"),
        (2, r"g[eé]nero|sexualidad|genere|sessualit[aà]"),
    ],
    "Life": [
        (6, r"aborto|abortiv|abortar|provida|pro-?vida|antiabortist|p[ií]ldora abortiva"
            r"|no nacid|nascituro|feto|fetal|s[ií]ndrome de down"
            r"|abortire|provita|pro-?vita|pillola abortiva|non nato"),
        (6, r"eutanasia|suicidio asistido|muerte digna|derecho a morir|cuidados paliativos"
            r"|sedaci[oó]n terminal|suicidio assistito|morte dignitosa|fine vita"
            r"|cure palliative|testamento biologico"),
        (6, r"gestaci[oó]n subrogada|maternidad subrogada|vientres? de alquiler|embri[oó]n"
            r"|fecundaci[oó]n in vitro|reproducci[oó]n asistida|congelaci[oó]n de [oó]vulos"
            r"|maternit[aà] surrogata|utero in affitto|embrione|fecondazione assistita"
            r"|procreazione assistita"),
    ],
    "Church & Religion": [
        (4, r"papa|vaticano|papal|pontif|cardenal|c[oó]nclave|santa sede|enc[ií]clica"
            r"|conferencia episcopal|derecho can[oó]nico|cardinale|conclave|enciclica"
            r"|conferenza episcopale|diritto canonico|pontefice"),
        (3, r"iglesia|cat[oó]lic|cristian|evang[eé]lic|protestante|ortodox|obispo|arzobispo"
            r"|sacerdote|p[aá]rroco|clero|di[oó]cesis|parroquia|misa|homil[ií]a|liturgia"
            r"|chiesa|cattolic|cristian|evangelic|protestant|ortodoss|vescovo|arcivescovo"
            r"|parroco|diocesi|parrocchia|messa|omelia|liturgia"),
        (3, r"laicismo|laicidad|secularizaci[oó]n|ateo|ate[ií]smo|isl[aá]mic|musulm[aá]n"
            r"|jud[ií]o|juda[ií]smo|hind[uú]|religi[oó]n|religios"
            r"|laicit[aà]|secolarizzazione|ateo|ateismo|islamic|musulman|ebraic|ebreo"
            r"|religione|religios"),
        (2, r"fe cristiana|oraci[oó]n|biblia|evangelio|jes[uú]s|dios|santo|beato"
            r"|preghiera|bibbia|vangelo|ges[uù]|dio|santo|beato"),
    ],
}
COMPILED = [(name, pats + [(w, re.compile(p, re.I)) for w, p in ML_SECTIONS.get(name, [])])
            for name, pats in COMPILED]

# "Other" was a landfill: 514 of 1,567 candidates on 14.08.2026, a third of the day, with
# the Clacton by-election, asylum-hotel policy and US election litigation all buried in it.
# These two themes are split out. The split happens ONLY on the residual path - an item
# that already matched a real section is untouched - so no existing section can lose
# anything to it. Order matters: immigration wins ties because "asylum policy vote" is an
# immigration story before it is an elections story.
OTHER_SPLIT = [
    ("Immigration & Asylum",
     # A bare \bborder\b stays, despite catching the odd state line. Narrowing it to
     # border+migration company was built and MEASURED on the 25.08.2026 sweep: it corrected
     # 4 loose placements but sent 6 items to NO SECTION AT ALL, including two real
     # border-trade stories ("US border reopens to Mexican cattle"). A wrong section is
     # visible and fixable in the sheet; no section is the bucket that hides real news.
     re.compile(r"migrant|migration|asylum|immigration|immigrant|border|deport|refugee"
                r"|\bICE\b|smuggl|people.smugg|channel crossing|small boat|dinghy"
                r"|visa\b|citizenship|naturalis|resettle|hotel(s)? (for|housing)"
                r"|illegal alien|undocumented|sanctuary (city|state)", re.I)),
    ("Politics, Government & Society",
     # \bvotes?\b/\bvoting\b: "voter" was here but not "vote", so TVP World's "Fedorov calls
     # for wartime vote" reached no section while the same story from The European Conservative
     # classified on "elections" (20.08.2026). Routing must not depend on which synonym an
     # outlet picked. Safe because other_section runs only when nothing else scored, so a vote
     # ON a subject with its own section - an assisted dying bill, a marriage bill - never
     # reaches here.
     re.compile(r"election|by-?election|ballot|polling station|voter|turnout|constituency"
                r"|\bvotes?\b|\bvoting\b"
                r"|candidate|campaign|primary\b|referendum|manifesto|\bpoll(s|ing)?\b"
                r"|farage|\breform\b|labour|tory|tories|conservative party|lib dem|snp\b"
                r"|starmer|burnham|badenoch|westminster|downing street|no\.? 10"
                r"|白宫|white house|senate|congress|governor|mayor|council(lor)?\b"
                r"|parliament|mp(s)?\b|cabinet|minister|resign|coalition|swing\b"
                # Constitutional and institutional politics, added 20.08.2026. The pattern
                # above is entirely elections and office-holders, so "Term Limits for Supreme
                # Court Justices are Unconstitutional" and "Federal judge finds ghost gun rule
                # unconstitutional" reached no section at all.
                #
                # Deliberately NOT a bare "court" or "judge": ordinary litigation is not
                # politics, and Politics is a residual split that nothing else may lose items
                # to (the 14.08.2026 guarantee). Each token below names a question about how
                # the state is constituted, not a case that happens to be in a courtroom -
                # which is why a Netflix trademark suit and an Allahabad dismissal appeal stay
                # unsectioned. Measured on the 20.08 sweep: 2 of 392 unsectioned items move.
                r"|unconstitutional|constitutionality|separation of powers|term limits"
                r"|judicial (review|independence|nominee|confirmation|appointment|reform)"
                r"|court.packing|\bSCOTUS\b|redistrict|gerrymander|filibuster|impeach"
                r"|executive order|legislature|statehouse"
                # "politic" itself was missing, so a headline whose only political word was
                # "political" reached no section at all - which is how the Belfast News
                # Letter's "...short-lived political marriage" ended up relying on its
                # publisher tag alone (20.08.2026). This can only pull items OUT of the
                # residual bucket; it cannot take one from a real section, because
                # other_section runs only when nothing else scored.
                r"|politic", re.I)),
]

SECTION_NAMES = ([name for name, _ in SECTIONS]
                 + [name for name, _ in OTHER_SPLIT] + ["Other"])


def other_section(headline):
    """Route a residual item to a split theme, or leave it in Other."""
    for name, rx in OTHER_SPLIT:
        if rx.search(headline):
            return name
    return "Other"

# Outlets whose entire output leans to one section. Free Speech especially needs this:
# FSU and spiked write about speech constantly without using the words "free speech"
# ("Nobody In Government Can Say They Were Not Warned").
SOURCE_HINTS = {
    "Free Speech & Civil Liberties": [
        "big brother watch", "open rights group", "reclaim the net",
        "free speech union", "spiked", "fire", "foundation for individual rights",
        "reclaim the net", "index on censorship", "the critic", "quillette",
        "conservative woman", "unherd",
    ],
    "Religious Freedom & Persecution": [
        "international christian concern", "persecution.org", "morningstar",
        "open doors", "forum 18", "bitter winter", "chinaaid", "release international",
        "aid to the church in need", "barnabas", "world watch",
    ],
    "Life": [
        "lifenews", "live action", "right to life", "spuc", "care not killing",
        "euthanasia prevention", "bioedge", "don't screen us out",
    ],
    "Gender, Identity & Sexuality": [
        "reduxx", "sex matters", "transgender trend", "lgb alliance",
        # Chris, 03.09.2026, adding her as a source after the "Pregnant Men" funding piece was
        # missed. The hint is the half that matters: her headlines lead on the money and the
        # institution ("£1.86 million: The taxpayer-funded research of...") and name the beat
        # only in passing, so they score 0 and the feed alone would have dropped her into
        # NO SECTION MATCHED daily. Safe here because SOURCE_HINTS is consulted only when
        # nothing scored - her press-regulation reporting still goes to Free Speech on its
        # own words, which testcases.txt pins.
        "charlotte gill",
    ],
}
SOURCE_BOOST = 4

# Celebrity, entertainment and sport chaff. PinkNews' unfiltered feed is the main source
# ("RuPaul's Drag Race UK season 8 cast", "'Gym penis' - what it means"). Suppressed here
# rather than in fetch_feeds.py so the sweep and seen.json stay complete.
# Dated newsletter round-ups from advocacy outlets - "First Liberty Insider: August 14th,
# 2026". An index of the week's items, not a story. Added 20.08.2026 when the litigator rule
# made them reachable; same family as the EWTN schedule and WORLD magazine-index entries.
NEWSLETTER_INDEX = re.compile(
    r"^[\w .&'-]{0,40}(insider|roundup|round-up|digest|newsletter|weekly|bulletin)\s*[:|-]\s*"
    r"(mon|tues|wednes|thurs|fri|satur|sun)?\w*,?\s*"
    r"(january|february|march|april|may|june|july|august|september|october|november|december)"
    r"\s+\d{1,2}(st|nd|rd|th)?,?\s*\d{4}\s*$", re.I)

CHAFF = [
    r"drag race|rupaul|strictly come dancing|love island|big brother|eurovision"
    r"|celebrity|red carpet|met gala|premiere|box office|trailer drops?|season \d"
    r"|episode \d|spoiler|\bcasting\b|cast (are|is|announced)|reboot|sequel",
    r"\bkiss(ed|ing)?\b.{0,30}\b(co-?star|scene|unscripted)|\bdating\b|split from|romance"
    r"|engaged to|baby bump|pregnancy announcement|reveals? (all|why|how she|how he)"
    r"|opens up about|hits back at trolls|savage response|goes viral",
    r"transfer (news|window|deadline)|signs for|goal(s)? in|premier league|world cup squad"
    r"|match report|final score|kick.off|wins? (gold|silver|bronze)|\bolympics?\b",
    r"what it means and whether|here'?s what we know|\d+ things|top \d+|best \d+"
    r"|quiz:|recipe|horoscope|weather warning|travel chaos|lottery|deals? of the day",
    r"fringe (comedy )?review|album review|restaurant review|theatre review|gig review",
    # Broadcast and podcast schedule entries - EWTN's feed carries a lot of these
    # ("At Home with Jim and Joy - Call in Show | 8-10-26").
    r"call.in show|\bepisode\b|podcast|– \d{1,2}[-/]\d{1,2}[-/]\d{2}|\| \d{1,2}-\d{1,2}-\d{2}"
    r"|watch live|live ?stream|replay|full show|radio show|daily broadcast",
    # Devotional, wellness and human-interest filler
    r"\d+ (other )?ways to|steward your|found healing|journey from trauma"
    r"|\bscams?\b|phishing|phantom hacker|nostalgia|the .+ era is here"
    r"|reflection for|daily devotion|verse of the day|prayer of the day",
]
CHAFF_RE = re.compile("|".join(CHAFF), re.I)

# The chaff patterns are heuristics over headlines, and on 13.08.2026 they were quietly
# deleting real stories: "slams" is a staple political verb, so an abortion-vs-deportation
# bill in Sweden and a Tamil Nadu Speaker's abortion remarks both vanished; "casting" hit
# "broadcasting"; "olympic" hit a women's-category policy story; "scam" hit an FBI
# marriage-fraud prosecution. Anchoring helped, but the durable fix is this override: an
# item carrying a genuine issue or hard-news signal is never suppressed, whatever else the
# headline contains. Chaff should only ever remove items that have nothing else going on.
CHAFF_RESCUE = re.compile(
    r"abortion|pro-?life|foet|unborn|euthanas|assisted (dying|suicide)|surrogac|surrogate"
    r"|ivf|embryo|persecut|blasphem|apostas|convert|missionar|martyr|church|bishop|diocese"
    r"|cathedral|priest|pastor|imam|rabbi|synagogue|mosque|christian|catholic|anglican"
    r"|muslim|jewish|hindu|sikh|marriage|divorce|adoption|foster|parental|puberty blocker"
    r"|gender[- ]?(critical|identity|ideology|transition|affirming|reassignment)|trans(gender)?"
    r"|detrans|single[- ]sex|women'?s (sport|category|prison|refuge)|free speech|censor"
    r"|blocked online|conscience|religious (freedom|liberty)|conversion (therapy|practice)"
    r"|court|judge|ruling|verdict|tribunal|inquest|inquiry|bill\b|law\b|legislat|senate"
    r"|parliament|congress|minister|arrest|charged|sentenc|jailed|convict|prosecut"
    r"|deport|asylum|banned|ban\b|petition|report finds|poll(ing)?\b"
    r"|\bgender\b", re.I)

# Some filler mentions the right words and still is not news: EWTN's "Pro-Life Weekly |
# Full EPISODE" is a schedule entry, "Ryan Lochte marriage controversy ... reveals all" is
# showbiz, and "verse of the day" is devotional. These formats are never rescued, because
# the format itself is the disqualifier - no subject matter redeems a listings entry.
CHAFF_HARD = re.compile(
    r"drag race|rupaul|strictly come dancing|love island|big brother|eurovision"
    r"|\bcelebrity\b|red carpet|met gala|box office|trailer drops?|season \d|\bspoiler"
    r"|\breboot\b|\bsequel\b|reveals? (all|why|how she|how he)"
    r"|call.in show|\bepisodes?\b|podcast|watch live|live ?stream|\breplay\b|full show"
    r"|radio show|daily broadcast|\| \d{1,2}-\d{1,2}-\d{2}|– \d{1,2}[-/]\d{1,2}[-/]\d{2}"
    r"|reflection for|daily devotion|verse of the day|prayer of the day"
    r"|quiz:|\brecipe|horoscope|lottery|deals? of the day|\d+ things|top \d+|best \d+"
    r"|fringe (comedy )?review|album review|restaurant review|theatre review|gig review",
    re.I)


# Pornographic SEO spam, riding in on the Gender and Life search feeds. Chris, 31.08.2026:
# two of these reached LIVE sections rather than the suppressed bucket - a Vietnamese porn
# scrape classified into Gender, Identity & Sexuality and an "[xXx]...xnxx new pornx" string
# into Life - because their headlines were read as ordinary words.
#
# Two things force the shape of this pattern. There is no outlet to blocklist: both arrived
# as Google News redirects the decoder could not resolve, so the outlet parsed out as "Air
# and Space Museum", a name that will be different and equally wrong next time. And the feeds
# carrying them are search feeds the beats depend on, so this cannot move up into the fetch
# filter without costing real Gender and Life coverage.
#
# So it matches on spam ORTHOGRAPHY, never on subject matter. Bare "porn", "sex" and "nude"
# are deliberately absent: "You Can't Be Charged For Possessing AI Child Porn, Court Rules"
# and "child sex changes" are real stories on this beat, and a subject-matter rule would take
# the beat down with the spam. What is matched instead is the vocabulary of scraper sites -
# xxx/xnxx runs, porn- with a site suffix, and the Vietnamese scrape markers - none of which
# a newsroom ever writes.
PORN_SPAM = re.compile(
    r"\bxn?x{2,}\b"                             # xxx, [xXx], xnxx
    r"|\bporn(?:x|o|hub|tube|star)s?\b"          # pornx/porno/pornhub - NOT bare "porn"
    r"|\bx-?videos?\b|\bxhamster\b|\bsex-?videos?\b|sex!\+?videos?"
    r"|\bphim\s+sex\b|\bxem\s+phim\b|\bvietsub\b"   # Vietnamese porn scrapes
    r"|\bnude\s+(?:pics?|photos?|videos?|scenes?)\b"
    r"|\b(?:watch|download)\s+(?:full\s+)?(?:sex|porn)\b",
    re.I)


# Outlets that only ever arrive here by accident, via a Google News keyword feed catching a
# showbiz story that happens to say "marriage" or "baby". No rescue applies to them.
CELEB_SOURCES = re.compile(
    r"people\.com|\bpeople\b magazine|hello!|\bok!\b|us weekly|tmz|e! ?online"
    r"|e! ?(news|online)|just jared|page six"
    r"|entertainment (weekly|tonight)|billboard|variety|hollywood reporter|pinkvilla"
    r"|bollywood|koimoi|sportskeeda|deadline\.com"
    # anchored: the feed titles this one "People", and Peoples Gazette Nigeria is a real
    # source that must not be caught
    r"|^people$", re.I)


CELEB_KEEP = re.compile(
    r"abortion|surrogac|euthanas|assisted (dying|suicide)|ivf|embryo|persecut"
    r"|court|judge|ruling|verdict|lawsuit|\bsues?\b|\bsued\b|bill\b|\blaw\b|legislat"
    r"|senate|parliament|congress|governor|supreme court|referendum|arrest|charged"
    r"|sentenc|convict|banned|\bban\b|policy|petition|trans(gender)?\b|gender|church"
    r"|bishop|christian|catholic|school|censor|free speech", re.I)



# A discrete local incident that reached a section only on a weak keyword. Chris marked six
# of these "Sad news but not really on target" on 14.08.2026 - a Virginia campus shooting, a
# Redford Township fire, an Irish student electrocuted on holiday - all admitted to Marriage,
# Family & Education because the headline contained "university", "student" or "family".
#
# Refusing weak matches outright was tested and is wrong: it removes 109 items from that
# section including "Mother sues Portland Public Schools over gender lessons" and two SPUC
# assisted-suicide stories. The distinguishing feature is not the weak score, it is that the
# item is a one-off incident with no issue behind it. All three conditions must hold.
LOCAL_INCIDENT = re.compile(
    r"\bshot\b|shooting|stabb|collision|\bblaze\b|drown|electrocut"
    r"|body found|found dead|\bfatal(ly)?\b|burglar|robbery|carjack"
    r"|missing (man|woman|boy|girl|teen)|road (death|traffic)"
    r"|\bfire\b (at|breaks|destroy|guts)|dead after|killed in (a )?(crash|fire|collision)",
    re.I)
# Road traffic specifically - see the incident gate. Deliberately not just "died": a crash,
# a collision or a joyrider is the whole story in these, and an issue story that happens to
# involve one is rescued by ISSUE_ANCHOR before this is reached.
ROAD_TRAFFIC = re.compile(
    r"\b(crash|collision|joyrider|hit-?and-?run)\b|\broad (death|traffic)\b", re.I)

# "Family is in the title but the core of the argument is voting and how asian families are
# voting as a family unit" (Chris, 24.08.2026) - electoral integrity, not family policy.
FAMILY_VOTING = re.compile(
    r"\bfamily voting\b|\bvoting as a family\b|\bfamilies voting\b", re.I)

# Chris, 25.08.2026: ICC's "UK Pastor Booked on Bizarre Charges" filed as Church & Religion -
# "It should also be in the religious freedom section". A cleric prosecuted BY THE STATE is
# persecution; the Church catch-all takes it on the word "pastor" alone. The guard is what
# makes this safe: a cleric charged with abuse, fraud or assault is a church-scandal story and
# stays put, which is why "Laicized Wisconsin priest arrested over new grooming charges" is
# untouched by this.
CLERGY_PROSECUTED = re.compile(
    r"\b(pastor|priest|bishop|imam|clergy|clergyman|missionary|preacher|nun|monk|evangelist)"
    r"\b[^.]{0,60}?\b(booked|charged|arrested|detained|jailed|imprisoned|sentenced|convicted"
    r"|prosecuted|fined|deported|banned)\b"
    r"|\b(booked|charged|arrested|detained|jailed|imprisoned|sentenced|convicted|prosecuted)"
    r"\b[^.]{0,40}?\b(pastor|priest|bishop|imam|clergy|missionary|preacher|nun|monk)\b", re.I)
# ...and a second guard, added the same hour because the fixture caught the regression: a
# Western state prosecuting a cleric over WHAT HE SAID is a free-speech story, which is Chris's
# own ruling of 20.08.2026 on The Federalist's "U.K. Bans Bishop, Lawmaker Convicted Of 'Hate
# Speech' For Agreeing With The Bible". Persecution is what happens where the state is not the
# forum. Without this the new clergy rule silently reversed a correction he had already made.
CLERGY_SPEECH_CASE = re.compile(
    r"hate speech|free speech|freedom of expression|censor|misgender|blasphem\w* law"
    r"|tweet|social media post|offensive (post|joke|remark)|for (saying|posting|preaching)"
    r"|agreeing with the bible", re.I)
CLERGY_SCANDAL = re.compile(
    r"\babuse|assault|groom|molest|fraud|theft|steal|stole|embezzl|launder|indecent|porn"
    r"|misconduct|rape|paedophil|pedophil|drink.driv|drunk", re.I)

# Chris, 25.08.2026, on GB News's "Sudanese migrant allowed to stay in Britain and cannot be
# deported because she married her cousin", filed under Marriage: "This is a migration issue
# first and foremost before a marriage one. Suggest ways of fixing the logic." The logic that
# failed is keyword weighting - "married"/"marriage" scores Marriage, "migrant"/"deported"
# scores Immigration, and Marriage won on count. Weighting alone cannot fix it, because the
# marriage really is in the headline. What distinguishes the story is that the marriage is
# INSTRUMENTAL: the news is an immigration DECISION, and the marriage is its cause. So the
# rule keys on the decision, not on the word "migrant" - a deportation or leave-to-remain
# outcome is an immigration story whatever produced it.
IMMIGRATION_DECISION = re.compile(
    r"\b(cannot be deported|can(no|')t be deported|allowed to stay|deportation order"
    r"|leave to remain|right to remain|granted asylum|refused asylum|asylum (claim|appeal)"
    r"|removal (order|flight)|deportation (flight|appeal)|immigration tribunal"
    r"|avoid(s|ed)? deportation|spared deportation)\b", re.I)

# Islamism is a political ideology and the Church & Religion catch-all grabs it on the stem
# "islam". Chris marked spiked's "Islamism and the silence of the 'progressives'" as "more of
# a society section article" (24.08.2026). Genuine religion coverage carries its own
# vocabulary, so requiring the absence of that keeps mosque/persecution stories in place.
ISLAMISM_POLITICAL = re.compile(r"\bislamis(m|t|ts)\b", re.I)
RELIGION_PRACTICE = re.compile(
    r"mosque|imam|worship|congregation|persecut|convert|blasphem|prayer|church|christian"
    r"|cathedral|diocese|bishop|priest|pastor|shrine|pilgrim", re.I)

# If any of these appear, it is about an issue and stays whatever else the headline says.
ISSUE_ANCHOR = re.compile(
    r"abortion|pro-?life|unborn|foet|surrogac|euthanas|assisted (dying|suicide|death)"
    r"|end of life|palliative|\bIVF\b|embryo"
    r"|\bgender\b|trans(gender)?\b|\bLGBT|sexualit|\bsex\b|same-sex|single.sex"
    r"|marriage|divorce|parental rights|parents'? rights|sex education|curriculum"
    r"|faith school|home ?school|safeguarding|grooming"
    r"|church|christian|catholic|muslim|islam|jewish|religio|faith|bishop|priest|pastor"
    r"|persecut|blasphem|free speech|censor|conscience"
    r"|\bbill\b|legislat|\bpolicy\b|inquiry|watchdog|regulator|campaign group", re.I)


# Sections reached through the residual path carry no keyword score, so every item in them
# looks "weak" by construction. Applying the incident rule there suppressed 52 items on the
# first run including a Trump licensing-data policy story ("Year After Deadly Crash...") and
# an ICE custody death. It belongs only where a real weighted match placed the item.
RESIDUAL_SECTIONS = {"Immigration & Asylum", "Politics, Government & Society", "Other"}



SCHOOL_ROUTINE = re.compile(
    r"back-?to-?school|opens? (its |their )?doors|block party|open day|prize.?giving"
    r"|graduation|prom\b|yearbook|honou?r roll|bake sale|fundrais|field trip"
    # "assembly" alone matched the West Bengal Assembly and the NI Assembly. It was harmless
    # only because this function was never called; wiring it in on 17.08.2026 made it live.
    r"|school assembly|morning assembly"
    r"|sports day|school (fair|fete|concert|play|musical|trip|bus route|lunch menu)"
    r"|first day of (school|term)|term (starts|begins)|enrol(ment|ling) opens"
    r"|new (principal|headteacher) (named|appointed)|ribbon.cutting"
    # Chris, 27.08.2026, on the Telegraph's "Private schools ban Meta smart glasses amid
    # bullying fears" and FOX 2 Detroit's "Birmingham parents split over schools'
    # bell-to-bell cellphone ban": "This isn't a big enough story and doesn't really cross
    # section with our other issues to warrant inclusion." One school or district setting its
    # own rule about a gadget is house-keeping. The escape hatch below is what keeps the real
    # version of this story: a government banning phones in schools carries "law", "bill",
    # "policy" or one of the governance words now in EDUCATION_ANCHOR, so it survives.
    r"|bell.?to.?bell"
    r"|(ban|bans|banned|bar|bars|barred|prohibit)\w*\b.{0,30}\b(phone|phones|smartphone"
    r"|smartphones|cellphone|cellphones|mobile|mobiles|smart ?glasses|smart ?watch"
    r"|smartwatches|earbuds|headphones|device|devices)\b", re.I)
# What makes an education story ours: who decides, what is taught, what a child is exposed to.
EDUCATION_ANCHOR = re.compile(
    r"parental (rights|consent|notification|opt.?out)|parents'? rights|sex education"
    r"|relationships education|\bRSE\b|curriculum|faith school|home ?school|ofsted"
    r"|school prayer|gender|trans|LGBT|safeguarding|grooming|abuse|censor|free speech"
    r"|banned book|library|indoctrinat|ideolog|religio|christian|catholic|islam"
    r"|lawsuit|court|ruling|policy|bill\b|law\b|inquiry|tribunal|discriminat"
    # Governance words, added 27.08.2026 with the device clause in SCHOOL_ROUTINE above.
    # A single school's gadget rule is house-keeping; a government's is education policy, and
    # only the actor tells the two apart.
    r"|government|minister|parliament|congress|legislat|governor|senate|statewide"
    r"|nationwide|countrywide|department for education|\bDfE\b|school board vote", re.I)


# A crime that happens to occur at a school or university. Chris, 17.08.2026: "We're
# interested in university and school stories where they overlap our other concerns on things
# like free speech or transgender." A stabbing, an arrest or a court case on a campus is a
# crime story that borrowed the word "student" - it reaches Marriage, Family & Education on a
# score of 2 and displaces real family and schooling policy. EDUCATION_ANCHOR is the escape
# hatch: a grooming scandal, a safeguarding failure or a free-speech arrest still carries one.
SCHOOL_CRIME = re.compile(
    r"\b(arrest|charg|convict|sentenc|jail|stabb|shot|shooting|murder|assault|rap(e|ed|ing)"
    r"|threaten|kidnap|robbed|burglar|drunk|crash)\w*\b", re.I)
SCHOOL_CONTEXT = re.compile(
    r"\b(school|college|university|campus|student|pupil|principal|headteacher|teacher)s?\b",
    re.I)


def is_school_crime(headline, score):
    """Campus crime with no education-policy dimension. Same gate as is_school_routine."""
    if score > 3:
        return False
    if not (SCHOOL_CONTEXT.search(headline) and SCHOOL_CRIME.search(headline)):
        return False
    return not EDUCATION_ANCHOR.search(headline)


def is_school_routine(headline, score):
    """Routine school or parish activity with no policy or rights dimension behind it.

    Gated at 4 rather than 2 so it also catches "church hosts free back-to-school block
    party", which reaches Church & Religion on the word "church" and scores 3. Anything
    matching a section's strong patterns (5 or 6 - abortion, gender, persecution) is never
    touched, so a school shooting policy row or a church closure survives.
    """
    if score > 4:
        return False
    if not SCHOOL_ROUTINE.search(headline):
        return False
    return not EDUCATION_ANCHOR.search(headline)


def is_local_incident(headline, score, section=None):
    """True only if all four conditions hold: keyword-placed, weak, incident, no issue.

    The score is recomputed from the keyword tables rather than trusted, because a publisher
    category sets a synthetic score of 4 and that was defeating the gate: Boston.com tags a
    campus shooting ['News','National News','Education','Crime'], so category routing filed
    it under Education at score 4 and the incident rule never fired. The publisher is not
    wrong - it is an education story to them - but it is not one in this briefing's sense.
    """
    if section in RESIDUAL_SECTIONS:
        return False
    if ISSUE_ANCHOR.search(headline):
        return False
    # Chris, 24.08.2026: four road-traffic tragedies reached Marriage, Family & Education on
    # the TEST 20260824 draft - two A66 crash stories and two M9 funeral pieces - each marked
    # "only loosely about family and doesn't cross-section into our other issues such as
    # family law, gender ideology, etc., to warrant coverage here". They survived the incident
    # rule because "families" scores well enough to clear the >2 escape below. A collision with
    # no issue behind it is a local incident however high "family" scored, so road traffic
    # skips that escape - it still has to clear the ISSUE_ANCHOR check above.
    if ROAD_TRAFFIC.search(headline):
        return True
    ranked = score_sections(headline, "")
    real = ranked[0][0] if ranked else 0
    if max(real, 0) > 2:
        return False
    return bool(LOCAL_INCIDENT.search(headline))


# Roundup and digest formats - Chris: "Don't include the Rebel Roundup or roundups".
ROUNDUP = re.compile(
    r"\broundup\b|round-?up\b|\bdigest\b|\bbriefing\b|week in review|weekly recap"
    r"|what we learned|top stories|news in brief|in pictures|live ?blog|as it happened"
    r"|morning (mail|edition|update)|evening (update|edition)|\bbulletin\b"
    r"|newsletter|this week in|the week in"
    # Magazine issue index pages, not articles. WORLD's "News Magazines for Christians |
    # Vol. 41, No. 9" reached the 17.08 edition (Chris flagged it) - it is a contents page
    # whose link goes to the issue, not to a story. Matches "Vol. 41, No. 9" and "Issue 12".
    r"|\bvol\.? ?\d+,? ?(no\.?|issue) ?\d+|\bissue no\.? ?\d+", re.I)

# Outlets Chris has ruled out. Anglican Mainstream: "They just repost old news from
# elsewhere" (15.08.2026), said twice.
# Outlets Chris has ruled out. Anglican Mainstream reposts old news (15.08.2026); the rest
# he removed on 16.08.2026. Blocked on the display name because most reach us as Google News
# redirects, where the URL host is news.google.com and tells us nothing.
BLOCKED_OUTLETS = re.compile(
    # Every internal space is [- ]? because an outlet name is a bare DOMAIN whenever the item
    # arrives without a stated source (outlet_from_url), and a literal space could never match
    # one. Found 20.08.2026 when Chris asked for Evangelical Times to be "dropped completely":
    # "evangelical-times.org" was not blocked, and nor were truthnigeria.com,
    # anglicanmainstream.net, barnabasaid.org, 24-7pressrelease.com, leadershipnewspapers.com
    # or newyorkdailynews.com - six of the nine blocks had the same hole, silently. "zenit" is
    # now \b-anchored so it cannot catch an outlet called Zenith.
    r"anglican[- ]?mainstream|clarion-?ledger|businessmirror|quiver[- ]?quantitative"
    r"|leadership[- ]?newspapers?|telangana[- ]?today|daily[- ]?country[- ]?today"
    r"|new[- ]?york[- ]?daily[- ]?news|massterlist"
    # Chris's markup on the 19.08.2026 edition: "Remove Barnabas Aid as a source", "I asked
    # for Christian Daily International not to be included as a source", "Drop Christian
    # Daily as a source". The Christian Daily family publishes under at least four names
    # (Christian Daily International, Christianity Daily, Christianity Daily News and the
    # bare domain), so the pattern covers the stem rather than one masthead.
    r"|barnabas[- ]?aid|christian[- ]?daily|christianity[- ]?daily"
    # Chris's markup on the 20.08.2026 edition: "Never include this as a source"
    # (Truth Nigeria), "Remove this as a source" (24-7 Press Release Newswire, This
    # Day, Zenit), "Never include Evangelical Times as a source as they are always
    # late with the news". 24-7 Press Release Newswire has no feed at all - it reaches
    # us as a Google News redirect, which is why every one of these is blocked on the
    # display name rather than the URL.
    r"|truth[- ]?nigeria|24-7[- ]?press[- ]?release|this[- ]?day|\bzenit\b"
    r"|evangelical[- ]?times"
    # Chris's markup on the TEST 20260824 draft: "Drop this source completely" (Voice of
    # Emirates, which arrives under its Arabic masthead), "Drop as a source" (Rediff, AOL.com)
    # and "This is a repeat from previous days. Also drop as a source." (China Daily). All
    # four reach us as Google News redirects, so the block has to be on the display name.
    r"|صوت الإمارات|voice[- ]?of[- ]?emirates|\brediff\b|china[- ]?daily|\baol\b"
    # Chris's markup of the TEST 20260825 draft: "Remove as a source" against each of these.
    r"|moneycontrol|brobible|lgbtqnation|queerty"
    # Chris's markup of the 20260827 edition: "Remove as a source permanently" against seven
    # more. Two lessons in this batch. News18 was already in ENTERTAINMENT_DESKS, which only
    # gates the marriage-gossip rule - it had never been a ban, so its religious-freedom
    # output published freely; a source Chris rules out has to reach THIS list, not a
    # topic-specific one. And "Topeka Capital-Journal" is a Gannett masthead of the
    # <City> Capital-Journal shape, so the token is anchored to Topeka rather than left as a
    # bare "capital-?journal" that would also take the Kansas and Ohio papers with it.
    r"|dainik[- ]?jagran|muslim[- ]?network[- ]?tv|\bnews18\b|nenews|topeka[- ]?capital"
    r"|basketballnews|the[- ]?catholic[- ]?thing|oz[- ]?arab", re.I)



# "Christian" is also a first name, and "Christian Gonzalez" (NFL cornerback) and "Christian
# Walker" (Astros first baseman) put five sports items into Church & Religion on 16.08.2026.
# Chris flagged the same collision in his markup. A faith word immediately followed by a
# capitalised surname is a person, not a subject.
# The faith word must be matched case-insensitively but the SURNAME must stay capitalised -
# that asymmetry is the whole signal, so the flag is scoped rather than global.
NAME_COLLISION = re.compile(
    # Only words that are also common GIVEN names. "Bishop Mutsaerts" and "Pope Leo" are
    # titles - the person is the subject and the story is genuinely religious.
    r"\b(?i:christian|grace|faith|trinity|chastity|mercy)\s+[A-Z][a-z]+")
SPORTS_OUTLETS = re.compile(
    r"mlb\.com|bleacher report|profootballrumors|nfl rumors|espn|sky sports|talksport"
    r"|basketball network|front office sports|your sports edge|nbc sports|cbs sports"
    r"|the athletic|sportskeeda|goal\.com", re.I)


# Organisations whose name begins with a faith word. Without this, "Christian Concern
# responds to cohabitation plans" reads as a person called Christian.
FAITH_ORGS = re.compile(
    r"christian (concern|today|post|institute|solidarity|aid|legal|daily|headlines"
    r"|medical|reform|network|broadcasting|science|coalition|action|research|union)"
    r"|faith (matters|leaders|action)|grace (community|church|bible)"
    r"|trinity (college|church|school)|mercy (ships|corps|health)", re.I)


# Sport and showbiz vocabulary - positive evidence that a faith word is somebody's name.
PERSON_CONTEXT = re.compile(
    r"\b(contract|extension|traded?|signing|signed|draft|roster|practice|preseason"
    r"|season|game|games|match|innings|touchdown|homer|home run|slugger|cornerback"
    r"|quarterback|striker|midfielder|coach|lineup|injury|injured|scored|playoff"
    r"|blast|rally|win over|defeat|astros|patriots|seahawks|yankees|dodgers|wnba|nba"
    r"|hairstyle|girlfriend|boyfriend|red carpet)\b", re.I)



# Celebrity-marriage gossip. Chris marked the Harry & Meghan item on 15.08.2026 - "Celebrity
# marriage stories can sometimes be worth covering but this gossip is not" - and I failed to
# implement it; the next edition carried six of them, mostly from Indian entertainment desks
# whose output reaches Marriage, Family & Education on the word "marriage" alone.
#
# Keyed on tabloid FRAMING rather than on names, because a list of celebrities is unbounded
# and out of date the moment it is written. The framings are what generalise: a prenup
# detail, a bombshell, someone recalling family opposition, someone breaking silence.
# Marriage as public policy or crime, which must survive the gossip rule.
CIVIC_MARRIAGE = re.compile(
    r"child marriage|forced marriage|sham marriage|marriage fraud|interfaith marriage"
    r"|same-sex marriage|marriage (law|bill|act|rate|tax|allowance|policy|equality)"
    r"|cohabit|divorce (law|reform|rate)|court|tribunal|ruling|convict|charged|arrest"
    r"|government|minister|parliament|legislat|bishop|church|christian|catholic", re.I)

GOSSIP = re.compile(
    r"bombshell|make-?or-?break|explodes amid|breaks? (her |his |their )?silence"
    r"|prenup|hidden detail|secret (wedding|romance|deal talks)|controversial marriage"
    r"|recalls? family opposition|opens? up about (her|his|their) (marriage|divorce|split)"
    r"|spotted (with|together)|steps out with|cosy|cozy up|sparks .{0,20}rumou?rs"
    r"|fuels .{0,20}rumou?rs|inside .{0,30}(marriage|divorce|split)|marriage hell"
    r"|\| bollywood|year-younger|age-shaming|wedding certificate|marriage decision"
    r"|i married the wrong|love life|dating history|ex-?wife|ex-?husband", re.I)
# Entertainment desks whose marriage coverage is never our subject.
ENTERTAINMENT_DESKS = re.compile(
    r"telangana today|news18|pinkvilla|koimoi|bollywood hungama|filmfare|etimes"
    r"|hindustan times.*bollywood|zoom tv|india forums", re.I)


def is_name_collision(headline):
    """A faith word used as somebody's personal name.

    The first version stripped the matched pair and looked for religion in what was left,
    which destroyed the evidence: "Kidnapped Christian Worshipers in Southern Nigeria" lost
    "Worshipers" along with "Christian" and read as a man called Christian. It suppressed 51
    items including the Jaranwala convictions. Title-case headlines make every noun look like
    a surname, so the pattern alone can never decide this - positive evidence of a person is
    required, and in practice that means sport and contract vocabulary.
    """
    if FAITH_ORGS.search(headline):
        return False
    if not NAME_COLLISION.search(headline):
        return False
    return bool(PERSON_CONTEXT.search(headline))



EXCLUSIONS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "exclusions.txt")


def load_exclusions():
    """Headlines Chris has ruled out individually, where no rule generalises the judgement."""
    try:
        with open(EXCLUSIONS_PATH) as fh:
            return [ln.strip() for ln in fh
                    if ln.strip() and not ln.lstrip().startswith("#")]
    except OSError:
        return []


EXCLUSIONS = load_exclusions()


def is_excluded(headline):
    h = (headline or "").lower()
    return any(x.lower() in h for x in EXCLUSIONS)


def is_blocked_outlet(outlet=""):
    """True if Chris has ruled this outlet out entirely.

    Pulled out of is_chaff on 20.08.2026. Folding the two together meant a source he had
    BANNED was printed in the CHAFF bucket, under a heading reading "pick from here if one
    is genuinely news" - and on 20.08 that invitation was taken literally and three
    Christianity Daily items were published against a standing decision from 19.08. A ban
    and an over-matching filter need opposite responses, so they no longer share a bucket.
    compose.py imports this rather than keeping its own copy, so the two cannot drift.
    """
    return bool(outlet and BLOCKED_OUTLETS.search(outlet))


def is_chaff(headline, outlet="", categories=None):
    """True if the headline is celebrity/sport/schedule filler and nothing more."""
    if is_excluded(headline):
        return True
    if NEWSLETTER_INDEX.match(headline or ""):
        return True
    if is_blocked_outlet(outlet):
        return True
    # Unconditional, and ahead of every rescue: no subject matter redeems porn spam.
    if PORN_SPAM.search(headline or ""):
        return True
    if outlet and SPORTS_OUTLETS.search(outlet):
        return True
    if GOSSIP.search(headline) and not CIVIC_MARRIAGE.search(headline):
        return True
    if outlet and ENTERTAINMENT_DESKS.search(outlet) and not CIVIC_MARRIAGE.search(headline):
        return True
    if is_name_collision(headline):
        return True
    # Publisher tags it as arts/culture filler - Chris marked these "Not interesting".
    if category_is_filler(categories):
        return True
    if ROUNDUP.search(headline):
        return True
    if outlet and CELEB_SOURCES.search(outlet):
        # A blanket ban here repeated the "slams" mistake within minutes of fixing it:
        # People.com also carried the Massachusetts abortion law and the Texas surrogacy
        # birth, both of which Chris wanted. So these outlets are kept only for hard news,
        # and the weak family words that let showbiz through - marriage, divorce, baby -
        # are deliberately not in CELEB_KEEP.
        return not CELEB_KEEP.search(headline)
    if CHAFF_HARD.search(headline):
        return True
    return bool(CHAFF_RE.search(headline)) and not CHAFF_RESCUE.search(headline)


def diversify(rows, per_outlet, exempt_at=None):
    """Hold any one masthead to `per_outlet` items at the top of a section.

    The unfiltered commentary magazines publish all day and score well, so they crowd out
    everything else: on 13.08.2026 The Critic, UnHerd and spiked were 17 of the 28 Free
    Speech candidates, and Other led with four consecutive Daily Signal pieces. Chris asked
    that a section not be "just full on one source". Overflow is not dropped - it moves to
    the visible tail, so a big day at one outlet is still there to pick from.

    Chris, 13.08.2026: an outlet "can take more than three slots if important". So the cap
    is a tie-break among ordinary items, never a ceiling on good ones - anything scoring
    `exempt_at` or above ignores it. A day when The Spectator files six strong pieces should
    read as six Spectator pieces; what the cap stops is six *filler* pieces crowding out
    other mastheads.
    """
    if not per_outlet or per_outlet <= 0:
        return list(rows), []
    seen, top, over = {}, [], []
    for it in rows:
        key = (it["outlet"] or "?").lower()
        seen[key] = seen.get(key, 0) + 1
        if seen[key] <= per_outlet or (exempt_at is not None
                                       and importance(it) >= exempt_at):
            top.append(it)
        else:
            over.append(it)
    return top, over

# Spanish and Italian public affairs, appended so the Other bucket is reachable too.
_ML_OTHER = (r"|gobierno|ministr|parlament|congreso|senado|\bley\b|proyecto de ley|decreto"
             r"|tribunal|juez|sentencia|fiscal|denuncia|detenid|elecciones|votaci[oó]n"
             r"|referend|migrant|inmigraci[oó]n|deportaci[oó]n|sanidad|hospital|ayuntamiento"
             r"|comunidad aut[oó]noma|governo|ministr|parlamento|senato|\blegge\b"
             r"|disegno di legge|decreto|tribunale|giudice|sentenza|procura|arrestat"
             r"|elezioni|\bvoto\b|referendum|migrant|immigrazione|espulsione|sanit[aà]"
             r"|ospedale|comune\b|regione\b")


# ---------------------------------------------------------------------------
# "Other" is not a residual bucket.
#
# Chris, 16.08.2026: "The other section shouldn't be a dump for news that didn't make other
# sections but genuinely interesting high ranking news on new AI features etc."
#
# So it stops being "matched nothing but reads as public affairs" - which is how it became a
# third of the day - and becomes a positive category with its own subject matter. An item has
# to earn Other, not merely fail everywhere else.
# ---------------------------------------------------------------------------
# Long-form ideas essays. Chris gave two exemplars on 17.08.2026 - the Cosmos Institute's
# "AI and the ownership..." reading list and a Poetry Foundation essay on nostalgia - saying
# these are "the kind of articles we should populate it with". Neither matches OTHER_INTEREST:
# what makes them wanted is their character, not their topic, so gate on the source the way
# SOURCE_HINTS does rather than inventing keywords for "thoughtful". Items from these outlets
# reach Other without needing a subject keyword. Keep the list to outlets that publish little
# and publish essays - a general-interest magazine here would reopen the landfill.
ESSAY_SOURCES = re.compile(
    r"cosmos institute|the browser|\baeon\b|new atlantis|comment magazine"
    r"|asterisk|nautilus|marginalian", re.I)

OTHER_INTEREST = re.compile(
    # AI and the technology that shapes public life
    r"\bA\.?I\.?\b|artificial intelligence|machine learning|\bLLM\b|chatbot|chatgpt"
    r"|openai|anthropic|\bclaude\b|gemini|copilot|deepfake|algorithm|automation"
    r"|robot(ics)?|driverless|autonomous vehicle|quantum comput|semiconductor|\bchips?\b"
    r"|big tech|silicon valley|\bmeta\b|google|microsoft|apple\b|amazon\b|\bx\.com\b"
    r"|social media (ban|law|rules|platform)|smartphone ban|screen time"
    # science and medicine of consequence
    r"|breakthrough|clinical trial|vaccine|pandemic|\bWHO\b|gene therapy|stem cell"
    r"|fertility (breakthrough|research)|life expectancy|birth ?rate|population"
    r"|space (mission|telescope|launch)|\bNASA\b|mars\b|asteroid"
    # the world moving
    r"|war\b|ceasefire|peace (deal|talks|treaty)|treaty|summit|sanctions|coup\b"
    r"|famine|earthquake|hurricane|wildfire|flood(ing|s)?\b|nuclear"
    r"|energy (crisis|policy|prices)|inflation|recession|interest rates"
    # Added 19.08.2026, the only two of the day's 40 hand-rescues that genuinely belong in
    # Other rather than in a section of their own: great-power geopolitics with no country
    # keyword ("The Arctic: China Taking Over the Top of the World"), and online
    # radicalisation ("Children becoming 'intoxicated by extremism' online").
    r"|arctic|south china sea|taiwan strait|geopolitic|great power|sphere of influence"
    # Bare "extremis" admitted a Guardian fitness column about "endurance extremists" the
    # same morning, which is precisely the landfill this gate exists to prevent - so the
    # radicalisation sense is anchored to an online/ideological referent.
    r"|radicalis|radicaliz|violent extremis|counter-?extremis"
    r"|extremis\w*\b.{0,25}(online|content|propaganda|material|network)"
    r"|(online|social media|internet)\b.{0,30}extremis", re.I)


# An item that matched no section is only interesting if it reads as public affairs.
# Without this gate, "Other" fills with arts, history and lifestyle pieces from the
# unfiltered magazines (Henry VIII, shallots, Ricky Gervais).
OTHER_ALLOW = re.compile(_ML_OTHER.lstrip("|") + "|" +
    
    r"polic\w+|politic|government|minister|parliament|senate|congress|white house"
    # laws?/bills? not law\b/bill\b: the anchored singular silently dropped every plural,
    # e.g. "...targets 'Conversion' and 'Land Jihad' with tough new laws in state".
    r"|election|campaign|vote|bills?\b|laws?\b|legal|court|judge|ruling|tribunal|inquiry"
    r"|prosecut|crime|prison|migrant|migration|asylum|immigration|border|deport"
    r"|welfare|benefits|tax|economy|budget|spending|council|mayor|devolution"
    r"|\bNHS\b|hospital|doctor|nurse|health|care home|social care"
    r"|\bDEI\b|diversity|woke|equity|inclusion|discrimination|racism|antisemit"
    r"|protest|strike|union|charity|regulator|watchdog|surveillance|privacy"
    r"|\bAI\b|artificial intelligence|technology|social media|smartphone|online"
    r"|universit\w*|school|education|ofsted|curriculum|exam"
    r"|report|research|study|survey|poll|data|figures|statistics|census"
    r"|privilege|socialis|capitalis|free market|hypocrisy|scandal|resign|apolog"
    r"|war|conflict|terror|military|defence|sanction|treaty|\bUN\b|europe|brexit"
    # Gaps found on 14.08.2026 by auditing what fell through with NO section at all.
    # Each of these was a real story the briefing silently dropped:
    # party and politician names, because a by-election piece need not say "election"
    # ("Nigel Farage's hollow victory", "Zia Yusuf has become a liability for Reform");
    r"|farage|\breform\b|labour|tor(y|ies)|lib dem|\bsnp\b|starmer|burnham|badenoch"
    r"|by-?election|victory|defeat|majority|seat\b|constituency|manifesto"
    # education, where "exam" and "school" missed results-day coverage entirely
    # ("Boys Widen Lead Over Girls in A-level Top Grades");
    r"|a-?levels?|gcses?|btec|grades?|pupils?|students?|teacher|headteacher|admissions"
    # defence spelled as a verb, and the country names themselves
    # ("Zelensky: We need US to sell us 10pc of its Patriots to defend Ukraine");
    r"|defend|missile|ukraine|russia|nato|zelensky|putin|gaza|israel|iran|hamas"
    # and religious-practice words the Church section does not itself carry
    # ("Adult baptisms increase in Germany as overall numbers continue to decline").
    r"|baptis|congregation|parish|seminar(y|ians)|ordination|vocations",
    re.I)


def score_sections(headline, outlet):
    """Return [(score, section)] best first, for the six keyword sections."""
    blob = outlet.lower()
    out = []
    for name, pats in COMPILED:
        s = sum(w for w, rx in pats if rx.search(headline))
        if s and any(h in blob for h in SOURCE_HINTS.get(name, [])):
            s += SOURCE_BOOST
        if s:
            out.append((s, name))
    out.sort(key=lambda x: (-x[0], SECTION_NAMES.index(x[1])))
    return out


# Church & Society is a residual bucket: only take an item if no specific section wanted
# it with real confidence.
# --- ranking -------------------------------------------------------------------
# The keyword score decides WHICH SECTION an item belongs to and is good at that.
# It is a poor guide to importance, because it just counts how many keyword groups a
# headline happens to contain: on 12.08.2026 "Pope Leo sends letter of solidarity to
# CofE church" scored 11 (pope + CofE + church) while "British bishop calls new PM to
# bat for jailed Catholic Hong Kong activist Jimmy Lai" scored 5 and fell below the
# display cut. These two bumps apply to RANKING ONLY.

# Outlets Chris actually cites. Anything from them outranks local filler.
SOURCE_TIER = [
    "crux", "catholic herald", "christian today", "premier christian", "lifesitenews",
    "lifenews", "live action", "spuc", "right to life", "international christian concern",
    "persecution.org", "morningstar", "alliance defending freedom", "adf", "christian concern",
    "christian institute", "spiked", "the critic", "unherd", "spectator", "telegraph",
    "the times", "reduxx", "sex matters", "free speech union", "national review",
    "daily signal", "federalist", "daily wire", "wng", "world news group",
    "washington stand", "national catholic", "ncregister", "ewtn", "osv news",
    "catholic world report", "bitter winter", "open doors", "iona institute",
    # "anglican mainstream" and "truth nigeria" were BOTH here and both blocked - a blocked
    # outlet listed as a preferred one. Inert, because a blocked item never reaches a cluster,
    # but it is exactly the stale contradiction a future reader trips over. Removed 24.08.2026.
    "christian post", "catholic news agency", "vatican news",
    "first things", "public discourse", "gb news", "the tablet", "church times",
    "euthanasia prevention", "thomas more", "scotusblog",
    # Gap surfaced on 14.08.2026: Baptist Press ran in that edition but was untiered,
    # so an untiered aggregator beat it inside a duplicate cluster.
    "baptist press", "catholic review", "catholic sun", "the pillar", "zenit",
    # Chris, 31.08.2026: APPENDED, not inserted, so his order of preference above is
    # untouched. SOURCE_TIER held no mainstream national beyond the Telegraph, Times and
    # GB News, so on the trans-military filing Advocate.com - an advocacy outlet, unlisted
    # - led a cluster of eight over the Washington Post's own report on keyword score
    # alone, and he added that link back by hand. Only the case he flagged is added here;
    # the wider gap (Guardian, BBC, Sky, Independent, Mail all absent) is his call.
    "washington post",
]
TIER_BUMP = 6

# Organisations that generate the documents other outlets then report on. Inside a
# duplicate cluster these win, because the release IS the story and Chris wants the
# body that published it cited, not whoever aggregated it (Chris, 14.08.2026).
PRIMARY_SOURCE = [
    "alliance defending freedom", "adf international", "adfmedia", "adf",
    "spuc", "right to life", "international christian concern", "persecution.org",
    "sex matters", "free speech union", "liberty justice center", "chinaaid",
    "barnabas aid", "open doors", "national right to life", "euthanasia prevention",
    "australian christian lobby", "christian concern", "christian institute",
    "family first", "iona institute", "thomas more", "forum 18", "bitter winter",
    # Adversarial bodies count too: on a suit they filed, their own filing is the
    # primary document, and provenance is not an ideological judgement.
    "aclu", "liberty counsel", "becket",
]
PRIMARY_BUMP = 4

# Outlets the coverage check watches (compose.py). PRIMARY_SOURCE plus the issue press whose
# reporting Chris repeatedly asks for and which is structurally easy to miss: single-outlet
# pieces, x1 by construction, sinking in a corroboration-ordered sheet. Kept SEPARATE from
# PRIMARY_SOURCE on purpose - that list means "published the document itself" and drives
# provenance ranking, so putting newsrooms in it would hand them cluster wins they have not
# earned. This list carries no ranking weight at all; it only decides what gets flagged when
# a source files and nothing of theirs is picked. Built from his 24.08.2026 markup, where
# Desiring God, Live Action, WORLD, the Daily Signal and the Federalist were all missed.
COVERAGE_WATCH = PRIMARY_SOURCE + [
    "desiring god", "live action", "liveaction", "wng", "world news group",
    "daily signal", "federalist", "catholic herald", "premier christian", "christian today",
]

# Where two primary sources collide, name the winner explicitly rather than leaving it
# to score noise. ADF International beats EWTN on the UN-letter-to-Nigeria story and
# every future one like it (Chris, 14.08.2026).
# Chris, 24.08.2026: "prefer the Guardian over Premier generally". On the TEST 20260824 draft
# the Lib Dems religious-discrimination story ran from Premier - "Good article but the Guardian
# as a source article would have been better". Premier files short wire-style pieces on stories
# the Guardian reports at length, and both are in SOURCE_TIER, so the tie was going to feed
# order. This is a general preference, not a one-off for that story.
CLUSTER_PREFER = [("alliance defending freedom", "ewtn"), ("adf", "ewtn"),
                  ("guardian", "premier")]
PREFER_BUMP = 20

# Institutional action tracks news value far better than keyword repetition.
ACTION = re.compile(
    r"court|ruling|judge|verdict|bill\b|\blaw\b|legislat|sentenc|convict|arrest|jailed"
    r"|imprison|detain|ban(ned|s)?\b|inquiry|tribunal|lawsuit|sues?\b|petition|veto"
    r"|resign|sacked|fired|killed|murder|abduct|kidnap|raid|deport|struck down|upheld"
    r"|passes|approves|rejects|blocks|orders|warns|report finds|study finds", re.I)
ACTION_BUMP = 3


STOPW = set("the and for over with that from have has was are will says said into amid"
            " his her their its new not but who what how why after before their they".split())


def _stem(w):
    """Crude suffix strip so outlets' different phrasings of one story still match.

    Without it, "marriage fraud scheme" and "marriage fraud schemes" shared only two
    significant words and fell under the overlap threshold - which is how eight versions of
    one green-card sweep each took its own line at the top of 13.08.2026's sheet, and why
    its corroboration count read x2 instead of x8. Deliberately not a real stemmer: this
    only has to make plurals and tenses of the same word agree.
    """
    for suf in ("ational", "ing", "edly", "ies", "ed", "es", "s"):
        if w.endswith(suf) and len(w) - len(suf) >= 4:
            return w[:-len(suf)] + ("y" if suf == "ies" else "")
    return w


def _deaccent(s):
    """Fold accents to ASCII, so an accented name survives tokenising as ONE word.

    Chris, 28.08.2026: "This is old news and should have been deduplicated" - BGEA's "UK
    Drops Travel Ban for Päivi Räsänen" against Christian Today's "Päivi Räsänen granted UK
    visa" three days earlier. Not a threshold problem. sig_words strips [^a-z0-9] BEFORE
    tokenising, so every accented word was SPLIT at the accent and the fragments then failed
    the length gate: "Päivi" -> "p"/"ivi", "Räsänen" -> "r"/"s"/"nen", all discarded. Her
    name was invisible to sig_words, to ENTITY_RE (whose [A-Z][a-z]{2,} cannot match "Pä"
    either) and therefore to every clustering and repeat check that reads them.

    The blast radius was never one Finn: "Müller" tokenised as "ller", "Gutiérrez" as
    "guti"+"rrez", "México" as "xico", "Orbán" vanished. Every non-English name in the sweep
    was either destroyed or replaced by junk that could only match other junk.
    """
    return unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode("ascii")


def sig_words(headline):
    t = re.sub(r"[^a-z0-9 ]", " ", _deaccent(headline).lower())
    return {_stem(w) for w in t.split() if len(w) > 3 and w not in STOPW}


# A primary source that is RELAYING a newsroom is not the primary source of that story.
#
# Chris, 31.08.2026. PRIMARY_SOURCE exists because an advocacy body's own release IS the
# document (the ADF/EWTN case, 14.08.2026). But the bump was unconditional, so it also fired
# when the body was simply passing on someone else's reporting - and then it SUPPRESSED that
# reporting. Six newsrooms filed on Burnham abstaining (Telegraph, Times, Independent x2,
# Manchester Evening News, LBC) and all six collapsed under SPUC's item, whose own summary
# opens "According to Politics UK, Andy Burnham has told Labour MPs...". The sheet shows one
# line per story, so only SPUC's was ever visible and the edition ran an opinion column where
# the news report should have been.
#
# Tested on the item's own FEED SUMMARY, not its article text: clustering happens before
# attach_openings, so at this point the text does not exist yet. The summary is free and,
# for the cases that matter, carries the attribution verbatim.
#
# The institution guard is the half that keeps the original behaviour intact. "According to a
# new Government assessment" is Right To Life reading a document - tier 1 in the same edition
# - and "according to the United Nations" is ADF citing the body whose letter it published.
# Only attribution to something that is NOT an institution counts as a relay.
_RELAY_ATTRIB = re.compile(
    # trigger matched case-insensitively, the NAME case-sensitively: requiring a capitalised
    # proper noun is what separates "According to Politics UK" from "according to a report".
    r"\b(?i:according to|as (?:first )?reported by|citing|per)\s+(?:the\s+)?"
    r"((?:[A-Z][\w’'&.\-]*\s+){0,3}[A-Z][\w’'&.\-]*)"
    r"|((?:[A-Z][\w’'&.\-]*\s+){0,3}[A-Z][\w’'&.\-]*)\s+(?:reports|reported|has reported)\b")

_INSTITUTION = re.compile(
    r"government|court|commission|ministr|department|office|council|parliament|senate"
    r"|congress|assembly|tribunal|inquiry|committee|police|nhs|united nations|\bun\b"
    r"|\bwho\b|assessment|survey|census|study|data|figures|statistics|report\b|analysis"
    r"|minister|bishop|diocese|conference|charity|organisation|organization|foundation"
    r"|institute|society|association|coalition|campaign|spokes|university|hospital"
    r"|ombudsman|regulator|authority|agency|bureau|council", re.I)


def relays_another_outlet(item):
    """True if a PRIMARY_SOURCE item attributes its story to another news outlet.

    Only ever True for a primary source: a newsroom does not hold the provenance bump, so
    it has nothing to lose and must not be penalised for ordinary sourcing.
    """
    outlet = (item.get("outlet") or "").lower()
    if not any(t in outlet for t in PRIMARY_SOURCE):
        return False
    for m in _RELAY_ATTRIB.finditer(item.get("summary") or ""):
        name = (m.group(1) or m.group(2) or "").strip()
        if not name or _INSTITUTION.search(name):
            continue
        # Its own name is not a relay - "SPUC reports" is SPUC reporting.
        if name.lower() in outlet or outlet.split()[0:1] and outlet.split()[0] in name.lower():
            continue
        return True
    return False


def cluster_rank(item):
    """Rank WITHIN a duplicate cluster. Deliberately not rank_score.

    Every member of a cluster is the same story, so news-value signals must not choose
    between them - that is a category error. ACTION_BUMP exists to rank DIFFERENT
    stories, and on 14.08.2026 it silently demoted ADF International's own release
    ("UN Experts Release Letter ... Warning of ...", 11) below EWTN's write-up of it
    ("UN letter warns Nigeria ...", 14) purely because the regex matches the active
    verb "warns" but not the noun "Warning". Advocacy bodies title releases in nouns
    and newsrooms use active verbs, so that bias was systematic, not a one-off.

    Inside a cluster the questions that actually matter are provenance and link
    quality, so rank on: primary source, outlet tier, whether it already ran, the
    keyword score, then a direct publisher link over an unresolved redirect.

    Precedence is a tuple, not a sum, so a cosmetic signal can never outrank a real
    one. An additive version of this was tried first and was worse: a +2 "direct link"
    bump beat TIER_BUMP and handed 11 of 78 clusters to outlets Chris does not cite
    (National Desk over Baptist Press, Spectator Australia over the Telegraph) while
    promoting two stories that had already run on 08-13.
    """
    outlet = (item.get("outlet") or "").lower()
    # SOURCE_TIER is written in Chris's rough order of preference, so its index breaks
    # ties between two cited outlets. Without this the winner was just feed order: the
    # two pairs the 12.08.2026 fix was built around (Catholic Herald vs OSV News,
    # Telegraph vs GB News) score identically and were decided by luck.
    _tp = source_tier_pos(item.get("outlet"))
    tier_pos = len(SOURCE_TIER) if _tp is None else _tp
    # 2 = a primary source publishing its own document, 1 = everything else, 0 = a primary
    # source merely relaying a newsroom, which must not outrank that newsroom's own report.
    relays = relays_another_outlet(item)
    primacy = 0 if relays else (2 if any(t in outlet for t in PRIMARY_SOURCE) else 1)
    return (
        primacy,                                                # who published it
        1 if _tp is not None else 0,                            # outlets Chris cites
        0 if item.get("seen_on") else 1,                        # don't re-lead old news
        -tier_pos,                                              # preferred outlet first
        0 if (item.get("url") or "").startswith("https://news.google.com/") else 1,
        item.get("_score", 0),
    )


def apply_cluster_preference(group):
    """Promote a named winner to the front, but only if its counterpart is really here.

    Applied per-cluster rather than as a score bump on the item, because a global
    penalty would demote EWTN in every cluster it appears in - including the many that
    contain no ADF item at all, where EWTN is the right lead and would have been pushed
    below local filler.
    """
    for winner, loser in CLUSTER_PREFER:
        w = next((it for it in group if winner in (it.get("outlet") or "").lower()), None)
        if w is None or w is group[0]:
            continue
        if loser in (group[0].get("outlet") or "").lower():
            group.remove(w)
            group.insert(0, w)
            return


# Chris, 15.08.2026: "Dedupe stories like this unless they're of huge importance or mention
# ADF International, Christian Concern or CitizenGO." The missionary release ran six times in
# the calibration edition. Extra angles now need to earn their place.
DEDUPE_EXEMPT = re.compile(
    r"ADF International|Alliance Defending Freedom|Christian Concern|CitizenGO"
    r"|Christian Legal Centre", re.I)



# ---------------------------------------------------------------------------
# Entity clustering.
#
# Word-overlap clustering matches wire copy well - eleven outlets on the Virginia State
# shooting all write nearly the same sentence - but it cannot connect a report to an
# argument about that report, because a good comment headline deliberately avoids restating
# the news. On 14.08.2026 five items covered Jason Arday's death; the three news reports
# clustered, the two spiked comment pieces did not, because they shared only the name.
#
# The fix is to treat a RARE shared proper noun as a link. "Jason Arday" in five headlines on
# one day is near-conclusive. Frequency is what keeps it safe: "Trump" or "Supreme Court"
# appear in dozens of items and would merge the whole briefing, so only entities appearing in
# a handful of items count, and a name-only link additionally needs some topical overlap.
# ---------------------------------------------------------------------------
ENTITY_STOP = {
    "The", "A", "An", "This", "That", "New", "Why", "How", "What", "When", "Who", "After",
    "But", "And", "For", "In", "On", "At", "Of", "To", "Is", "Are", "Was", "Were", "Will",
    "Not", "No", "Says", "Said", "Live", "Watch", "Exclusive", "Breaking", "Opinion",
    "First", "Last", "More", "Most", "Now", "One", "Two", "Three", "It", "He", "She", "They",
    "There", "Here", "These", "Those", "Their", "Some", "Only", "Even", "Just", "Still",
}
ENTITY_RE = re.compile(r"\b([A-Z][a-z]{2,}(?:\s+[A-Z][a-z]{2,}){0,2})\b")
ENTITY_MIN_DF = 2       # must appear in at least two items to be a link at all
ENTITY_MAX_DF = 12      # above this it is a topic, not a story
# Significant words two headlines must ALSO share before a rare entity links them. See the
# reasoning in same_story(). Tightening ENTITY_MAX_DF instead was measured on 18.08.2026 and
# is the weaker lever (27.9% wrong at MAX_DF=5, against 22% from this floor), so the DF gate
# is left alone: it decides which entities are distinctive, this decides what a link means.
ENTITY_COOCCUR_MIN = 3


def entities(headline):
    """Multi-word proper nouns, minus sentence-initial noise."""
    out = set()
    # Deaccented first: ENTITY_RE is [A-Z][a-z]{2,}, which cannot match "Päivi" or "Orbán",
    # so accented names were not entities at all. See _deaccent().
    for m in ENTITY_RE.finditer(_deaccent(headline)):
        phrase = m.group(1).strip()
        words = [w for w in phrase.split() if w not in ENTITY_STOP]
        if not words:
            continue
        if len(words) >= 2:
            out.add(" ".join(words).lower())
        elif len(words[0]) >= 5:
            out.add(words[0].lower())
    return out


def ent_tokens(headline):
    """Normalised single tokens from a headline's entities.

    entities() returns PHRASES, because ENTITY_RE takes runs of up to three capitalised
    words - and in a title-cased headline that produces both garbage ("Prime Minister
    Texted") and, worse, phrases that cannot match their own components. On 19.08.2026 the
    Susie Wiles impersonator story ran as two unlinked leads because one headline yielded
    "susie wiles impersonator" and the other "wiles", and phrase equality never fired. The
    Philippine school shooting split the same way on "philippine" vs "philippines".

    Tokens fix both, and the document-frequency gate works BETTER on them: a rare phrase
    built from common words ("supreme court appeal") used to pass as distinctive, while a
    common token inside it now correctly fails on its own frequency.
    """
    out = set()
    for phrase in entities(headline):
        for word in phrase.split():
            if len(word) >= 5:
                # Light plural fold, long words only - keeps Wales/Wale and Texas/Texa apart.
                out.add(word[:-1] if len(word) > 6 and word.endswith("s") else word)
    return out


def region_text(item):
    """The article's own opening, for regions.region(). One helper so every call site agrees.

    Order matters: a fetched opening beats a feed summary, because the summary is very often
    a bare headline echo and echoing the headline can only ever repeat the headline's own
    geography. Returns "" when there is nothing, which is the no-op case.
    """
    return (item.get("_opening") or real_summary(item) or item.get("_lede") or "")[:600]


def entity_index(rows):
    """entity token -> list of row ids, keeping only the distinctive ones."""
    df = {}
    for it in rows:
        for e in ent_tokens(it["headline"]):
            df.setdefault(e, []).append(id(it))
    return {e: ids for e, ids in df.items()
            if ENTITY_MIN_DF <= len(set(ids)) <= ENTITY_MAX_DF}


# Words that mark a story as having MOVED ON rather than being another report of the same
# event. Chris, 17.08.2026: "her giving the baby back is new detail compared to what we had
# before so we need to assess clustered stories for details and only dedupe the same stories
# rather than updates." The surrogacy cluster collapsed "surrogate will fight for custody"
# (process) into the same group as "parents GET custody" (outcome) and led with the process.
DEVELOPMENT = re.compile(
    r"\b(gives? birth|born|gets?|granted|awarded|wins?|won|loses?|lost|overturn\w*|upheld"
    r"|uphold\w*|convicted|acquitted|sentenc\w*|released|freed|resign\w*|elected|struck down"
    r"|blocked|approved|rejected|dismissed|settle[ds]?|dropped|dies?|died|arrested|charged"
    r"|handed over|returns?|returned|reunited|custody)\b", re.I)
#
# Do NOT extend this list with more outcome verbs. Tried on 27.08.2026 and reverted the same
# hour: adding "passes" broke the France Constitutional Court pair in testcases.txt, because
# is_development_of fires on ASYMMETRY - one headline carrying a word the other lacks - and
# "approves" was not in the list. Two reports of one ruling then looked like two stages of a
# story. Every verb added here creates that trap with each of its own synonyms that is
# absent, so the list is safer incomplete than half-extended. The prospective/outcome axis
# below is the safe way to separate stages, because it tests a property both headlines have.

# Language that places a story BEFORE the event, as against reporting the event. A separate
# axis from DEVELOPMENT above, which lists outcomes: "MPs to vote on the Bill" and "MPs vote
# down the Bill" share almost every significant word and neither carried an outcome verb, so
# the cross-day check called the second a repeat of the first. A scheduled event and its
# result are never the same story.
PROSPECTIVE = re.compile(
    r"\bto (vote|rule|decide|hear|consider|debate|publish|announce|introduce|table|meet)\b"
    r"|\bset to\b|\bexpected to\b|\bdue to (vote|rule|decide|begin|start)\b"
    r"|\bpoised to\b|\bprepares? to\b|\bplans? to\b|\blooks? set to\b"
    r"|\bahead of (the |a )?(vote|ruling|hearing|debate|reading|decision)\b"
    r"|\bcountdown\b|\bweeks? left\b|\bdays? left\b", re.I)


# Was permission GIVEN or WITHHELD? A third axis, and built the way the warning above says a
# stage test has to be: it asks a question BOTH headlines answer, so it cannot fire merely
# because one of them happens to use a word the other's synonym list is missing.
#
# Chris, 28.08.2026, on the Räsänen arc. Three headlines, one story, and the DEVELOPMENT list
# scored all the wrong ones:
#   "UK Drops Travel Ban for Päivi Räsänen"        -> no match at all ("drops" absent)
#   "Päivi Räsänen granted UK visa but not in time" -> "granted"
#   "UK bars Finnish Christian MP Päivi Räsänen"    -> no match at all ("bars" absent)
# So the ban being LIFTED read as staged-against-unstaged and was called a development of
# itself, while the ban being IMPOSED and the ban being LIFTED both scored empty and could
# not be told apart. Exactly the asymmetry trap, from two absent synonyms.
#
# Extending DEVELOPMENT was the obvious fix and is the one that comment forbids, for good
# reason: ~20 present-tense forms would each open the same trap against their own missing
# synonyms. Polarity sidesteps it. Both headlines are placed on the axis or neither is, and
# two headlines on the SAME side are reporting the same moment however differently they word
# it — which is the claim _DEV_CLASSES makes one synonym pair at a time.
PERMISSION_GIVEN = re.compile(
    r"\b(grants?|granted|lifts?|lifted|drops?|dropped|allows?|allowed|admits?|admitted"
    r"|clears?|cleared|reinstates?|reinstated|restores?|restored)\b", re.I)
PERMISSION_REFUSED = re.compile(
    r"\b(bars?|barred|bans?|banned|denies|denied|refuses?|refused|revokes?|revoked"
    r"|suspends?|suspended|excludes?|excluded)\b", re.I)


# A lifting verb governing a restriction NOUN. "UK Drops Travel Ban" reads as both sides at
# once otherwise - "Drops" is the verb and "Ban" is merely its object - and that ambiguity is
# what left the headline unplaced on this axis and so still broken. Checked first, because the
# verb decides the direction and the noun is only what it acts on.
LIFTS_RESTRICTION = re.compile(
    r"\b(drops?|dropped|lifts?|lifted|overturns?|overturned|quashe?[sd]?|ends?|ended"
    r"|scraps?|scrapped|reverses?|reversed)\s+(?:\w+\s+){0,3}?"
    r"(ban|barring|exclusion|embargo|restriction|sanction)s?\b", re.I)


def _permission(headline):
    """'given', 'refused', or None when the headline does not sit on this axis at all.

    None for BOTH readings at once as well as neither: a headline arguing both ways is
    exactly the case where this axis has nothing useful to say, so it defers to the word
    lists rather than guessing.
    """
    if LIFTS_RESTRICTION.search(headline):
        return "given"
    given = bool(PERMISSION_GIVEN.search(headline))
    refused = bool(PERMISSION_REFUSED.search(headline))
    if given == refused:
        return None
    return "given" if given else "refused"


# DEVELOPMENT members that also have an everyday NOUN or ADJECTIVE reading. Chris,
# 27.08.2026: "Fix the DEVELOPMENT noun/verb collision."
#
# This list is short because it was measured rather than imagined. Scanning every DEVELOPMENT
# match across the archived editions, these five are the only members where a non-verbal
# reading actually occurs: "full return of religion classes", "is a win for", "The Lost
# Drive". The first heuristic tried - treat a match followed by "of" as nominal - looked
# right and is exactly backwards for the other candidates it flagged, because "convicted OF
# child rape", "acquitted OF inviting support" and "dies OF malaria" are all verbs taking a
# complement. It was measured, found to misread 60% of "convicted", and discarded.
DEV_AMBIGUOUS = re.compile(r"^(returns?|wins?|lost)$", re.I)

# What immediately precedes a noun and never a finite verb: a determiner, a possessive, a
# number or an ordinary attributive adjective. Deliberately a CLOSED list of function words
# plus the handful of adjectives that actually turn up in front of these five - an open-ended
# adjective list would eventually swallow a subject noun and start deleting real verbs.
DEV_NOMINAL_BEFORE = re.compile(
    r"\b(the|a|an|its|his|her|their|our|my|your|this|that|these|those|no|any|some|each"
    r"|every|another|both|either|neither|full|partial|complete|total|outright|swift|sudden"
    r"|dramatic|historic|eventual|surprise|shock|possible|likely|apparent|so-called"
    r"|first|second|third|fourth|final|latest|next|last|only|same|such)\s+$", re.I)


# Inflection. Two thirds of the blocked pairs the archive scan found were one word in two
# forms - win/wins, return/returns/returned, resign/resignation - and normalising those needs
# no semantic judgement whatsoever, which is why it is done first and separately from the
# classes below. Longest suffix first, and only on stems long enough to survive it.
_DEV_SUFFIXES = ("ation", "ings", "ing", "ies", "ed", "es", "s", "d")


def _dev_stem(token):
    token = token.lower().strip()
    for suf in _DEV_SUFFIXES:
        if token.endswith(suf) and len(token) - len(suf) >= 4:
            return token[: -len(suf)]
    return token


# Genuine synonymy, and ONLY where the archive scan produced a pair this function wrongly
# blocked. Each line names the pair that earned it. This is deliberately not a thesaurus: every
# class added here is a claim that two words describe the SAME moment, and a wrong one merges
# two real stories for good.
#
# "arrested"/"charged" is deliberately absent. The scan found one pair where they were the same
# story (a New Brunswick church arson reported a day apart), but arrest and charge are a real
# progression, and a class collapsing them would delete that signal everywhere else.
_DEV_CLASSES = [
    # "US missionary ... is released" / "American missionary ... freed"; and the same story
    # again as "reunited with wife".
    {"freed", "free", "frees", "releas", "released", "release", "reunit", "reunited"},
    # "Supreme Court upholds Trump's order" / "Supreme Court gives Trump an interim win".
    # "win"/"wins" are listed as both forms rather than stemmed: _dev_stem protects stems
    # shorter than four characters, because the alternative - stripping down to three - turns
    # "freed" into "fre" while "free" stays "free", which is worse than enumerating two words.
    {"uphold", "upholds", "upheld", "win", "wins", "back", "backs", "backed"},
    # "Texas drag show ban struck down" / "judge ... in overturning Texas drag show ban".
    {"struck down", "strike down", "overturn", "quash", "revers"},
]
_DEV_CLASS_OF = {}
for _n, _cls in enumerate(_DEV_CLASSES):
    for _w in _cls:
        _DEV_CLASS_OF[_w] = "class%d" % _n


def _dev_key(token):
    """The identity a development word is compared on: its class, else its stem."""
    stem = _dev_stem(token)
    return _DEV_CLASS_OF.get(stem) or _DEV_CLASS_OF.get(token.lower()) or stem


def _dev_matches(headline):
    """DEVELOPMENT hits in `headline`, with the nominal readings dropped."""
    out = set()
    for m in DEVELOPMENT.finditer(headline):
        token = m.group(0)
        if DEV_AMBIGUOUS.match(token) and DEV_NOMINAL_BEFORE.search(headline[:m.start()]):
            continue        # "full return of...", "a win for...", "the lost generation"
        out.add(_dev_key(token))
    return out


def is_development_of(a, b):
    """True when two same-subject items report DIFFERENT stages, not the same moment.

    Only fires when one carries a development word the other does not - so two reports of the
    same ruling still cluster, but "will fight for custody" and "parents get custody" do not.
    """
    ha, hb = a.get("headline") or "", b.get("headline") or ""
    # One looking forward to an event and the other reporting it are different stages, even
    # when neither names an outcome verb (27.08.2026).
    if bool(PROSPECTIVE.search(ha)) != bool(PROSPECTIVE.search(hb)):
        return True
    # Permission given vs withheld, when BOTH headlines sit on that axis. Decided here rather
    # than left to fall through, because the whole point is that it is more reliable than the
    # DEVELOPMENT word lists for this shape of story: same side means one moment worded two
    # ways, opposite sides mean the restriction was imposed and then lifted, which is the
    # genuine development in the arc. See _permission() (28.08.2026, the Räsänen markup).
    pa, pb = _permission(ha), _permission(hb)
    if pa and pb:
        return pa != pb
    da, db = _dev_matches(ha), _dev_matches(hb)
    if not da and not db:
        return False
    return bool(da ^ db) and not (da & db)


def same_story(a, b, wa, wb, shared_entities):
    """Word overlap as before, OR a distinctive shared entity plus a little topical overlap."""
    # Never cluster across sections. The French Constitutional Council ruled on assisted dying
    # AND an under-15 social media ban; ten reports of it classified into six sections, and the
    # cluster collapsed them all into the Life lead, so Jurist's free-speech angle never
    # appeared as its own line for curation (Chris flagged this 17.08.2026). Two sections means
    # two different concerns, which is exactly when both belong in the briefing.
    sa, sb = a.get("_section"), b.get("_section")
    if sa and sb and sa != sb:
        return False
    if is_development_of(a, b):
        return False
    if wa and wb:
        overlap = len(wa & wb) / max(1, min(len(wa), len(wb)))
        if overlap >= 0.55 or len(wa & wb) >= 5:
            return True
    if shared_entities:
        # A name alone is not enough - Farage on Clacton and Farage on welfare are two
        # stories. Require the name plus THREE other significant words in common.
        #
        # That floor was 1 until 19.08.2026, which barely implemented the intent above: one
        # shared significant word is nearly free, so any two stories sharing a rare-ish
        # entity merged. Measured against 18.08's picks, 32 of 219 duplicate flags were
        # demonstrably wrong - a story flagged "prefer that" which Chris had picked while
        # rejecting its lead. Four Indonesia earthquake reports were flagged as duplicates
        # of a Dearborn unity rally (entity "christian", zero other words shared), and a
        # California surrogacy case as a duplicate of a Texas Ten Commandments appeal.
        #
        # At >=3 the wrong flags fall to 12 and precision goes from 32% to 22% wrong. The
        # cost is 25 fewer correct flags, which is the right trade because the two errors
        # are not symmetric: a wrong flag says "prefer that" about a story Chris wanted and
        # risks losing it, while a missing flag costs one extra near-duplicate line to read.
        #
        # Verified both directions on that day's corpus and locked in testcases.txt: the
        # Wiles impersonator pair, the France Constitutional Court trio, Reform's welfare
        # plan and the Philippine school shooting all share >=3 and still merge; every
        # absurd pair above shares <=1 and no longer does.
        return len(wa & wb) >= ENTITY_COOCCUR_MIN
    return False


# --- Cross-day repeats --------------------------------------------------------------------
# Chris, 27.08.2026: "Build story clustering across days."
#
# STRICTER than same_story above, on purpose. Within a day a wrong merge costs one line off
# the sheet. Across days a wrong flag says "you already ran this", and the natural response
# is to drop it - so the expensive error is a false positive, and the thresholds are set to
# make that rare rather than to catch every repeat. A missed repeat costs a duplicate item in
# one edition; a false one costs a story that never ran at all.
# Set by repeat_eval.py on 27.08.2026, replacing the 0.70/6 these shipped at that morning.
# Those were chosen by eyeballing one day's flags on the reasoning that cross-day matching
# should be STRICTER than within-day, because a wrong cross-day flag invites dropping a story
# that never ran. Measured, that strictness bought nothing and cost 30 points of recall: at
# 0.70/6 the matcher found 43.9% of same-story pairs, at 0.55/5 it finds 73.6%, and the flag
# rate on 30,000 real cross-day same-section pairs moved from 13 to 19. Same question, same
# thresholds as same_story - the day between two headlines is not itself evidence.
CROSSDAY_OVERLAP = 0.55
CROSSDAY_WORDS = 5
# The ratio arm divides by the SMALLER significant-word set, so a short headline saturates it:
# "From the sea to the streets" reduces to one word, {street}, and scored 1.0 against every
# headline mentioning a street. Measured on the 27.08 picks, that mechanism produced the only
# two flags that were plainly wrong out of 50. Below this floor the ratio is not evidence and
# only the absolute-count arm may fire.
CROSSDAY_MIN_WORDS = 4
# The entity arm, cross-day. Off unless the caller supplies an index built over the UNION of
# today's corpus and the recent editions - a document frequency measured on one day cannot
# say whether a token is distinctive across a week. Numbers here are set by repeat_eval.py,
# not by argument; see repeat_eval_log.txt for what each change moved.
# Also 3, and also measured: at 4 recall was 0.439 against 0.540 at 3, with the cross-day
# flag rate unchanged to three decimal places. At 2 it gains one point of recall and 21
# same-day false positives, which is the trade this floor exists to refuse.
CROSSDAY_ENTITY_WORDS = 3
# Distinctive entity TOKENS that alone justify a cross-day link, with no other word overlap
# required. Two, i.e. a full personal name whose forename and surname each survive the DF gate
# independently. One is deliberately not enough: a single distinctive surname is how "Farage
# on Clacton" and "Farage on welfare" would merge, which is the same error the within-day
# ENTITY_COOCCUR_MIN exists to prevent (28.08.2026).
CROSSDAY_ENTITY_TOKENS = 2


def phrase_tokens(phrase):
    """The DF-gateable tokens of an already-lowercased entity phrase.

    Mirrors ent_tokens' inner rule, but takes the phrase directly. ent_tokens cannot be used
    on one: it re-runs ENTITY_RE, which needs capitals, so a lowercased phrase yields the
    empty set - and `all(t in ents for t in set())` is vacuously True, which silently turned
    the DF gate off for every short name ("pope leo", both words under five characters) on
    28.08.2026. An empty result here means "no gateable token", and callers must read it as
    a refusal rather than a pass.
    """
    return {w[:-1] if len(w) > 6 and w.endswith("s") else w
            for w in (phrase or "").split() if len(w) >= 5}


def union_entity_index(rows, past):
    """Distinctive entities over today's corpus AND the recent editions, as one corpus.

    Document frequency is a property of a corpus, so asking whether a token is distinctive
    "across two days" is not a well-formed question until the two days are one corpus. That
    is all this does. Built once per run and handed to ran_before; without it the entity arm
    stays off, which is the correct default for a two-item comparison that has no corpus at
    all (run_tests calls it that way).
    """
    corpus = [{"headline": it.get("headline") or ""} for it in rows]
    corpus += [{"headline": h.get("headline") or ""} for h in past]
    return entity_index(corpus)


def ran_before(item, history, ents=None):
    """The most recent recent-edition appearance of the same story, or None.

    Compares prose, not URLs, which is the entire point: Right To Life's 25.08 piece came
    back on 27.08 at the same slug with "-2" on the end and no URL-keyed store could see it.

    Three guards, each earning its place:
      - same section, as in same_story. Two sections means two concerns.
      - is_development_of, so a running story that has MOVED is not called a repeat. "MPs
        vote down the Bill" after "MPs to vote on the Bill" is the news, not an echo.
      - the word-overlap arm only. The entity arm of same_story leans on ENTITY_MIN_DF, a
        document frequency measured across ONE day's corpus; there is no honest way to
        compute it across two, and faking it would quietly drop the floor to "shares any
        rare-ish name", which is the precision loss that was measured and rejected on
        19.08.2026.
    """
    headline = item.get("headline") or ""
    wa = sig_words(headline)
    if not wa:
        return None
    ta = ent_tokens(headline) if ents else set()
    section = item.get("_section")
    best = None
    for past in history:
        if section and past.get("section") and past["section"] != section:
            continue
        wb = sig_words(past.get("headline") or "")
        if not wb:
            continue
        shared = wa & wb
        ratio_ok = (min(len(wa), len(wb)) >= CROSSDAY_MIN_WORDS
                    and len(shared) / max(1, min(len(wa), len(wb))) >= CROSSDAY_OVERLAP)
        linked = ratio_ok or len(shared) >= CROSSDAY_WORDS
        if not linked and ents:
            shared_ents = {e for e in (ta & ent_tokens(past.get("headline") or ""))
                           if e in ents}
            if shared_ents and len(shared) >= CROSSDAY_ENTITY_WORDS:
                # A distinctive name in common, plus real topical overlap. Same two-part test
                # the within-day clusterer uses, at a higher word floor: the cost asymmetry is
                # worse here, because a wrong cross-day link invites dropping a story that
                # never ran.
                linked = True
            elif any(len(phrase_tokens(p)) >= CROSSDAY_ENTITY_TOKENS
                     and all(t in ents for t in phrase_tokens(p))
                     for p in (entities(headline)
                               & entities(past.get("headline") or ""))):
                # ...or the two headlines share a multi-word NAME intact, every token of which
                # is distinctive over the union corpus. Both halves of that are load-bearing,
                # and each was learned by watching the other one fail on 28.08.2026:
                #
                #   phrases without the DF gate -> merged five unrelated Pope Leo stories, the
                #     White House, Dolly Parton and Our Lady. A multi-word name is not
                #     distinctive by construction.
                #   the DF gate without phrases -> merged "Virginia's Catch-22 for Military
                #     Chaplains" into "Canada Bars Military Chaplains", on the loose tokens
                #     "military" and "chaplain" drawn from DIFFERENT phrases in each headline.
                #
                # Together they are exact: "paivi rasanen" survives intact in both headlines
                # AND both its tokens clear the gate, while the chaplains pair shares no
                # phrase at all and Pope Leo's tokens are far above ENTITY_MAX_DF.
                # Chris, 28.08.2026: BGEA's "UK Drops Travel Ban for Päivi Räsänen" against
                # Christian Today's "Päivi Räsänen granted UK visa" three days earlier - one
                # event, reported late. "drops"/"granted" and "travel ban"/"visa" share no
                # words, so the pair carries her name and nothing else and dies on the
                # three-word floor above.
                #
                # Safe only because the index is the UNION of today and the history. Tried
                # without a frequency gate and it merged five unrelated Pope Leo stories, the
                # White House, Dolly Parton and Our Lady - a multi-word name is NOT
                # distinctive by construction. Over the union corpus every one of those tokens
                # is above ENTITY_MAX_DF and excluded, while "paivi"/"rasanen" reach DF 2 -
                # once today, once in history - and pass. Today's corpus alone cannot see
                # that: the token is rare today precisely because its other use is in the
                # past, which is what MIN_DF=2 was rejecting.
                linked = True
        if not linked:
            continue
        if is_development_of(item, past):
            continue
        if best is None or past["date"] > best["date"]:
            best = past
    return best


def is_comment_piece(item):
    """Argument rather than report - used to allow comment alongside the news lead."""
    h = item.get("headline") or ""
    if COMMENT.search(h):
        return True
    if OUTCOME.search(h):
        return False
    outlet = (item.get("outlet") or "").lower()
    return any(t in outlet for t in (
        "spiked", "the critic", "unherd", "spectator", "first things", "public discourse",
        "national review", "federalist", "conservative woman", "quillette", "compact",
        "the article", "guido", "washington stand"))



def unify_clusters(rows):
    """Move every member of a story cluster into the lead's section.

    Clustering ran per-section, so the Jason Arday story never grouped: the news reports
    classified into Marriage, Family & Education and the two spiked comment pieces into
    Gender, Identity & Sexuality, and the two halves never met. Chris, 16.08.2026: "the Arday
    stories aren't grouped". A story is one thing and belongs in one place, so clustering now
    happens across the whole day and the lead decides where the cluster lives.
    """
    sets = [(it, sig_words(it["headline"]), ent_tokens(it["headline"])) for it in rows]
    ents = entity_index(rows)
    seen, moved = set(), 0
    for i, (a, wa, ea) in enumerate(sets):
        if id(a) in seen:
            continue
        group = [a]
        seen.add(id(a))
        for b, wb, eb in sets[i + 1:]:
            if id(b) in seen:
                continue
            shared = {e for e in (ea & eb) if e in ents}
            if same_story(a, b, wa, wb, shared):
                group.append(b)
                seen.add(id(b))
        if len(group) > 1:
            # A cluster lives where the NEWS is. Previously the highest-importance member
            # decided, which let a strong comment piece drag the reports into its section.
            reports = [it for it in group if not is_comment_piece(it)]
            lead = max(reports or group, key=importance)
            for it in group:
                if it.get("_section") != lead["_section"]:
                    it["_section"] = lead["_section"]
                    moved += 1
    return moved



US_SHARE = 0.30          # Chris, 18.08.2026: raised from 0.25 when the cap was first wired
                         # in. It had never actually run - cap_us_share() was defined on
                         # 16.08 and never called, so every edition since shipped uncapped
                         # (38% US on 18.08, seven of nine sections over the old quarter).
                         # 30% is the deliberate starting point for a cap that now bites.
# ...unless the story ranks very high. Set from the real distribution: on 16.08.2026 the
# 95th percentile of importance was 20 and the 99th was 24, so 20 exempted roughly one item
# in twenty and let the cap bite, while a Supreme Court ruling or a mass killing clears it.
# A tier outlet with a plain outcome verb scores 20 on its own, so the bar sits above that.
US_EXEMPT_AT = 22
# 22 is correct and deliberately unchanged. It nearly got lowered on 18.08.2026, which would
# have been the wrong fix for a real problem.
#
# When the cap was first actually run, the exemption fired for 1 of 136 US picks. The reason
# was a UNITS MISMATCH, not a bad threshold: importance() weights corroboration most heavily,
# compose.py never stamped _corr, so reach scored 0 for every story and the whole scale sat
# several points low - median 8, 95th percentile 18. At that scale 22 exempts almost nothing,
# and the tempting fix was to drop the number to 18.
#
# That would have gutted the cap. With _corr stamped (compose.py now calls
# stamp_corroboration), the same 136 picks run median 9, 95th 21, max 29: 22 exempts 4 of them,
# ~3%, which is Chris's stated intent of "roughly one item in twenty". 18 on the corrected
# scale would exempt 18%.
#
# The lesson is about the shape of the bug rather than the number: a threshold that stops
# firing is as likely to mean the measurement moved as that the threshold is wrong. Check what
# feeds the score before touching the bar.


def us_allowance(n_non_us, share=US_SHARE, section_cap=None):
    """How many US items a section may hold so US share lands on `share`.

    With a section cap the answer is simply share x cap. Without one the section's final
    size depends on how many US items survive, which is circular, so solve it:
    allowed = floor(share * n_non_us / (1 - share)). For share 0.3 and 35 non-US items that
    is 15, giving a 50-item section at exactly 30%. Taking floor(share * len(picks)) instead
    would quietly overshoot, because the dropped items shrink the denominator.
    """
    if section_cap:
        return max(1, int(section_cap * share))
    return max(1, int(n_non_us * share / (1.0 - share)))


def cap_us_share(rows, share=US_SHARE, exempt_at=US_EXEMPT_AT, limit=None,
                 exempt_ids=None):
    """Hold United States items to a share of a section, letting strong ones through.

    American coverage dominates the corpus - 427 of 1,120 placed candidates on 16.08.2026,
    more than twice the UK - because the US movement press is prolific and files in English.
    Left alone it crowds out the UK, Europe and the persecution reporting from Africa and
    Asia that this briefing exists to surface. The exemption matters as much as the cap: a
    Supreme Court ruling is not dropped for being American.

    Expects rows already ordered best-first. Returns (kept, dropped).

    `limit` overrides the allowance; compose.py passes one from us_allowance() so the share
    is measured against the section's FINAL size rather than the pick list's length.

    `exempt_ids` holds id() of rows the caller has marked must-run. compose.py passes its
    tier-1 picks. Chris, 24.08.2026, marking up the TEST 20260824 draft: a Life list of ten
    stories "should have been included even if it meant breaching the cap", and a Gender list
    "should be included and if the ... cap for this section is breached, they outrank other
    stories here". Three of those he named had in fact been PICKED and then cut here - the
    WORLD and Daily Signal New Jersey pieces and the Federalist abortion-pill piece - because
    the only exemption was `exempt_at`, an importance() score. Keyword importance is not the
    same judgement as "must run", and where they disagreed the score won silently.
    Exempt rows still CONSUME quota, so they displace lower-tier American items before any
    non-US item is touched; the share is only exceeded if must-runs alone overfill it.
    """
    if limit is None:
        limit = max(1, int(len(rows) * share))
    exempt_ids = exempt_ids or frozenset()
    kept, dropped, used = [], [], 0
    for it in rows:
        if regions.region(it["headline"], it.get("outlet") or "", "",
                          region_text(it)) == "United States":
            if id(it) in exempt_ids:
                used += 1
            elif used >= limit and importance(it) < exempt_at:
                dropped.append(it)
                continue
            else:
                used += 1
        kept.append(it)
    return kept, dropped


def cluster_duplicates(rows):
    """Group items covering the same story and name what to take from each cluster.

    Two of the three misses on 12.08.2026 came from choosing the wrong member of a pair.
    Since 16.08.2026 clustering also links reports to commentary via shared rare entities,
    and a cluster can yield more than one pick: the best report, plus any comment pieces from
    outlets Chris reads. He asked for that explicitly - "you can have multiple comments if
    they're good" - because on a story like Jason Arday's death the report carries the facts
    and the comment carries the argument, and he wants both.
    """
    sets = [(it, sig_words(it["headline"]), ent_tokens(it["headline"])) for it in rows]
    ents = entity_index(rows)
    seen, clusters = set(), []
    for i, (a, wa, ea) in enumerate(sets):
        if id(a) in seen:
            continue
        group = [a]
        seen.add(id(a))
        for b, wb, eb in sets[i + 1:]:
            if id(b) in seen:
                continue
            shared = {e for e in (ea & eb) if e in ents}
            if same_story(a, b, wa, wb, shared):
                group.append(b)
                seen.add(id(b))
        if len(group) > 1:
            clusters.append(group)
    marks = {}
    for group in clusters:
        # importance(), not rank_score: on 16.08.2026 three outlets covered the UK
        # cohabitation proposals and the cluster promoted the weakest of them, because the
        # lead was still being chosen by the old keyword-weighted score.
        group.sort(key=lambda it: -importance(it))
        reports = [it for it in group if not is_comment_piece(it)]
        comments = [it for it in group if is_comment_piece(it)]
        lead = reports[0] if reports else group[0]
        marks[id(lead)] = "  <<< TAKE THIS ONE of %d on this story" % len(group)
        # Comment pieces from the outlets Chris reads stand alongside the report.
        keep_comments = [c for c in comments if c is not lead
                         and any(t in (c.get("outlet") or "").lower() for t in SOURCE_TIER)]
        for c in keep_comments:
            marks[id(c)] = "  <<< also take: comment on the same story"
        for other in group:
            if id(other) not in marks:
                # .get, not ["_i"]: _i is stamped by main(), so any other caller - a test, a
                # measurement script, a future consumer - crashed with KeyError here. Same
                # shape as the --sheet break on 18.08.2026: a function reading a field only
                # one caller happens to set. Degrade the label instead of dying.
                marks[id(other)] = ("  (same story as %s - prefer that)"
                                    % lead.get("_i", "?"))
    return marks


def corroborate(rows):
    """How many outlets are carrying each story, computed across every section.

    This is the one importance signal that costs nothing and is not a guess: if eleven
    outlets file on a Nigerian court ruling and one files on a diocesan appointment, the
    first is the bigger story, and no keyword table can tell you that. cluster_duplicates
    already finds the groups but only uses them to pick a winner and discard the rest.

    Deliberately global rather than per-section, because a big story crosses sections - the
    Trump Medicaid ruling landed in Life, Gender and Church & Society at once, and counting
    inside one section would have scored it as three small stories instead of one large one.

    Returns {id(item): (count, lead_item, tier)} - a 3-tuple, not the 2-tuple this docstring
    claimed until 18.08.2026. The tier slot is read as [2] by stamp_corroboration(). Worth
    stating precisely, because the whole US-cap exemption turned on this contract and it was
    documented only at a call site.
    """
    sets = [(it, sig_words(it["headline"])) for it in rows]
    seen, out = set(), {}
    for i, (a, wa) in enumerate(sets):
        if id(a) in seen or len(wa) < 3:
            continue
        group = [a]
        seen.add(id(a))
        for b, wb in sets[i + 1:]:
            if id(b) in seen or len(wb) < 3:
                continue
            if len(wa & wb) / max(1, min(len(wa), len(wb))) >= 0.55 or len(wa & wb) >= 5:
                group.append(b)
                seen.add(id(b))
        # Relaying items sort LAST, whatever they score. This is the selection that decides
        # the one line the sheet prints per story, and it is NOT cluster_rank: rank_score has
        # no PRIMARY_SOURCE term, so on 31.08.2026 SPUC's relay of "Burnham to abstain" beat
        # the Telegraph's own report on keyword score alone - both are in SOURCE_TIER and
        # neither matched ACTION - and six national reports were invisible to the curator.
        # Fixing cluster_rank alone did not touch this path; see run_tests for both.
        group.sort(key=cluster_lead_key)
        # How many of the outlets on this story are ones Chris actually reads. Raw counts
        # measure general news bigness: an FBI visa-fraud sweep draws eight mainstream
        # outlets, while a Nigerian court freeing a Christian woman draws two movement
        # outlets and matters far more here. Weighting by tier is what turns corroboration
        # into "important across our issue cluster" rather than "widely covered".
        tier = sum(1 for it in group
                   if any(t in (it.get("outlet") or "").lower() for t in SOURCE_TIER))
        for it in group:
            out[id(it)] = (len(group), group[0], tier)
    for it in rows:                      # items with too few significant words
        tier = 1 if any(t in (it.get("outlet") or "").lower() for t in SOURCE_TIER) else 0
        out.setdefault(id(it), (1, it, tier))
    return out


def real_summary(item, max_len=200):
    """The feed summary, trimmed, if it says more than the headline - else None.

    36% of feed summaries are the headline again (measured 18.08.2026), and printing those
    on the sheet would double its size for nothing. "Real" = at least 3 significant words
    the headline does not contain.
    """
    s = re.sub(r"\s+", " ", (item.get("summary") or "")).strip()
    if not s:
        return None
    def words(t):
        return set(re.findall(r"[a-z]{4,}", t.lower()))
    if len(words(s) - words(item.get("headline") or "")) < 3:
        return None
    return s[:max_len]


LEDES_CACHE = os.path.join(HERE, "ledes.json")


OPENINGS_CACHE = os.path.join(HERE, "openings.json")


# Bumped whenever fetch_article_opening changes what it returns. Entries written under an
# older schema are dropped rather than served: on 25.08.2026 the fetch went from 1200 chars
# / 3 paragraphs to 4000 / 10 and gained a boilerplate scrubber, and 493 cached shallow
# entries would otherwise have looked exactly like deep ones to everything downstream.
# Failures are still never cached - that lesson is from the resolver, 18.08.2026.
OPENINGS_SCHEMA = 2


def attach_openings(leads, cap=0, workers=8):
    """Fetch the article OPENING (standfirst + first paragraphs) and derive text signals.

    Option 1 + 3 + 5, Chris 24.08.2026. Differs from attach_ledes in three ways that matter:

      * it fetches more text - one sentence cannot tell a report from an argument;
      * it fetches for leads that already HAVE a feed summary, because those summaries are
        very often bare headline echoes (the two petition items on 23.08.2026 both were), so
        "has a summary" is not the same as "has text worth judging";
      * what it produces is read by textsignals, not printed raw.

    Cached in its own file, NOT ledes.json: the two hold different things (300-char standfirst
    vs 1200-char opening) and mixing them would silently serve one where the other was meant.
    Failures are not cached - the resolver taught that on 18.08.2026, when 381 cached misses
    froze a working decoder out of the pipeline.

    Signals fall back to the feed summary when no page could be fetched, and to None when
    there is no usable text at all. 44% of a day's candidates are unfetchable (36% unresolved
    Google News redirects, 9% paywalled), so "unknown" has to stay a real answer.
    """
    import concurrent.futures as _futures
    try:
        cache = json.load(open(OPENINGS_CACHE))
    except (ValueError, OSError):
        cache = {}
    if cache.get("__schema__") != OPENINGS_SCHEMA:
        cache = {"__schema__": OPENINGS_SCHEMA}
    todo = [it for it in leads
            if not it.get("paywalled")
            and "news.google.com" not in (it.get("url") or "")
            and fetch_feeds.url_key(it["url"]) not in cache]
    if cap:
        todo = todo[:cap]
    # Two passes, fast then gentle. Raising the cap to "every fetchable lead" on 25.08.2026
    # turned ~300 fetches into ~750, and at 8 workers that burst got throttled: 401 of 752
    # succeeded, where an unbiased A/B put the extractor's real success rate at 78%. Retrying
    # the misses at 4 workers recovered 73% of them, which says the losses were rate limiting
    # and not unfetchable pages. A miss here is not free - it sends a story to the ranker as
    # a bare headline, which is the exact failure this whole change exists to remove.
    live = 0

    def _pass(batch, nworkers):
        got = 0
        with _futures.ThreadPoolExecutor(max_workers=nworkers) as pool:
            for it, text in zip(batch, pool.map(
                    lambda i: fetch_feeds.fetch_article_opening(i["url"]), batch)):
                if text:
                    cache[fetch_feeds.url_key(it["url"])] = text
                    got += 1
        return got

    if todo:
        live = _pass(todo, workers)
        missed = [it for it in todo
                  if fetch_feeds.url_key(it["url"]) not in cache]
        if missed:
            live += _pass(missed, max(2, workers // 2))
    if live:
        try:
            tmp = OPENINGS_CACHE + ".tmp"
            with open(tmp, "w") as fh:
                json.dump(cache, fh)
            os.replace(tmp, OPENINGS_CACHE)
        except OSError:
            pass
    for it in leads:
        opening = cache.get(fetch_feeds.url_key(it["url"]))
        if opening:
            it["_opening"] = opening
        it["_sig"] = textsignals.signals(
            it["headline"], opening or real_summary(it) or it.get("_lede"))
    return live


PREVIEWS_CACHE = os.path.join(HERE, "previews.json")


def attach_previews(leads, workers=6):
    """Public preview text for PAYWALLED leads. Kept apart from attach_openings on purpose.

    Paywalled leads were skipped outright until 25.08.2026, which meant the outlets Chris
    picks from most - Spectator, Times, Critic, UnHerd, Catholic Herald - were the ones the
    ranker could not read. 9% of leads, and not a random 9%.

    What comes back is a capped preview, never the article: see fetch_article_preview for
    why the cap is a boundary rather than a tuning knob. Its own cache file, for the same
    reason ledes and openings have separate ones - a 600-char preview and a 4000-char
    opening are different things and must not be served for one another.
    """
    import concurrent.futures as _futures
    try:
        cache = json.load(open(PREVIEWS_CACHE))
    except (ValueError, OSError):
        cache = {}
    todo = [it for it in leads
            if it.get("paywalled")
            and "news.google.com" not in (it.get("url") or "")
            and fetch_feeds.url_key(it["url"]) not in cache]
    live = 0
    if todo:
        with _futures.ThreadPoolExecutor(max_workers=workers) as pool:
            for it, text in zip(todo, pool.map(
                    lambda i: fetch_feeds.fetch_article_preview(i["url"]), todo)):
                if text:
                    cache[fetch_feeds.url_key(it["url"])] = text
                    live += 1
    if live:
        try:
            tmp = PREVIEWS_CACHE + ".tmp"
            with open(tmp, "w") as fh:
                json.dump(cache, fh)
            os.replace(tmp, PREVIEWS_CACHE)
        except OSError:
            pass
    for it in leads:
        if it.get("paywalled"):
            got = cache.get(fetch_feeds.url_key(it["url"]))
            if got:
                it["_preview"] = got
    return live


def attach_sibling_text(leads, workers=6):
    """For a lead with no readable text, read another outlet on the SAME story instead.

    The last route, and the only one that reaches an outlet which refuses machine access
    altogether. The Telegraph answers 402 Payment Required and is not going to be talked
    round; but on 25.08.2026 its prison-conversions story was x2, and the other outlet on
    it was readable. Ranking the Telegraph lead on a sibling's account of the same events
    is not a substitute for the piece - it is how you find out what the story IS, so a
    story Chris would pick does not sink for the accident of who broke it.

    The briefing still links the Telegraph. This only feeds judgement: the sheet labels the
    text with the outlet it came from, so it is never mistaken for the lead's own words.
    """
    import concurrent.futures as _futures
    blind = [it for it in leads
             if not it.get("_opening") and not it.get("_preview")
             and not real_summary(it) and not it.get("_lede")
             and it.get("_siblings")]

    def best_sibling(it):
        cands = [s for s in it["_siblings"]
                 if not s.get("paywalled")
                 and "news.google.com" not in (s.get("url") or "")]
        return cands[0] if cands else None

    pairs = [(it, best_sibling(it)) for it in blind]
    pairs = [(it, s) for it, s in pairs if s is not None]
    live = 0
    if pairs:
        with _futures.ThreadPoolExecutor(max_workers=workers) as pool:
            for (it, sib), text in zip(pairs, pool.map(
                    lambda p: fetch_feeds.fetch_article_opening(p[1]["url"]), pairs)):
                if text:
                    it["_sibtext"] = text
                    it["_sibfrom"] = sib.get("outlet") or "another outlet"
                    live += 1
    return live


def attach_ledes(leads, cap=150, workers=8):
    """Fetch the article's own standfirst for text-starved leads, best-first, capped.

    Only for stories the feed leaves blind: no real summary, a direct (non-Google) link,
    not paywalled. Successes are cached in ledes.json so a same-morning re-run costs
    nothing; failures are NOT cached - the resolver taught that lesson on 18.08.2026,
    when 381 cached misses froze a working decoder out of the pipeline. Returns the number
    fetched live (0 on a fully cached or fully failed day - never raises).
    """
    import concurrent.futures as _futures
    try:
        cache = json.load(open(LEDES_CACHE))
    except (ValueError, OSError):
        cache = {}
    todo = [it for it in leads
            if real_summary(it) is None
            and not it.get("paywalled")
            and "news.google.com" not in (it.get("url") or "")]
    todo.sort(key=lambda i: -importance(i))
    hits = misses = 0
    fetchable = []
    for it in todo:
        k = fetch_feeds.url_key(it["url"])
        if k in cache:
            it["_lede"] = cache[k]
            hits += 1
        elif misses < cap:
            fetchable.append((k, it))
            misses += 1
    if fetchable:
        with _futures.ThreadPoolExecutor(max_workers=workers) as pool:
            for (k, it), lede in zip(fetchable,
                                     pool.map(lambda p: fetch_feeds.fetch_lede(p[1]["url"]),
                                              fetchable)):
                if lede:
                    it["_lede"] = lede
                    cache[k] = lede
        tmp = LEDES_CACHE + ".tmp"
        with open(tmp, "w") as fh:
            json.dump(cache, fh)
        os.replace(tmp, LEDES_CACHE)
    return len(fetchable)


def stamp_corroboration(rows):
    """Write _corr / _corr_tier onto every row, so importance() can read them.

    Both shortlist.py and compose.py need this, and compose.py went without it until
    18.08.2026 - which silently disabled the US cap's exemption for major stories, because
    importance() weights corroboration most heavily and it defaulted to 1 for everything.
    The stamping lives here, in one place, so the two callers cannot drift on which tuple
    index carries the count and which the tier.

    Pass the day's placed, non-chaff candidates: corroboration must be counted across the
    whole corpus, not across a curated pick list, or the near-duplicates that prove a story
    is big have already been removed and every story looks like an x1.
    """
    corr = corroborate(rows)
    members = {}
    for it in rows:
        members.setdefault(id(corr[id(it)][1]), []).append(it)
    for it in rows:
        count, lead, tier = corr[id(it)]
        it["_corr"] = count
        it["_corr_tier"] = tier
        # Every other outlet on this story. Only the cluster LEAD is fetched for text, so
        # when the lead is paywalled or blocked its siblings are the only readable account
        # of the same events - see attach_sibling_text.
        if lead is it:
            it["_siblings"] = [o for o in members.get(id(it), []) if o is not it]
        # True on the cluster's best item - the one line the sheet prints per story. Stamped
        # here rather than left in main(), because on 18.08.2026 the sheet still read the
        # local `corr` dict this helper replaced, and --sheet died with a NameError that the
        # fixture could not see (it never runs main). The lead flag is part of the contract.
        it["_corr_lead"] = lead is it
    return rows


def source_tier_pos(outlet):
    """Index of the SOURCE_TIER entry this outlet matches, or None.

    SOURCE_TIER is matched by SUBSTRING, and "the times" is a substring of other mastheads:
    on 31.08.2026 "The Times of India" and "The Times of Israel" were both being scored as
    The Times of London - TIER_BUMP plus its tier_pos - 29 items on that one sweep. It
    surfaced while chasing why the Burnham-abstain cluster would not lead with the Telegraph:
    once SPUC's relay was demoted the lead went to The Times of India, which had beaten the
    Telegraph on a bump it was never entitled to.

    A tier entry followed by " of " is a different masthead. Kept as one helper so the score
    path and the cluster path cannot drift on the answer.
    """
    ol = (outlet or "").lower()
    for i, t in enumerate(SOURCE_TIER):
        j = ol.find(t)
        if j < 0:
            continue
        if ol[j + len(t):].lstrip().startswith("of "):
            continue
        return i
    return None


def _link_is_unreadable(item):
    """True if this item's link is a Google News redirect rather than a publisher URL.

    Evaluated at CLUSTER time, before compose.py's resolver runs, so some of these would
    have resolved later. That is the right trade anyway: when a sibling already has a direct
    publisher URL for the same story, betting on the sibling costs nothing and betting on
    the redirect can cost the reader a dead link.
    """
    return "news.google.com" in (item.get("url") or "")


def cluster_lead_key(item):
    """Sort key choosing which member of a cluster becomes the line the sheet prints.

    Named and lifted out of corroborate() so a test can reach it. Three terms, in order:

    1. RELAYING SORTS LAST. Provenance beats everything: an advocacy body's own release
       leads over a newsroom's write-up of it. Added 31.08.2026 after SPUC's relay of
       "Burnham to abstain" beat the Telegraph's own report and hid six national reports.
    2. AN UNREADABLE LINK SORTS AFTER A READABLE ONE. rank_score is _score + TIER_BUMP +
       ACTION_BUMP and has no URL term at all, so an undecodable Google News redirect
       sorted level with a clean publisher URL. On 01.09.2026 that made Japan Today's
       redirect - resolve() returns None for it - the lead of a cluster whose other member,
       The Japan Times, had a direct URL and was supplying the text the sheet printed.
       Ranked BELOW relay deliberately: provenance is a question about who published the
       document, this is only about whether the reader can open it.
    3. Then rank_score, as before.
    """
    return (relays_another_outlet(item), _link_is_unreadable(item), -rank_score(item))


def rank_score(item):
    """Higher ranks earlier. Section assignment is unaffected."""
    bump = 0
    outlet = (item.get("outlet") or "").lower()
    if source_tier_pos(item.get("outlet")) is not None:
        bump += TIER_BUMP
    if ACTION.search(item["headline"]):
        bump += ACTION_BUMP
    return item["_score"] + bump


# The heart of the ranking: did something *happen*, or did somebody *say something*?
#
# The old ACTION regex scored "Supreme Court strikes down the law" and "Campaigner slams
# the law" identically, because both contain "law". That single conflation is why four of
# the stories Chris wanted on 13.08.2026 sat at ranks 53-88: a digest has to lead with
# outcomes, and reaction is what fills the space underneath them.
OUTCOME = re.compile(
    r"\bruled?\b|\bruling\b|struck down|strikes down|upheld|upholds|overturn|quashed"
    r"|passed?\b|passes\b|signs?\b|signed|enacted|vetoe?d?|repeal|amended"
    r"|banned|bans\b|sentenc|jailed|convict|acquit|arrest|charged|detained|deported"
    r"|resign|sacked|fired|dismissed|struck off|disbarred|expelled|suspended"
    r"|killed|murdered|died|dead\b|shot|abducted|kidnapped|raided|bombed|burned"
    r"|orders?\b|ordered|blocks?\b|blocked|grants?\b|granted|approved|rejects?\b|rejected"
    r"|refuses?\b|refused|denies\b|denied\b|bars\b|barred|halts?\b|halted"
    r"|wins?\b|won\b|loses?\b|lost\b|awarded|fined|settled|dropped charges"
    # \bfreed\b: bare "freed" substring-matched "freedom", handing +8 outcome to every
    # "religious freedom" headline - this briefing's core beat, mis-scored wholesale until
    # 18.08.2026. Caught by an ABOVE pair that used "religious freedom" as inert filler.
    r"|born\b|released|\bfreed\b|acquitted|closes?\b|closed|opens\b|launched"
    r"|takes effect|comes into force|becomes law|elected|appointed|ordained"
    # Present-tense forms and hand-over verbs were missing, so genuine outcomes scored ZERO:
    # "Parents get baby surrogate wouldn't abort" and "Couple receives custody" both matched
    # nothing at all, which is a large part of why they ranked below the process story about
    # the same case (Chris flagged the case 17.08.2026).
    r"|approves\b|grants\b|receives?\b|\bgets?\b|\bgains?\b|hands? over|takes custody"
    r"|regains?\b|returns?\b|reunited|gives? birth|gave birth|wins custody"
    # A law's EFFECT is an outcome, not only its enactment. "Massachusetts Now Protects
    # Abortion Throughout Pregnancy" and "New Law Legalizing Abortions Up Until Birth"
    # both scored zero here on 18.08.2026 and ranked below commentary on the same law.
    # Finite/past forms and "law + gerund" only: bare "legalising" stays unmatched, because
    # "An open letter against legalising assisted suicide" is advocacy about a prospect,
    # not an outcome - there is a guard ABOVE case for exactly that.
    r"|legali[sz]e[sd]\b|decriminali[sz]e[sd]\b|law (legali[sz]ing|decriminali[sz]ing)"
    r"|now (protects?|allows?|requires?|guarantees?|bans?|legal\b)"
    # "UN adopts declaration" and "judge confirmed" scored zero (18.08.2026). "confirmed"
    # only in the past form: "X confirms plans" is speech, "judge confirmed" is a result.
    r"|adopts?\b|adopted\b|confirmed\b", re.I)
# A ruling that has not happened yet is not an outcome. "\bruled?\b" matched the "rule" in
# "Judge TO RULE on assisted dying bill next month", scoring it 8 - above the actual ruling.
FUTURE_INTENT = re.compile(
    r"\bto (rule|decide|hear|vote|consider|report|publish|announce)\b"
    r"|\b(will|would|could|may|might|set to|expected to|due to|poised to|prepares to)\b"
    r"|\bnext (week|month|year|term)\b|\bahead of\b|\bawait\w*\b", re.I)
PROCESS = re.compile(
    r"\burges?\b|calls? (for|on)|\bwarns?\b|\bslams?\b|criticis|criticiz|condemn"
    r"|demands?\b|accus|denies\b|defends?\b|responds?\b|hits? back|insists?\b"
    r"|plans?\b|considers?\b|proposes?\b|weighs\b|mulls\b|seeks?\b|prepares?\b"
    r"|plead|plans to|plots|plea\b|plead", re.I)
# Scale: an institution acting nationally outranks the same act locally.
SCALE = re.compile(
    r"supreme court|high court|court of appeal|constitutional court|\bECHR\b|\bECtHR\b"
    r"|parliament|congress|senate|house of (commons|lords|representatives)|cabinet"
    r"|nationwide|country-?wide|national(ly)?\b|federal|state-?wide|landmark|historic"
    r"|first (time|ever|country|state)|unanimous|precedent|major|sweeping"
    # Devolved and state legislatures. Until 18.08.2026 only the literal "statewide"
    # matched anything sub-national, so Holyrood, the Senedd and Stormont scored as if no
    # institution were involved - blind spots a UK-focused briefing cannot afford. Kept to
    # named bodies rather than the bare word "assembly", which would fire on church
    # assemblies and public gatherings.
    r"|holyrood|senedd|stormont|scottish parliament|welsh parliament"
    r"|northern ireland assembly|d[aá]il\b|oireachtas|bundestag"
    r"|state legislature|statehouse|governor sign", re.I)
# Commentary framings - fine to run, but they are not the day's lead.
COMMENT = re.compile(
    r"^(why|how|what|when|who|the case (for|against)|in defence|in defense|on\b)"
    r"|\?\s*$|opinion:|comment:|analysis:|explainer|explained\b|my \w+\b"
    r"|we (need|must|should)|let'?s\b|isn'?t it|the trouble with|the problem with", re.I)


# Spanish and Italian equivalents, appended so the said-versus-happened axis works in those
# languages too - without these a Spanish court ruling scored as commentary and sank.
OUTCOME = re.compile(OUTCOME.pattern +
    # Word boundaries added 18.08.2026. These tokens were appended bare and several are
    # substrings of ordinary English words, so ENGLISH headlines collected the +8 outcome
    # bonus: "Senegal"/"Negative" via nega, "Confirmation"/"affirmation" via firma,
    # "declaration" via declara, "approval" via Italian approva, "fallout" via fall[oó],
    # "affirmative" via firmat. Each has a failing ABOVE pair in testcases.txt; the Spanish
    # keep-cases there stop this tightening from costing real es/it coverage. Tokens left
    # bare are ones whose English collisions are themselves outcomes (prohibi-, incarcerat-,
    # abrogat-, promulgat-) or that no English word contains.
    r"|aprueba|anula|proh[ií]be|condena|deroga|rechaza|\bfirma\b|promulga|detiene|absuelve"
    r"|dimite|destituye|\bdeclara\b|sentencia|autoriza|deniega|entra en vigor"
    r"|\bapprova\b|annulla|vieta|condanna|abroga|respinge|arresta|assolve"
    r"|si dimette|dichiara|autorizza|\bnega\b"
    r"|aprob[oó]|aprobad|promulg|firm[oó]\b|prohib[ií]|prohibid|conden[oó]|condenad"
    r"|detenid|arrestad|encarcelad|dimiti[oó]|destituid|absuelt|sentenci[oó]|\bfall[oó]\b"
    r"|anul[oó]|derog[oó]|rechaz[oó]|admiti[oó] a tr[aá]mite|entra en vigor|muri[oó]|asesinad"
    r"|aprovat|approv[oò]|promulgat|\bfirmat|vietat|proibit|condannat|arrestat|incarcerat"
    r"|dimess|assolt|sentenziat|annullat|abrogat|respint|entra in vigore|mort[oa]\b|uccis"
    # The persecution beat's own outcome verbs, missing until 31.08.2026. OUTCOME already had
    # killed/murdered/abducted/jailed, but not the words those stories actually use: a pastor
    # "martyred" and a state that "destroys" a church both scored ZERO outcome credit, so
    # "Baptist Pastor Martyred in Myanmar" ran at i2 while a court order about two dogs
    # ("euthanasia order ... dismissed") ran at i10 and an eagle's at i13. 25 verbs were
    # absent. Deliberately NOT added: "stabbed", which LOCAL_INCIDENT already handles and
    # which would inflate ordinary crime - the same trap as bare "freed" matching "freedom".
    # Finite/past forms only, and \b-anchored where a longer word reverses the meaning:
    # bare "criminalis" matched "deCRIMINALISes" and handed outcome credit to "Campaigners
    # call on Ireland to decriminalise blasphemy", flipping an 18.08.2026 ABOVE pair on its
    # first run. Bare infinitives are out for the same reason "legalising" is - "vows to
    # destroy" is a threat, not an event.
    # VERB FORMS ONLY - no nouns. "destruction" and "demolition" were both tried and both
    # broke a pair on the first run: "Bishop laments the destruction of Christian heritage"
    # is a said, not a happened, and "Council SEEKS approval for church demolition" scored
    # level with "Council WINS approval" once the noun matched. A noun names the event
    # without asserting it occurred, which is the whole distinction this regex exists for.
    r"|martyr|destroys|destroyed|demolished|razed|torched|bulldozed|beheaded|\bexecuted\b"
    r"|massacred|massacres|lynched|lynching|desecrat|vandalis|vandaliz|seized|seizes"
    r"|confiscat|outlaws\b|outlawed|\bcriminalis|\bcriminaliz|evicted|expropriat"
    r"|forcibly (convert|remov)",
    re.I)
PROCESS = re.compile(PROCESS.pattern +
    # Word boundaries added 18.08.2026, same disease as OUTCOME's: bare es/it tokens fired
    # inside English words. Measured on that day's sweep: "urge[n]?" inside "sURGEry" put a
    # process tag on the Baby Gabriel surgery headlines, "critica" inside "CRITICAlly
    # injured" tagged shooting reports, "insta" matched "INSTAgram"; the audit also caught
    # pide/sPIDEr, exigen/EXIGENt, reclama/RECLAMAtion, propone/PROPONEnt before they bit.
    # Failing ABOVE pairs and a Spanish keep-case are in testcases.txt.
    r"|\bpiden?\b|\bexigen?\b|\breclaman?\b|advierte[n]?|denuncia[n]?|\bcritican?\b"
    r"|acusa[n]?|niega[n]?|defiende[n]?|\bproponen?\b|estudia[n]?|\binstan?\b"
    r"|\burgen?\b|alerta[n]?"
    r"|chiede|esige|avverte|accusa|\bnega\b|difende|valuta",
    re.I)
SCALE = re.compile(SCALE.pattern +
    r"|tribunal supremo|tribunal constitucional|audiencia nacional|congreso de los diputados"
    r"|senado|consejo de ministros|hist[oó]ric|sin precedentes|por primera vez"
    r"|corte costituzionale|cassazione|consiglio dei ministri|camera dei deputati"
    r"|storic|senza precedenti|per la prima volta",
    re.I)
CHAFF_RESCUE = re.compile(CHAFF_RESCUE.pattern +
    r"|aborto|eutanasia|matrimonio|familia|famiglia|iglesia|chiesa|obispo|vescovo"
    r"|g[eé]nero|genere|libertad|libert[aà]|tribunal|tribunale|\bley\b|\blegge\b",
    re.I)



# Chris, 16.08.2026, on a Christian Concern piece: "I'm genuinely interested in what the
# organisation does." The advocacy bodies CitizenGO works alongside are worth carrying for
# their own sake - a press release from them is a fact about the movement, not just a story.
# Distinct from SOURCE_TIER, which is about outlet quality; this is about organisational
# interest, and it is deliberately a short list.
FOLLOWED_ORGS = re.compile(
    r"^(christian concern|christian legal centre|adf international"
    r"|alliance defending freedom|citizengo|christian institute|the christian institute"
    r"|spuc|right to life uk|care not killing|the iona institute|iona institute"
    r"|free speech union|sex matters|lgb alliance|open doors|barnabas|release international"
    r"|international christian concern)$", re.I)
FOLLOWED_BONUS = 5


# Jurisdictions whose entire English-language press corps is a handful of outlets, so that
# corroboration count cannot mean what it means for a UK or US story. Deliberately NOT a list
# of "unimportant" countries - it is a list of small MARKETS. Ireland and New Zealand are here
# for the same reason Malta is: two or three outlets cover a national story, and x2 there is
# the equivalent of x15 in Washington.
SMALL_MARKET = re.compile(
    r"\bmalta\b|maltese|cyprus|cypriot|estonia|latvia|lithuania|slovenia|slovakia|slovak"
    r"|luxembourg|iceland|montenegro|north macedonia|albania|moldova|\bgeorgia\b(?! state)"
    r"|armenia|bosnia|croatia|serbia|kosovo|liechtenstein|monaco|andorra|san marino"
    r"|new zealand|\bireland\b|irish\b|uruguay|paraguay|costa rica|panama|nicaragua"
    r"|honduras|guatemala|el salvador|belize|jamaica|trinidad|barbados|guyana|suriname"
    r"|rwanda|malawi|botswana|namibia|eswatini|lesotho|gambia|sierra leone|liberia"
    r"|togo|benin|burundi|djibouti|mauritius|seychelles|cape verde|fiji|samoa|tonga"
    r"|papua new guinea|vanuatu|\btimor\b|timor-leste|bhutan|maldives|brunei|\blaos\b"
    r"|mongolia", re.I)
# Outlets whose home market is small, for stories that name no country in the headline.
SMALL_MARKET_OUTLETS = re.compile(
    r"maltatoday|times of malta|malta independent|cyprus mail|the irish catholic|gript"
    r"|iona institute|irish independent|irish times|newstalk|rt[eé]\b|the post \(new zealand"
    r"|nz herald|stuff \(new zealand|nation\.cymru|jamaica gleaner|irie fm", re.I)
# What a small-market story gets instead of a reach score. Set at the value a story carried by
# two mainstream outlets receives (3), so it is treated as real news without being promoted
# above genuinely well-covered events.
SMALL_MARKET_BASELINE = 3


def is_small_market(item):
    """True when corroboration count would measure the press corps, not the story."""
    if SMALL_MARKET.search(item.get("headline") or ""):
        return True
    return bool(SMALL_MARKET_OUTLETS.search(item.get("outlet") or ""))


# Option 3's weight: +/- this much for primary_doc / comment. ON at 4 by Chris's decision,
# 24.08.2026, having been shown the measurements and the caveat.
#
# Measured on all four archived editions (rank_eval_log.txt):
#     weight 0   concordance 0.6164   top-40 precision 0.450
#     weight 2   concordance 0.6174   top-40 precision 0.456
#     weight 4   concordance 0.6174   top-40 precision 0.469
#
# The known cost, recorded so a later reader does not have to rediscover it: signals reach
# only ~41% of leads, and 45% of items from the commentary outlets carry NO signal because
# those outlets are the paywalled ones. So the comment penalty lands on commentary we can
# read and not on commentary we cannot - it is partly a penalty on being readable. Four
# editions of concordance cannot detect that asymmetry. If paywalled columns start running
# high while readable ones sink, this is the first thing to suspect.
#
# Interacts with US_EXEMPT_AT (22), which compares importance(): a comment piece now sits 4
# lower and clears it less often, a primary-doc piece 4 higher and clears it more often. With
# tiers 1-2 already exempt from the US share, that bites only tier-3 American items.
#
# One more property, measured on item 822 of the 23.08 sweep and worth knowing: the verdict
# depends on WHICH text was available. That story reads "report doc" from its feed summary (a
# straight news lede) and got no signal at all on a later run when the fetch came back empty -
# so the same piece can score +4 one morning and +0 the next on fetch luck. Successes are
# cached in openings.json and failures are not, so this settles down over time rather than
# oscillating forever, but ranking now has a fetch-dependent component it did not have before.
TEXT_SIGNAL_WEIGHT = 4


def importance(item):
    """Composite importance, used to order the day. Section assignment is unaffected.

    Ordered by how much each signal actually predicts news value:

      corroboration  how many outlets filed on it - the only signal that measures the
                     event rather than its wording, so it carries the most weight
      outcome        something happened, as against somebody commenting on it
      scale          a national institution acting, as against a local one
      source tier    the outlets Chris cites, damped so a masthead cannot outweigh events
      issue score    keyword density, damped hard - it is a classifier, not a judge
      recency        a tiebreak, not a driver
    """
    h = item["headline"]
    n = item.get("_corr", 1)
    # General reach is real but capped: many outlets covering something says it is news,
    # not that it is news for this audience.
    #
    # Corroboration measures the SIZE OF THE PRESS CORPS as much as the size of the story,
    # so in a small jurisdiction it measures the wrong thing entirely. MaltaToday's abortion
    # survey ran x1 and scored 0 for reach - not because the story was small but because
    # Malta has one English-language paper covering it. Chris, 17.08.2026: "weight it by
    # importance not corroboration for small countries." So a small-market story is neither
    # rewarded nor punished for reach; it stands or falls on outcome, scale and issue, which
    # are intrinsic to the story rather than to the market it was published in.
    reach = min(7, int(round(3 * math.log(n, 2)))) if n > 1 else 0
    # max(), not a replacement: the baseline is a floor for thin markets, never a ceiling on
    # a story that genuinely was widely covered.
    score = max(reach, SMALL_MARKET_BASELINE) if is_small_market(item) else reach
    # Movement reach carries more weight per outlet, and is what promotes the persecution
    # and life stories that mainstream feeds barely touch.
    score += min(9, 3 * item.get("_corr_tier", 0))

    # A future ruling reads as an outcome by vocabulary but is process by substance, so it is
    # scored as process however outcome-shaped its verbs are.
    if OUTCOME.search(h) and not FUTURE_INTENT.search(h):
        score += 8
    elif PROCESS.search(h) or FUTURE_INTENT.search(h):
        score += 3
    if COMMENT.search(h):
        score -= 2
    if SCALE.search(h):
        score += 3

    outlet = (item.get("outlet") or "").lower()
    if any(t in outlet for t in SOURCE_TIER):
        score += 4
    if FOLLOWED_ORGS.match(outlet.strip()):
        score += FOLLOWED_BONUS
    score += min(6, item.get("_score", 0))

    age = item.get("age_h")
    if age is not None:
        # Thresholds scale with the sweep window (fixed 18.08.2026). They were hard-coded
        # at 12h/48h, which contradicted Monday: the window widens to 84h precisely to
        # ADMIT the weekend, and the fixed 48h line then demoted every weekend story for
        # being a weekend story - Sunday church and persecution reporting worst of all.
        # Proportional cutoffs (window/3 fresh, window*4/3 stale) reproduce 12h/48h exactly
        # on a normal 36h day and stop the stale malus firing inside a widened window.
        fresh, stale = SWEEP_WINDOW_H / 3.0, SWEEP_WINDOW_H * 4.0 / 3.0
        score += 2 if age <= fresh else (-2 if age > stale else 0)

    # Option 3 (Chris, 24.08.2026): let the article's own opening adjust the score. Small and
    # bounded on purpose - +/-2 against a scale whose median is ~9 - because this is the axis
    # that already went wrong once. On 18.08.2026 keyword density over body text was measured
    # and rejected for REWARDING commentary, so the adjustment here is the opposite sign: a
    # piece whose opening argues rather than reports is demoted, and one that names a document
    # it rests on is promoted.
    #
    # Applied ONLY where signals exist. Never guess from silence: 44% of a day's candidates
    # are unfetchable, so treating "no signal" as "not comment" would hand every paywalled
    # column a free pass - and paywalled columns are most of the commentary in this corpus.
    # That asymmetry is exactly why this is off by default; see TEXT_SIGNAL_WEIGHT.
    if TEXT_SIGNAL_WEIGHT:
        sig = item.get("_sig")
        if sig:
            if sig["kind"] == "comment":
                score -= TEXT_SIGNAL_WEIGHT
            if sig["primary_doc"]:
                score += TEXT_SIGNAL_WEIGHT
    return score


CHURCH = "Church & Religion"
SPECIFIC_MIN = 3

# An office-holder facing legal or party consequences. Used only to demote a weak Church
# match (see classify), never to claim a story outright.
POLITICIAN_LEGAL = re.compile(
    r"\b(MPs?|MLA|MSP|\bTD\b|senator|congressman|congresswoman|councillor|mayor"
    r"|minister|governor|deputy)\b.{0,40}"
    r"(charged|convicted|arrested|sentenced|on trial|resign|quits?|suspended|sacked|jailed)"
    r"|(charged|convicted|arrested|sentenced|suspended|sacked|jailed)\b.{0,40}"
    r"\b(MPs?|MLA|MSP|senator|congressman|councillor|mayor|minister|governor)\b", re.I)


# Religious-liberty litigators. Deliberately NOT in SOURCE_HINTS: that list is consulted
# when nothing scored at all, and on 20.08.2026 putting them there swept a First Liberty piece
# on Supreme Court term limits and its dated newsletter index into Religious Freedom. Used only
# where a WEAK Church score already proves the headline is about religion.
LIBERTY_LITIGATORS = re.compile(
    r"adfmedia|alliance defending freedom|\bADF\b|first liberty|becket"
    r"|thomas more society|liberty counsel", re.I)


def source_section(outlet):
    """Section implied by a single-issue outlet, when no keyword matched.

    Matching is word-bounded: a bare substring test put "FireRescue1" into Free Speech
    because the hint list contains "fire" for FIRE, the Foundation for Individual Rights
    and Expression.
    """
    home = " %s " % (outlet or "").lower().strip()
    for section, names in SOURCE_HINTS.items():
        for name in names:
            if re.search(r"(?<![a-z])%s(?![a-z])" % re.escape(name), home):
                return section
    return None



# ---------------------------------------------------------------------------
# Publisher category tags.
#
# Chris marked up the 14.08.2026 edition and 8 of his 8 corrections in Free Speech were
# already answered by the feed's own <category> tags: spiked files both Jason Arday pieces
# under "Identity Politics"/"EDI", the Edwina Currie piece under "Immigration", the Smears
# Commission under "Politics". My keyword classifier disagreed with the publisher AND with
# Chris in every one of those cases.
#
# So where a publisher labels its own story, that label wins. This also retires the
# SOURCE_HINTS hack for the commentary magazines, which routed everything spiked wrote to
# Free Speech on the theory that spiked writes about speech - importing its politics,
# immigration and identity coverage along with it.
# ---------------------------------------------------------------------------
CATEGORY_MAP = [
    ("Immigration & Asylum",
     r"^(immigration|migration|migrants?|asylum|refugees?|small boats?|borders?)$"),
    ("Gender, Identity & Sexuality",
     r"^(identity politics|EDI|DEI|diversity|equality diversity|race and racism"
     r"|gender|transgender|trans|lgbt.*|sexuality|feminism|women'?s rights"
     r"|critical race theory|woke(ness)?)$"),
    ("Life",
     r"^(abortion|pro-?life|euthanasia|assisted (dying|suicide)|end of life|surrogacy"
     r"|ivf|bioethics|right to life)$"),
    ("Religious Freedom & Persecution",
     r"^(persecution|religious (freedom|liberty|persecution)|blasphemy|martyrdom"
     r"|christian persecution)$"),
    ("Free Speech & Civil Liberties",
     r"^(free speech|freedom of (speech|expression)|censorship|cancel culture"
     r"|civil liberties|privacy|surveillance|digital id|online safety)$"),
    ("Marriage, Family & Education",
     r"^(marriage|family|families|parenting|education|schools?|universit(y|ies)"
     r"|childhood|birth ?rate|demography)$"),
    ("Church & Religion",
     r"^(church|christianity|catholic(ism)?|anglican|religion|faith|islam|judaism"
     r"|vatican|theology|bishops?)$"),
    ("Politics, Government & Society",
     r"^(politics|government|elections?|parliament|westminster|congress|senate"
     r"|conservative party|labour party|reform uk|democrats?|republicans?|policy"
     r"|economy|welfare|crime|justice|society|social affairs|law|legal)$"),
]
CATEGORY_MAP = [(name, re.compile(rx, re.I)) for name, rx in CATEGORY_MAP]
# Tags that say "this is arts/culture filler", which Chris marked "not interesting".
CATEGORY_DROP = re.compile(
    r"^(books?|book review|arty types|arts|theatre|theatre review|film|music|television"
    r"|radio|podcasts?|sport|cricket|football|recipes?|food|drink|travel|fashion"
    r"|obituar(y|ies)|crossword|satire|on theatre|everyday lies)$", re.I)


def category_section(categories):
    """Section implied by the publisher's own tags, or None.

    Ordered by CATEGORY_MAP, so a piece tagged both "Free Speech" and "Immigration" - as
    The Critic tagged "The intractable problems pulling modern Britain apart" - goes to
    Immigration, which is where Chris put it.
    """
    if not categories:
        return None
    for name, rx in CATEGORY_MAP:
        for c in categories:
            if rx.match((c or "").strip()):
                return name
    return None


def category_is_filler(categories):
    """Arts/culture filler - but only when the publisher gives it no substantive tag.

    First cut suppressed The Critic's "The intractable problems pulling modern Britain
    apart" because it carries Books and Book Review, ignoring that it also carries
    Immigration, Free Speech and Grooming Gangs - and Chris had explicitly said that one
    belonged in Immigration. A substantive tag now always wins.
    """
    if not categories:
        return False
    if category_section(categories):
        return False
    hits = [c for c in categories if CATEGORY_DROP.match((c or "").strip())]
    return bool(hits) and len(hits) >= max(1, len(categories) // 2)


# How decisively a headline must disagree with the publisher's own tag before it wins. See
# the reasoning in classify(); the value was fitted to the 20.08.2026 sweep, not guessed.
TAG_OVERRIDE_MIN = 5


# How close two sections must be for the article's own opening to break the tie. Chris,
# 25.08.2026: "Let's add something else other than keyword weighting then that could
# categorise stories like the Sudanese one correctly."
#
# The mechanism is different in kind from weighting, which is why it can succeed where
# reweighting cannot. GB News's "Sudanese migrant allowed to stay in Britain and cannot be
# deported because she married her cousin" genuinely contains both subjects, so no set of
# keyword weights is principled - "married" really is in the headline. What separates them is
# EMPHASIS, and a headline is written to intrigue while an opening is written to say what
# happened. That opening reads "The Home Office initially rejected her asylum application,
# citing suspicions the marriage was not legitimate": immigration leads, marriage is the
# reason given. So when the headline cannot decide, ask the article.
#
# Bounded on purpose. It only runs when the top two sections are within LEAD_TIEBREAK_MARGIN,
# only when text exists, and only over the first LEAD_CHARS - reading the whole body would
# reintroduce the 18.08.2026 failure where commentary out-scores the report it discusses,
# since an essay eventually mentions everything.
LEAD_TIEBREAK_MARGIN = 3
LEAD_CHARS = 300
# The lead must WIN by this much, not merely edge ahead. At >0 the rule was measured on the
# 25.08.2026 sweep and moved 7 of 848 items with text - but three of those were wrong in the
# same direction, pulling religious-liberty stories into Church & Religion ("College Student
# Denied Financial Aid for Choosing Religious Major", "Ten Commandments displays spark new
# religious freedom battle"). A liberty case's opening is naturally thick with "church" and
# "Christian", so a crude lead score always drifts that way.
LEAD_DECISIVE_BY = 3
# ...and that boundary is excluded outright. Religious Freedom vs Church & Religion is the
# most-corrected line in the whole classifier - 14 SECTION cases in testcases.txt exist for it
# alone, plus the tag-override rule and the clergy-prosecution rule. A generic text heuristic
# has no business overruling judgements that specific.
LEAD_TIEBREAK_SKIP = {frozenset(("Religious Freedom & Persecution", "Church & Religion"))}


# An animal being put down is not a Life story. Chris, 31.08.2026: all three of these
# classified as ('Life', 6) - the same section and weight as a genuine assisted-dying story -
# because the end-of-life rule matches "euthanas" and nothing asked WHOSE death it is:
#
#   Appeal of euthanasia order for 'Bubba,' 'Stewie,' dismissed by judge      (two dogs)
#   Tennessee mayor helps halt federal euthanasia order for rescued bald eagle
#   Frost Fund helps save animals from euthanasia with shelter transport trips
#
# That is how a dog and an eagle came to outrank a martyred pastor on the 31.08 sheet. It is
# a CLASSIFICATION defect, not a ranking one - the ABOVE pairs for it were tried and removed,
# see testcases.txt - and the fix belongs here, where the section is decided.
#
# Both halves are required, and the animal noun is looked for in the TEXT as well as the
# headline: "Appeal of euthanasia order for 'Bubba,' 'Stewie,'" names two dogs without using
# the word, which is exactly the case a headline-only rule would miss.
_EOL_WORDS = r"euthanas|put (?:down|to sleep)|\bcull(?:ed|ing)?\b"
_ANIMAL_WORDS = (r"\b(?:dogs?|cats?|puppy|puppies|kitten|pets?|animals?|horses?|eagle|"
                 r"terrier|shepherd|livestock|cattle|sheep|kennel|zoo|wildlife|raptor|"
                 r"veterinar|shelter (?:animal|pet|dog|cat)|bald eagle)\b")


_APOS = {0x2019: "'", 0x2018: "'", 0x02BC: "'", 0xFF07: "'",
         0x201C: '"', 0x201D: '"'}


def _norm_apos(s):
    """Fold typographic quotes to ASCII so keyword patterns match real newspaper copy.

    For MATCHING only - never write the result back onto an item, because compose.py
    copies the headline into the document verbatim.
    """
    return (s or "").translate(_APOS)


def is_animal_euthanasia(headline, text=""):
    """True if this is an animal being put down, not a human end-of-life story."""
    blob = "%s %s" % (headline or "", text or "")
    return bool(re.search(_EOL_WORDS, blob, re.I) and re.search(_ANIMAL_WORDS, blob, re.I))


def classify(headline, outlet, categories=None, text=""):
    # Sham-marriage and marriage-fraud stories stay in Marriage, Family & Education. I had
    # routed them out to Other as off-topic; Chris overruled that on 13.08.2026 - fraud
    # against the institution is in scope. The real defect that day was not the section but
    # the clustering: eight outlets' versions of one green-card sweep each got their own
    # line, which sig_words now stems to prevent.
    # The publisher's own tag beats my keywords when it gives a clear answer - but a tag
    # breaks a TIE, it does not overrule a headline that is decisive and disagrees.
    #
    # Chris, 20.08.2026, on The Federalist's "U.K. Bans Bishop, Lawmaker Convicted Of 'Hate
    # Speech' For Agreeing With The Bible" filed under Religious Freedom & Persecution:
    # "This is a free speech issue rather than a religious freedom and persecution one."
    # The headline was never ambiguous - it scores 5 for Free Speech and 0 for Religious
    # Freedom - but The Federalist tags its own piece "Religious Freedom" and "Christian
    # persecution", and the tag returned before the headline was scored at all. A Western
    # state prosecuting someone over religious speech is a speech story; persecution is what
    # happens where the state is not the forum.
    #
    # The override is deliberately narrow: the headline's top section must be SPECIFIC (not
    # the Church & Religion catch-all), must clear TAG_OVERRIDE_MIN, and the tagged section
    # must score NOTHING on the headline. Where the headline says little the tag still wins
    # outright - which is what keeps The Critic's "The intractable problems pulling modern
    # Britain apart" in Immigration, where Chris put it on 19.08.2026.
    #
    # TAG_OVERRIDE_MIN is 5, not SPECIFIC_MIN's 3, and the difference was measured against the
    # 20.08.2026 sweep rather than guessed. At 3 the rule moved 7 items and three of those
    # were worse: a PinkNews piece about an economic adviser and a Florida primary report both
    # went to Gender on the bare word "gay" (score 3), and a French senator's complaint about
    # anti-Christian mockery left Religious Freedom on a 3. At 5 it moves 4, of which two are
    # the wins - this case, and spiked's "we must defend press freedom from the woke lynch
    # mob" (11), which the Gender tag had been holding out of Free Speech.
    # Chris, 24.08.2026 (TEST 20260824 draft). Two corrections keyword scoring cannot reach,
    # because the deciding word is present but is not what the piece is about. Both sit ahead
    # of the publisher tag: they are his explicit judgement, not a tie-break.
    # Checked FIRST, before any keyword scoring: an animal being put down must not reach a
    # section at all. See is_animal_euthanasia above for why this is a classifier fix and not
    # a ranking one.
    if is_animal_euthanasia(headline, text):
        return None, 0
    # Typographic apostrophes are normalised for MATCHING ONLY - the caller's headline is
    # untouched, because the doc copies it verbatim. Every possessive in the keyword tables
    # was written with a straight apostrophe, and British newspapers publish U+2019, so
    # women'?s could never match women’s. Found by the 01.09.2026 pre-run test: the
    # Telegraph's "Give biological men legal right to compete in women’s sport, say Greens"
    # scored (None, 0) and was dropped entirely, and LifeSiteNews' men-in-women's-sports poll
    # landed in Politics. Normalising here rather than editing each pattern fixes the ones
    # nobody has thought of yet; it is safe because the only two curly apostrophes in this
    # file are inside _RELAY_ATTRIB's [\w’'&.\-] class, which accepts both forms already.
    headline = _norm_apos(headline)
    text = _norm_apos(text)
    if FAMILY_VOTING.search(headline):
        return "Politics, Government & Society", 6
    if ISLAMISM_POLITICAL.search(headline) and not RELIGION_PRACTICE.search(headline):
        return "Politics, Government & Society", 6
    if IMMIGRATION_DECISION.search(headline):
        return "Immigration & Asylum", 6
    if (CLERGY_PROSECUTED.search(headline) and not CLERGY_SCANDAL.search(headline)
            and not CLERGY_SPEECH_CASE.search(headline)):
        return "Religious Freedom & Persecution", 6

    tagged = category_section(categories)
    ranked = score_sections(headline, outlet)
    if tagged:
        top_score, top_section = (ranked[0] if ranked else (0, None))
        tagged_score = next((n for n, sec in ranked if sec == tagged), 0)
        if (top_section and top_section not in (tagged, CHURCH)
                and top_score >= TAG_OVERRIDE_MIN and tagged_score == 0):
            return top_section, top_score
        return tagged, max(4, ranked[0][0] if ranked else 4)

    # Lead-text tiebreak. Placed after the tag logic so a decisive publisher tag still wins,
    # and before the residual routing so it can only ever choose between two sections the
    # headline already nominated - it can never invent one.
    if text and len(ranked) >= 2 and ranked[0][0] - ranked[1][0] <= LEAD_TIEBREAK_MARGIN:
        lead = re.sub(r"\s+", " ", text)[:LEAD_CHARS]
        lead_ranked = dict((sec, sc) for sc, sec in score_sections(lead, ""))
        a_sec, b_sec = ranked[0][1], ranked[1][1]
        if frozenset((a_sec, b_sec)) not in LEAD_TIEBREAK_SKIP:
            a, b = lead_ranked.get(a_sec, 0), lead_ranked.get(b_sec, 0)
            if b - a >= LEAD_DECISIVE_BY:
                return b_sec, ranked[1][0]

    ranked = ranked
    if not ranked:
        hinted = source_section(outlet)
        if hinted:
            return hinted, 1
        # OTHER_ALLOW still admits an item to the Immigration/Politics splits; plain "Other"
        # now additionally requires a positive subject of its own.
        if OTHER_ALLOW.search(headline):
            routed = other_section(headline)
            if routed != "Other" or OTHER_INTEREST.search(headline):
                return routed, 0
        if outlet and ESSAY_SOURCES.search(outlet):
            return "Other", 0
        return (("Other", 0) if OTHER_INTEREST.search(headline) else (None, 0))
    specific = [(s, n) for s, n in ranked if n != CHURCH]
    if specific and specific[0][0] >= SPECIFIC_MIN:
        return specific[0][1], specific[0][0]
    church = [(s, n) for s, n in ranked if n == CHURCH]
    if church:
        # Chris, 19.08.2026, on "Christian DUP MP Jim Shannon charged with common assault"
        # filed under Church & Religion: "This is more of a politics article as the subject is
        # a politician." Only a WEAK church score is overridden - 3 is the bare "christian"
        # or "pastor" word - and only when the headline is an office-holder facing legal or
        # party consequences. A sermon prosecution scores 5+ in Religious Freedom or Free
        # Speech and never reaches this branch, which is what stops the rule swallowing the
        # persecution stories that also say "MP".
        #
        # Routed through other_section rather than returned as Politics directly: Politics is
        # a residual split, not a section in SECTIONS, so this is the only path that respects
        # the 14.08.2026 guarantee that nothing else can lose items to it.
        # A religious-liberty litigator's release scores only the bare "Christian"/"church"
        # word, i.e. a weak Church score, so Church wins by default and the story lands in
        # the wrong section (Chris, 20.08.2026, on the ADF release). Same shape and same
        # threshold as the POLITICIAN_LEGAL override below: only a WEAK church score is
        # overridden, so anything that genuinely scored elsewhere is untouched.
        if church[0][0] <= 3 and outlet and LIBERTY_LITIGATORS.search(outlet):
            return "Religious Freedom & Persecution", church[0][0]
        if church[0][0] <= 3 and POLITICIAN_LEGAL.search(headline):
            routed = other_section(headline)
            if routed != "Other":
                return routed, church[0][0]
        return CHURCH, church[0][0]
    return specific[0][1], specific[0][0]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("json_path")
    ap.add_argument("--per-section", type=int, default=0,
                    help="cap items shown per section (0 = no cap, the default)")
    ap.add_argument("--per-outlet", type=int, default=3,
                    help="most items one outlet may hold at the top of a section before "
                         "the rest move to the visible tail (0 = no limit)")
    ap.add_argument("--outlet-exempt", type=int, default=14,
                    help="importance at or above which an item ignores the per-outlet cap; "
                         "an outlet may hold as many slots as it earns")
    ap.add_argument("--sheet", action="store_true",
                    help="one compact line per STORY across all sections, ordered by how "
                         "many outlets carry it. Read this in a single pass to rank by "
                         "importance; ~20k tokens for a full day")
    ap.add_argument("--opening-cap", type=int, default=0,
                    help="max article openings to fetch (0 = every fetchable lead, the "
                         "default since 25.08.2026 - ranking reads the text, so a cap "
                         "silently decides which stories get judged on their headline)")
    ap.add_argument("--text-chars", type=int, default=900,
                    help="how much article text to print per story in --sheet (default 900; "
                         "was 260 before 25.08.2026)")
    ap.add_argument("--leads-json", metavar="PATH",
                    help="sheet only: also write a machine-readable manifest of the leads "
                         "shown, for record_tiers.py. Emitted from the same list the sheet "
                         "prints, so the two cannot disagree about what a lead is")
    ap.add_argument("--tiers-db", default=None,
                    help="path to the tier store (default: tiers.json beside the scripts)")
    ap.add_argument("--new-only", action="store_true",
                    help="sheet only: print just the leads tiers.json has no verdict on, or "
                         "whose article text has changed since it was judged. Turns a re-run "
                         "from a full re-read into a diff")
    ap.add_argument("--no-ledes", action="store_true",
                    help="sheet only: skip fetching article ledes for text-starved stories")
    ap.add_argument("--show-chaff", action="store_true",
                    help="list suppressed celebrity/entertainment items instead")
    args = ap.parse_args()

    data = json.load(open(args.json_path))
    global SWEEP_WINDOW_H
    SWEEP_WINDOW_H = data.get("window_hours") or SWEEP_WINDOW_H
    items = data["items"]
    buckets = {n: [] for n in SECTION_NAMES}
    # Two different failure modes, deliberately kept apart. Lumping them together hid the
    # real one: of 208 items suppressed on 14.08.2026, only 20 were celebrity/sport/schedule
    # chaff - the other 188 simply matched no section, and that bucket was where the
    # Farage by-election commentary, the A-level results and a Zelensky story went. They
    # need opposite fixes (tighten the chaff regex vs widen OTHER_ALLOW), so a single
    # "SUPPRESSED" list pointed every future reader at the wrong one.
    chaff, unsectioned, already = [], [], []
    blocked = []

    for idx, it in enumerate(items):
        it["_i"] = idx                      # index into items[], used by compose.py
        # Checked BEFORE is_chaff so a banned source never lands in a bucket that invites
        # a second opinion. See is_blocked_outlet.
        if is_blocked_outlet(it["outlet"] or ""):
            blocked.append(it)
            continue
        if is_chaff(it["headline"], it["outlet"] or "", it.get("categories")):
            chaff.append(it)
            continue
        section, sc = classify(it["headline"], it["outlet"] or "", it.get("categories"),
                               region_text(it))
        if section and is_local_incident(it["headline"], sc, section):
            chaff.append(it)          # printed in the SUPPRESSED list, never silently gone
            continue
        # is_school_routine was written but never wired in - it sat as dead code until
        # 17.08.2026, which is why "Carson City School District opens doors to students" had
        # to be handled by hand. Both school gates run here now, and like every other
        # suppression the item is PRINTED, not silently dropped.
        if section and is_school_routine(it["headline"], sc):
            chaff.append(it)
            continue
        if section and is_school_crime(it["headline"], sc):
            chaff.append(it)
            continue
        if section is None:                  # matched nothing and reads as off-topic
            unsectioned.append(it)
            continue
        it["_score"] = sc
        it["_section"] = section
        # Previously-published stories are NOT excluded any more (Chris, 13.08.2026):
        # a running story can legitimately appear on consecutive days. They stay in their
        # section, flagged with the date they last went out so a repeat is a choice.
        if it.get("seen_on"):
            already.append(it)
        buckets[section].append(it)

    # Corroboration is stamped once, on every candidate, so importance() can read it
    # without the count having to be threaded through every call site.
    all_rows = [it for name in SECTION_NAMES for it in buckets[name]]
    stamp_corroboration(all_rows)

    out = sys.stdout
    if args.sheet:
        # One pass over everything, collapsed to one line per *story* rather than per item.
        #
        # This replaces the subagent fan-out for ranking, and it is both cheaper and better.
        # Measured on the 13.08.2026 sweep: 742 candidates as bare lines is ~20k tokens,
        # while 17 review subagents cost ~250-300k, almost all of it scaffolding and a brief
        # repeated seventeen times. Worse, slicing by section makes cross-cluster judgement
        # impossible - a reviewer holding only Life cannot know a Nigerian court ruling
        # outranks the fifth Trump piece, which is exactly the comparison Chris asked for.
        leads = [it for it in all_rows if it.get("_corr_lead")]
        # Sorted TWICE, and both are load-bearing. This first pass orders the fetch queue:
        # attach_ledes is capped and takes leads best-first, so a bad order here decides
        # which stories get text at all.
        leads.sort(key=lambda i: (-importance(i), -i["_corr"], i["age_h"] or 0))
        # Text assessment (Chris, 18.08.2026): the judge should read what the article SAYS,
        # not only its headline. Feed summaries are free; for stories the feed leaves blind
        # a bounded fetch recovers the article's own standfirst. Deliberately surfaced HERE,
        # to the judgement pass, and kept out of importance() - measured on this day's sweep,
        # regex-scoring body text mostly rewards commentary that narrates outcomes.
        fetched = 0 if args.no_ledes else attach_ledes(leads)
        opened = 0 if args.no_ledes else attach_openings(leads, cap=args.opening_cap)
        # Then the two routes for leads the opening fetch cannot reach: a capped public
        # preview for paywalled leads, and - last - another outlet's account of the same
        # story for the ones that refuse machine access entirely.
        previewed = 0 if args.no_ledes else attach_previews(leads)
        borrowed = 0 if args.no_ledes else attach_sibling_text(leads)
        # ...and re-sorted now the text exists, because importance() reads the text signals
        # that attach_openings has just written. Until 25.08.2026 only the first sort ran, so
        # the sheet was ORDERED on importance-without-text while PRINTING importance-with-text:
        # the iNN column rose at 252 of 1,111 adjacent pairs and the header's promise of a
        # reading order was quietly false. With TEXT_SIGNAL_WEIGHT at 4 the two differ by up
        # to 8 points, so this moves real stories, not just the numbers beside them.
        leads.sort(key=lambda i: (-importance(i), -i["_corr"], i["age_h"] or 0))
        # COVERAGE, not work done. Until 01.09.2026 this line reported `fetched`,
        # `previewed` and `borrowed` - the three counters for what this RUN had to go and
        # get - and silently omitted `opened`, which is the main text route and was assigned
        # to a variable nothing ever read. The brief tells the morning run to report this
        # line and treat a sharp drop as "the day was ranked on headlines", so it has to
        # mean readability. It did not: on a warm cache (01.09.2026, a 36h window over the
        # ground the 84h Monday sweep already covered) it read 176 of 929 = 19% while true
        # coverage was 89%, and it raised a false alarm. Worse in the other direction - if
        # attach_openings failed outright, `opened` would be 0 and this line would look
        # unchanged, hiding the exact failure it exists to surface.
        #
        # The branch order below MIRRORS the sheet's own (text -> preview -> feed -> page
        # -> sibling -> nothing). If you change one, change both, or this reports a
        # readability the sheet does not print.
        def _text_route(it):
            if it.get("_opening"):  return "text"
            if it.get("_preview"):  return "preview"
            if real_summary(it):    return "feed"
            if it.get("_lede"):     return "page"
            if it.get("_sibtext"):  return "sibling"
            return None

        routes = collections.Counter(_text_route(it) for it in leads)
        have = sum(v for k, v in routes.items() if k)
        total = len(leads) or 1
        sys.stderr.write(
            "text coverage: %d/%d leads readable (%.0f%%) - %d article text, %d paywalled "
            "preview, %d feed summary, %d shallow page, %d via another outlet, %d NO TEXT\n"
            % (have, len(leads), 100.0 * have / total, routes["text"], routes["preview"],
               routes["feed"], routes["page"], routes["sibling"], routes[None]))
        sys.stderr.write(
            "  fetched this run (rest came from cache): %d opening(s), %d lede(s), "
            "%d preview(s), %d sibling(s)\n" % (opened, fetched, previewed, borrowed))
        if 100.0 * have / total < 70:
            sys.stderr.write(
                "  TEXT COVERAGE DEGRADED - under 70%. The day is being ranked on headlines; "
                "say so prominently in the final message.\n")

        def lead_text(it):
            return it.get("_opening") or it.get("_preview") or it.get("_sibtext")

        # The manifest is written from `leads` BEFORE --new-only filters it: recording only
        # the leads that were re-read would leave every unchanged story permanently absent
        # from the store, and so permanently "new" - the exact loop this is meant to break.
        if args.leads_json:
            import tiers as _tiers
            manifest = [{"i": it["_i"], "key": fetch_feeds.url_key(it["url"]),
                         "section": it.get("_section"), "headline": it.get("headline"),
                         "outlet": it.get("outlet"),
                         "text_id": _tiers.text_id(lead_text(it))} for it in leads]
            with open(args.leads_json, "w") as fh:
                json.dump(manifest, fh)
            sys.stderr.write("wrote %d lead(s) to %s\n"
                             % (len(manifest), args.leads_json))

        if args.new_only:
            import tiers as _tiers
            db = _tiers.load(args.tiers_db or _tiers.TIERS_DB)
            total = len(leads)
            leads = [it for it in leads
                     if _tiers.stale(db, fetch_feeds.url_key(it["url"]), lead_text(it))]
            sys.stderr.write(
                "--new-only: %d of %d lead(s) need judging (%d already decided on the same "
                "text)\n" % (len(leads), total, total - len(leads)))

        # Cross-day repeats (Chris, 27.08.2026). Attached AFTER --new-only has narrowed the
        # list, so a re-run costs nothing extra, and reported on stderr because a history that
        # silently came back empty would leave the check looking like it ran. If the archive
        # is missing - a fresh machine, or a restore that has not happened yet - this is a
        # no-op, and the line below is the only thing that would say so.
        stamp = history.edition_date(data)
        past = history.load_history(before=stamp)
        seen_editions = history.editions_loaded(before=stamp)
        # The entity arm needs a document frequency measured over ONE corpus, so the index is
        # built over today's leads AND the recent editions together. Without this argument
        # ran_before falls back to word overlap alone, which is what run_tests' two-item
        # calls want and is NOT what a real edition wants: measured 27.08.2026, the arm takes
        # same-story recall from 0.540 to 0.736.
        past_ents = union_entity_index(leads, past)
        repeats = 0
        for it in leads:
            hit = ran_before(it, past, ents=past_ents)
            if hit:
                it["_ran_story"] = hit
                repeats += 1
        sys.stderr.write(
            "cross-day: %d lead(s) match a story from the last %d edition(s) [%s]%s\n"
            % (repeats, len(seen_editions), ", ".join(seen_editions) or "none",
               "  -- NO ARCHIVE READ, repeat check is inactive" if not seen_editions else ""))

        out.write("RANKING SHEET - %d stories from %d candidates, %s sources\n"
                  % (len(leads), len(all_rows), data.get("sources", "?")))
        out.write("one line per story; xN = N outlets carrying it (the only free measure of "
                  "how big it is)\ncols: N | section | region | iN xN | headline | outlet | "
                  "age\n'> text:' is the article's own opening, fetched and scrubbed of page "
                  "furniture - rank on this, not the headline. '> feed:' is the outlet's own "
                  "summary, used when the page could not be fetched; '> page:' an older "
                  "shallow standfirst.\n'> preview (£...)' is a PAYWALLED story's public "
                  "preview - the publisher's own summary and opening, never the article. It "
                  "is short by design, so judge it against other previews, not against a "
                  "full '> text:' line.\n'> via <outlet> on the same story' is a DIFFERENT "
                  "outlet's account, read because the lead itself refuses machine access. It "
                  "tells you what the story is; it is not the lead's own words, and the "
                  "briefing still links the lead.\n'> NO TEXT:' says why nothing could be "
                  "read. Judge those on the headline and do not mistake silence for "
                  "insignificance - the outlet it happens to most is the Telegraph.\n"
                  "read the whole sheet, then tier: "
                  "1 must run, 2 if room, 3 filler. Compare across sections, not within.\n"
                  "★ = a primary source (advocacy body's own release, court filing, etc). "
                  "These are x1 by definition and sink in a corroboration-ordered sheet, so "
                  "read every ★ line before tiering - compose.py warns if a ★ source filed "
                  "today and nothing of theirs was picked.\n"
                  "'[ran DD]' means this exact URL ran in an earlier edition. "
                  "'[SAME STORY ran DD: ...]' is the stronger warning: the same story under "
                  "a DIFFERENT url, which is how Right To Life's 25.08 piece came back on "
                  "27.08 unflagged. Neither is a veto - a running story can legitimately "
                  "run again - but the second one means read the past headline before you "
                  "pick it.\n\n")
        # ★ marks a PRIMARY_SOURCE item. The sheet is ordered by corroboration, which is the
        # right order for judging how big a story is and the WRONG one for finding the stories
        # Chris cares most about: an advocacy body's own release is x1 by definition - nobody
        # else has filed it yet - so SPUC, ADF, Live Action, Desiring God and WORLD sink to the
        # bottom of a 2,400-line sheet however important they are. On 24.08.2026 he listed 33
        # stories that should have run and 17 of them were in the sweep, unpicked, most of them
        # exactly that shape. The marker does not reorder anything - reordering by source would
        # bury the day's real news instead - it just makes them findable wherever they sit.
        for it in leads:
            n = it["_corr"]
            star = " ★" if any(t in (it["outlet"] or "").lower()
                               for t in PRIMARY_SOURCE) else ""
            out.write("%d%s | %s | %s | i%-2d x%d | %s | %s%s | %s%s\n" % (
                it["_i"], star, it["_section"][:4],
                regions.region(it["headline"], it["outlet"], "", region_text(it)),
                importance(it), n, it["headline"], it["outlet"],
                (" £" if it["paywalled"] else "") +
                (" ↗" if "news.google.com" in it["url"] else ""),
                "new" if it["age_h"] is None else "%sh" % it["age_h"],
                ("  [ran %s]" % it["seen_on"][5:] if it.get("seen_on") else "")
                + ('  [SAME STORY ran %s: "%s" - %s]'
                   % (it["_ran_story"]["date"][4:6] + "-" + it["_ran_story"]["date"][6:],
                      it["_ran_story"]["headline"][:70],
                      it["_ran_story"]["outlet"])
                   if it.get("_ran_story") else "")))
            flags = textsignals.flag_string(it.get("_sig"))
            if flags:
                out.write("    > is: %s\n" % flags)
            text = real_summary(it)
            if it.get("_opening"):
                out.write("    > text: %s\n" % it["_opening"][:args.text_chars])
            elif it.get("_preview"):
                out.write("    > preview (£, publisher's own summary): %s\n"
                          % it["_preview"])
            elif text:
                out.write("    > feed: %s\n" % text)
            elif it.get("_lede"):
                out.write("    > page: %s\n" % it["_lede"][:200])
            elif it.get("_sibtext"):
                out.write("    > via %s on the same story: %s\n"
                          % (it["_sibfrom"], it["_sibtext"][:args.text_chars]))
            else:
                # Say WHY there is no text. An absent line reads as an absent story, and
                # the outlet it happens to most is the Telegraph - 8 of its 12 leads on
                # 25.08.2026 - which is exactly the outlet Chris does not want under-ranked
                # for it. A stated reason is harder to skim past than a gap.
                if it.get("paywalled"):
                    why = ("paywalled, and this publisher serves no public preview - "
                           "judge on the headline")
                elif "news.google.com" in (it.get("url") or ""):
                    why = "unresolved Google News redirect - no page to read"
                else:
                    why = "page could not be fetched (blocked or unavailable)"
                out.write("    > NO TEXT: %s\n" % why)
        for label, rows in (("BLOCKED SOURCES - ruled out by Chris. Do NOT pick from "
                             "here; this is not an over-matching filter", blocked),
                            ("CHAFF - celebrity/sport/schedule filler", chaff),
                            ("NO SECTION MATCHED - widen OTHER_ALLOW if any of these "
                             "are real news", unsectioned)):
            if rows:
                out.write("\nSUPPRESSED, %s (%d):\n" % (label, len(rows)))
                for it in rows:
                    out.write("%d | %s | %s\n"
                              % (it["_i"], it["headline"][:96], (it["outlet"] or "")[:20]))
        return

    if args.show_chaff:
        for label, rows in (("BLOCKED SOURCES - ruled out by Chris, do NOT pick", blocked),
                            ("CHAFF - celebrity/sport/schedule filler", chaff),
                            ("NO SECTION MATCHED", unsectioned)):
            out.write("SUPPRESSED, %s (%d)\n\n" % (label, len(rows)))
            for it in rows:
                out.write("%d | %s | %s\n"
                          % (it["_i"], it["headline"][:96], (it["outlet"] or "")[:24]))
            out.write("\n")
        return

    out.write("SHORTLIST from %s\n" % data.get("generated", "?"))
    out.write("window %sh | %d candidates | suppressed: %d chaff + %d no section matched "
              "(--show-chaff to audit both)\n"
              % (data.get("window_hours", "?"), len(items), len(chaff), len(unsectioned)))
    out.write("pick by the leading number; compose.py copies the fields verbatim\n")
    out.write("cols: N | region | headline | outlet | author | age    "
              "(£ = paywalled, ↗ = link is a Google News redirect, prefer a direct "
              "version of the same story where one is listed)\n")
    out.write("each section is already ordered UK -> Europe -> North America -> "
              "Australia/NZ -> Asia -> Africa -> Latin America -> global -> unplaced; "
              "pick top-down to keep that order\n")

    for name in SECTION_NAMES:
        rows = sorted(buckets[name], key=lambda i: (-importance(i), i["age_h"] or 0))
        # A cap must never hide an item: everything past it still prints, compactly.
        cut = args.per_section or len(rows)
        top, over = diversify(rows[:cut], args.per_outlet,
                              exempt_at=args.outlet_exempt)
        head = regions.sort_by_region(top,
                                      key=lambda i: (i["headline"], i["outlet"], i.get("url") or ""))
        tail = regions.sort_by_region(over + rows[cut:],
                                      key=lambda i: (i["headline"], i["outlet"], i.get("url") or ""))
        marks = cluster_duplicates(rows)
        dups = sum(1 for m in marks.values() if m.startswith("  ("))
        out.write("\n### %s  (%d%s)\n"
                  % (name, len(rows),
                     ", %d near-duplicates flagged" % dups if dups else ""))
        for it in head:
            flags = (" £" if it["paywalled"] else "") + \
                    (" ↗" if "news.google.com" in it["url"] else "")
            out.write("%d | %s | %s | %s%s | %s | %s%s\n" % (
                it["_i"], regions.region(it["headline"], it["outlet"], "",
                                         region_text(it)),
                it["headline"], it["outlet"], flags, it["author"] or "-",
                "new" if it["age_h"] is None else "%sh" % it["age_h"],
                ("  [ran %s]" % it["seen_on"][5:] if it.get("seen_on") else "")
                + marks.get(id(it), "")))
        if tail:
            out.write("--- lower-ranked, same section (%d) ---\n" % len(tail))
            for it in tail:
                out.write("%d | %s | %s | %s%s%s\n" % (
                    it["_i"], regions.region(it["headline"], it["outlet"], "",
                                         region_text(it)),
                    it["headline"], it["outlet"],
                    " ↗" if "news.google.com" in it["url"] else "",
                    marks.get(id(it), "")))

    if already:
        out.write("\n# %d of the items above also ran in an earlier edition; each is marked\n"
                  "# [ran DD] on its line. Repeating a running story is fine.\n" % len(already))

    # Suppression used to be the one place an item could vanish without trace: the ranking
    # tail always prints, but chaff simply disappeared unless --show-chaff was passed, and
    # nobody passes it. That is how the "slams" rule went unnoticed. Print the discards.
    # Blocked sources print FIRST and with the opposite instruction to the other two. The
    # other buckets exist so a wrong suppression is visible and can be overridden; this one
    # exists so a standing decision is visible and is NOT overridden.
    if blocked:
        out.write("\n### SUPPRESSED, BLOCKED SOURCES (%d) - outlets Chris has ruled out "
                  "entirely.\n### These are NOT an over-matching filter and are NOT for "
                  "review: do not pick from this list.\n### compose.py will refuse to build "
                  "if one appears in picks.json.\n" % len(blocked))
        for it in blocked:
            out.write("%d | %s | %s\n"
                      % (it["_i"], it["headline"][:100], (it["outlet"] or "")[:24]))

    for label, rows in (("CHAFF (%d) - celebrity, sport and schedule filler", chaff),
                        ("NO SECTION MATCHED (%d) - nothing in the headline reached a "
                         "section. This is the bucket that hides real news: widen "
                         "OTHER_ALLOW if any of these belong in the briefing", unsectioned)):
        if rows:
            out.write("\n### SUPPRESSED, " + (label % len(rows))
                      + ". Listed so a wrong suppression is visible - pick from here if "
                        "one is genuinely news.\n")
            for it in rows:
                out.write("%d | %s | %s\n"
                          % (it["_i"], it["headline"][:100], (it["outlet"] or "")[:24]))


if __name__ == "__main__":
    main()
