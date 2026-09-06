#!/usr/bin/env python3
"""Work out which part of the world a story belongs to.

The briefing is ordered UK first, then Europe, then the rest — the pattern the
hand-made editions follow. shortlist.py presents candidates in this order and
compose.py enforces it, so both import from here and cannot drift apart.

Place names in the headline beat the outlet's home country: "Australia adds
sexuality and gender identity to census" is an Australian story even when an Iowa
newspaper files it. Items with neither signal are "Unplaced" and sort last, so a
bad guess never buries a UK story.
"""

import re

# Briefing order. "Unplaced" is deliberately last.
# Chris, 16.08.2026: "lead with the UK, then Ireland, then Europe, then the US, Canada,
# Australia, New Zealand", with Latin America moved up to sit straight after the US - it is
# CitizenGO's largest constituency outside Europe, and ranking it low was letting today's
# thin English-language coverage stand in for its actual importance.
# International sits 4th, above the anglosphere: a UN treaty vote, a WHO instrument or a
# Strasbourg ruling binds all thirty countries CitizenGO works in at once, which outranks any
# single national story. Chris agreed 16.08.2026. The Vatican is NOT here - it is in Europe,
# where it belongs geographically, because leaving it under "International" sorted 19 papal
# items a day below New Zealand in a briefing whose largest section is Church & Religion.
TIERS = ["UK", "Ireland", "Europe", "International", "United States", "Latin America",
         "Canada", "Australia", "New Zealand", "Africa", "Asia", "Middle East",
         "Unplaced"]
TIER_INDEX = {t: i for i, t in enumerate(TIERS)}

# Matched against the headline, in this order.
HEADLINE_SIGNALS = [
    ("UK",
     # "U.K." with stops never matched \bUK\b, so a British activist questioned by British
     # police was filed under Canada on the strength of Rebel News's masthead (Chris,
     # 19.08.2026: "This should be in the UK section"). The story decides, not the outlet.
     r"\bUK\b|\bU\.K\.|britain|british|(?<!new )england|english|scotland|scottish"
     r"|(?<!new south )\bwales\b|welsh"
     r"|northern ireland|westminster|whitehall|holyrood|stormont|senedd"
     # \bMPs?\b and \bMSPs?\b moved to ACTOR_SIGNALS on 20.08.2026: most parliaments call
     # their members MPs, so "Ukrainian MPs appoint new defence minister" was filed UK. The
     # unambiguous institutions below stay here, because only Britain has a Westminster.
     r"|house of (lords|commons)|downing street"
     r"|\blabour\b|\btory\b|\btories\b|conservative party|reform uk|\blib dem"
     r"|starmer|badenoch|farage|\bSNP\b|sturgeon|swinney|flynn|\bscots\b"
     r"|rayner|burnham|streeting|\bNHS\b|ofsted|\bEHRC\b|ofcom|\bCPS\b|home office"
     # Chris, 27.08.2026: a Guido story about HMRC hiring American consultants was filed
     # under the United States, because "US" was the only geographic token the headline
     # offered - HMRC was not in this list at all. The peers alongside it were missing too.
     r"|\bHMRC\b|\bDWP\b|\bDVLA\b|\bHMCTS\b|\bHMPO\b|valuation office agency"
     r"|crown court|high court of justice|london|manchester|birmingham|liverpool"
     r"|glasgow|edinburgh|cardiff|belfast|yorkshire|county durham"
     r"|church of england|\bC of E\b|\bCofE\b|canterbury|lambeth|york minster"),
    ("Ireland",
     r"(?<!northern )\bireland\b|\birish\b|dublin|\bd[aá]il\b|taoiseach|oireachtas"
     r"|sinn f[eé]in|fine gael|fianna f[aá]il|leinster house|galway|cork\b|limerick"),
    ("Europe",
     r"vatican|holy see|\bpope\b|papal|leo xiv|castel gandolfo|roman curia"
     r"|\bEU\b|european union|brussels|strasbourg|\bECHR\b|european (court|commission|parliament)"
     r"|france|french|paris|germany|german|berlin|spain|spanish"
     r"|italy|italian|rome\b|poland|polish|slovakia|slovak|hungary|hungarian|czech"
     r"|austria|netherlands|dutch|belgium|belgian|sweden|swedish|norway|norwegian"
     r"|denmark|danish|finland|portugal|greece|greek|switzerland|swiss|ukraine"
     r"|russia|russian|romania|bulgaria|croatia|serbia|malta|luxembourg|iceland|estonia"
     # The country names were all here but only SOME of their adjectival forms, so a headline
     # using the adjective alone never reached Europe: "ukraine" matched but "ukrainian" did
     # not (found 20.08.2026 - five items misfiled that day, to Unplaced, Australia and the
     # UK). The MPs token had been masking it by claiming those headlines for Britain.
     r"|ukrainian|kyiv|kiev|austrian|finnish|portuguese|romanian|bulgarian|croatian"
     r"|serbian|maltese|icelandic|estonian|slovenia|slovenian|lithuania|lithuanian"
     r"|latvia|latvian|cyprus|cypriot|albania|albanian|bosnia|montenegro|kosovo"),
    # US PLACE names only. The actor tokens that used to live here - trump, congress, US,
    # the agency acronyms - moved to US_ACTOR below and are tested only after every other
    # geography has had a turn. See region_detail for why.
    ("United States",
     r"\bMass\.|united states|america(n|ns)?\b"
     r"|new mexico|texas|florida|california|new york|michigan|colorado|illinois|massachusetts"
     r"|idaho|kansas|missouri|minnesota|ohio|virginia|maryland|iowa|nebraska|utah"
     r"|carolina|georgia|arizona|indiana|kentucky|tennessee|alabama|mississippi"
     r"|louisiana|oklahoma|arkansas|wisconsin|oregon|nevada|montana|wyoming|dakota"
     r"|connecticut|vermont|maine|new hampshire|new jersey|pennsylvania|delaware"
     r"|rhode island|alaska|hawaii|chicago|houston|dallas|atlanta|denver|seattle"
     r"|boston|philadelphia|phoenix|miami|pittsburgh|new england|baltimore|milwaukee"
     r"|minneapolis|st\.? louis|kansas city|cleveland|cincinnati|nashville|memphis"
     r"|portland|sacramento|san diego|san francisco|las vegas|orlando|tampa|charlotte"
     r"|\bNBA\b|\bWNBA\b|\bNFL\b|\bMLB\b|ivy league"),
    ("Canada",
     r"canada|canadian|ottawa|ontario|quebec|qu[eé]bec|alberta|manitoba|saskatchewan"
     r"|british columbia|toronto|montreal|vancouver|calgary|\bMAiD\b|trudeau|carney"),
    ("Australia",
     r"australia|australian|\bNSW\b|queensland|melbourne|sydney|canberra|brisbane"
     r"|perth|adelaide|tasmania|albanese|(?<!davis )hanson|\bVAD\b|\bAFL\b"),
    ("New Zealand",
     r"new zealand|\bkiwi\b|auckland|wellington|christchurch|luxon|ardern|all blacks"),
    ("Asia",
     # \bindia rather than a bare "india": Indiana is a US state, and an unanchored match
     # posted Indiana stories to Asia. Same substring class as the Woman/Oman bug below.
     r"\bindia\b|\bindian\b|\bindians\b|delhi|mumbai|china|chinese|beijing|hong kong|japan|japanese|tokyo"
     r"|korea|korean|seoul|pakistan|pakistani|bangladesh|vietnam|indonesia|philippines"
     r"|malaysia|singapore|thailand|myanmar|nepal|sri lanka|afghanistan|kazakh"
     r"|taiwan|tamil|mongolia|cambodia|laos|bhutan|maldives"),
    ("Middle East",
     # "oman\b" had no LEADING boundary, so it matched the "oman" inside Woman, Roman and
     # Ottoman - and because Middle East is tested before Africa, Asia and Latin America,
     # any headline containing "woman" was posted to the Middle East. It put a Nigerian
     # court ruling, a Brazilian misgendering conviction and a Lowestoft murder case there:
     # 17 items in one sweep (found 17.08.2026). Michael Jordan needs the same guard.
     r"iran|iranian|iraq|iraqi|syria|syrian|israel|israeli|palestin|west bank|gaza"
     r"|lebanon|lebanese|(?<!michael )\bjordan\b|turkey|turkish|saudi|emirates|\bUAE\b|qatar|kuwait"
     r"|bahrain|\boman\b|\bomani\b|yemen|hormuz"
     # City names were missing entirely, so "Spitting at nuns: Religious harassment by Jewish
     # extremists becomes routine in Jerusalem" was Unplaced (Chris, 17.08.2026).
     r"|jerusalem|tel aviv|ramallah|bethlehem|nazareth|hebron|damascus|beirut|tehran"
     r"|baghdad|riyadh|doha|dubai|abu dhabi|amman\b|ankara|istanbul"),
    ("Africa",
     r"nigeria|nigerian|kenya|kenyan|uganda|sudan|sudanese|ethiopia|somalia|egypt"
     r"|egyptian|algeria|morocco|tunisia|libya|ghana|cameroon|congo|tanzania|zimbabwe"
     r"|zambia|mozambique|south africa|senegal|\bmali\b|niger\b|burkina|eritrea"
     r"|rwanda|malawi|namibia|botswana|angola|chad\b|benin|togo|ivory coast"
     # Added 20.08.2026. "Fulani Militias Kill 24 Christians in Governor Mutfwang's County"
     # named no country at all, so it fell through to the outlet map and landed in the US.
     r"|fulani|boko haram|plateau state|benue|kaduna"),
    ("Latin America",
     r"(?<!new )mexico|(?<!new )mexican|brazil|brazilian|argentina|chile|chilean|colombia|colombian"
     r"|peru|bolivia|ecuador|venezuela|cuba|cuban|nicaragua|honduras|guatemala"
     r"|el salvador|uruguay|paraguay|dominica|haiti|panama|costa rica"),
    ("International",
     # These acronyms are matched CASE-SENSITIVELY via (?-i:...). The whole pattern list runs
     # under re.I, which made "\bWHO\b" match the ordinary English word "who" - so any headline
     # containing "who" was posted to International, 32 of them in one sweep, including
     # "'Trans moms' who tortured..." and "Surrogate mother who saved baby...", both of which
     # shipped in the 17.08 edition under the wrong region. Same family as the Woman/Oman bug.
     r"(?-i:\bUN\b|\bWHO\b|\bOSCE\b)|united nations|unicef|unesco|world health"
     r"|council of europe|synod of bishops"
     r"|worldwide|global(ly)?\b|international (court|community|report|law)"),
]
HEADLINE_SIGNALS = [(t, re.compile(p, re.I)) for t, p in HEADLINE_SIGNALS]

# Tokens that name an ACTOR rather than a place. Tested only after every place signal above
# has failed, because a US actor appearing in a foreign story does not make it a US story.
#
# Chris, 20.08.2026, on the two Cameroon posts being separated: the deeper cause was that
# four of the day's five Nigeria stories had been filed as United States. "United States" sat
# 4th in HEADLINE_SIGNALS and "Africa" 10th, and first match won - so "U.S. condemns latest
# mass killing against Nigerian Christians" and "US Congressman Urges Trump Administration To
# Keep Nigeria On Religious Freedom Blacklist" were both American. That scattered the day's
# biggest persecution cluster across the section, and spent the 25% US quota on African
# stories. Same principle as the Rebel News case in testcases.txt: region follows the story.
# "Chinese National Cast Illegal Ballot", "17 Iranian Hackers Charged In Massive U.S.
# University Cybertheft Scheme" - the crime is American and only the defendant is foreign, but
# "chinese" and "iranian" are place signals and won on order alone (found 20.08.2026 while
# measuring the US/actor split). A nationality immediately followed by a person-noun is a
# description of somebody, not a location, so it is removed from the text the PLACE pass
# reads - but only when the headline also carries a US signal, i.e. when there is a rival
# location at all. Where the nationality is the whole story ("Pakistani Christians face daily
# discrimination at work") nothing is stripped and it still places the item.
PERSON_NATIONALITY = re.compile(
    r"\b(chinese|iranian|indian|pakistani|russian|nigerian|haitian|mexican|somali|syrian"
    r"|afghan|iraqi|turkish|korean|japanese|vietnamese|filipino|cuban|venezuelan|ukrainian)"
    r"[- ](national|nationals|citizen|citizens|immigrant|immigrants|migrant|migrants"
    r"|refugee|refugees|hacker|hackers|student|students|worker|workers|national\b)", re.I)

# A nationality attached to a PERSON'S ROLE, which tells you where the person is from and
# nothing about where the story happened. Separate from PERSON_NATIONALITY above, which is
# deliberately narrow (nationality + migrant/citizen/worker) and is used for a different job:
# keeping a US-actor headline out of the wrong tier. This one exists solely to decide whether
# a headline's geography is really just somebody's passport - the trigger for reading the
# article's opening instead. Chris, 25.08.2026: "This is a British pastor but the story is
# based in India so should be grouped with Indian stories."
NATIONALITY_OF_PERSON = re.compile(
    r"\b(british|uk|english|scottish|welsh|irish|american|us|canadian|australian|kiwi"
    r"|chinese|iranian|indian|pakistani|russian|nigerian|haitian|mexican|somali|syrian"
    r"|afghan|iraqi|turkish|korean|japanese|vietnamese|filipino|cuban|venezuelan|ukrainian"
    r"|french|german|italian|spanish|polish|dutch|swedish|danish|norwegian|finnish)"
    r"[- ](pastor|priest|bishop|imam|rabbi|missionary|preacher|nun|monk|evangelist|clergyman"
    r"|doctor|nurse|surgeon|teacher|lecturer|academic|scholar|lawyer|barrister|judge"
    r"|politician|lawmaker|mp|senator|minister|mayor|activist|campaigner|journalist"
    r"|reporter|author|writer|businessman|businesswoman|entrepreneur|soldier|veteran"
    r"|footballer|athlete|student|man|woman|couple|family|mother|father|teenager|pensioner)"
    r"s?\b", re.I)

# A nationality attached to a THING a domestic body brought in - consultants, kit, software.
# Same job as NATIONALITY_OF_PERSON above, one step out from people: it tells you where the
# thing came from and nothing about where the story happened. Chris, 27.08.2026, on Guido's
# "HMRC Recruited US Big Brother Experts for Tax Snooping Plans": "While US is in the
# headline, this is a UK story. Shouldn't you be scanning text to confirm such news" - the
# actor is HMRC, and "US" only qualifies the consultancy it hired. Kept as narrow as its
# sibling: the noun list is bought-in expertise and equipment, not any noun at all, because
# "US troops" or "US sanctions" ARE the story wherever they land.
NATIONALITY_OF_THING = re.compile(
    r"\b(british|uk|english|scottish|welsh|irish|american|us|canadian|australian"
    r"|chinese|indian|russian|israeli|french|german|italian|spanish|dutch|japanese|korean)"
    # Up to two words may sit between the nationality and the noun it qualifies: the case
    # this was written for reads "US Big Brother Experts". Bounded, because an unbounded gap
    # would let "US" bind to a noun in the next clause and relocate the story wrongly.
    r"[- ](?:[A-Za-z]+[- ]){0,2}"
    r"(expert|experts|consultant|consultants|consultancy|contractor|contractors"
    r"|firm|firms|adviser|advisers|advisor|advisors|specialist|specialists|software"
    r"|technology|tech|kit|equipment|hardware|supplier|suppliers|vendor|vendors"
    r"|model|models|system|systems|provider|providers|agency|agencies)\b", re.I)

# Cities that exist in more than one of our tiers. A bare one of these is not evidence of
# region on its own - Chris, 27.08.2026, on FOX 2 Detroit's "Birmingham parents split over
# schools' bell-to-bell cellphone ban": "While Birmingham is a city in the UK, this is
# clearly a US story and should be in that section." Every name here has a well-known US
# namesake, so when it is the headline's ONLY signal the outlet gets to overrule it.
AMBIGUOUS_CITY = re.compile(
    r"\b(birmingham|boston|manchester|cambridge|oxford|richmond|bristol|plymouth|reading"
    r"|hull|lincoln|preston|warwick|windsor|newport|halifax|rochester|exeter|durham"
    r"|worcester|gloucester|bath|dover|salem|athens|london(?!derry))\b", re.I)

ACTOR_SIGNALS = [
    # A bare "MPs" is British only when no other country is named; see the UK block above.
    # Ordered before the US so a UK-shaped headline is not claimed by a US actor token.
    ("UK", re.compile(r"\bMPs?\b|\bMSPs?\b", re.I)),
    ("United States",
     re.compile(r"\bUS\b|\bU\.S\.|washington|white house"
                r"|congress|senate|house republicans|supreme court|scotus|trump|biden|\bGOP\b"
                r"|democrat|republican|medicaid|medicare|\bDOJ\b|\bFDA\b|\bCMS\b"
                r"|\bHHS\b|\bICE\b|\bMAGA\b"
                # Chris, 27.08.2026: "New Mexico should be further up in this section as we
                # group by country." Law360's "Diocese Says Religious Freedom Fair Defense To
                # DHS Taking" had no place token, no readable page and no DHS here either, so
                # it came out Unplaced and sank to the bottom of Religious Freedom. These are
                # the federal agencies that were missing next to the ones already listed.
                r"|\bDHS\b|\bFBI\b|\bIRS\b|\bFEMA\b|\bEPA\b|\bCDC\b|\bATF\b"
                r"|\bUSCIS\b|\bDEA\b|\bNIH\b|\bpentagon\b|\bDoD\b"
                r"|jp ?morgan|goldman sachs|wall street|polymarket|nasdaq|\bSEC\b", re.I)),
]

# Fallback: where the outlet itself is based. Plain substring match, lowercased, LONGEST key
# wins - which is the mechanism that keeps generic words usable. Note ties do NOT win: the
# check is "longer than the best so far", so an equal-length key found later loses. That is
# why "deccan herald" and not "deccan" is needed to beat the UK's "herald" (both 6).
#
# Short generic keys here are a standing trap. On 17.08.2026 "herald" was posting Deccan
# Herald and Miami Herald to the UK, "express" was posting The Indian Express to the UK, and
# "telegraph" was posting telegraphindia.com to the UK - an Assam child-marriage story led the
# UK block of Marriage, Family & Education in the 17.08 edition because of it. The fix for
# each is a longer, more specific key in the right tier, never deleting the generic one.
OUTLET_HOME = {
    "UK": [
        "telegraph", "the times", "daily mail", "mail online", "guardian", "bbc",
        "sky news", "gb news", "spectator", "the critic", "unherd", "spiked",
        "christian today", "christian concern", "christian institute", "premier christian",
        "catholic herald", "church times", "scotsman", "herald", "news letter",
        "nation.cymru", "metro", "independent", "express", "free speech union",
        "right to life uk", "spuc", "care not killing", "anglican mainstream",
        "statement", "reduxx", "sex matters", "transgender trend", "secular society",
        # Added 17.08.2026 - all were Unplaced, which sorts last, behind Australia.
        "sceptic", "canary", "european conservative", "institute of economic affairs",
        "civitas", "joseph rowntree", "jrf.org", "fabian", "resolution foundation",
        "iain dale", "alastair campbell", "national secular society",
        "humanists uk", "quillette", "tablet", "pinknews", "religion media centre",
        "conservative woman", "conservative home", "politics home", "guido fawkes",
        "labourlist", "schools week", "parent power", "he byte", "anglican ink",
        "psephizo", "fulcrum", "licc", "cmf", "byline times", "thearticle", "tortoise",
        "new statesman", "economist", "financial times", "daily star", "the sun",
    ],
    "Europe": [
        "brussels signal", "euractiv", "deutsche welle", "politico.eu", "european conservative",
        "aroundprague", "dutchnews", "luxembourg times", "infovaticana", "cne",
        "european times", "kathpress", "il foglio",
     "the local", "rfi", "le monde", "vatican news", "voz.us", "around prague", "katholisch",
     # Polish sources added 20.08.2026 after ZENIT was blocked and took the only copy of the
     # same-sex unions veto with it. Needed here because Polish political surnames are not
     # place names, so a headline like "Morawiecki confirms breakaway opposition group will
     # form new party" reaches Unplaced, which sorts last - behind New Zealand.
     "notes from poland", "tvp world",],
    "United States": [
        # Global persecution desks deliberately NOT listed here, though they are US-based:
        # ICC, persecution.org, ChinaAid, Morning Star News and Truth Nigeria each appear in
        # the Africa/Asia/International blocks below, and a tie loses to dict order - so
        # listing them twice silently posted their Nigerian and Chinese reporting to the US
        # (found 20.08.2026). The story's own region is the better default for a wire desk.
        "fox news", "new york post", "nypost", "washington post", "wall street journal",
        "new york times", "daily signal", "daily wire", "federalist", "national review",
        "breitbart", "christian post", "lifenews", "lifesitenews", "live action",
        "washington stand", "heritage", "catholic world report", "national catholic",
        "miami herald", "the pillar", "charlotte lozier", "lozier", "nautilus",
        "marginalian", "homenewshere", "first things", "scotusblog",
        "ewtn", "osv news", "catholic news agency", "cbn", "axios", "the hill",
        "newsweek", "npr", "cnn", "cbs", "nbc", "usa today", "deseret", "wng",
        "world news group", "first things", "public discourse", "relevant", "crisis magazine",
        "christianity today", "baptist press", "daily citizen", "liberty justice",
        "alliance defending freedom", "adf", "townhall", "texas tribune", "stateline",
        "truthout", "the atlantic", "the new yorker", "bloomberg", "reuters",
        "associated press", "ap news", "gatestone", "frc", "family research",
        "institute for family studies", "ifstudies",
        "canadian press",
        "secular pro", "focus on the family", "standing for freedom", "the 74",
        "wbur", "wcvb", "boston globe", "chicago tribune", "charlotte observer",
        "news-gazette", "post-gazette", "star-telegram", "desert sun", "oskaloosa",
        "heartlander", "missouri independent", "arizona capitol", "arkansas times",
     "catholic sun", "catholic review", "angelus news", "the pillar", "wng.org", "fox 2 detroit", "fox 26", "khou", "wcia", "wpri", "wqad", "nbc boston", "politico", "scotusblog", "mother jones", "advocate.com", "out magazine", "lgbtqnation", "urban milwaukee", "dallas express", "first liberty", "lozier", "sba pro-life", "human life international", "los angeles times", "oklahoman", "boston herald", "san francisco chronicle", "washington times", "daily kos", "courthouse news", "denver7", "maine morning star",],
    "Australia": [
        "the australian", "sydney morning herald", "abc news (australia", "news.com.au",
        "courier mail", "spectator australia", "the age", "afr", "stuff", "the post",
     "catholic weekly", "australian christian lobby", "citynews",
        # Chris, 27.08.2026: "This should be grouped with Australian stories". NT is the
        # Northern Territory. Longer than the UK list's bare "independent", which was
        # matching inside "NT Independent" and calling it British - longest-match-wins is
        # what makes the correction a one-line addition rather than a guard on "independent".
        "nt independent", "nt news",],
    "Asia": [
        "times of india", "theprint", "uca news", "asianews", "korea joongang",
        "japan times", "scmp", "south china", "turkish minute",
        "dawn", "express tribune", "the nation (pakistan", "deccan", "the hindu",
        # Longer than the UK's "herald"/"express"/"telegraph", so longest-match sends these
        # to Asia instead. "cna" is Channel News Asia (Singapore); checked against the whole
        # sweep for collisions before adding - it is the only outlet containing that string.
        "deccan herald", "indian express", "telegraphindia", "cna", "hans india",
        "channelnewsasia",
        "new indian express", "radio veritas", "christian daily", "bitter winter",
        "chinaaid", "straits times", "asia news network", "ucanews",
     "news on air", "counterview", "matters india", "hans india", "telangana", "northeast today", "law trend", "etv bharat", "news18", "firstpost", "better india", "chosun",],
    "Africa": [
        "morningstar", "the sun nigeria", "vanguard", "premium times", "truth nigeria",
        "citizen digital", "peoples gazette", "tribune online", "the nation newspaper",
        "guardian nigeria", "daily trust", "punch", "business news nigeria",
     "thisday", "daily post nigeria", "sahara reporters", "legit", "kenyans.co.ke", "modern ghana", "church of nigeria", "sacbc", "southern cross", "church times nigeria", "national daily", "ait live", "face2face",],
    "International": [
        "vatican news", "crux", "aleteia", "zenit", "international christian concern",
        "persecution.org", "open doors", "forum 18", "un news", "world watch",
        "aid to the church", "churchinneed", "acn", "release international",
        "christian solidarity", "article 19", "impact international",
    ],
    "Ireland": ["gript", "irish catholic", "iona institute", "rte", "irish times",
                "irish independent", "the journal.ie"],
    "Canada": ["rebel news", "lifecanada", "b.c. catholic", "catholic register",
               "euthanasia prevention", "globe and mail", "campaign life", "national post",
               "cbc"],
    "New Zealand": ["the post (new zealand)", "stuff (new zealand)", "family first nz",
                    "nz herald", "newsroom"],
    "Middle East": ["middle east eye", "middle east monitor", "jerusalem post",
                    "arab news", "times of israel", "al-monitor", "haaretz"],
    "Latin America": ["aci prensa", "gaudium press", "aci digital", "infobae",
                      "el pais", "la nacion"],
}


# Domains are unambiguous where outlet names are not. "The Daily Telegraph" is the Sydney
# paper; "The Telegraph" is the London one - and both tidy to strings containing "telegraph",
# so no name rule can separate them. Chris, 17.08.2026: "The Daily Telegraph is Australian,
# The Telegraph (£) is London." Checked BEFORE the name map, and longest-match like it.
DOMAIN_HOME = {
    "Europe": ["notesfrompoland.com", "tvpworld.com"],
    "UK": ["telegraph.co.uk", "thetimes.co.uk", "dailymail.co.uk", "theguardian.com",
           "bbc.co.uk", "gbnews.com", "spectator.co.uk", "thecritic.co.uk", "unherd.com",
           "spiked-online.com", "scotsman.com", "independent.co.uk", "express.co.uk",
           "dailysceptic.org", "thecanary.co", "statement.com", "nation.cymru",
           # Chris, 28.08.2026: "This is a UK story" - the National Secular Society on Barnet
           # Council, filed Unplaced because nothing in the headline is geographic and the
           # standfirst's only marker is a London borough no rule names.
           #
           # The generic TLDs rather than secularism.org.uk alone, because adding mastheads
           # one at a time is the drift this map keeps losing to: the same sweep had Norfolk
           # Police on attitude.co.uk and three Premier Woman Alive pieces sitting Unplaced
           # for exactly the same reason. A British domain is a sound DEFAULT and nothing
           # more - domain_home is only consulted once the headline and the text have found
           # nothing, so a UK outlet reporting Nigeria still files under Africa.
           ".co.uk", ".org.uk"],
    "Australia": ["dailytelegraph.com.au", "theaustralian.com.au", "smh.com.au",
                  "abc.net.au", "news.com.au", "spectator.com.au", "heraldsun.com.au",
                  "couriermail.com.au", "acl.org.au"],
    "United States": ["nytimes.com", "washingtonpost.com", "foxnews.com", "nypost.com",
                      "dailywire.com", "dailysignal.com", "nationalreview.com",
                      "thefederalist.com", "firstthings.com", "miamiherald.com"],
    "Asia": ["telegraphindia.com", "timesofindia.indiatimes.com", "deccanherald.com",
             "thefederal.com",
             "indianexpress.com", "channelnewsasia.com", "koreatimes.co.kr"],
    "Ireland": ["irishtimes.com", "independent.ie", "gript.ie", "ionainstitute.ie"],
    "New Zealand": ["thepost.co.nz", "stuff.co.nz", "nzherald.co.nz"],
    "Canada": ["theglobeandmail.com", "ctvnews.ca", "nationalpost.com"],
}


US_PLACE_RX = next(rx for tier, rx in HEADLINE_SIGNALS if tier == "United States")


def domain_home(url=""):
    """Tier for a URL's host, or None. Longest match wins, as with outlet names."""
    u = (url or "").lower()
    if not u:
        return None
    best, best_tier = "", None
    for tier, domains in DOMAIN_HOME.items():
        for d in domains:
            if d in u and len(d) > len(best):
                best, best_tier = d, tier
    return best_tier


def region_detail(headline, outlet="", url="", text=""):
    """Return (tier, how) where how is "headline", "text", "outlet" or "none".

    The distinction matters for ordering: a British outlet writing about American
    sport ("NBA's Enes Kanter Freedom pull anti-trans stunt", PinkNews) is placed in
    the UK only by its outlet, and should not lead the UK block ahead of stories that
    are actually about Britain.

    `text` is the article's own opening - feed summary or fetched standfirst - and is
    consulted ONLY when the headline's single geographic signal is a nationality attached
    to a person. Chris, 25.08.2026, on ICC's "UK Pastor Booked on Bizarre Charges": "This
    is a British pastor but the story is based in India so should be grouped with Indian
    stories." The region has to follow the story, and in that headline the only geographic
    token is the man's nationality - India appears solely in the body ("...charged a British
    Christian leader of Indian descent in Maharashtra, India...").

    Deliberately narrow. Reading text whenever the headline is merely thin would let a
    passing mention relocate a story, and 59% of candidates have no text at all, so the
    rule has to behave identically for them. The trigger is specific: a person-nationality
    match that IS the whole geographic signal, and a different, non-person place named in
    the opening.
    """
    text_body = text or ""
    text = headline or ""
    place_text = text
    if any(rx.search(text) for _, rx in ACTOR_SIGNALS) or US_PLACE_RX.search(text):
        place_text = PERSON_NATIONALITY.sub(" ", text)
    # Does the headline's geography come only from a person's nationality? Compare the
    # headline with that nationality removed: if the signal disappears, it was the person.
    # Strip the three "this is a label on someone or something, not a location" shapes before
    # asking whether any real geography survives. NATIONALITY_OF_THING joined the pair on
    # 27.08.2026; the test below is unchanged in form, which is the point - one more way for
    # a headline's geography to turn out to be borrowed rather than its own.
    stripped = NATIONALITY_OF_THING.sub(
        " ", NATIONALITY_OF_PERSON.sub(" ", PERSON_NATIONALITY.sub(" ", text)))
    for tier, rx in HEADLINE_SIGNALS:
        if rx.search(place_text):
            borrowed_only = not any(r.search(stripped) for _, r in HEADLINE_SIGNALS)
            if borrowed_only and text_body:
                for btier, brx in HEADLINE_SIGNALS:
                    body_places = NATIONALITY_OF_THING.sub(
                        " ", NATIONALITY_OF_PERSON.sub(
                            " ", PERSON_NATIONALITY.sub(" ", text_body)))
                    if btier != tier and brx.search(body_places):
                        return btier, "text"
            # No body to appeal to, or the body agreed: the outlet still gets a say when the
            # ONLY thing the headline offered was a city that exists in two countries. The
            # outlet is hard evidence and an ambiguous city name is not, so a local US
            # station reporting on its own Birmingham outranks the headline's UK reading.
            # Guarded on the signal being ambiguous AND alone - a headline that also says
            # "England" keeps its tier however American the masthead.
            without_city = AMBIGUOUS_CITY.sub(" ", stripped)
            if (AMBIGUOUS_CITY.search(place_text)
                    and not any(r.search(without_city) for _, r in HEADLINE_SIGNALS)):
                by_outlet = _outlet_tier(outlet, url)
                if by_outlet and by_outlet != tier:
                    return by_outlet, "outlet"
            return tier, "headline"
    # Only now: a headline whose sole geographic signal is a US actor is a US story.
    #
    # This fallback used to be unconditional, and that was the deeper half of Chris's
    # 27.08.2026 note. A bare "US" is an ACTOR signal, not a HEADLINE_SIGNALS place, so a
    # headline whose only token was "US" never reached the borrowed-nationality test above -
    # it fell straight through to here and was filed as American without the article ever
    # being read. "HMRC Recruited US Big Brother Experts" is fixed above by HMRC now being a
    # UK token, but "Taxman recruited US consultants" would still have been wrong. So the
    # same two questions get asked here: was that token merely a label on a person or a
    # bought-in thing, and if so does the body name somewhere real?
    for tier, rx in ACTOR_SIGNALS:
        if rx.search(text):
            if text_body and not rx.search(stripped):
                body_places = NATIONALITY_OF_THING.sub(
                    " ", NATIONALITY_OF_PERSON.sub(
                        " ", PERSON_NATIONALITY.sub(" ", text_body)))
                for btier, brx in HEADLINE_SIGNALS:
                    if btier != tier and brx.search(body_places):
                        return btier, "text"
            return tier, "headline"
    by_outlet = _outlet_tier(outlet, url)
    if by_outlet:
        return by_outlet, "outlet"
    return "Unplaced", "none"


def _outlet_tier(outlet="", url=""):
    """Tier from the publisher alone - domain first, then the masthead. None if neither knows.

    Pulled out of region_detail on 27.08.2026 so the ambiguous-city rule above can ask the
    same question mid-way through without duplicating the lookup or reordering it.
    """
    # A Google News redirect carries no publisher host, so this simply returns None there
    # and the outlet-name map still does the work.
    by_domain = domain_home(url)
    if by_domain:
        return by_domain
    home = (outlet or "").lower()
    # Longest match wins, not first tier. Iterating tiers in order made "spectator" (UK)
    # beat "spectator australia", and "new zealand" sitting in the old combined Australia
    # list beat "the post (new zealand)". The more specific name is always the right answer.
    best, best_tier = "", None
    for tier, names in OUTLET_HOME.items():
        for name in names:
            if name and name in home and len(name) > len(best):
                best, best_tier = name, tier
    return best_tier


def region(headline, outlet="", url="", text=""):
    """Return the tier this story belongs to."""
    return region_detail(headline, outlet, url, text)[0]


# A tier is not a country. Africa holds Nigeria and Cameroon; Asia holds India and Pakistan.
# Chris, 20.08.2026: "This Cameroon post should be grouped with the other Cameroon post not
# underneath it" - the two were separated by a Nigeria story because nothing below the tier
# existed to sort on. Only the multi-country tiers need entries; UK, Ireland, the US, Canada,
# Australia, New Zealand, International and Unplaced are each already one group.
#
# Tokens are deliberately copied from HEADLINE_SIGNALS above, guards and all - (?<!new )mexico,
# \boman\b, (?<!michael )\bjordan\b, niger\b - so a country cannot be detected here by a
# pattern the tier itself would reject. Order matters within a tier: longer, more specific
# names first, so "south africa" is not eaten by a bare "africa"-family token.
COUNTRY_SIGNALS = {
    "Europe": [
        ("Vatican", r"vatican|holy see|\bpope\b|papal|leo xiv|castel gandolfo|roman curia"),
        ("Ukraine", r"ukraine|ukrainian|kyiv|kiev"),
        ("Russia", r"russia|russian|moscow|putin"),
        ("France", r"france|french|paris|macron"),
        ("Germany", r"germany|german|berlin"),
        ("Poland", r"poland|polish|warsaw"),
        ("Spain", r"spain|spanish|madrid|ceuta"),
        ("Italy", r"italy|italian|\brome\b|meloni"),
        ("Hungary", r"hungary|hungarian|budapest|orban"),
        ("Sweden", r"sweden|swedish|stockholm"),
        ("Finland", r"finland|finnish|helsinki"),
        ("Netherlands", r"netherlands|dutch|amsterdam"),
        ("Belgium", r"belgium|belgian"),
        ("Austria", r"austria|austrian|vienna"),
        ("Switzerland", r"switzerland|swiss|geneva"),
        ("Portugal", r"portugal|portuguese|lisbon|fatima"),
        ("Greece", r"greece|greek|athens"),
        ("Norway", r"norway|norwegian|oslo"),
        ("Denmark", r"denmark|danish|copenhagen"),
        ("Slovakia", r"slovakia|slovak"),
        ("Czechia", r"czech|prague"),
        ("Romania", r"romania|romanian"),
        ("Serbia", r"serbia|serbian|belgrade"),
        ("Croatia", r"croatia|croatian"),
        ("Bulgaria", r"bulgaria|bulgarian"),
        ("Malta", r"\bmalta\b|maltese"),
        ("Estonia", r"estonia|estonian"),
        ("Iceland", r"iceland"),
        ("Luxembourg", r"luxembourg"),
        ("EU", r"\bEU\b|european union|brussels|strasbourg|\bECHR\b"
               r"|european (court|commission|parliament)"),
    ],
    "Africa": [
        ("South Africa", r"south africa"),
        ("Nigeria", r"nigeria|nigerian|fulani|boko haram|plateau state|benue|kaduna|abuja"),
        ("Cameroon", r"cameroon"),
        ("Kenya", r"kenya|kenyan|nairobi"),
        ("Uganda", r"uganda"),
        ("Sudan", r"sudan|sudanese"),
        ("Ethiopia", r"ethiopia"),
        ("Somalia", r"somalia|somali\b"),
        ("Egypt", r"egypt|egyptian|cairo"),
        ("Algeria", r"algeria"),
        ("Morocco", r"morocco|moroccan"),
        ("Tunisia", r"tunisia"),
        ("Libya", r"libya"),
        ("Ghana", r"ghana"),
        ("Congo", r"congo"),
        ("Tanzania", r"tanzania"),
        ("Zimbabwe", r"zimbabwe"),
        ("Zambia", r"zambia"),
        ("Mozambique", r"mozambique|mozambican"),
        ("Senegal", r"senegal"),
        ("Mali", r"\bmali\b"),
        ("Niger", r"niger\b"),
        ("Burkina Faso", r"burkina"),
        ("Eritrea", r"eritrea"),
        ("Rwanda", r"rwanda"),
        ("Malawi", r"malawi"),
        ("Namibia", r"namibia"),
        ("Botswana", r"botswana"),
        ("Angola", r"angola"),
        ("Chad", r"chad\b"),
        ("Benin", r"benin"),
        ("Togo", r"togo"),
        ("Ivory Coast", r"ivory coast"),
    ],
    "Asia": [
        ("North Korea", r"north korea|pyongyang|kim jong"),
        ("South Korea", r"south korea|korea|korean|seoul"),
        ("Hong Kong", r"hong kong"),
        ("India", r"\bindia\b|\bindian\b|\bindians\b|delhi|mumbai|tamil|maharashtra"
                  r"|kerala|nagaland|chhattisgarh|\bRSS\b|bhagwat"),
        ("China", r"china|chinese|beijing|tibet|uyghur|uighur"),
        ("Japan", r"japan|japanese|tokyo"),
        ("Pakistan", r"pakistan|pakistani|islamabad|lahore"),
        ("Bangladesh", r"bangladesh"),
        ("Vietnam", r"vietnam"),
        ("Indonesia", r"indonesia"),
        ("Philippines", r"philippines|filipino|manila|bangsamoro|mindanao"),
        ("Malaysia", r"malaysia"),
        ("Singapore", r"singapore"),
        ("Thailand", r"thailand|\bthai\b|bangkok"),
        ("Myanmar", r"myanmar|burma|karen\b"),
        ("Nepal", r"nepal"),
        ("Sri Lanka", r"sri lanka"),
        ("Afghanistan", r"afghanistan|afghan|taliban|kabul"),
        ("Kazakhstan", r"kazakh"),
        ("Taiwan", r"taiwan"),
        ("Mongolia", r"mongolia"),
        ("Cambodia", r"cambodia"),
        ("Laos", r"laos"),
        ("Bhutan", r"bhutan"),
        ("Maldives", r"maldives"),
    ],
    "Middle East": [
        ("Israel/Palestine", r"israel|israeli|palestin|west bank|gaza|jerusalem|tel aviv"
                             r"|ramallah|bethlehem|nazareth|hebron|taybeh|netanyahu"),
        ("Iran", r"iran|iranian|tehran"),
        ("Iraq", r"iraq|iraqi|baghdad"),
        ("Syria", r"syria|syrian|damascus"),
        ("Lebanon", r"lebanon|lebanese|beirut"),
        ("Jordan", r"(?<!michael )\bjordan\b|amman\b"),
        ("Turkey", r"turkey|turkish|ankara|istanbul"),
        ("Saudi Arabia", r"saudi|riyadh"),
        ("UAE", r"emirates|\bUAE\b|dubai|abu dhabi"),
        ("Qatar", r"qatar|doha"),
        ("Kuwait", r"kuwait"),
        ("Bahrain", r"bahrain"),
        ("Oman", r"\boman\b|\bomani\b"),
        ("Yemen", r"yemen"),
    ],
    "Latin America": [
        ("Costa Rica", r"costa rica"),
        ("El Salvador", r"el salvador|salvadoran"),
        ("Mexico", r"(?<!new )mexico|(?<!new )mexican"),
        ("Brazil", r"brazil|brazilian"),
        ("Argentina", r"argentina|argentine"),
        ("Chile", r"chile|chilean"),
        ("Colombia", r"colombia|colombian|bogota"),
        ("Peru", r"\bperu\b|peruvian"),
        ("Bolivia", r"bolivia"),
        ("Ecuador", r"ecuador"),
        ("Venezuela", r"venezuela|venezuelan"),
        ("Cuba", r"\bcuba\b|cuban"),
        ("Nicaragua", r"nicaragua|nicaraguan|ortega"),
        ("Honduras", r"honduras"),
        ("Guatemala", r"guatemala"),
        ("Uruguay", r"uruguay"),
        ("Paraguay", r"paraguay"),
        ("Dominican Republic", r"dominica"),
        ("Haiti", r"haiti|haitian"),
        ("Panama", r"panama"),
    ],
}
COUNTRY_SIGNALS = {tier: [(c, re.compile(p, re.I)) for c, p in pairs]
                   for tier, pairs in COUNTRY_SIGNALS.items()}


def country_of(headline, outlet="", url=""):
    """Country within a region, for grouping. Falls back to the tier name.

    Returning the TIER when no country is recognised is deliberate: it makes every
    unrecognised item in a region one group, which keeps them together at the end of that
    region rather than interleaving them with the countries that were identified.
    """
    tier = region_detail(headline, outlet, url)[0]
    for country, rx in COUNTRY_SIGNALS.get(tier, ()):
        if rx.search(headline or ""):
            return country
    return tier


def tier_rank(tier):
    return TIER_INDEX.get(tier, len(TIERS))


def sort_key(headline, outlet="", url=""):
    """(tier, confidence) — stories genuinely about a place lead its block."""
    tier, how = region_detail(headline, outlet, url)
    return (tier_rank(tier), 0 if how == "headline" else 1)


def sort_by_region(items, key):
    """Stable sort into briefing order. `key` maps an item to (headline, outlet).

    Within a region, stories about the same country are grouped (Chris, 20.08.2026). The
    group's position is the position of its FIRST member, not alphabetical: the
    highest-ranked story still decides which country leads the region, and its countrymates
    move up to join it. Everything else about the sort is unchanged and still stable, so any
    judgement about what leads a region survives.
    """
    decorated = []
    for i, it in enumerate(items):
        args = key(it)
        tier, how = region_detail(*args)
        decorated.append((tier_rank(tier), 0 if how == "headline" else 1,
                          country_of(*args), i, it))
    # Counter is global but only ever compared WITHIN a (tier, confidence) block, and inside
    # one block the counters are handed out in first-appearance order - which is the property
    # being asserted.
    first_seen = {}
    for tr, conf, country, _i, _it in decorated:
        first_seen.setdefault((tr, conf, country), len(first_seen))
    decorated.sort(key=lambda d: (d[0], d[1], first_seen[(d[0], d[1], d[2])], d[3]))
    return [d[4] for d in decorated]
