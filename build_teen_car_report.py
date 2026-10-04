#!/usr/bin/env python3
"""
Build the teen-driver vehicle report: Volvo XC70 vs Jeep Wrangler (PDF).

Usage:  python3 build_teen_car_report.py [output.pdf]

Reuses the layout from build_report.py. Every VIN in this report is
re-validated offline at build time; the build fails if one stops passing.
"""
import sys

from build_report import (AMBER, GREEN, GREY, OLIVE, RULE, RUST, S, SAND, KeepTogether, P,
                          Paragraph, Spacer, Table, TableStyle, build, bullets, callout,
                          colors, datatable, hx, inch, rule, tag)
from reportlab.platypus import CondPageBreak, NextPageTemplate, PageBreak
from datetime import date

from vin_tools import check_digit, decode

TITLE = 'Teen Driver Vehicle Report'
GREEN_BG = colors.HexColor('#eaf1ea')
AMBER_BG = colors.HexColor('#f7f1de')

# ---------------------------------------------------------------- candidates
# 'reported' is UNVERIFIED search-snippet data, kept only so it can be
# challenged. The VIN columns are computed offline and are the only verified part.
XC70_CANDIDATES = [
    {
        'vin': 'YV4952BZ2D1165870',
        'reported': '2013 XC70 T6 AWD, 118,798 mi, $6,995. Location not indexed.',
        'verdict': 'CHECK',
        'note': 'Sweet-spot year and the lowest mileage found. But it is the T6 (more power '
                'than a new driver needs) and priced below the 2013 3.2 book value - ask why.',
    },
    {
        'vin': 'YV4902BZ6D1161318',
        'reported': '2013 XC70 T6 Premier Plus AWD, 139,865 mi, $8,497. Location not '
                    'indexed.',
        'verdict': 'CHECK',
        'note': 'Good year, fair price for the trim. T6 again, and 140k miles is deep into '
                'angle-gear territory - only with documented AWD service.',
    },
    {
        'vin': 'YV4952NC0F1192558',
        'reported': '2015 XC70 3.2 Premier Plus AWD, 144,815 mi, $9,560, Arizona',
        'verdict': 'CHECK',
        'note': 'Dry-state car with the preferred 3.2 engine (confirm via the federal '
                'decoder). 2015 draws mixed complaint data, and 145k miles is high.',
    },
    {
        'vin': 'YV4902BZXD1156784',
        'reported': '2013 XC70 T6 AWD, 107,706 mi, $18,400',
        'verdict': 'SKIP',
        'note': 'Real VIN, but $18,400 is roughly double book value for a 2013. Either the '
                'price was mis-paired by the index or the car is badly overpriced.',
    },
    {
        'vin': 'YV4940BZ9D1162052',
        'reported': '2013 XC70 3.2 Premier AWD, 218,261 mi, $5,525, Arizona',
        'verdict': 'SKIP',
        'note': 'Right engine, right climate, far too many miles for a teenager\'s daily car. '
                'Below your budget floor for a reason.',
    },
]

# Wrangler VINs in the $7,000-$12,000 band, carried over from the Jeep report.
WRANGLER_IN_BAND = [
    ('1J4AA2D1XAL173194', '2010 2-dr Sport, reported $10,700 / 111,535 mi, Lakewood CO'),
    ('1J4BA6H17BL574757', '2011 Unlimited Rubicon, reported $11,899-$12,599, mileage reported '
                          'two different ways'),
]


def _assert_vins():
    for v in [c['vin'] for c in XC70_CANDIDATES] + [v for v, _ in WRANGLER_IN_BAND]:
        want, err = check_digit(v)
        assert not err and want == v[8], 'VIN failed at build time: %s' % v


# ---------------------------------------------------------------- content
def story(fw):
    _assert_vins()
    s = [NextPageTemplate('body')]
    s += cover(fw)
    s.append(PageBreak())
    s += section_answer(fw)
    s += section_method(fw)
    s += section_scorecard(fw)
    s += section_safety(fw)
    s += section_winter(fw)
    s += section_xc70(fw)
    s += section_wrangler(fw)
    s += section_candidates(fw)
    s += section_sourcing(fw)
    s += section_inspection(fw)
    s += section_plan(fw)
    s += section_sources(fw)
    return s


def cover(fw):
    s = [Spacer(1, 0.92 * inch)]
    s.append(P('VEHICLE ACQUISITION RESEARCH', 'cover_lbl'))
    s.append(Spacer(1, 5))
    s.append(P('A Car for a New Driver', 'title'))
    s.append(P('Volvo XC70 AWD vs Jeep Wrangler - reliability, safety and winter capability',
               'subtitle'))
    s.append(Spacer(1, 0.40 * inch))
    facts = [
        ['DRIVER', 'High-school student - a new driver'],
        ['USE', 'Daily school commute in the Denver metro, plus winter ski trips on the\n'
                'I-70 mountain corridor'],
        ['BUDGET', '$7,000 - $12,000'],
        ['PRIORITY', 'Reliability first; safety treated as co-equal because of the driver'],
        ['SOURCING', 'Colorado, plus dry states (Arizona, New Mexico, Nevada, Utah,\n'
                     'California, West Texas) for the right unit'],
        ['REPORT DATE', date.today().strftime('%B %d, %Y')],
    ]
    rows = [[Paragraph(k, S['cover_lbl']),
             Paragraph(v.replace('\n', '<br/>'), S['cover_val'])] for k, v in facts]
    t = Table(rows, colWidths=[1.32 * inch, fw - 1.32 * inch])
    t.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 5), ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LINEBELOW', (0, 0), (-1, -2), 0.4, RULE),
    ]))
    s.append(t)
    s.append(Spacer(1, 0.2 * inch))
    s.append(callout(
        'The short answer',
        'Buy the <b>Volvo XC70</b> - specifically a <b>2012-2014 3.2 AWD</b> - and put proper '
        'winter tires on it. The Wrangler is the wrong vehicle for a new driver: it is '
        'excluded from the IIHS teen-safety list, it has part-time four-wheel drive that '
        'leaves a novice in rear-wheel drive on an icy morning, and your budget only reaches '
        'its weakest model years. Section 1 explains the call; the rest of the report is the '
        'evidence and a buying plan.',
        accent=GREEN, bg=GREEN_BG))
    s.append(Spacer(1, 0.08 * inch))
    s.append(P('<b>CONTENTS</b>', 'cover_lbl'))
    s.append(Spacer(1, 3))
    for c in ['1.  The recommendation', '2.  Method and evidence grading',
              '3.  Head-to-head scorecard', '4.  Safety for a new driver',
              '5.  Winter and ski-trip capability', '6.  Volvo XC70 buyer\'s guide',
              '7.  Why the Wrangler falls short at this budget',
              '8.  VIN-authenticated XC70 candidates', '9.  Sourcing from dry states',
              '10. XC70 pre-purchase inspection checklist', '11. Action plan', '12. Sources']:
        s.append(Paragraph(c, S['toc']))
    return s


def section_answer(fw):
    s = [P('1.  The recommendation', 'h1'), rule()]
    s.append(P(
        'You asked for the most reliable choice between two vehicles. For most buyers that '
        'would be the whole question. For a teenager it is half of it, because the evidence '
        'is unambiguous that new drivers crash at far higher rates than experienced ones - '
        'which is why the Insurance Institute for Highway Safety and Consumer Reports publish a '
        'separate list of used vehicles they consider suitable for teens. This report weighs '
        'reliability and crash protection together, and on both the answer is the same.',
        'body'))
    s.append(callout(
        'Buy: 2012-2014 Volvo XC70 3.2 AWD',
        [P('<b>Why the XC70 wins.</b> Full-time all-wheel drive that needs no decisions from '
           'the driver; standard side-curtain airbags and stability control; a long, car-based '
           'wagon body that is stable at highway speed; and - unlike the Wrangler - its best '
           'model years actually sit <i>inside</i> your budget, at roughly $7,000-$10,300 '
           'private-party.', 'callb'),
         Spacer(1, 4),
         P('<b>Why that exact spec.</b> 2012-2014 is where complaint data is lowest. The '
           'naturally aspirated <b>3.2</b> (about 235-240 hp, timing <b>chain</b>) over the '
           'turbocharged T6, because IIHS deliberately favours lower power for teen drivers. '
           '<b>AWD</b> specifically - the 2015-2016 "T5 Drive-E" XC70 is front-wheel drive '
           'only and is not the car you want for ski trips.', 'callb'),
         Spacer(1, 4),
         P('<b>The condition.</b> Under about 120,000 miles, with evidence the AWD angle gear '
           'has been serviced or replaced - that part is the XC70\'s one notorious failure '
           'point (Section 6.3). Then fit winter tires; under Colorado\'s November 2025 traction '
           'law update, AWD alone no longer satisfies the law (Section 5.2).', 'callb')],
        accent=GREEN, bg=GREEN_BG))
    s.append(callout(
        'Do not buy: Jeep Wrangler, for this driver',
        'Three independent reasons, any one of which would be enough. <b>Safety:</b> IIHS and '
        'Consumer Reports exclude it from their teen list, citing marginal side-crash results '
        'and a 3-of-5-star rollover rating. <b>Winter:</b> its part-time 4WD is rear-wheel '
        'drive until the driver engages it - the wrong system for a novice on a commute that '
        'alternates between dry and icy pavement. <b>Reliability:</b> $12,000 reaches only '
        '2007-2012 Wranglers, which include its two worst years; the dependable 2015-2017 cars '
        'start around $13,000 (Section 7).',
        accent=RUST))
    s.append(callout(
        'Honest caveat - and a third option worth five minutes',
        [P('Neither vehicle is on the IIHS teen list. The Wrangler was tested and did not '
           'qualify; the XC70 was <b>never tested at all</b> by IIHS or NHTSA, so its safety '
           'case is engineering and platform-based rather than a published score (Section 4). '
           'That is a materially better position than the Wrangler\'s, but it is not a rating.',
           'callb'),
         Spacer(1, 4),
         P('If "best in reliability" truly outranks the Volvo, the teen list does include AWD '
           'models with proven crash scores: the <b>2015-2018 Subaru Outback</b>, <b>2015+ '
           'Toyota RAV4</b>, <b>2015+ Honda CR-V</b> and <b>2014+ Mazda CX-5</b> (built after '
           'October 2013). Toyota and Honda in particular carry stronger reliability '
           'reputations than Volvo. I did not price these against your budget - worth a check '
           'before you commit.', 'callb')],
        accent=AMBER, bg=AMBER_BG))
    return s


def section_method(fw):
    s = [CondPageBreak(2.6 * inch), P('2.  Method and evidence grading', 'h1'), rule()]
    s.append(P(
        'As in the earlier Jeep reports, the environment this was compiled in cannot reach the '
        'listing marketplaces, CARFAX, or the NHTSA VIN-decoding and recall APIs - they are '
        'blocked at the network layer. Research used server-side web search only. Every VIN '
        'below was recovered from search indexes and then <b>authenticated offline</b> with '
        'the federal check-digit algorithm, which Volvo VINs sold in the US follow exactly as '
        'Jeep VINs do. All seven VINs in this report pass.', 'body'))
    grades = [
        [tag('VERIFIED', GREEN), 'Computed offline from the VIN itself, or stated by an '
         'authoritative source (IIHS, CDOT, KBB, RepairPal, NHTSA recall data).'],
        [tag('REPORTED', AMBER), 'Recovered from a search index and plausible, but not '
         'independently confirmable here. Every listing price and mileage is REPORTED - '
         'confirm it with the seller before acting.'],
        [tag('FLAGGED', RUST), 'Recovered from a search index and internally inconsistent. '
         'Example: one KBB snippet valued a 2015 XC70 3.2 at $5,725-$6,725, below the 2013 and '
         '2014 ranges. A newer car is rarely worth less, so that figure is not used.'],
    ]
    s.append(datatable(['Grade', 'Meaning'], grades, [1.0 * inch, fw - 1.0 * inch]))
    return s


def section_scorecard(fw):
    s = [CondPageBreak(3.0 * inch), P('3.  Head-to-head scorecard', 'h1'), rule()]
    s.append(P('As each vehicle exists inside a $7,000-$12,000 budget - not as each model '
               'line exists at its best.', 'small'))
    W, L, T = GREEN, RUST, GREY   # winner, loser, tie colours for the verdict column
    rows = [
        ['On the IIHS / CR teen-vehicle list', 'No - never crash-tested',
         'No - tested, did not qualify', 'XC70', W],
        ['Published crash / rollover results', 'None (platform siblings scored top marks)',
         'Marginal side; 3-of-5-star rollover', 'XC70', W],
        ['Side-curtain airbags', 'Standard', 'Not fitted', 'XC70', W],
        ['Winter drivetrain', 'Full-time AWD - no driver input',
         'Part-time 4WD - rear-drive until engaged', 'XC70', W],
        ['Highway stability', 'Long, car-based wagon',
         'Short wheelbase, solid front axle, death-wobble prone', 'XC70', W],
        ['Reliability rating', 'RepairPal 3.5 / 5; about $804 a year', 'JK about 2.8 / 5; '
         'about $987 a year', 'XC70', W],
        ['Best years inside budget?', 'Yes - 2012-2014 at $7k-$10.3k',
         'No - best years (2015-17) start near $13k', 'XC70', W],
        ['Signature failure', 'AWD angle gear, $200-$3,500',
         '3.8L oil burning, TIPM, death wobble', 'XC70', W],
        ['Teen insurance', 'Not found - get a quote',
         'Among the cheapest SUVs to insure', 'Wrangler', L],
        ['Ski and school gear', 'Wagon cargo bay, roof rails',
         'Small cargo area, soft-top security', 'XC70', W],
    ]
    s.append(datatable(
        ['Criterion', 'Volvo XC70 (2012-14 3.2 AWD)', 'Jeep Wrangler (2007-12 JK)', 'Edge'],
        [[Paragraph('<b>%s</b>' % r[0], S['cell']), Paragraph(r[1], S['cell']),
          Paragraph(r[2], S['cell']), tag(r[3], r[4])] for r in rows],
        [1.6 * inch, 2.05 * inch, 2.15 * inch, fw - 5.8 * inch]))
    s.append(Spacer(1, 6))
    s.append(P(
        'The Wrangler takes one row outright - insurance - and it is a real point: an '
        '18-year-old\'s full-coverage premium on a Wrangler is reported at about <b>$1,649 per '
        'six months</b>, and it sits among the cheapest SUVs to insure for young drivers. No '
        'comparable figure for the XC70 surfaced. Get a quote on a specific VIN for both '
        'before you decide, because a large gap there is the one thing in this table that '
        'could move a family budget.', 'body'))
    return s


def section_safety(fw):
    s = [CondPageBreak(3.0 * inch), P('4.  Safety for a new driver', 'h1'), rule()]
    s.append(P('4.1  What IIHS looks for in a teen car', 'h2'))
    s.append(P(
        'The IIHS / Consumer Reports teen list is built on four principles: <b>lower '
        'power-to-weight ratios</b> (less temptation and less consequence), <b>larger and '
        'heavier vehicles</b> (no small cars), <b>electronic stability control</b>, and '
        '<b>high crash-protection ratings</b>. Current used recommendations require good '
        'results in five IIHS tests: moderate front overlap, side, driver-side small overlap, '
        'roof strength and head restraints.', 'body'))
    s.append(P('4.2  The Wrangler: tested, and found wanting', 'h2'))
    s.append(bullets([
        'Excluded from the teen list. Reported reasons: <b>marginal side-crash results</b>, '
        'no front crash prevention available, and <b>3 of 5 stars</b> in NHTSA rollover '
        'resistance.',
        'The redesigned 2018+ Wrangler became the first vehicle to <b>roll onto its side in '
        'the IIHS small overlap test</b> - twice. IIHS called out the ejection risk in a '
        'vehicle with removable roof and doors and <b>no side-curtain airbags</b> designed to '
        'deploy in a rollover. That test was of the newer model; the 2007-2012 JK your budget '
        'reaches is older still and had no curtain airbags either.',
        'Handling compounds it: a short wheelbase and solid front axle, and the JK\'s '
        'documented <b>death wobble</b> - violent front-end oscillation set off by a bump at '
        '45-65 mph - is a frightening event for an experienced driver and a dangerous one for '
        'a new driver.',
    ]))
    s.append(P('4.3  The XC70: never tested - which is different from failing', 'h2'))
    s.append(P(
        'The 2008-2016 XC70 has <b>no IIHS or NHTSA crash-test results</b>. Neither agency '
        'tested it, so it cannot appear on a list that requires test scores. That is a gap in '
        'the evidence, not a negative finding, and the surrounding evidence is strong:', 'body'))
    s.append(bullets([
        'It rides on Volvo\'s P3 platform alongside the <b>S80</b>, which was an IIHS 2009 '
        'Top Safety Pick, and the <b>S60 and XC60</b>, which earned top marks when IIHS '
        'introduced the small overlap test in 2012.',
        'Standard equipment includes stability control, anti-lock brakes with brake-force '
        'distribution, front, side and <b>side-curtain airbags</b>, and Volvo\'s whiplash '
        'protection system.',
        'Choose the <b>3.2</b> over the T6. The turbocharged T6 is the faster car and that is '
        'exactly the argument against it here - IIHS favours lower power-to-weight for teens.',
    ]))
    s.append(callout(
        'Put it plainly',
        'You are choosing between a vehicle that was crash-tested and fell short, and one that '
        'was never crash-tested but shares engineering with siblings that tested at the top. '
        'That is an easy choice between these two. If you want a published score in hand, '
        'that is the case for the Subaru, Toyota, Honda and Mazda options in Section 1.',
        accent=OLIVE, bg=SAND))
    return s


def section_winter(fw):
    s = [CondPageBreak(3.0 * inch), P('5.  Winter and ski-trip capability', 'h1'), rule()]
    s.append(P('5.1  Full-time AWD vs part-time 4WD', 'h2'))
    s.append(P(
        'This is the most underrated difference between the two vehicles for your use. The '
        'XC70\'s all-wheel drive is always on: the car apportions power between the axles by '
        'itself, and the driver does nothing.', 'body'))
    s.append(P(
        'The JK Wrangler\'s Command-Trac system is <b>part-time</b>. In 4WD the front and rear '
        'axles are locked together, so it must only be used on low-traction surfaces - '
        'running it on dry pavement causes excessive tyre and drivetrain wear. In normal '
        'driving the Wrangler is therefore <b>rear-wheel drive</b>. A Denver winter commute is '
        'exactly the case that system handles worst: dry arterials, then a shaded icy '
        'intersection, then dry again. It asks a new driver to anticipate ice and shift '
        'modes correctly, every time. Full-time AWD asks nothing.', 'body'))
    s.append(P('5.2  Colorado\'s traction law changed in November 2025', 'h2'))
    s.append(P(
        'Many drivers believe AWD satisfies the I-70 traction law. <b>Since the November 2025 '
        'update it does not on its own.</b> An AWD or 4WD vehicle must also carry tyres with '
        'at least <b>3/16 inch</b> of tread that are winter-rated (mountain-snowflake '
        'symbol), all-weather rated, or mud-and-snow (M+S). Otherwise chains or an approved '
        'traction device are required.', 'body'))
    law = [
        ['Where', 'I-70 Mountain Corridor between Dotsero and Morrison - i.e. every ski trip '
                  'west of Denver - and any other state highway when activated'],
        ['When', 'Every year from 1 September through 31 May'],
        ['Penalty', 'Reported as a $50 fine plus a $17 surcharge under the update; older '
                    'reporting cites fines up to about $650. The fine is the small cost.'],
    ]
    s.append(datatable(['', ''], [[Paragraph('<b>%s</b>' % a, S['cell']),
                                   Paragraph(b, S['cell'])] for a, b in law],
                       [0.8 * inch, fw - 0.8 * inch]))
    s.append(Spacer(1, 6))
    s.append(callout(
        'The single best safety purchase in this whole report',
        'A dedicated set of <b>winter tyres</b> (mountain-snowflake rated) on their own wheels. '
        'AWD helps a car accelerate on snow; it does nothing for stopping or turning, which is '
        'where new drivers get into trouble. Winter tyres improve all three, and they make the '
        'car traction-law compliant on every ski day. Budget for them inside the purchase, '
        'not after it.',
        accent=GREEN, bg=GREEN_BG))
    return s


def section_xc70(fw):
    s = [CondPageBreak(3.0 * inch), P('6.  Volvo XC70 buyer\'s guide', 'h1'), rule()]
    s.append(P('6.1  Which XC70', 'h2'))
    gens = [
        ['2008-2010', '3.2 I6 AWD; T6 turbo AWD', 'CAUTION',
         '2008 is flagged as a year to avoid in complaint data, with electronic throttle '
         'module faults. 2009-2010 are acceptable but older than you need at this budget.',
         AMBER],
        ['2011', '3.2 I6 AWD; T6 turbo AWD', 'ACCEPTABLE',
         'Fine if it is the best-kept car you find; not a target year.', GREY],
        ['2012-2014', '3.2 I6 AWD; T6 turbo AWD', 'TARGET',
         'Lowest complaint counts of the generation and squarely inside budget. Choose the '
         '3.2: naturally aspirated, timing chain, gentler power for a new driver.', GREEN],
        ['2015', '3.2 / T6 AWD; T5 Drive-E FWD', 'CAUTION',
         'Mixed complaint data. The new T5 Drive-E is <b>front-wheel drive only</b> - check '
         'the badge and decode the VIN.', AMBER],
        ['2016', 'T5 AWD 2.5L 5-cyl turbo; T5 Drive-E FWD', 'AVOID',
         'Final year; 3.2 and T6 dropped. Flagged for turbocharger failures and angle-gear '
         'failures, the AWD engine uses a timing belt, and prices start near $12,000.', RUST],
    ]
    s.append(datatable(
        ['Years', 'Powertrains', 'Verdict', 'Basis'],
        [[Paragraph('<b>%s</b>' % g[0], S['cell']), Paragraph(g[1], S['cell']),
          tag(g[2], g[4]), Paragraph(g[3], S['cell'])] for g in gens],
        [0.78 * inch, 1.5 * inch, 0.92 * inch, fw - 3.2 * inch]))
    s.append(Spacer(1, 6))
    s.append(P(
        'Older second-generation XC70s (2001-2007) fall below your budget floor and share the '
        'angle-gear weakness without the later safety and refinement gains. Not recommended.',
        'small'))

    s.append(P('6.2  What it costs', 'h2'))
    vals = [
        ['2013 XC70 3.2', '$6,395 - $7,720', 'Market from about $6,950'],
        ['2013 XC70 3.2 Premier Plus', '$7,175 - $9,200', ''],
        ['2014 XC70 3.2', '$8,000 - $10,250', 'Market from about $8,931'],
        ['2014 XC70 3.2 Premier', '$7,725 - $9,900', ''],
        ['2015 XC70 (all)', 'FLAGGED - see Section 2', 'Market from about $7,700'],
        ['2016 XC70 (all)', '-', 'Market from about $11,999'],
    ]
    s.append(datatable(['Vehicle', 'KBB private-party', 'Lowest listings seen'],
                       vals, [2.1 * inch, 1.8 * inch, fw - 3.9 * inch]))
    s.append(Spacer(1, 6))
    s.append(P(
        'The practical target is <b>$8,000-$10,500</b> for a good 2012-2014 3.2 AWD, leaving '
        '$1,500-$4,000 of your $12,000 for winter tyres, an inspection, and an early '
        'maintenance reserve. RepairPal puts average XC70 repair spend at about <b>$804 a '
        'year</b> - roughly 0.5 shop visits annually, with a 9% chance any given repair is '
        'severe - and rates it 3.5 of 5, sixth of 14 luxury midsize SUVs.', 'body'))

    s.append(P('6.3  Known weak points', 'h2'))
    s.append(bullets([
        '<b>AWD angle gear (transfer case).</b> The XC70\'s notorious failure. Its seal '
        'deteriorates and transmission fluid leaks into the angle gear; left alone it can '
        'fail outright. Repairs reported at <b>$200 to $3,500</b> depending on whether it is '
        'caught at the seal or after the gear fails. Ask for evidence of service or '
        'replacement, and have the inspector look for leaks and burnt-oil smell.',
        '<b>3.2 engine specifics.</b> Timing <i>chain</i>, not belt - no scheduled belt job. '
        'Known issues: wear in the timing gearbox gears and bearings, leaks around the timing '
        'chain cover and vacuum pump, and a whistle under the hood that signals a failed oil '
        'separator (PCV) membrane - a modest repair if done early.',
        '<b>Rear self-levelling suspension.</b> Rear air-spring failures are reported. A '
        'sagging rear on an unloaded car is the tell.',
        '<b>Turbocharged engines (T6, 2016 T5).</b> Turbo failures and wastegate rattle are '
        'reported; the 2015-2016 T5 also carries a timing belt due every 10 years or 100,000 '
        'miles. One more reason to prefer the 3.2.',
        '<b>Suspension wear.</b> Struts and bushings are reported to wear relatively quickly '
        '- normal at this mileage, but price it in.',
    ]))
    s.append(P('6.4  Recalls to confirm closed', 'h2'))
    rc = [
        ['2012', 'Seat belts may not restrain the occupant; separately, a seat wiring harness '
                 'fault can cause front or side airbags to deploy improperly or not at all, '
                 'and affect the lap-belt pretensioner.'],
        ['2014', 'On cars with keyless ignition, the central electronic module can malfunction: '
                 'wipers run continuously, and turn signals, high beams and the headlight '
                 'switch may not work.'],
    ]
    s.append(datatable(['Model year', 'Recall'],
                       [[Paragraph('<b>%s</b>' % a, S['cell']), Paragraph(b, S['cell'])]
                        for a, b in rc], [0.9 * inch, fw - 0.9 * inch]))
    s.append(Spacer(1, 4))
    s.append(P('Recall coverage for 2013 and 2015-2016 did not surface in search. Run every '
               'candidate\'s VIN at nhtsa.gov/recalls - it takes a minute and covers all years.',
               'small'))
    return s


def section_wrangler(fw):
    s = [CondPageBreak(3.0 * inch),
         P('7.  Why the Wrangler falls short at this budget', 'h1'), rule()]
    s.append(P(
        'The earlier Jeep reports found that the dependable Wranglers are the <b>2015-2017</b> '
        'JKs with the 3.6L Pentastar - and that they book at roughly $13,200-$15,800 '
        'private-party. A $12,000 ceiling stops short of all of them. What it does reach:',
        'body'))
    yrs = [
        ['2007', 'Worst launch year: pronounced death wobble, airbag warning faults.'],
        ['2008-2011', '3.8L V6: weak, and known to burn oil past 100,000 miles. TIPM electrical '
                      'failures. The 2011 Unlimited Sport books at $9,800-$11,850.'],
        ['2012', 'Rated the <b>worst</b> JK year - around ten recalls, TIPM and airbag faults, '
                 'and the early Pentastar cylinder-head defect. Books at $11,330-$13,680, so '
                 'mostly above budget anyway.'],
    ]
    s.append(datatable(['Years', 'What you get'],
                       [[Paragraph('<b>%s</b>' % a, S['cell']), Paragraph(b, S['cell'])]
                        for a, b in yrs], [0.85 * inch, fw - 0.85 * inch]))
    s.append(Spacer(1, 6))
    s.append(P(
        'So inside your budget the Wrangler is not "the reliable option with a safety '
        'trade-off". It is the weaker option on reliability <i>and</i> on safety <i>and</i> on '
        'winter drivetrain. If you overrule this report and buy one anyway, the two in-band '
        'candidates from the Jeep report remain the place to start - both VINs pass the check '
        'digit:', 'body'))
    s.append(datatable(['VIN', 'Reported'],
                       [[Paragraph(v, S['mono']), Paragraph(r, S['cell'])]
                        for v, r in WRANGLER_IN_BAND],
                       [1.6 * inch, fw - 1.6 * inch]))
    s.append(Spacer(1, 4))
    s.append(P('...and in that case fit winter tyres, choose a hardtop, and treat the '
               'death-wobble road test in the Jeep report\'s Section 11.1 as non-negotiable.',
               'small'))
    return s


def section_candidates(fw):
    s = [CondPageBreak(3.0 * inch), P('8.  VIN-authenticated XC70 candidates', 'h1'), rule()]
    s.append(P(
        'Five complete XC70 VINs were recovered. <b>All five pass the check digit</b>, and in '
        'every case the claimed model year matches VIN position 10; all decode to the '
        'Torslanda plant in Gothenburg, Sweden. Trim and engine (3.2 vs T6) cannot be proven '
        'from the check digit - confirm them at vpic.nhtsa.dot.gov.', 'body'))
    rows = []
    for c in XC70_CANDIDATES:
        d = decode(c['vin'])
        col = {'GO': GREEN, 'CHECK': AMBER, 'SKIP': RUST}[c['verdict']]
        rows.append([
            Paragraph(c['vin'], S['mono']), tag('PASS', GREEN),
            Paragraph('<b>%s</b>' % d['year'], S['cell']),
            Paragraph(c['reported'], S['cell']),
            Paragraph('<font color="%s"><b>%s</b></font><br/>%s'
                      % (hx(col), c['verdict'], c['note']), S['cell']),
        ])
    s.append(datatable(['VIN', 'Chk', 'Yr', 'Reported (UNVERIFIED)', 'Assessment'], rows,
                       [1.42 * inch, 0.5 * inch, 0.42 * inch, 1.75 * inch, fw - 4.09 * inch]))
    s.append(Spacer(1, 6))
    s.append(P('8.1  Leads without a full VIN', 'h2'))
    s.append(bullets([
        '<b>Tucson, AZ</b> - 2010 XC70 3.2 AWD, Ice White, 126,851 mi, reported $7,995. Dry '
        'climate and the right engine; a year older than the target window.',
        '<b>Arizona</b> - 2008 XC70 3.2, 90,800 mi. Tempting mileage, but 2008 is the '
        'generation\'s weakest year. Pass unless the inspection is spotless.',
    ]))
    s.append(callout(
        'An honest read of this list',
        'None of these is the ideal car. The target - a 2012-2014 3.2 AWD under about 120,000 '
        'miles with angle-gear records - did not surface in the indexes this environment can '
        'reach. That is a limit of the search, not of the market: XC70s in this band are '
        'common. Treat the table as a calibration of what prices and mileages look like, and '
        'run the searches in Section 11 from an ordinary browser.',
        accent=AMBER, bg=AMBER_BG))
    return s


def section_sourcing(fw):
    s = [CondPageBreak(3.0 * inch), P('9.  Sourcing from dry states', 'h1'), rule()]
    s.append(P(
        'Your instinct to look at dry states is sound for an XC70, with one calibration from '
        'the earlier reports: Colorado uses magnesium chloride rather than rock salt and is '
        'itself dry, so a Colorado car is not a Rust Belt car. The dry-state advantage is '
        'real but modest - use it to widen the pool and break ties, not as a reason to buy a '
        'worse car farther away.', 'body'))
    st = [
        ['New Mexico (Albuquerque)', 'about 450 mi', 'Best first look. One day\'s drive home; '
         'earlier research named central and southern New Mexico among the best rust-free '
         'sources.'],
        ['Utah (Salt Lake City)', 'about 520 mi', 'Dry climate, but Utah does salt roads - '
         'inspect the underside as you would a Colorado car.'],
        ['Nevada (Las Vegas)', 'about 750 mi', 'Very dry. Heavy sun - see below.'],
        ['Arizona (Phoenix / Tucson)', 'about 820-900 mi', 'Two Arizona candidates surfaced '
         'here. Driest market; harshest sun.'],
        ['California', 'about 1,000 mi', 'Deep supply; the Jeep report found CA cheaper than '
         'Texas for Wranglers.'],
        ['West Texas', 'varies', 'Dry. Avoid Houston and the Gulf Coast - Texas is a top-three '
         'state for flood-damaged cars.'],
    ]
    s.append(datatable(['Market', 'From Denver', 'Notes'],
                       [[Paragraph('<b>%s</b>' % a, S['cell']), Paragraph(b, S['cell']),
                         Paragraph(c, S['cell'])] for a, b, c in st],
                       [1.75 * inch, 1.05 * inch, fw - 2.8 * inch]))
    s.append(Spacer(1, 6))
    s.append(bullets([
        '<b>Desert cars trade rust for sun.</b> Check the dashboard for cracks, leather for '
        'splitting, every rubber seal and the headlight lenses for perishing and hazing, and '
        'the air conditioning - desert cars work it hard.',
        '<b>Fly out and drive it home.</b> The earlier report found that cheaper than shipping '
        'and better diligence: the drive is a long road test. Albuquerque in particular is a '
        'one-day return.',
        '<b>Colorado registration.</b> An out-of-state purchase needs a DR 2698 VIN '
        'verification and, because 80127 is inside the Denver-Boulder programme area, a '
        'Colorado emissions test. The Jeep report\'s Section 3.7 lists the full paperwork.',
        '<b>Remote-buying rules from the earlier report still apply.</b> Independent '
        'inspection before money moves; title in the seller\'s name; no wire transfers to '
        'individuals.',
    ]))
    return s


def section_inspection(fw):
    s = [CondPageBreak(3.0 * inch),
         P('10.  XC70 pre-purchase inspection checklist', 'h1'), rule()]
    s.append(P('Hand this to an independent shop - ideally one that services Volvos.', 'small'))
    blocks = [
        ['AWD SYSTEM - the priority', [
            'Angle gear (transfer case): fluid leaks, burnt-oil smell, seal condition',
            'Records of angle-gear service, seal replacement or unit replacement',
            'Rear differential and AWD coupling condition; road test for driveline clunks',
            'All four tyres matching brand, size and wear - mismatches stress the AWD system',
        ]],
        ['ENGINE AND DRIVETRAIN', [
            'Confirm engine by VIN decode: 3.2 (preferred) vs T6 vs T5',
            'Leaks at the timing chain cover and vacuum pump (3.2)',
            'Whistle under the hood at idle - oil separator / PCV membrane (3.2)',
            'Turbo noise or wastegate rattle (T6 / T5); timing-belt records on any 2015-16 T5',
            'Transmission shift quality hot and cold; full OBD-II scan including stored codes',
        ]],
        ['SUSPENSION AND BRAKES', [
            'Rear ride height unloaded - sag indicates air-spring or levelling failure',
            'Struts, control-arm bushings and end links for wear and play',
            'Brake lines and underbody - required on any Colorado or Utah car',
        ]],
        ['SAFETY SYSTEMS', [
            'Airbag and stability-control warning lights illuminate at key-on, then go out',
            'All open recalls closed (nhtsa.gov/recalls), especially the 2012 airbag harness '
            'and 2014 electronic-module campaigns',
            'Seat belts retract and latch properly in every seat',
        ]],
        ['CLIMATE HISTORY', [
            'Desert car: dash, leather, seals, headlight lenses, A/C performance',
            'Any Gulf Coast or flood-region history: carpet and spare-well silt, seat-belt '
            'webbing staining, corrosion on interior fasteners',
        ]],
    ]
    for head, items in blocks:
        rows = [[Paragraph('<b>%s</b>' % head, S['cellh'])]]
        rows += [[Paragraph('<font face="Courier-Bold" color="#7d8a63">[&nbsp;&nbsp;]</font>'
                            '&nbsp;&nbsp;%s' % it, S['cell'])] for it in items]
        t = Table(rows, colWidths=[fw])
        st = [('BACKGROUND', (0, 0), (0, 0), OLIVE), ('GRID', (0, 0), (-1, -1), 0.4, RULE),
              ('LEFTPADDING', (0, 0), (-1, -1), 7), ('RIGHTPADDING', (0, 0), (-1, -1), 7),
              ('TOPPADDING', (0, 0), (-1, -1), 4), ('BOTTOMPADDING', (0, 0), (-1, -1), 4)]
        st += [('BACKGROUND', (0, i), (-1, i), SAND) for i in range(2, len(rows), 2)]
        t.setStyle(TableStyle(st))
        s.append(KeepTogether([t, Spacer(1, 7)]))
    return s


def section_plan(fw):
    s = [CondPageBreak(3.0 * inch), P('11.  Action plan', 'h1'), rule()]
    steps = [
        ['1', 'Get insurance quotes first', 'Quote a 2013 XC70 3.2 AWD and a 2010 Wrangler for '
         'your teen. If the gap is large, you want to know before you shop.'],
        ['2', 'Run the searches', 'CarGurus, Cars.com, Autotrader: "Volvo XC70", 2012-2014, '
         'AWD, under 120,000 miles, $7,000-$11,000. Search Denver first, then Albuquerque, '
         'Salt Lake City, Las Vegas, Phoenix, Tucson.'],
        ['3', 'Filter on engine', 'Prefer the 3.2. Accept a T6 only if it is clearly the best '
         'car. Exclude anything labelled "Drive-E" or FWD.'],
        ['4', 'Decode before you call', 'vpic.nhtsa.dot.gov to confirm engine and drivetrain; '
         'nhtsa.gov/recalls for open recalls; vin_tools.py for the check digit.'],
        ['5', 'Ask one question first', '"Has the angle gear been serviced or replaced, and do '
         'you have the paperwork?" A clear yes with records moves a car to the top.'],
        ['6', 'History and title', 'Your own CARFAX or AutoCheck plus an NMVTIS title check. '
         'Skip any flood or salvage brand, and any Gulf Coast history.'],
        ['7', 'Independent inspection', 'Section 10 checklist, at a shop you chose. A refusal '
         'ends the conversation.'],
        ['8', 'Buy the tyres with the car', 'Mountain-snowflake winter tyres on their own '
         'wheels, before the first ski trip and before 1 September traction-law season.'],
    ]
    s.append(datatable(['#', 'Step', 'Detail'],
                       [[Paragraph('<b>%s</b>' % a, S['cell']),
                         Paragraph('<b>%s</b>' % b, S['cell']), Paragraph(c, S['cell'])]
                        for a, b, c in steps],
                       [0.3 * inch, 1.6 * inch, fw - 1.9 * inch]))
    s.append(Spacer(1, 8))
    s.append(callout(
        'The one-line summary',
        'A <b>2012-2014 Volvo XC70 3.2 AWD</b>, under about 120,000 miles, with angle-gear '
        'records, found in Colorado or a nearby dry state for <b>$8,000-$10,500</b>, on '
        '<b>winter tyres</b>. It is the more reliable, safer and better winter vehicle of the '
        'two at this budget. If you would rather have a published IIHS score, look at the '
        'Outback, RAV4, CR-V and CX-5 years in Section 1 before you buy.',
        accent=GREEN, bg=GREEN_BG))
    return s


def section_sources(fw):
    s = [CondPageBreak(3.0 * inch), P('12.  Sources', 'h1'), rule()]
    s.append(P('Recovered through server-side search; the pages themselves could not be '
               'fetched from the compilation environment.', 'small'))
    groups = [
        ('Teen-driver safety', [
            'iihs.org - Safe vehicles for teens (IIHS / Consumer Reports), 2025 list and criteria',
            'iihs.org - 2009 Top Safety Picks (Volvo)',
            'thetruthaboutcars.com / jalopnik.com / autotrader.ca - Wrangler rolls over in IIHS '
            'small overlap test',
            'weartv.com / carpro.com / autoguide.com - teen list coverage and model years']),
        ('Volvo XC70', [
            'repairpal.com - XC70 reliability rating, repair costs, model-year problems',
            'carwhere.com / truedelta.com / au7o.io - years to avoid, known issues, angle gear',
            'whatcar.com - used XC70 2007-2016 reliability',
            'mymotorlist.com - B6324S 3.2 engine (timing chain, known issues)',
            'go-parts.com / fcpeuro.com - XC70 timing belt intervals (T5)',
            'cargurus.com / truecar.com / kbb.com / cars.com - 2016 XC70 powertrains',
            'kbb.com - 2013, 2014, 2015 XC70 3.2 values',
            'truecar.com / cargurus.com / kbb.com - XC70 listings, Arizona and nationwide',
            'carcomplaints.com / consumerreports.org - XC70 safety data, recalls',
            'carcheckervin.com / carvertical.com - Volvo VIN plant codes']),
        ('Jeep Wrangler', [
            'Prior Jeep Wrangler due-diligence report in this repository (reliability, '
            'valuations, death wobble)',
            'wikipedia.org / awdwiki.com / jk-forum.com - Command-Trac part-time 4WD',
            'moneygeek.com / carinsurance.com / policygenius.com - teen insurance costs']),
        ('Colorado', [
            'codot.gov - November 2025 traction law update; passenger vehicle traction law',
            'coloradolaw.net / tetongravity.com / unofficialnetworks.com - traction law changes',
            'dmv.colorado.gov - VIN inspections, DR 2698']),
        ('Standards applied offline', [
            'ISO 3779 / 49 CFR Part 565 - VIN check digit (vin_tools.py)']),
    ]
    for title, items in groups:
        s.append(P(title, 'h3'))
        s.append(bullets(items, style='small'))
    s.append(rule())
    s.append(P('Research support for a private vehicle purchase - not a vehicle history '
               'report, a title search, a mechanical inspection or professional advice. Prices '
               'and mileages are REPORTED and time-sensitive; confirm each with the seller.',
               'small'))
    return s


if __name__ == '__main__':
    out = sys.argv[1] if len(sys.argv) > 1 else 'Teen_Car_Volvo_XC70_vs_Jeep_Wrangler.pdf'
    print('Built:', build(out, story_fn=story, title=TITLE,
                          header_right='New driver  |  School + ski  |  $7,000-$12,000',
                          subject='Volvo XC70 vs Jeep Wrangler for a teen driver in Colorado, '
                                  '$7,000-$12,000'))
