#!/usr/bin/env python3
"""
Build a single-VIN research dossier (PDF) for 1J4FA69S54P720187.

Usage:  python3 build_vin_dossier.py [output.pdf]

The decode, check digit and filter verdicts are computed live from
vin_tools.py and wrangler_filter.py at build time.
"""
import sys
from datetime import date

from reportlab.platypus import CondPageBreak, NextPageTemplate, PageBreak

from build_report import (AMBER, GREEN, GREY, OLIVE, RULE, RUST, S, SAND, KeepTogether, P,
                          Paragraph, Spacer, Table, TableStyle, build, bullets, callout,
                          colors, datatable, hx, inch, rule, tag)
from vin_tools import check_digit, decode
import wrangler_filter as wf

VIN = '1J4FA69S54P720187'
TITLE = 'VIN Dossier - %s' % VIN
GREEN_BG = colors.HexColor('#eaf1ea')
AMBER_BG = colors.HexColor('#f7f1de')

# Other 2004 VINs sharing the 1J4FA69S pattern, each indexed as a Rubicon.
SIBLING_RUBICONS = ['1J4FA69SX4P710688', '1J4FA69S34P705056', '1J4FA69S64P728749',
                    '1J4FA69S44P736736', '1J4FA69S64P755434', '1J4FA69S34P755746',
                    '1J4FA69S64P756910', '1J4FA69S94P784636']

D = decode(VIN)
WANT, ERR = check_digit(VIN)
assert not ERR and WANT == VIN[8], 'subject VIN failed its check digit'
for v in SIBLING_RUBICONS:
    w, e = check_digit(v)
    assert not e and w == v[8], 'sibling VIN failed: %s' % v

AS_LISTED = wf.evaluate(dict(vin=VIN, price=9999, miles=91290, state='VA', city='Chantilly',
                             reported_year=2004))


def story(fw):
    s = [NextPageTemplate('body')]
    s += cover(fw)
    s.append(PageBreak())
    for fn in (sec_findings, sec_decode, sec_spec, sec_history, sec_lead, sec_dealer,
               sec_risk, sec_value, sec_questions, sec_sources):
        s += fn(fw)
    return s


def cover(fw):
    s = [Spacer(1, 0.92 * inch), P('SINGLE-VEHICLE RESEARCH DOSSIER', 'cover_lbl'),
         Spacer(1, 5), P('2004 Jeep Wrangler Rubicon', 'title'),
         P('VIN %s' % VIN, 'subtitle'), Spacer(1, 0.4 * inch)]
    facts = [
        ['VIN', '%s - check digit PASS' % VIN],
        ['DECODES TO', '2004 Wrangler TJ, Rubicon, 4.0L inline six, built in Toledo, Ohio'],
        ['POSSIBLE LISTING', 'Euro Auto Sport, Chantilly, Virginia (unconfirmed - Section 5)'],
        ['CONTEXT', 'Teen driver in Colorado; budget $7,000-$12,000; reliable years only'],
        ['REPORT DATE', date.today().strftime('%B %d, %Y')],
    ]
    t = Table([[Paragraph(k, S['cover_lbl']), Paragraph(v, S['cover_val'])] for k, v in facts],
              colWidths=[1.45 * inch, fw - 1.45 * inch])
    t.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'TOP'),
                           ('LEFTPADDING', (0, 0), (-1, -1), 0),
                           ('TOPPADDING', (0, 0), (-1, -1), 5),
                           ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
                           ('LINEBELOW', (0, 0), (-1, -2), 0.4, RULE)]))
    s += [t, Spacer(1, 0.2 * inch)]
    s.append(callout(
        'The short answer',
        'This is a <b>genuine VIN for a 2004 TJ Rubicon with the 4.0 inline six</b> - a '
        'best-rated TJ year and the most capable Wrangler of its generation. No accident, '
        'salvage, auction or prior sale record for it surfaced anywhere in the open web. '
        'Whether it is the car at Euro Auto Sport is <b>not yet proven</b>: their indexed '
        'listing (stock #12280) shows no VIN and is titled "Sport" in one place, and '
        '$9,999 is far below what a real Rubicon usually fetches. Get the VIN on stock #12280 '
        'confirmed before anything else.',
        accent=AMBER, bg=AMBER_BG))
    s += [Spacer(1, 0.08 * inch), P('<b>CONTENTS</b>', 'cover_lbl'), Spacer(1, 3)]
    for c in ['1.  Findings at a glance', '2.  VIN decode, position by position',
              '3.  What a 2004 Rubicon is', '4.  History search: what was and was not found',
              '5.  The Chantilly lead', '6.  The dealer', '7.  Risk assessment for this buyer',
              '8.  Value', '9.  Questions for the dealer and inspection points', '10. Sources']:
        s.append(Paragraph(c, S['toc']))
    return s


def sec_findings(fw):
    s = [P('1.  Findings at a glance', 'h1'), rule()]
    rows = [
        [tag('VERIFIED', GREEN), 'The VIN is genuine (ISO 3779 check digit passes).'],
        [tag('VERIFIED', GREEN), 'Model year 2004, 4.0L inline six, Toledo-built TJ.'],
        [tag('STRONG', GREEN), 'Trim is Rubicon: series code 6 is Rubicon in TJ decoder '
                               'tables, and eight other authenticated 2004 VINs with the '
                               'same 1J4FA69S pattern are all listed as Rubicons.'],
        [tag('VERIFIED', GREEN), 'Passes the reliable-year rules: 2004 is a best TJ year, '
                                 'after the 0331 head and before the OPDA failures.'],
        [tag('NOT FOUND', GREY), 'No listing, auction, salvage, insurance-loss or prior-sale '
                                 'record for this VIN in any search index this environment '
                                 'could reach.'],
        [tag('UNPROVEN', AMBER), 'That it is the car for sale at Euro Auto Sport, Chantilly.'],
        [tag('CONFLICT', RUST), 'Euro Auto Sport\'s 2004 (stock #12280) is titled "Sport" '
                                'on one listing page and priced like a Sport.'],
        [tag('RULED OUT', GREY), 'The burgundy 2004 Rubicon also in Chantilly is a different '
                                 'car (VIN ...784636, NOVA Autoland).'],
        [tag('FILTER', RUST), 'As a Virginia-listed TJ, the automatic filter excludes it for '
                              'frame-rot risk - see Section 7 for why a frame inspection, '
                              'not the rule, should decide.'],
    ]
    s.append(datatable(['Status', 'Finding'], [[a, Paragraph(b, S['cell'])] for a, b in rows],
                       [1.05 * inch, fw - 1.05 * inch]))
    return s


def sec_decode(fw):
    s = [CondPageBreak(3.0 * inch), P('2.  VIN decode, position by position', 'h1'), rule()]
    rows = [
        ['1-3', '1J4', 'Jeep multipurpose vehicle, built in the USA (Chrysler-era WMI)',
         'VERIFIED'],
        ['4', 'F', 'GVWR / restraint class', 'PARTIAL'],
        ['5', 'A', 'Vehicle line - Wrangler TJ, 4x4', 'PARTIAL'],
        ['6', '6', '<b>Series: Rubicon.</b> TJ decoder tables list 6 = Rubicon from 2003, '
                   'when the trim launched. Every other 1J4FA69S 2004 VIN found is a Rubicon.',
         'STRONG'],
        ['7', '9', 'Body style - 2-door open body', 'PARTIAL'],
        ['8', 'S', '<b>Engine: 4.0L inline six</b>, unleaded (S = 4.0L in TJ decoder tables)',
         'VERIFIED'],
        ['9', '5', 'Check digit - computed value is 5, VIN carries 5: <b>PASS</b>', 'VERIFIED'],
        ['10', '4', 'Model year <b>2004</b>', 'VERIFIED'],
        ['11', 'P', 'Assembly plant - Toledo, Ohio (code P; "Toledo #2" in TJ-era guides)',
         'VERIFIED'],
        ['12-17', '720187', 'Production serial. The authenticated 2004 Rubicons found span '
                            '705056 to 784636; this one sits early in that run.', 'VERIFIED'],
    ]
    col = {'VERIFIED': GREEN, 'STRONG': GREEN, 'PARTIAL': AMBER}
    s.append(datatable(['Pos', 'Value', 'Meaning', 'Grade'],
                       [[Paragraph('<b>%s</b>' % a, S['cell']), Paragraph(b, S['mono']),
                         Paragraph(c, S['cell']), tag(d, col[d])] for a, b, c, d in rows],
                       [0.48 * inch, 0.72 * inch, fw - 2.15 * inch, 0.95 * inch]))
    s.append(Spacer(1, 6))
    s.append(P('Positions 4, 5 and 7 are graded PARTIAL because their exact code tables were '
               'not confirmed; none of them affects any conclusion here. The federal decoder at '
               'vpic.nhtsa.dot.gov returns the manufacturer\'s own record and should confirm '
               'trim and engine - it was unreachable from this environment.', 'small'))
    s.append(P('2.1  Corroborating VINs', 'h2'))
    s.append(P('Eight other 2004 VINs with the same 1J4FA69S prefix surfaced in listings and '
               'auction indexes, every one described as a Rubicon. All eight pass the check '
               'digit:', 'body'))
    grid = [SIBLING_RUBICONS[i:i + 4] for i in range(0, 8, 4)]
    t = Table([[Paragraph(v, S['monos']) for v in row] for row in grid],
              colWidths=[fw / 4] * 4)
    t.setStyle(TableStyle([('GRID', (0, 0), (-1, -1), 0.4, RULE),
                           ('BACKGROUND', (0, 0), (-1, -1), SAND),
                           ('TOPPADDING', (0, 0), (-1, -1), 4),
                           ('BOTTOMPADDING', (0, 0), (-1, -1), 4)]))
    s.append(t)
    return s


def sec_spec(fw):
    s = [CondPageBreak(3.0 * inch), P('3.  What a 2004 Rubicon is', 'h1'), rule()]
    s.append(P(
        'The Rubicon was the off-road flagship of the TJ line from 2003. Factory equipment '
        'that separates it from a Sport or X - and that you should physically confirm, since '
        'a "Rubicon" with missing Rubicon hardware has either been parted out or is not one:',
        'body'))
    s.append(datatable(['Component', 'Rubicon specification'], [
        ['Axles', 'Dana 44 front <b>and</b> rear (a Sport has a lighter Dana 30 front)'],
        ['Lockers', 'Tru-Lok selectable air-actuated lockers front and rear; engage in 4-Low '
                    'below about 10 mph'],
        ['Transfer case', 'NV241 "Rock-Trac" with a 4:1 low range'],
        ['Gearing', '4.10 axle ratio'],
        ['Driveshafts', 'Heavy-duty, 1330 u-joints'],
        ['Engine', '4.0L inline six, 190 hp'],
        ['Transmission', 'Manual or automatic (Euro Auto Sport\'s car is listed as a 4-speed '
                         'automatic)'],
        ['Wheels and tyres', '16x8 five-spoke aluminium, Goodyear Wrangler MT/R LT245/75R16'],
        ['Body', 'Diamond-plate rocker guards; Rubicon badging'],
        ['Brakes', 'Four-wheel discs'],
    ], [1.3 * inch, fw - 1.3 * inch]))
    s.append(Spacer(1, 6))
    s.append(P(
        'For a school-and-ski car, almost none of this matters day to day - lockers and a '
        '4:1 crawl ratio are rock-crawling equipment. What matters is that the Rubicon is still '
        'a TJ with the durable 4.0, and that its hardware is a target for hard off-road use, '
        'which is why Section 9 asks for an abuse inspection.', 'body'))
    return s


def sec_history(fw):
    s = [CondPageBreak(3.0 * inch),
         P('4.  History search: what was and was not found', 'h1'), rule()]
    s.append(P(
        'The VIN was searched exactly, and against listing marketplaces, enthusiast auctions '
        '(Bring a Trailer, Cars &amp; Bids, Hagerty), salvage and insurance auctions (Copart, '
        'IAAI and their archive sites) and free VIN-check aggregators.', 'body'))
    s.append(datatable(['Source class', 'Result for this VIN'], [
        ['Exact-VIN web search', 'One hit: a bulk index page of 2004 Wrangler VINs on a '
                                 'free mileage-check site. No vehicle-specific data.'],
        ['Dealer and marketplace listings', 'None indexed under this VIN'],
        ['Enthusiast auctions', 'None'],
        ['Salvage / insurance auctions', 'None - while several sibling 2004 Rubicons do appear '
                                         '(one sold on Copart in May 2026 with a Tennessee '
                                         'salvage certificate)'],
        ['Recalls (model-level)', 'Three on the 2004 Wrangler: a corrected tyre-information '
                                  'label, and two covering <i>aftermarket</i> Airtex fuel '
                                  'pumps and replacement brake master cylinders. None is a '
                                  'factory safety defect.'],
    ], [1.9 * inch, fw - 1.9 * inch]))
    s.append(Spacer(1, 6))
    s.append(callout(
        'What "nothing found" means',
        'Absence from public indexes is mildly reassuring - many total-loss vehicles leave a '
        'Copart or IAAI footprint that these sites archive - but it is <b>not</b> a clean '
        'history. Ownership count, accident reports, odometer readings, title brands and '
        'where the car has lived are only in CARFAX, AutoCheck and NMVTIS, all paid and all '
        'unreachable here. Those three checks are the next step, and the "where has it lived" '
        'answer decides the frame question in Section 7.',
        accent=AMBER, bg=AMBER_BG))
    return s


def sec_lead(fw):
    s = [CondPageBreak(3.0 * inch), P('5.  The Chantilly lead', 'h1'), rule()]
    s.append(P('Two 2004 Wranglers surfaced in Chantilly, Virginia:', 'body'))
    s.append(datatable(['', 'Euro Auto Sport', 'NOVA Autoland'], [
        ['Stock / VIN', 'Stock #12280; VIN not indexed', 'VIN 1J4FA69S94P784636'],
        ['Trim as listed', '"2004 Jeep Wrangler" - one listing page titles it '
                           '<b>Sport</b>', 'Rubicon'],
        ['Price', '$9,999', '$12,995 - $13,995 (two indexed figures)'],
        ['Mileage', '91,290', '47,779 - 47,795'],
        ['Colour', 'Black', 'Burgundy, dark slate grey interior'],
        ['Drivetrain', '4.0L I6, 4-speed automatic, 4WD', '4.0L I6'],
        ['Is it this VIN?', '<b>Unknown</b>', '<b>No</b> - different serial'],
    ], [1.25 * inch, (fw - 1.25 * inch) / 2, (fw - 1.25 * inch) / 2]))
    s.append(Spacer(1, 6))
    s.append(P('5.1  Reading the evidence', 'h2'))
    s.append(bullets([
        'If stock #12280 is a <b>Sport</b>, its VIN begins 1J4FA49S and it is not this car. '
        'The "Sport" title and the $9,999 price, which matches 2004 Sport money, both point '
        'this way.',
        'If stock #12280 <b>is</b> this VIN, it is a Rubicon advertised as a Sport. That '
        'happens - dealers mislabel trims - and it would make $9,999 a genuine bargain against '
        'Rubicon market prices. It would also mean you must physically confirm the Rubicon '
        'hardware in Section 3 is still on it.',
        'Listing data in this whole project has proved unreliable (several adverts carried the '
        'wrong year), so neither reading should be acted on until the dealer states the VIN.',
    ]))
    s.append(callout(
        'One question settles it',
        'Ask Euro Auto Sport: <i>"What is the full VIN on stock #12280?"</i> If it is '
        '%s, this dossier applies in full. If it is not, run whatever VIN they give you '
        'through wrangler_filter.py.' % VIN,
        accent=OLIVE, bg=SAND))
    return s


def sec_dealer(fw):
    s = [CondPageBreak(3.0 * inch), P('6.  The dealer', 'h1'), rule()]
    s.append(datatable(['', 'Euro Auto Sport (Euro Auto Sport LLC)'], [
        ['Address', '25284 Pleasant Valley Rd, Unit 132, Chantilly, VA 20152'],
        ['Phone', 'Indexed as both (571) 570-9050 and (571) 367-4620 - confirm which is current'],
        ['Website', 'euroautosportllc.com'],
        ['Type', 'Independent used-car dealer'],
        ['Inventory profile', 'About 33 vehicles, median price about $8,999, median 57 days '
                              'listed'],
        ['Reviews', 'A CARFAX dealer-review page exists; its rating could not be retrieved. '
                    'No BBB profile surfaced under this name.'],
    ], [1.4 * inch, fw - 1.4 * inch]))
    s.append(Spacer(1, 6))
    s.append(P(
        'There is nothing negative on record, but there is also very little on record at all. '
        'For an independent lot with a thin public footprint, verify before you rely:', 'body'))
    s.append(bullets([
        '<b>Licence.</b> Virginia dealers are licensed by the Motor Vehicle Dealer Board '
        '(mvdb.virginia.gov, 804-367-1100, dboard@mvdb.virginia.gov). Confirm Euro Auto Sport '
        'LLC holds a current licence.',
        '<b>Why it matters.</b> The Board\'s Motor Vehicle Transaction Recovery Fund can '
        'reimburse buyers who obtain a court judgment for fraud by a <i>licensed</i> dealer. '
        'That protection does not exist with an unlicensed seller.',
        '<b>Reviews.</b> Read the CARFAX dealer page and Google reviews yourself; look for '
        'specific complaints about title delays or undisclosed damage.',
    ]))
    return s


def sec_risk(fw):
    s = [CondPageBreak(3.0 * inch), P('7.  Risk assessment for this buyer', 'h1'), rule()]
    hard = '; '.join(AS_LISTED['hard']) or 'none'
    rows = [
        ['Virginia frame exposure', 'Northern Virginia salts its roads, and TJ frames rot from '
         'the inside out. Run as listed, the automatic filter returns <b>%s</b> (%s). That '
         'rule uses listing location as a proxy for history; for one specific car, the '
         'CARFAX location history and a hands-on frame inspection should decide. A long '
         'Virginia life plus visible frame scaling is a walk-away.' % (AS_LISTED['decision'],
                                                                        hard), RUST],
        ['No stability control', 'No TJ has electronic stability control - the main safety '
         'reason the earlier report preferred a 2014-2017 JK for a new driver.', RUST],
        ['Mud-terrain tyres', 'If it still wears Rubicon-style MT/R tyres, they are poor on wet '
         'and icy pavement. Budget for mountain-snowflake winter tyres; Colorado\'s traction '
         'law requires rated tyres anyway.', AMBER],
        ['Off-road abuse', 'Rubicons get used for what they were built for. Check skid plates, '
         'differential covers and rocker guards for heavy scarring; check alignment for bent '
         'steering or axle parts; and test both air lockers - leaks and failed compressors are '
         'common age faults.', AMBER],
        ['Age', 'A 22-year-old vehicle: rubber, bushings, wiring and seals have aged regardless '
         'of mileage. 91,290 miles, if that is this car, is moderate for the age.', AMBER],
        ['Distance', 'Chantilly is roughly 1,650 miles from 80127. Shipping will cost more than '
         'the $700-$1,100 quoted earlier for 1,000-mile routes, and Colorado registration needs '
         'a DR 2698 VIN verification and an emissions test.', GREY],
        ['Engine-specific faults', 'Not applicable: 2004 avoids the 2000-01 "0331" head and the '
         '2005-06 OPDA failures. Normal 4.0 oil leaks still apply.', GREEN],
    ]
    s.append(datatable(['Risk', 'Assessment', ''],
                       [[Paragraph('<b>%s</b>' % a, S['cell']), Paragraph(b, S['cell']),
                         Paragraph('<font color="%s"><b>%s</b></font>' % (hx(c), {
                             RUST: 'HIGH', AMBER: 'MED', GREY: 'NOTE', GREEN: 'CLEAR'}[c]),
                             S['cell'])] for a, b, c in rows],
                       [1.35 * inch, fw - 1.95 * inch, 0.6 * inch]))
    return s


def sec_value(fw):
    s = [CondPageBreak(3.0 * inch), P('8.  Value', 'h1'), rule()]
    s.append(datatable(['Source', '2004 Rubicon value'], [
        ['KBB private party', '$8,375 - $10,850'],
        ['Hagerty, good condition (July 2026)', '$16,667 - $22,233'],
        ['Chantilly, NOVA Autoland (47,779 mi)', '$12,995 - $13,995 asking'],
        ['Hillsborough CA (43,000 mi)', '$22,000 asking'],
        ['Motor Car Classics (65,388 mi)', '$28,900 asking'],
        ['eBay, 9,926 mi', 'Bid to $37,500'],
    ], [2.6 * inch, fw - 2.6 * inch]))
    s.append(Spacer(1, 6))
    s.append(P(
        'KBB values the Rubicon like any 22-year-old SUV; the enthusiast market (Hagerty, real '
        'asking prices) treats it as a collectible. Real transactions sit between the two and '
        'rise steeply as mileage falls. For a 91,000-mile example in honest condition, '
        '<b>$12,000-$18,000</b> is a realistic market range. A $9,999 Rubicon at that mileage '
        'would be either a mislabelled bargain or a car with a reason to be cheap - the same '
        'logic the filter applies to under-priced JKs. Either way it sits inside your $12,000 '
        'budget, which almost no honest Rubicon does.', 'body'))
    return s


def sec_questions(fw):
    s = [CondPageBreak(3.0 * inch),
         P('9.  Questions for the dealer and inspection points', 'h1'), rule()]
    blocks = [
        ['ASK BEFORE TRAVELLING', [
            'Full VIN on stock #12280 - does it match %s?' % VIN,
            'Is it a Rubicon or a Sport? Photos of the dash locker switch and Rubicon badging',
            'Clean title in the dealership\'s name? Any brand: salvage, rebuilt, flood?',
            'CARFAX or AutoCheck report - and where has the vehicle been registered over its life?',
            'Undercarriage and frame photos: rails, central skid plate area, rear control-arm '
            'mounts, body mounts',
            'Will they allow an independent pre-purchase inspection at a shop you choose?',
            'Out-the-door price including processing fees (Virginia dealers charge them)',
        ]],
        ['RUBICON-SPECIFIC INSPECTION', [
            'Dana 44 front axle present (not a swapped Dana 30)',
            'Both air lockers engage in 4-Low; compressor cycles off - a constantly running '
            'compressor means an air leak',
            'Rock-Trac 4:1 low range engages cleanly; no grinding',
            'Alignment readings - bent steering or axle parts show as abnormal camber',
            'Skid plates, differential covers, rocker guards: scarring level',
            'Lift or modification quality, if modified',
        ]],
        ['TJ ESSENTIALS', [
            'Frame tap test under the central skid plate and at the rear control-arm mounts',
            'Floor pans under the carpet; rear bumper and body mounts',
            '4.0 oil leaks: rear main, timing cover, oil pan, valve cover',
            'Three VIN plates match: dash, door jamb, frame stamping',
            'NMVTIS title check plus your own history report before money moves',
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


def sec_sources(fw):
    s = [CondPageBreak(2.6 * inch), P('10.  Sources', 'h1'), rule()]
    groups = [
        ('VIN decoding', ['quadratec.com / extremeterrain.com / wranglertjforum.com / '
                          'getahelmet.com - TJ VIN position tables (series 6 = Rubicon, '
                          'S = 4.0L, P = Toledo)',
                          'ISO 3779 / 49 CFR 565 - check digit, computed offline']),
        ('Vehicle and siblings', ['windowvinreport.com - bulk 2004 Wrangler VIN index',
                                  'auction123.com / vms.autorevo.com / cars.com / '
                                  'carsandbids.com / motorcarclassics.com - sibling 2004 '
                                  'Rubicon listings',
                                  'vincheck.it.com - sibling Copart records']),
        ('Specification and faults', ['vms.autorevo.com (Collins Bros Jeep) - 2004 Rubicon '
                                      'equipment', 'wranglertjforum.com - buying a used TJ; '
                                      'Rubicon lockers', 'carcomplaints.com / autosafety.org - '
                                      '2004 Wrangler recalls']),
        ('Value', ['hagerty.com - 2004 Wrangler Rubicon value', 'kbb.com - 2004 Rubicon',
                   'classic.com / ebay.com - TJ market']),
        ('Dealer', ['carsforsale.com / carzing.com / caredge.com / cruz.com / '
                    'euroautosportllc.com - Euro Auto Sport', 'carfax.com - dealer review '
                    'page', 'mvdb.virginia.gov - dealer licensing, Transaction Recovery Fund']),
    ]
    for t, items in groups:
        s.append(P(t, 'h3'))
        s.append(bullets(items, style='small'))
    s.append(rule())
    s.append(P('Research support only - not a vehicle history report, title search or '
               'inspection. Listing data is REPORTED and time-sensitive.', 'small'))
    return s


if __name__ == '__main__':
    out = sys.argv[1] if len(sys.argv) > 1 else 'VIN_Dossier_1J4FA69S54P720187.pdf'
    print('Built:', build(out, story_fn=story, title=TITLE,
                          header_right='2004 Wrangler Rubicon  |  Single-VIN research',
                          subject='Research dossier for Jeep Wrangler VIN %s' % VIN))
