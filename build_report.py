#!/usr/bin/env python3
"""
Build the Jeep Wrangler acquisition due-diligence report (PDF).

Usage:  python3 build_report.py [output.pdf]

Every VIN printed in the report is validated offline by vin_tools.check_digit
at build time; the build fails loudly if a VIN stops validating.
"""
import sys
from datetime import date

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (BaseDocTemplate, CondPageBreak, Frame, KeepTogether,
                                ListFlowable, ListItem, NextPageTemplate, PageBreak,
                                PageTemplate, Paragraph, Spacer, Table, TableStyle)

from vin_tools import CANDIDATES, check_digit, decode

# ----------------------------------------------------------------- palette
INK      = colors.HexColor('#1c1c18')
BODY     = colors.HexColor('#33332c')
OLIVE    = colors.HexColor('#3f4a2e')   # headline / rule colour
OLIVE_LT = colors.HexColor('#7d8a63')
SAND     = colors.HexColor('#f3efe4')
SAND_DK  = colors.HexColor('#e3dcc8')
RUST     = colors.HexColor('#9c4a25')   # warnings
GREEN    = colors.HexColor('#2f6b3f')   # verified
AMBER    = colors.HexColor('#8a6a12')   # unverified
GREY     = colors.HexColor('#6d6d64')
RULE     = colors.HexColor('#c9c2ad')

PAGE_W, PAGE_H = letter
MARGIN = 0.78 * inch

# ----------------------------------------------------------------- styles
_ss = getSampleStyleSheet()


def _st(name, **kw):
    base = kw.pop('parent', _ss['Normal'])
    return ParagraphStyle(name, parent=base, **kw)


S = {
    'title': _st('title', fontName='Helvetica-Bold', fontSize=27, leading=31,
                 textColor=INK, spaceAfter=6),
    'subtitle': _st('subtitle', fontName='Helvetica', fontSize=12.5, leading=17,
                    textColor=GREY, spaceAfter=4),
    'h1': _st('h1', fontName='Helvetica-Bold', fontSize=15.5, leading=19,
              textColor=OLIVE, spaceBefore=16, spaceAfter=7),
    'h2': _st('h2', fontName='Helvetica-Bold', fontSize=11.6, leading=15,
              textColor=INK, spaceBefore=12, spaceAfter=5),
    'h3': _st('h3', fontName='Helvetica-BoldOblique', fontSize=10, leading=13.5,
              textColor=OLIVE, spaceBefore=9, spaceAfter=3),
    'body': _st('body', fontName='Helvetica', fontSize=9.6, leading=13.8,
                textColor=BODY, alignment=TA_JUSTIFY, spaceAfter=6),
    'bullet': _st('bullet', fontName='Helvetica', fontSize=9.4, leading=13.2,
                  textColor=BODY, spaceAfter=2.5),
    'small': _st('small', fontName='Helvetica', fontSize=8.3, leading=11.4,
                 textColor=GREY, spaceAfter=4),
    'cell': _st('cell', fontName='Helvetica', fontSize=8.2, leading=10.8,
                textColor=BODY),
    'cellb': _st('cellb', fontName='Helvetica-Bold', fontSize=8.2, leading=10.8,
                 textColor=INK),
    'cellh': _st('cellh', fontName='Helvetica-Bold', fontSize=8.2, leading=10.6,
                 textColor=colors.white),
    'mono': _st('mono', fontName='Courier-Bold', fontSize=8.4, leading=11,
                textColor=INK),
    'monos': _st('monos', fontName='Courier', fontSize=7.8, leading=10.2,
                 textColor=BODY),
    'callh': _st('callh', fontName='Helvetica-Bold', fontSize=9.6, leading=12.6,
                 textColor=INK, spaceAfter=3),
    'callb': _st('callb', fontName='Helvetica', fontSize=9.1, leading=12.8,
                 textColor=BODY),
    'toc': _st('toc', fontName='Helvetica', fontSize=9.2, leading=12,
               textColor=BODY),
    'cover_lbl': _st('cover_lbl', fontName='Helvetica-Bold', fontSize=8,
                     leading=11, textColor=OLIVE_LT),
    'cover_val': _st('cover_val', fontName='Helvetica-Bold', fontSize=11,
                     leading=14, textColor=INK),
    'centre': _st('centre', fontName='Helvetica', fontSize=9, leading=12,
                  textColor=GREY, alignment=TA_CENTER),
}


def P(txt, s='body'):
    return Paragraph(txt, S[s])


def bullets(items, style='bullet', bullet='•'):
    return ListFlowable(
        [ListItem(P(i, style), leftIndent=13, value=bullet) for i in items],
        bulletType='bullet', start=bullet, leftIndent=13,
        bulletFontSize=7.5, bulletOffsetY=-1, spaceAfter=6)


def rule(color=RULE, thick=0.7, space=5):
    t = Table([['']], colWidths=[PAGE_W - 2 * MARGIN], rowHeights=[thick])
    t.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, -1), color),
                           ('TOPPADDING', (0, 0), (-1, -1), 0),
                           ('BOTTOMPADDING', (0, 0), (-1, -1), 0)]))
    return KeepTogether([Spacer(1, space), t, Spacer(1, space)])


def callout(heading, body_txt, accent=RUST, bg=None):
    """Tinted box with a coloured left spine."""
    bg = bg or SAND
    inner = [P(heading, 'callh')] if heading else []
    if isinstance(body_txt, str):
        inner.append(P(body_txt, 'callb'))
    else:
        inner.extend(body_txt)
    t = Table([['', inner]], colWidths=[3.6, PAGE_W - 2 * MARGIN - 3.6])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, 0), accent),
        ('BACKGROUND', (1, 0), (1, 0), bg),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (0, 0), 0), ('RIGHTPADDING', (0, 0), (0, 0), 0),
        ('LEFTPADDING', (1, 0), (1, 0), 10), ('RIGHTPADDING', (1, 0), (1, 0), 10),
        ('TOPPADDING', (1, 0), (1, 0), 8), ('BOTTOMPADDING', (1, 0), (1, 0), 9),
        ('TOPPADDING', (0, 0), (0, 0), 0), ('BOTTOMPADDING', (0, 0), (0, 0), 0),
    ]))
    return KeepTogether([Spacer(1, 3), t, Spacer(1, 8)])


def datatable(header, rows, widths, aligns=None, zebra=True, fontsize=8.2):
    """Table whose cells are already Paragraphs or plain strings."""
    def wrap(v, sty):
        return v if isinstance(v, Paragraph) else Paragraph(str(v), S[sty])

    data = [[wrap(h, 'cellh') for h in header]]
    data += [[wrap(c, 'cell') for c in r] for r in rows]

    t = Table(data, colWidths=widths, repeatRows=1)
    cmds = [
        ('BACKGROUND', (0, 0), (-1, 0), OLIVE),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('GRID', (0, 0), (-1, -1), 0.4, RULE),
        ('LINEBELOW', (0, 0), (-1, 0), 0.9, OLIVE),
        ('TOPPADDING', (0, 0), (-1, -1), 4.5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4.5),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('RIGHTPADDING', (0, 0), (-1, -1), 5),
    ]
    if zebra:
        for i in range(1, len(data)):
            if i % 2 == 0:
                cmds.append(('BACKGROUND', (0, i), (-1, i), SAND))
    for spec in (aligns or []):
        cmds.append(spec)
    t.setStyle(TableStyle(cmds))
    return t


def hx(color):
    """'#rrggbb' string for use inside Paragraph <font color=...> markup."""
    return '#%02x%02x%02x' % (int(color.red * 255 + 0.5),
                              int(color.green * 255 + 0.5),
                              int(color.blue * 255 + 0.5))


def tag(text, color):
    return Paragraph('<font color="%s"><b>%s</b></font>' % (hx(color), text), S['cell'])


# ----------------------------------------------------------------- chrome
REPORT_TITLE = 'Jeep Wrangler Acquisition Due-Diligence Report'


def _cover(canvas, doc):
    canvas.saveState()
    canvas.setFillColor(SAND)
    canvas.rect(0, PAGE_H - 3.15 * inch, PAGE_W, 3.15 * inch, stroke=0, fill=1)
    canvas.setFillColor(OLIVE)
    canvas.rect(0, PAGE_H - 3.21 * inch, PAGE_W, 0.06 * inch, stroke=0, fill=1)
    # seven grille slots, a quiet nod to the subject
    x0, y0, w, h, gap = MARGIN, PAGE_H - 1.42 * inch, 0.115 * inch, 0.5 * inch, 0.075 * inch
    canvas.setFillColor(OLIVE_LT)
    for i in range(7):
        canvas.rect(x0 + i * (w + gap), y0, w, h, stroke=0, fill=1)
    canvas.setFillColor(GREY)
    canvas.setFont('Helvetica', 7.6)
    canvas.drawCentredString(PAGE_W / 2.0, 0.55 * inch,
                             'Prepared for the requester  |  Not a substitute for a '
                             'title search, a VIN history report, or a hands-on inspection.')
    canvas.restoreState()


def _inner(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(RULE)
    canvas.setLineWidth(0.5)
    canvas.line(MARGIN, PAGE_H - 0.62 * inch, PAGE_W - MARGIN, PAGE_H - 0.62 * inch)
    canvas.setFont('Helvetica', 7.4)
    canvas.setFillColor(GREY)
    canvas.drawString(MARGIN, PAGE_H - 0.55 * inch, REPORT_TITLE)
    canvas.drawRightString(PAGE_W - MARGIN, PAGE_H - 0.55 * inch,
                           '80127 + CA + TX  |  $6,000-$18,000')
    canvas.line(MARGIN, 0.66 * inch, PAGE_W - MARGIN, 0.66 * inch)
    canvas.setFont('Helvetica', 7.4)
    canvas.drawString(MARGIN, 0.5 * inch, date.today().strftime('%B %d, %Y'))
    canvas.setFont('Helvetica-Bold', 8)
    canvas.setFillColor(OLIVE)
    canvas.drawRightString(PAGE_W - MARGIN, 0.5 * inch, str(canvas.getPageNumber()))
    canvas.restoreState()


def build(path):
    doc = BaseDocTemplate(
        path, pagesize=letter,
        leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=0.85 * inch, bottomMargin=0.85 * inch,
        title=REPORT_TITLE,
        author='Vehicle research brief',
        subject='Used Jeep Wrangler acquisition analysis, ZIP 80127 plus California and '
                'Texas, $6,000-$18,000')

    fw = PAGE_W - 2 * MARGIN
    cover_frame = Frame(MARGIN, MARGIN, fw, PAGE_H - 2 * MARGIN, id='cover',
                        leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
    body_frame = Frame(MARGIN, 0.85 * inch, fw, PAGE_H - 1.72 * inch, id='body',
                       leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
    doc.addPageTemplates([
        PageTemplate(id='cover', frames=[cover_frame], onPage=_cover),
        PageTemplate(id='body', frames=[body_frame], onPage=_inner),
    ])
    doc.build(story(fw))
    return path


# ----------------------------------------------------------------- content
def story(fw):
    s = [NextPageTemplate('body')]
    s += cover(fw)
    s.append(PageBreak())
    s += section_method(fw)
    s += section_market(fw)
    s += section_multistate(fw)
    s += section_candidates(fw)
    s += section_vin(fw)
    s += section_generations(fw)
    s += section_yearrisk(fw)
    s += section_recalls(fw)
    s += section_colorado(fw)
    s += section_seller(fw)
    s += section_ppi(fw)
    s += section_negotiation(fw)
    s += section_plan(fw)
    s += section_sources(fw)
    return s


def cover(fw):
    s = [Spacer(1, 0.92 * inch)]
    s.append(P('VEHICLE ACQUISITION RESEARCH', 'cover_lbl'))
    s.append(Spacer(1, 5))
    s.append(P('Jeep Wrangler', 'title'))
    s.append(P('Due-Diligence &amp; Seller-Reliability Report', 'subtitle'))
    s.append(Spacer(1, 0.40 * inch))

    facts = [
        ['SEARCH ORIGIN', 'ZIP 80127 - Ken Caryl / Littleton, Jefferson County, Colorado'],
        ['RADIUS', '20 miles local (Littleton, Lakewood, Englewood, Morrison, Golden,\n'
                   'Wheat Ridge, Arvada, Centennial, Denver metro south and west),\n'
                   'extended to California and Texas for remote sourcing'],
        ['BUDGET', '$6,000 - $18,000'],
        ['SCOPE', 'VIN authentication - vehicle history exposure - generation and\n'
                  'model-year reliability - seller and dealer reliability -\n'
                  'multi-state market comparison and landed cost'],
        ['REPORT DATE', date.today().strftime('%B %d, %Y')],
    ]
    rows = [[Paragraph(k, S['cover_lbl']),
             Paragraph(v.replace('\n', '<br/>'), S['cover_val'])] for k, v in facts]
    t = Table(rows, colWidths=[1.32 * inch, fw - 1.32 * inch])
    t.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LINEBELOW', (0, 0), (-1, -2), 0.4, RULE),
    ]))
    s.append(t)
    s.append(Spacer(1, 0.2 * inch))

    s.append(callout(
        'Read Section 1 before you read anything else.',
        'The marketplace sites holding live inventory (Cars.com, CarGurus, Autotrader, CARFAX, '
        'TrueCar, iSeeCars, KBB) and the NHTSA VIN-decoding API were all unreachable from the '
        'environment this report was compiled in - blocked at the network egress layer, not '
        'merely rate-limited. Every VIN below was therefore recovered from search-engine '
        'indexes and then <b>independently authenticated offline</b> using the ISO 3779 '
        'check-digit algorithm. That proves a VIN is structurally genuine. It does <b>not</b> '
        'prove the price, mileage, trim or dealer attached to it is correct - and Section 1.3 '
        'documents three cases where those attributes were demonstrably wrong.',
        accent=RUST))

    s.append(Spacer(1, 0.08 * inch))
    contents = [
        '1.  Method, evidence grading, and what this report can and cannot prove',
        '2.  What $6,000-$18,000 actually buys near 80127',
        '3.  Sourcing from California and Texas',
        '4.  VIN-authenticated candidate vehicles',
        '5.  Jeep Wrangler VIN decoding reference',
        '6.  Generation deep-dive: TJ, JK 3.8L, JK 3.6L',
        '7.  Model-year risk matrix',
        '8.  Recalls, warranty extensions, and the VIN checks to run',
        '9.  Regional risk: Colorado, California, Texas',
        '10.  Seller and dealer reliability assessment',
        '11. Pre-purchase inspection protocol',
        '12. Price anchoring and negotiation',
        '13. Action plan',
        '14. Sources',
    ]
    s.append(P('<b>CONTENTS</b>', 'cover_lbl'))
    s.append(Spacer(1, 3))
    for c in contents:
        s.append(Paragraph(c, S['toc']))
    return s


# ---------------------------------------------------------- 1. method
def section_method(fw):
    s = [P('1.  Method, evidence grading, and what this report can and cannot prove', 'h1'),
         rule()]

    s.append(P(
        'You asked for deep research on live listings, VINs, vehicle history and seller '
        'reliability. Three of those four are delivered in full. The fourth - live listing '
        'data - is delivered partially, and the honest accounting of why matters more than '
        'a padded list would.', 'body'))

    s.append(P('1.1  What was reachable, and what was not', 'h2'))
    s.append(P(
        'This report was compiled inside a sandboxed environment whose outbound network '
        'policy blocks nearly all third-party hosts. Confirmed blocked at the egress proxy '
        '(not a bot-detection block, not a rate limit - the TCP connection never completes):',
        'body'))

    blocked = [
        ['Cars.com, CarGurus, Autotrader, TrueCar, iSeeCars, KBB', 'Live listing inventory',
         tag('BLOCKED', RUST)],
        ['CARFAX, AutoCheck', 'Per-VIN accident / owner / title history',
         tag('BLOCKED', RUST)],
        ['vpic.nhtsa.dot.gov (free federal VIN decoder API)', 'Authoritative trim + engine decode',
         tag('BLOCKED', RUST)],
        ['api.nhtsa.gov (recall lookup by VIN)', 'Open-recall status',
         tag('BLOCKED', RUST)],
        ['BBB.org, DealerRater', 'Dealer complaint records',
         tag('BLOCKED', RUST)],
        ['Server-side web search', 'Indexed snippets of all of the above',
         tag('AVAILABLE', GREEN)],
    ]
    s.append(datatable(['Resource', 'What it would have provided', 'Status'],
                       blocked, [2.75 * inch, 2.5 * inch, fw - 5.25 * inch]))
    s.append(Spacer(1, 8))
    s.append(P(
        'Search indexes retain fragments of listing pages, so real VINs, real stock numbers, '
        'real dealer names and real valuation figures were recoverable. What could not be '
        'recovered is a complete, current, verified inventory snapshot. Anyone claiming '
        'otherwise from this environment would be inventing it.', 'body'))

    s.append(P('1.2  The offline authentication step', 'h2'))
    s.append(P(
        'Because search-snippet data cannot be trusted at face value, every VIN in this '
        'report was put through the ISO 3779 / 49 CFR 565 check-digit test, computed locally '
        'with no network access. The algorithm transliterates each character to a value, '
        'multiplies by a fixed positional weight, sums, and takes the remainder modulo 11; '
        'that remainder must equal the character in position 9.', 'body'))
    s.append(callout(
        'Why this test is worth running',
        'A fabricated or mis-transcribed 17-character string satisfies the check digit only '
        'about <b>1 time in 11</b>. Seven distinct VINs were recovered and <b>all seven '
        'passed</b>. The probability of that happening by chance is roughly 1 in 19 million. '
        'These are real, factory-issued VINs. The full validator source is reproduced in '
        'Section 5.4 so you can re-run it yourself.',
        accent=GREEN, bg=colors.HexColor('#eaf1ea')))

    s.append(P('1.3  Where the search layer was caught being wrong', 'h2'))
    s.append(P(
        'Authenticating the VINs exposed a second problem: the search summarisation layer '
        '<b>mis-pairs VINs with vehicle attributes</b>. The VIN itself encodes model year in '
        'position 10, so this is directly falsifiable, and it failed three times:', 'body'))

    mism = [
        ['1J4BA3H13BL589979', 'listed as a <b>2023</b> Wrangler Sport 4xe, $23,991',
         'Position 10 = <b>B</b> = <b>2011</b>. WMI 1J4 was retired for the 2012 model year. '
         'A 2023 4xe cannot carry this VIN.'],
        ['1J4FA49S31P347487', 'listed as a <b>2022</b> Wrangler Sahara, $28,549',
         'Position 10 = <b>1</b> = <b>2001</b>. VDS "FA49S" is a TJ-generation Sport with the '
         '4.0L I6. Off by 21 model years.'],
        ['1J4FA49S46P788486', 'listed as a <b>2023</b> Wrangler Sahara',
         'Position 10 = <b>6</b> = <b>2006</b>. Also a TJ Sport, not a late-model Sahara.'],
    ]
    s.append(datatable(
        ['VIN (authenticated)', 'What the search snippet claimed', 'What the VIN proves'],
        [[Paragraph(a, S['mono']), Paragraph(b, S['cell']), Paragraph(c, S['cell'])]
         for a, b, c in mism],
        [1.44 * inch, 1.95 * inch, fw - 3.39 * inch]))
    s.append(Spacer(1, 8))
    s.append(P(
        'A fourth inconsistency: VIN <b>1J4BA6H17BL574757</b> was returned twice, once as '
        '"$11,899 / 99,127 mi / Denver" and once as "$12,599 / 123,567 mi / Centennial." '
        'One vehicle cannot have two odometer readings. At least one snippet is stale, '
        'garbled, or describes a re-listing after the car moved between lots.', 'body'))

    s.append(P('1.4  Evidence grading used throughout', 'h2'))
    grades = [
        [tag('VERIFIED', GREEN), 'Proven by offline computation on the VIN itself, or stated '
         'consistently by a primary/authoritative source (KBB valuation bands, federal recall '
         'numbers, Colorado DOR process).'],
        [tag('REPORTED', AMBER), 'Recovered from a search index and plausible, but not '
         'independently confirmable from this environment. Treat as a lead to check, never as '
         'a fact to act on.'],
        [tag('CONTRADICTED', RUST), 'Recovered from a search index and shown false by the VIN '
         'or by an internal inconsistency.'],
    ]
    s.append(datatable(['Grade', 'Meaning'], grades, [1.15 * inch, fw - 1.15 * inch]))
    s.append(Spacer(1, 8))
    s.append(callout(
        'The one instruction that carries the most weight in this report',
        'Do not send money, place a deposit, or drive to a lot on the strength of any price or '
        'mileage figure printed here. Those are <b>REPORTED</b>. Phone the seller, quote the '
        'VIN, and make them state the mileage and out-the-door price out loud. Then run the VIN '
        'through the free federal decoder at vpic.nhtsa.dot.gov and the free recall lookup at '
        'nhtsa.gov/recalls - both are unreachable from here but take about ninety seconds each '
        'from any ordinary browser.',
        accent=RUST))
    return s


# ---------------------------------------------------------- 2. market
def section_market(fw):
    s = [CondPageBreak(3.1 * inch), P('2.  What $6,000-$18,000 actually buys near 80127', 'h1'), rule()]
    s.append(callout(
        'The extra $3,000 buys more than it looks like it should',
        'Raising the ceiling from $15,000 to $18,000 is not a 20% improvement in what you can '
        'buy - it is a change of category. At $15,000 every 3.6L Pentastar within reach was a '
        '2012 or 2013, the two worst-rated JK model years. At $18,000 the <b>2015-2017</b> JKs '
        '- consistently the best-rated of the entire generation - come inside private-party '
        'money. That reverses the central recommendation of the $15,000 analysis, and Section 7 '
        'sets out the new one.',
        accent=GREEN, bg=colors.HexColor('#eaf1ea')))

    s.append(P(
        'The Wrangler is the single most depreciation-resistant mainstream 4x4 sold in the '
        'United States. Your budget still does not reach a JL. What it now does reach is the '
        'whole mature end of the JK run, which is where you want to be.', 'body'))

    gens = [
        ['TJ', '1997-2006', '2-door only', '4.0L I6 (190 hp)\n2.4L/2.5L I4',
         '$6,000-$12,000',
         'Simplest, most durable drivetrain Jeep ever put in a Wrangler. '
         '<b>Frame rot is the killer</b> - and Colorado roads feed it.'],
        ['JK', '2007-2011', '2-door + Unlimited 4-door', '3.8L V6 (202 hp)',
         '$8,000-$15,000',
         'Modern comforts, 4-door option. Weak, thirsty engine that drinks oil past 100k. '
         'TIPM electrical gremlins. <b>Now a value play, not a stretch.</b>'],
        ['JK', '2012-2013', '2-door + Unlimited 4-door', '3.6L Pentastar V6 (285 hp)',
         '$12,000-$16,000',
         'Big power jump and the engine you want - but these are the two worst-rated JK '
         'years, and early Pentastar heads failed. <b>Hard to justify now.</b>'],
        ['JK', '2014', '2-door + Unlimited 4-door', '3.6L Pentastar V6 (285 hp)',
         '$14,000-$18,000',
         'First year clear of the cylinder-head defect. Denver average list price is '
         '$17,531 at an average 110,014 miles - reachable, but you are paying near the top of '
         'budget for a high-mile car.'],
        ['JK', '2015-2017', '2-door + Unlimited 4-door', '3.6L Pentastar V6 (285 hp)',
         '$14,000-$18,000+',
         '<b>The target.</b> Best-rated JK years, good engine, defect-free. Now inside budget '
         'at private-party money - Section 2.1 has the numbers. Expect to work for it at the '
         'lower-mileage end.'],
        ['JK / JL', '2018+', '2-door + Unlimited 4-door', '3.6L Pentastar V6 (285 hp)',
         'Above budget',
         'JL launch year brought its own teething problems. Out of reach and not worth '
         'chasing at this price.'],
    ]
    s.append(datatable(
        ['Gen', 'Years', 'Body', 'Engine', 'Typical ask', 'The trade you are making'],
        [[Paragraph(g[0], S['cellb'])] + [Paragraph(x.replace('\n', '<br/>'), S['cell'])
                                          for x in g[1:]] for g in gens],
        [0.40 * inch, 0.78 * inch, 0.88 * inch, 0.94 * inch, 1.00 * inch,
         fw - 4.0 * inch]))
    s.append(Spacer(1, 9))

    s.append(P('2.1  Valuation anchors', 'h2'))
    s.append(P(
        'Kelley Blue Book figures across the model years your budget now spans. The gap '
        'between trade-in and private-party is the dealer\'s margin, and it is your '
        'negotiating room. Read the <b>private-party</b> column as what the vehicle is worth; '
        'read the <b>trade-in</b> column as roughly what a dealer paid for it.', 'body'))
    kbb = [
        ['2011 Unlimited Sport (4-dr)', '$4,690 - $5,765', '$9,800 - $11,850', '$11,400'],
        ['2012 Unlimited Sport (4-dr)', '$6,515 - $7,915', '$11,330 - $13,680', '$13,150'],
        ['2014 Unlimited Sport (4-dr)', '$7,205 - $8,605', '$12,200 - $14,450', '-'],
        ['<b>2015 Unlimited Sport (4-dr)</b>', '$9,005 - $10,830', '<b>$13,190 - $15,790</b>',
         '$15,400'],
        ['2015 Sport S (2-dr)', '$6,915 - $8,340', '$12,500 - $14,900', '$14,550'],
        ['<b>2016 Sport (2-dr)</b>', '$9,990 - $11,840', '<b>$13,270 - $15,620</b>', '$14,900'],
        ['2017 Sport S (2-dr)', '$10,330 - $11,980', '$13,710 - $15,810', '-'],
    ]
    s.append(datatable(
        ['Vehicle', 'Trade-in value', 'Private-party value', 'Resale value'],
        kbb, [2.15 * inch, 1.35 * inch, 1.55 * inch, fw - 5.05 * inch],
        aligns=[('ALIGN', (1, 1), (-1, -1), 'CENTER')]))
    s.append(Spacer(1, 7))
    s.append(P(
        'Three conclusions. First, and decisively: <b>a 2015 Unlimited Sport carries a resale '
        'value of $15,400 and a private-party top end of $15,790.</b> That is inside $18,000 '
        'with room for tax and an inspection. The best-rated JK years are genuinely available '
        'to you now. Second, across all body styles the 2015 private-party range runs '
        '$13,700-$17,950 and the 2016 range $13,750-$18,700 - so the four-door Unlimiteds and '
        'higher trims sit at or just past your ceiling, while two-doors and base Sports sit '
        'comfortably inside it. Third, the 2011-2012 cars have not become bad buys; they have '
        'become <b>value</b> buys, several thousand dollars below your ceiling. That is a '
        'legitimate strategy if you would rather spend the difference on maintenance than on '
        'model year.', 'body'))
    s.append(callout(
        'Dealer retail runs above these numbers',
        'The Denver average list price for a 2014 Wrangler is <b>$17,531</b> against an average '
        '<b>110,014 miles</b> - which is well above the 2014 private-party band in the table. '
        'Franchise-dealer asking prices in this market carry a real premium over book. At '
        '$18,000 you will find 2015-2017 cars comfortably through private sale, and only at '
        'the high-mileage end of a dealer lot. Budget accordingly, and treat any dealer ask '
        'above the private-party top end as an opening position rather than a price.',
        accent=AMBER, bg=colors.HexColor('#f7f1de')))

    s.append(P('2.2  Supply in the search radius', 'h2'))
    s.append(P(
        'Inventory counts recovered from aggregator index pages. All graded '
        '<b>REPORTED</b> - counts churn daily and none could be re-confirmed.', 'small'))
    supply = [
        ['Cars.com', 'Wranglers under $15,000, Denver', '27'],
        ['iSeeCars', 'Wranglers under $15,000, Denver', '43'],
        ['Cars.com', 'Wrangler Unlimiteds under $20,000, Littleton', '67'],
        ['Cars.com', 'All Wranglers, Littleton', '114'],
        ['CarGurus', 'All Wranglers near Denver', '619 (from $5,995)'],
        ['CarGurus', 'All Wranglers near Littleton', '614 (from $4,210)'],
        ['TrueCar', 'All Wranglers, Littleton', '1,211 (from $4,786)'],
        ['iSeeCars', 'All Wranglers, Denver', '248 (from $6,977)'],
    ]
    s.append(datatable(['Source', 'Filter', 'Count'], supply,
                       [1.15 * inch, 3.3 * inch, fw - 4.45 * inch]))
    s.append(Spacer(1, 7))
    s.append(P(
        'No source published a count at exactly $18,000, so the band has to be bracketed. '
        'Denver holds 27-43 Wranglers under $15,000, and Littleton alone holds 67 Unlimiteds '
        'under $20,000. Interpolating, the $6,000-$18,000 window across the 20-mile radius '
        'plausibly contains <b>60 to 90 candidates</b> at any given moment - roughly double '
        'what the $15,000 ceiling reached, and the added inventory is concentrated in exactly '
        'the 2014-2017 years you most want. Treat that as a bracketed estimate, not a count.',
        'body'))
    s.append(P(
        'The practical effect: you can afford to be ruthless. Walk away from anything that '
        'fails a check in Section 11 - there will be another one next week, and now there '
        'will be several.', 'body'))
    return s


# ---------------------------------------------------------- 3. multi-state
def section_multistate(fw):
    s = [CondPageBreak(3.1 * inch),
         P('3.  Sourcing from California and Texas', 'h1'), rule()]

    s.append(callout(
        'What this section assumes',
        'That you are still based at 80127 and are widening where you <b>source</b> a vehicle - '
        'buying in California or Texas and bringing it to Colorado. Everything here is written '
        'for that case: landed cost, remote inspection, and Colorado titling. If instead you '
        'are relocating to one of those states, the vehicle analysis in Sections 6-8 carries '
        'over unchanged, but Section 3.7 (Colorado registration) does not apply and Section '
        '10.2 gains a state DMV you should substitute in.',
        accent=OLIVE, bg=SAND))

    s.append(P('3.1  Three reasons to extend, honestly ranked', 'h2'))
    s.append(bullets([
        '<b>Selection, by an order of magnitude.</b> Littleton lists 114 Wranglers in total. '
        'California lists <b>4,955 of the 2015 model year alone</b>. Houston holds over 1,165 '
        'Wranglers and Dallas over 1,345. When you are hunting a specific configuration - a '
        '2015-2017 Unlimited, low miles, unmodified, clean history - that difference is the '
        'whole argument.',
        '<b>Price, but not where you would expect it.</b> California statewide averages '
        '<b>$16,889</b> for a 2015 Wrangler. Texas is <i>more</i> expensive, not less. See 3.2.',
        '<b>Corrosion - real, but smaller than the internet will tell you.</b> See 3.3 before '
        'you pay a transport bill for it.',
    ]))

    s.append(P('3.2  Market comparison', 'h2'))
    s.append(P('Average list prices and supply, graded <b>REPORTED</b>. Note the model year '
               'differs by row - each is the year that market published.', 'small'))
    mkt = [
        ['<b>California</b> (statewide)', '2015', '<b>$16,889</b>', '-', '<b>4,955</b>',
         'Cheapest and deepest market found for the target year.'],
        ['Sacramento, CA', '2015', '$17,318', '107,574', '-',
         'Northern California; higher miles than the LA basin.'],
        ['Los Angeles, CA', '2016', '$18,486', '95,140', '-',
         'Premium metro pricing, but lower mileage.'],
        ['Houston, TX', '2015', '$17,727 - $18,106', '-', '428 - 446',
         'Deep supply. Also the highest flood-title risk in this report (3.4).'],
        ['Dallas, TX', '2015', '$18,370', '94,021', '-',
         'Most expensive market surveyed. Lower flood exposure than Houston.'],
        ['Denver, CO', '2014', '$17,531', '110,014', '-',
         'Highest average mileage of any market here.'],
        ['Littleton, CO', 'all', '-', '-', '114',
         'Your local pool - smallest by a wide margin.'],
    ]
    s.append(datatable(
        ['Market', 'MY', 'Avg list price', 'Avg miles', 'Listings', 'Read'],
        [[Paragraph(m[0], S['cell'])] + [Paragraph(x, S['cell']) for x in m[1:]] for m in mkt],
        [1.15 * inch, 0.46 * inch, 1.02 * inch, 0.62 * inch, 0.60 * inch, fw - 3.85 * inch],
        aligns=[('ALIGN', (1, 1), (4, -1), 'CENTER')]))
    s.append(Spacer(1, 8))
    s.append(callout(
        'The counterintuitive finding',
        'California is normally the expensive place to buy anything, and Texas the cheap one. '
        'For Wranglers it is the other way round. California statewide averages <b>$16,889</b> '
        'for a 2015 against Dallas at <b>$18,370</b> - a spread of roughly $1,500 in '
        'California\'s favour, on top of five times the inventory. Texas Wrangler prices are '
        'held up by exactly the demand you would expect in a truck state. '
        '<b>If you extend in only one direction, extend to California.</b>',
        accent=GREEN, bg=colors.HexColor('#eaf1ea')))

    s.append(P('3.3  The corrosion argument, calibrated', 'h2'))
    s.append(P(
        'The standard advice - "buy a southern truck, avoid the rust" - is aimed at buyers in '
        'the Rust Belt, where roads are treated with rock salt. You are not one of them, and '
        'the advice is weaker than it looks in your case.', 'body'))
    s.append(bullets([
        '<b>Colorado does not use rock salt.</b> It uses liquid magnesium chloride. That is '
        'still a salt and Section 9.1 does not retract a word of what it says about it - it is '
        'hygroscopic, it holds moisture against metal, and it attacks aluminium, magnesium and '
        'paint finishes. But it is <b>less corrosive than sodium chloride</b>, and Colorado\'s '
        'climate is dry.',
        '<b>So a Colorado Wrangler is not a Michigan Wrangler.</b> The gap between a Colorado '
        'car and a California car is real but modest. The gap between a Colorado car and an '
        'Ohio car is enormous. Do not price the first as though it were the second.',
        '<b>The genuinely rust-free zones are Arizona, central and southern New Mexico, and '
        'West Texas</b> - dry, and largely untreated. Coastal and East Texas is humid, and '
        'Houston adds salt air and flooding. A Houston Jeep is not automatically a dry Jeep.',
    ]))
    s.append(P(
        '<b>Practical conclusion:</b> let corrosion break a tie between two otherwise equal '
        'cars. Do not let it justify a $900 transport bill on its own when the Colorado '
        'alternative is inspectable in person. What corrosion <i>should</i> do is push you '
        'hard toward a TJ from California over a TJ from anywhere else, because Section 6.1 '
        'establishes that frame rot on a TJ is a structural write-off rather than a repair.',
        'body'))

    s.append(P('3.4  Texas: the flood problem', 'h2'))
    s.append(P(
        'Extending to Texas swaps one regional hazard for another, and the Texas one is worse.',
        'body'))
    flood = [
        ['Scale', 'Texas is one of the top three states nationally for flooded vehicles, '
                  'alongside Florida and Kentucky. Roughly <b>482,000 water-damaged cars '
                  'returned to the road in 2025</b>; tropical storms between June and August '
                  '2025 alone damaged 45,000. Hurricanes Harvey and Irma together damaged over '
                  '<b>637,000 vehicles</b>.'],
        ['The law', 'Texas requires the words <b>"Flood Damage"</b> on the title, and failing '
                    'to disclose damage to a buyer may violate the Texas Deceptive Trade '
                    'Practices Act.'],
        ['The gap', 'If the owner had no comprehensive cover, or the repair bill fell below the '
                    'threshold, <b>the vehicle may never be branded at all</b>. Uninsured flood '
                    'cars are cleaned up and sold with no documentary trace. This is structurally '
                    'the same trap as Colorado hail (Section 9.2) - and it is why a clean title '
                    'is evidence of very little.'],
        ['The defence', 'Run <b>NMVTIS</b>. It is the federal title database that states report '
                        'into and is queried before a state issues a new title, which makes a '
                        'flood brand far harder to wash out than it is from a commercial history '
                        'report. Then inspect physically for it - see Section 11.1.'],
    ]
    s.append(datatable(
        ['', ''],
        [[Paragraph('<b>%s</b>' % a, S['cell']), Paragraph(b, S['cell'])] for a, b in flood],
        [0.82 * inch, fw - 0.82 * inch]))
    s.append(Spacer(1, 8))
    s.append(P(
        '<b>Practical conclusion:</b> prefer <b>Dallas, Fort Worth, Austin and West Texas</b> '
        'over Houston and the Gulf Coast. If you do look at a Houston car, NMVTIS is not '
        'optional and neither is a physical flood inspection.', 'body'))

    s.append(P('3.5  California: what to watch instead', 'h2'))
    s.append(bullets([
        '<b>Smog is not your problem.</b> California emissions rules bind people registering '
        '<i>in</i> California. You are registering in Colorado. A California car carries '
        'CARB-specification emissions equipment, which is a superset of federal - it is legal '
        'in Colorado and will not obstruct you.',
        '<b>Colorado emissions still apply.</b> ZIP 80127 sits in Jefferson County, inside the '
        'Denver-Boulder emissions programme area, so the vehicle must pass a Colorado emissions '
        'test before you can register it regardless of where you bought it.',
        '<b>Sun damage replaces rust as the wear signature.</b> California Wranglers bake. '
        'Inspect the soft top and its windows for hazing and splits, the dashboard for cracking, '
        'the paint and clear coat for chalking, and every rubber seal for perishing. A hardtop '
        'that has spent fifteen years in the Inland Empire is a different object from one that '
        'lived in a Denver garage.',
        '<b>Modification density is high.</b> California and Colorado are both heavy off-road '
        'markets. Section 11.1 covers what a badly executed lift does; apply it with extra care '
        'to anything advertised as "built".',
    ]))

    s.append(P('3.6  Landed cost: what the car actually costs you', 'h2'))
    s.append(P(
        'An out-of-state car is never its sticker price. Two ways to get it home:', 'body'))
    land = [
        ['<b>Ship it</b> (open carrier)', 'CA to CO: <b>$690 - $1,077</b> Los Angeles to Denver; '
         'broader range $400 - $1,100.<br/>TX to CO: <b>$700 - $1,000</b>, typically 2-3 days.',
         'Enclosed transport roughly doubles it (CA $700-$1,400; TX $1,225-$1,750) and is not '
         'warranted for a used Wrangler. SUVs price above sedans, and a lifted Jeep on oversized '
         'tyres may attract a surcharge - declare the real height and width when quoting.'],
        ['<b>Fly and drive</b>', 'Roughly <b>$400 - $700</b> all-in: one-way fare, fuel, and a '
         'night on the road.',
         'Los Angeles to Denver is about 1,020 miles; Houston to Denver about 1,030. Slower and '
         'more effort - but you inspect the car yourself before money moves, and you get a '
         '1,000-mile shakedown that will surface a death wobble, an overheat, an oil habit or a '
         'transmission fault long before a transporter would. <b>Usually the better choice on '
         'both cost and diligence.</b>'],
    ]
    s.append(datatable(
        ['Method', 'Cost', 'Assessment'],
        [[Paragraph(a, S['cell']), Paragraph(b, S['cell']), Paragraph(c, S['cell'])]
         for a, b, c in land],
        [1.15 * inch, 1.55 * inch, fw - 2.7 * inch]))
    s.append(Spacer(1, 8))
    s.append(P(
        'Add the transport figure to the asking price before you compare anything against a '
        'Colorado car. A $15,500 California Wrangler shipped to Denver is a <b>$16,400</b> '
        'Wrangler, and that is before a remote inspection. Against the California price '
        'advantage of roughly $1,500 identified in 3.2, shipping consumes most of the margin - '
        'which is precisely why flying out to collect it is the stronger play.', 'body'))

    s.append(P('3.7  Registering an out-of-state purchase in Colorado', 'h2'))
    reg = [
        ['VIN verification', 'Form <b>DR 2698</b> is required for any vehicle brought in from '
         'out of state. The inspection must be performed by a law enforcement officer, a '
         'licensed Colorado dealer, or a licensed Colorado emissions testing station agent.'],
        ['Emissions test', 'Required - Jefferson County is inside the Denver-Boulder programme '
         'area. Fully electric vehicles are exempt statewide; nothing in this report is one.'],
        ['At the county office', 'Secure and verifiable ID; <b>two</b> proofs of address; the '
         'out-of-state title signed by the seller; the completed DR 2698; and proof of valid '
         'Colorado liability insurance.'],
        ['Sales tax', 'Paid to Colorado at your local rate, not to the state you bought in. '
         'Budget it against the purchase price, not the advertised price.'],
        ['Odometer disclosure', 'On a remote sale this requires <b>original signatures</b> from '
         'both parties. A standard power of attorney is not accepted for it - only a Secure '
         'Power of Attorney. Get this right or the title transfer stalls.'],
    ]
    s.append(datatable(
        ['Requirement', 'Detail'],
        [[Paragraph('<b>%s</b>' % a, S['cell']), Paragraph(b, S['cell'])] for a, b in reg],
        [1.32 * inch, fw - 1.32 * inch]))
    s.append(Spacer(1, 8))

    s.append(P('3.8  Buying remotely without getting burned', 'h2'))
    s.append(P(
        'Distance removes almost every natural check on a bad transaction. These are '
        'non-negotiable:', 'body'))
    s.append(bullets([
        '<b>Independent PPI first, money second.</b> A shop <i>you</i> chose and <i>you</i> '
        'paid, near the seller. Never the seller\'s shop, never the selling dealer\'s service '
        'department. Give them the checklist in Section 11.1 and ask for photographs of all '
        'three VIN plates - dash, door jamb and frame stamping.',
        '<b>Live video, not a recording.</b> Ask for a walkaround on a live call. Have them '
        'start the engine <i>cold</i> in front of you, pan the undercarriage, and hold the '
        'camera on the VIN plates and the odometer. A seller who will only send edited clips '
        'is telling you something.',
        '<b>Title in the seller\'s name, matching their ID.</b> Photographed, before you '
        'travel. A mismatch means an unlicensed dealer and no consumer protection.',
        '<b>Never wire funds to an individual.</b> Bank-to-bank at closing, or a genuine escrow '
        'service you selected. Any request for gift cards, cryptocurrency, or a "shipping '
        'company escrow" the seller recommends is a scam without exception.',
        '<b>Vet the transporter.</b> FMCSA-licensed, insured and bonded. Insist on a signed '
        'Bill of Lading with condition notes and photographs at <i>both</i> pickup and '
        'delivery - it is your only recourse for transit damage.',
    ]))

    s.append(callout(
        'Section verdict',
        '<b>California is the extension worth making.</b> Five times the inventory of the '
        'target years, the lowest average price of any market surveyed, a dry climate, and none '
        'of the flood exposure. Search it as your primary market for a 2015-2017. '
        '<br/><br/>'
        '<b>Texas is conditional.</b> The supply is enormous but prices are the highest of the '
        'three states and the flood-title risk is the worst. Go there for a specific car that '
        'justifies it, prefer Dallas / Fort Worth / Austin over Houston, and treat NMVTIS as '
        'mandatory. '
        '<br/><br/>'
        '<b>Colorado stays the default for anything you can drive to.</b> Once you add $700-'
        '$1,000 of transport and a remote inspection, the out-of-state price advantage largely '
        'evaporates - and you lose the ability to put your own hands on the car. The honest '
        'ranking is: <b>a clean local car you inspected yourself beats a cheaper remote one</b>, '
        'and the remote markets are there to give you options when the local pool of 114 does '
        'not contain what you want.',
        accent=OLIVE, bg=SAND))
    return s


# ---------------------------------------------------------- 4. candidates
def section_candidates(fw):
    s = [CondPageBreak(3.1 * inch), P('4.  VIN-authenticated candidate vehicles', 'h1'), rule()]
    s.append(P(
        'Twelve complete VINs were recovered across the three markets - four in California and '
        'Texas, eight in Colorado. <b>All twelve pass the check digit</b>, and for every one of '
        'the four out-of-state cars the claimed model year matches the year encoded in VIN '
        'position 10. The left half of this table is <b>VERIFIED</b> - computed from the VIN '
        'itself, offline. The right half is <b>REPORTED</b> - what a search snippet claimed, '
        'which Section 1.3 shows is unreliable.', 'body'))

    rows = []
    for c in CANDIDATES:
        d = decode(c['vin'])
        want, err = check_digit(c['vin'])
        assert not err and want == c['vin'][8], 'VIN failed at build time: %s' % c['vin']
        verdict_col = {'GO': GREEN, 'CHECK': AMBER, 'SKIP': RUST}[c['verdict']]
        region_col = {'CA': OLIVE, 'TX': RUST, 'CO': GREY}[c['region']]
        rows.append([
            Paragraph(c['vin'], S['mono']),
            tag('PASS', GREEN),
            Paragraph('<b>%s</b>' % d['year'], S['cell']),
            tag(c['region'], region_col),
            Paragraph(c['reported'], S['cell']),
            Paragraph('<font color="%s"><b>%s</b></font><br/>%s'
                      % (hx(verdict_col), c['verdict'], c['note']), S['cell']),
        ])
    s.append(datatable(
        ['VIN', 'Chk', 'Yr', 'Mkt', 'Reported listing data (UNVERIFIED)',
         'Assessment'],
        rows,
        [1.42 * inch, 0.52 * inch, 0.42 * inch, 0.42 * inch, 1.68 * inch,
         fw - 4.46 * inch]))
    s.append(Spacer(1, 9))

    s.append(P('4.1  Partial VINs from dealer stock numbers', 'h2'))
    s.append(P(
        'Franchise dealers almost always set the advertised stock number to the '
        '<b>last eight characters of the VIN</b>. That convention leaks the model year and '
        'assembly plant even when the full VIN is not indexed. Three useful leads:', 'body'))
    stock = [
        ['GL246888', '<b>G = 2016</b>, L = Toledo South',
         '<b>AutoNation Chrysler Jeep Broadway, 5445 S Broadway, Littleton CO 80121.</b> A 2016 '
         'Wrangler at a franchise Jeep store inside your radius - squarely in the best-rated '
         'JK years and, per Section 2.1, plausibly inside $18,000. <b>The single most '
         'promising lead in this report.</b> Get the full VIN and the price.'],
        ['AL126983', 'A = 2010, L = Toledo South',
         'AutoNation CDJR Southwest, Littleton. Reported as a 2010 Wrangler; a 2010 Unlimited '
         'Sport with 93,066 mi and service records was separately described at this dealer.'],
        ['DL645044', 'D = 2013, L = Toledo South',
         'Reported as a 2013 Wrangler Sahara, "Rock Lobster" orange, 73,495 mi. A 2013 is a '
         '3.6L Pentastar car - see Section 6.3 before you get attached to it.'],
    ]
    s.append(datatable(
        ['Stock #', 'Decodes to', 'Lead'],
        [[Paragraph(a, S['mono']), Paragraph(b, S['cell']), Paragraph(c, S['cell'])]
         for a, b, c in stock],
        [0.78 * inch, 1.35 * inch, fw - 2.13 * inch]))
    s.append(Spacer(1, 9))

    s.append(callout(
        'Shortlist: where to spend your first five phone calls',
        [P('<b>1. 1C4BJWDG6FL569653</b> - 2015 Unlimited Sport, 81,024 mi, La Crescenta CA. '
           'The lowest mileage of any in-target candidate in this report, in the exact model '
           'year and trim Section 7 identifies as the target, from the cheapest and deepest '
           'market. No price was indexed. <i>Ask: price, and whether they will hold it for an '
           'independent PPI.</i>', 'callb'),
         Spacer(1, 4),
         P('<b>2. Stock GL246888</b> - 2016 Wrangler at AutoNation Chrysler Jeep Broadway, '
           'Littleton. Not a full VIN, but the strongest lead here: a best-rated model year, '
           'the good engine, at a franchise Jeep store eight miles from 80127. Only the raised '
           'ceiling puts this in play. <i>Ask: the full VIN, the price, and the mileage.</i>',
           'callb'),
         Spacer(1, 4),
         P('<b>3. 1C4BJWEG6EL123953</b> - 2014 Unlimited four-door, reported 122,634 mi, 3.6L, '
           'Englewood. The first model year clear of the Pentastar cylinder-head defect. The '
           'mileage is high and a 2014 Unlimited Sport books at $12,200-$14,450 private-party, '
           'so anything near $18,000 is overpriced. <i>Ask: price, and service history for the '
           'last 30,000 miles.</i>', 'callb'),
         Spacer(1, 4),
         P('<b>4. 1C4AJWAG1CL117007</b> - 2012 two-door, reported 54,371 mi, 3.6L manual, '
           'Englewood. By far the lowest mileage recovered. Worth a call purely for that, but '
           '2012 is a Pentastar cylinder-head year and the raised budget means you no longer '
           '<i>have</i> to accept that risk. <i>Ask: price, and whether the left cylinder head '
           'has ever been replaced.</i>', 'callb'),
         Spacer(1, 4),
         P('<b>5. 1J4AA2D1XAL173194</b> - 2010 two-door, reported $10,700 / 111,535 mi, '
           'Lakewood. No longer the safe compromise it was at a $15,000 ceiling - now the '
           'deliberate value play, leaving roughly $7,000 of headroom for maintenance. '
           '<i>Ask: oil consumption over the last 5,000 miles.</i>', 'callb')],
        accent=OLIVE, bg=SAND))

    s.append(P('4.2  Vehicles to drop now', 'h2'))
    s.append(bullets([
        '<b>1C4HJXDN9LW170163</b> - genuinely a 2020 JL Willys, but reported at $23,500. Even '
        'at the raised ceiling that is 31% over. Out of scope, and the gap is too wide to '
        'negotiate away.',
        '<b>1J4FA49S31P347487</b> (2001 TJ) and <b>1J4FA49S46P788486</b> (2006 TJ) - real '
        'vehicles, and a 2006 TJ is a credible buy at this budget. But both were indexed '
        'against Colorado Springs listings, roughly 60-70 miles from 80127. Outside your '
        '20-mile radius. Included here only because they prove the search layer was scrambling '
        'years, which is the finding that shapes this whole report.',
        '<b>1J4BA3H13BL589979</b> - a real 2011 Unlimited, but the only price attached to it '
        'in the index ($23,991) belonged to a different, newer vehicle. Nothing reliable is '
        'known about what this one costs. Worth a lookup, not a drive.',
    ]))
    return s


# ---------------------------------------------------------- 4. VIN reference
def section_vin(fw):
    s = [CondPageBreak(3.1 * inch), P('5.  Jeep Wrangler VIN decoding reference', 'h1'), rule()]
    s.append(P(
        'You will encounter VINs this report has never seen. This section makes you '
        'self-sufficient: read any Wrangler VIN off a windshield or a door jamb and know the '
        'year, the plant, and whether the seller is telling you the truth about the car.',
        'body'))

    s.append(P('5.1  Position map', 'h2'))
    pos = [
        ['1-3', 'WMI - World Manufacturer Identifier',
         '<b>1J4</b> = Jeep multipurpose vehicle, US-built (through MY2011). '
         '<b>1C4</b> = FCA US LLC (MY2012 onward). A "1J4" on a car advertised as 2012 or '
         'newer is an immediate red flag.', 'VERIFIED'],
        ['4', 'GVWR / restraint-system class',
         'Encodes gross weight rating together with airbag configuration. Varies by year; '
         'confirm against the federal decoder rather than trusting a forum chart.', 'PARTIAL'],
        ['5', 'Vehicle line',
         'Distinguishes the Wrangler line and drive configuration (4x4, left- vs right-hand '
         'drive).', 'PARTIAL'],
        ['6', 'Series / trim',
         'Sport vs Sahara vs Rubicon. On JK Unlimiteds the observed pattern is '
         '<b>3</b>=Sport, <b>5</b>=Sahara, <b>6</b>=Rubicon.', 'PARTIAL'],
        ['7', 'Body style', 'Two-door vs four-door Unlimited.', 'PARTIAL'],
        ['8', 'Engine code',
         'On the JK this separates the 3.8L V6, the 3.6L Pentastar V6 and the 2.8L CRD diesel '
         '(never sold in the US).', 'PARTIAL'],
        ['9', 'Check digit',
         'Computed from all sixteen other characters. This is the anti-fraud position and the '
         'one you can verify yourself with no internet access at all.', 'VERIFIED'],
        ['10', 'Model year',
         'Single character, full table in 4.2. Cannot be faked without breaking the check '
         'digit.', 'VERIFIED'],
        ['11', 'Assembly plant',
         'Every Wrangler in this report was built in Toledo, Ohio - <b>L</b> = Toledo South / '
         'Supplier Park, <b>P</b> = Toledo North, <b>W</b> = Toledo Assembly.', 'VERIFIED'],
        ['12-17', 'Sequential production serial',
         'Build order. Useful only for spotting two "identical" listings that are secretly the '
         'same car.', 'VERIFIED'],
    ]
    s.append(datatable(
        ['Pos', 'Field', 'What it tells you', 'Confidence'],
        [[Paragraph('<b>%s</b>' % p[0], S['cell']), Paragraph(p[1], S['cell']),
          Paragraph(p[2], S['cell']),
          tag(p[3], GREEN if p[3] == 'VERIFIED' else AMBER)] for p in pos],
        [0.42 * inch, 1.45 * inch, fw - 2.72 * inch, 0.85 * inch]))
    s.append(Spacer(1, 8))
    s.append(callout(
        'On positions 4 through 8',
        'These are graded PARTIAL deliberately. Chrysler revised its VDS encoding several times '
        'across the TJ, JK and JL runs, and the enthusiast-forum charts that circulate online '
        'contradict each other on the details. The patterns above held for every VIN examined '
        'here, but do not bet a purchase on them. The free federal decoder at '
        '<b>vpic.nhtsa.dot.gov</b> returns the manufacturer-submitted trim, engine displacement '
        'and body class for any VIN and is authoritative. It was blocked from this environment; '
        'it will not be blocked from yours.',
        accent=AMBER, bg=colors.HexColor('#f7f1de')))

    s.append(P('5.2  Model-year codes (position 10)', 'h2'))
    yr = [['V', '1997'], ['W', '1998'], ['X', '1999'], ['Y', '2000'], ['1', '2001'],
          ['2', '2002'], ['3', '2003'], ['4', '2004'], ['5', '2005'], ['6', '2006'],
          ['7', '2007'], ['8', '2008'], ['9', '2009'], ['A', '2010'], ['B', '2011'],
          ['C', '2012'], ['D', '2013'], ['E', '2014'], ['F', '2015'], ['G', '2016'],
          ['H', '2017'], ['J', '2018'], ['K', '2019'], ['L', '2020'], ['M', '2021'],
          ['N', '2022'], ['P', '2023'], ['R', '2024'], ['S', '2025'], ['T', '2026']]
    ncol = 6
    grid, row = [], []
    for code, year in yr:
        row.append(Paragraph('<font face="Courier-Bold">%s</font>  %s' % (code, year), S['cell']))
        if len(row) == ncol:
            grid.append(row)
            row = []
    if row:
        row += [''] * (ncol - len(row))
        grid.append(row)
    t = Table(grid, colWidths=[fw / ncol] * ncol)
    t.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.4, RULE),
        ('BACKGROUND', (0, 0), (-1, -1), SAND),
        ('TOPPADDING', (0, 0), (-1, -1), 4), ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
    ]))
    s.append(t)
    s.append(Spacer(1, 5))
    s.append(P(
        'The letters <b>I</b>, <b>O</b>, <b>Q</b>, <b>U</b> and <b>Z</b> are never used as '
        'year codes, and I, O and Q never appear anywhere in a VIN - they are too easily '
        'confused with 1 and 0. A "VIN" containing any of them is not a VIN.', 'small'))

    s.append(P('5.3  Running the check digit by hand', 'h2'))
    s.append(P(
        'Transliterate every character to a number, multiply each by its positional weight, '
        'sum the products, divide by 11, and keep the remainder. A remainder of 10 is written '
        'as the letter X. That value must equal position 9.', 'body'))
    trans = [
        ['Letter values', 'A=1  B=2  C=3  D=4  E=5  F=6  G=7  H=8&nbsp;&nbsp;|&nbsp;&nbsp;'
                          'J=1  K=2  L=3  M=4  N=5  P=7  R=9&nbsp;&nbsp;|&nbsp;&nbsp;'
                          'S=2  T=3  U=4  V=5  W=6  X=7  Y=8  Z=9'],
        ['Digit values', 'Digits 0-9 take their own value.'],
        ['Weights (pos 1-17)', '8  7  6  5  4  3  2  10  <b>0</b>  9  8  7  6  5  4  3  2'],
    ]
    tt = Table([[Paragraph('<b>%s</b>' % a, S['cell']), Paragraph(b, S['monos'])]
                for a, b in trans], colWidths=[1.25 * inch, fw - 1.25 * inch])
    tt.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('GRID', (0, 0), (-1, -1), 0.4, RULE),
        ('BACKGROUND', (0, 0), (0, -1), SAND),
        ('TOPPADDING', (0, 0), (-1, -1), 5), ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 6), ('RIGHTPADDING', (0, 0), (-1, -1), 6),
    ]))
    s.append(tt)
    s.append(Spacer(1, 5))
    s.append(P(
        'Position 9 carries weight 0, so the check digit never influences its own calculation. '
        'Worked example on the 2010 two-door from Section 4: '
        '<b>1J4AA2D1XAL173194</b> sums to a remainder of 10, which is written <b>X</b> - and '
        'X is exactly what sits in position 9. It passes.', 'body'))

    s.append(P('5.4  Reproducible validator', 'h2'))
    s.append(P(
        'The complete implementation used to authenticate every VIN in this report ships '
        'alongside it as <b>vin_tools.py</b>. Run it against any VIN a seller gives you:',
        'body'))
    code = Table([[Paragraph(
        '$ python3 vin_tools.py 1J4AA2D1XAL173194<br/>'
        '<br/>'
        'VIN&nbsp;&nbsp;&nbsp;: 1J4AA2D1XAL173194<br/>'
        "CHECK&nbsp;: position 9 is 'X', algorithm requires 'X'  -&gt;  PASS<br/>"
        'WMI&nbsp;&nbsp;&nbsp;: 1J4 = Chrysler Group LLC / Jeep, USA-built<br/>'
        "YEAR&nbsp;&nbsp;: pos10 'A' = 2010<br/>"
        "PLANT&nbsp;: pos11 'L' = Toledo South / Supplier Park, Toledo OH<br/>"
        'SERIAL: 173194', S['monos'])]], colWidths=[fw])
    code.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f5f4ee')),
        ('BOX', (0, 0), (-1, -1), 0.5, RULE),
        ('LEFTPADDING', (0, 0), (-1, -1), 10), ('RIGHTPADDING', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 8), ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    s.append(code)
    s.append(Spacer(1, 6))
    s.append(callout(
        'What a passing check digit does NOT mean',
        'It proves the number is well-formed and almost certainly factory-issued. It does not '
        'prove the VIN belongs to the car in front of you. VIN swapping on stolen vehicles is '
        'real. On any car you are serious about, physically compare <b>three</b> plates - the '
        'dashboard plate visible through the windshield, the driver door-jamb sticker, and the '
        'frame stamping - and confirm all three match each other and match the title. '
        'Mismatched, missing, scratched or re-riveted plates end the conversation.',
        accent=RUST))
    return s


# ---------------------------------------------------------- 5. generations
def section_generations(fw):
    s = [CondPageBreak(3.1 * inch), P('6.  Generation deep-dive', 'h1'), rule()]

    s.append(P('6.1  TJ, 1997-2006 - the 4.0L is immortal, the frame is not', 'h2'))
    s.append(P(
        'The 4.0-litre AMC-derived inline six is the most durable engine ever fitted to a '
        'Wrangler. Simple, under-stressed, cheap to work on, and routinely seen past 250,000 '
        'miles. If drivetrain longevity is your priority, nothing else at this price competes.',
        'body'))
    s.append(P('Known weak points:', 'h3'))
    s.append(bullets([
        '<b>Oil leaks, plural.</b> The 4.0L weeps from the timing chain cover, rear main seal, '
        'oil pan gasket and valve cover. Expect at least one. Budget for it; a rear main seal '
        'is a transmission-out job.',
        '<b>Oil Pump Drive Assembly (OPDA).</b> Specific to 2005-2006 TJs with the 4.0L. Known '
        'failure point - ask directly whether it has been replaced.',
        '<b>Frame rot. This is the deal-breaker.</b> TJ frames corrode <i>from the inside out</i>: '
        'water enters through openings in the upper frame rails, pools in the lower sections '
        'where there are no drain holes, and eats outward. By the time you can see it, it is '
        'advanced. Concentrated under the central skid plate, at the rear control-arm mounts, '
        'around the body mounts, and near the fuel tank and rear bumper mounts.',
    ]))
    s.append(callout(
        'The five-minute TJ test that saves you $8,000',
        'Get under it with a bright flashlight and a screwdriver. Tap - do not stab - the frame '
        'rails under the central skid plate and at the rear control-arm mounts. Sound metal '
        'rings. Rotten metal thuds, flexes, or gives. If the screwdriver goes through, walk '
        'away and do not negotiate. A rotted TJ frame is a structural write-off; replacement '
        'runs to five figures and exceeds the value of every vehicle in your budget. '
        'A Colorado TJ that has seen twenty winters of magnesium chloride is guilty until '
        'proven innocent.',
        accent=RUST))

    s.append(P('6.2  JK with the 3.8L V6, 2007-2011 - comfortable, gutless, thirsty', 'h2'))
    s.append(P(
        'The JK brought coil springs, a proper interior, and crucially the four-door '
        'Unlimited. The engine it launched with was a minivan V6 pressed into service: 202 '
        'horsepower hauling a heavy, brick-shaped 4x4. It is adequate, not good, and at '
        'Colorado altitude it feels worse - naturally aspirated engines lose roughly three '
        'percent of their output per thousand feet, so a 202 hp engine is making closer to '
        '170 hp in Denver and less on a mountain pass.', 'body'))
    s.append(P('Known weak points:', 'h3'))
    s.append(bullets([
        '<b>Oil consumption after 100,000 miles.</b> Traced to low-tension piston rings '
        'combined with the thin 5W-20 oil specified largely for fuel-economy certification. '
        'Chrysler\'s official position was that <b>one quart per 750 miles</b> is within '
        'normal limits and warranted no repair. That is roughly a quart a fortnight for an '
        'ordinary commuter. Ask every 3.8L seller how often they top up, and watch their face.',
        '<b>TIPM failure (Totally Integrated Power Module).</b> Affects 2007-2012. The TIPM is '
        'the central electrical brain; when it degrades it produces genuinely bizarre symptoms '
        '- fuel pump cutting out, horn sounding by itself, wipers running unbidden, no-start '
        'conditions. Replacement typically $400-$800. A test drive will not reveal an '
        'intermittent TIPM.',
        '<b>Death wobble.</b> See 5.4.',
    ]))

    s.append(P('6.3  JK with the 3.6L Pentastar, 2012 onward - the good engine, the bad years',
               'h2'))
    s.append(P(
        'The 2012 Pentastar swap took the JK from 202 hp to 285 hp and transformed the '
        'vehicle. It is unambiguously the engine to want. The complication is that 2012 and '
        '2013 are also the two worst-rated JK model years, and early Pentastars had a '
        'specific, expensive defect.', 'body'))
    s.append(P('The left cylinder-head failure:', 'h3'))
    s.append(bullets([
        'Early left-bank heads suffered valve-seat erosion and valve-guide wear. In the worst '
        'cases an exhaust valve dropped into the cylinder and destroyed the piston.',
        'The signature symptom is a persistent <b>cylinder 2 misfire</b>. If a seller mentions '
        'a rough idle, a check-engine light, or a recent misfire code on a 2011-2013 Pentastar, '
        'that is the tell.',
        'Chrysler put the exposed population at roughly <b>7,500 engines</b> and revised the '
        'head design in <b>August 2012</b>. The corrected part number is <b>RL141353AC</b>.',
        'Chrysler extended coverage on the left cylinder head from 5 years / 100,000 miles to '
        '<b>10 years / 150,000 miles</b> for a defined segment of 2011-2013 Pentastar vehicles. '
        'On a 2012 or 2013 car in 2026, that extension has now expired on time even if mileage '
        'is low - so the repair is yours. Confirm the head was either replaced under the '
        'extension or is a post-August-2012 build.',
    ]))
    s.append(callout(
        'The question that decides a 2012 or 2013 purchase',
        'Call any Chrysler, Dodge, Jeep or Ram dealer service department with the VIN and ask '
        'them to pull the <b>factory warranty and campaign history</b>. It is free, it takes '
        'them two minutes, and it tells you whether the left cylinder head was ever replaced. '
        'A 2012 with a documented head replacement is arguably <i>safer</i> than one without - '
        'the known defect has already been bought out at someone else\'s expense.',
        accent=OLIVE, bg=SAND))

    s.append(P('6.4  Death wobble - what it actually is', 'h2'))
    s.append(P(
        'Death wobble affects the entire JK run, 2007 through 2018. It presents as violent, '
        'self-sustaining oscillation of the front axle, typically triggered between 45 and 65 '
        'mph by a bump, expansion joint or road seam. It is frightening and it does not '
        'settle until you slow down substantially.', 'body'))
    s.append(P(
        'It is widely misdescribed as a single defective part. It is not. It is the '
        'characteristic behaviour of a solid front axle on a short wheelbase once <i>any</i> '
        'link in the steering and suspension chain develops play - worn track bar or track bar '
        'bushings, loose ball joints, tired wheel bearings, failing steering damper, worn '
        'anti-roll bar drop links, or simply wheels out of balance. Lifted Jeeps and Jeeps on '
        'oversized tyres are markedly more prone, which matters in Colorado where a large '
        'share of the used stock is modified.', 'body'))
    s.append(P(
        '<b>How to test for it:</b> get the vehicle to 50-60 mph on a road with known seams or '
        'patches and drive over them deliberately. A seller who steers around every bump on '
        'the test route is managing your impressions. Insist on the route you choose.', 'body'))

    s.append(P('6.5  Overall generation reliability', 'h2'))
    s.append(P(
        'Aggregated owner data puts the JK generation at roughly <b>2.8 out of 5</b> for '
        'reliability with an average annual repair cost near <b>$987</b>. Frame that number '
        'properly: it is well above the mainstream-SUV average, and it is the ongoing cost of '
        'entry, not a worst case. Set aside $1,000 a year for maintenance on top of the '
        'purchase price and you will not be ambushed.', 'body'))
    return s


# ---------------------------------------------------------- 6. year risk
def section_yearrisk(fw):
    s = [CondPageBreak(3.1 * inch), P('7.  Model-year risk matrix', 'h1'), rule()]
    s.append(P(
        'Ranked for a buyer working in the $6,000-$18,000 band. At a $15,000 ceiling this '
        'matrix was an exercise in damage limitation - the reachable years were largely the '
        'bad ones. At $18,000 the best rows in the table are live options, and the strategy '
        'changes from avoiding the worst to buying the best.', 'body'))

    yrs = [
        ['2007', 'JK 3.8', 'AVOID',
         'First JK year. Death wobble notably pronounced. Airbag warning lights cycling on '
         'and off. First-model-year teething throughout.', RUST],
        ['2008-2009', 'JK 3.8', 'CAUTION',
         'Teething largely resolved. Still 3.8L oil consumption and TIPM exposure. RHD models '
         'fall under the clockspring recall.', AMBER],
        ['2010-2011', 'JK 3.8', 'ACCEPTABLE',
         'Best of the 3.8L years. Engine is weak but the known faults are understood and cheap '
         'to diagnose. No longer the default pick - now the <b>value</b> pick, several thousand '
         'below your ceiling.', GREEN],
        ['2012', 'JK 3.6', 'HIGH RISK',
         'Rated the <b>worst</b> JK year: roughly ten recalls, TIPM failures, airbag faults, '
         'death wobble, and engine problems that in bad cases meant a rebuild or replacement '
         'at $4,400 or more. Also the first Pentastar year, with the early cylinder-head '
         'defect.', RUST],
        ['2013', 'JK 3.6', 'HIGH RISK',
         'Transmission failures and engine stalling are the recurring complaints. Also carries '
         'the 13V-234 transmission oil cooler tube recall.', RUST],
        ['2014', 'JK 3.6', 'GOOD',
         'Pentastar head issue resolved, most JK teething behind it. <b>Now reachable</b> - '
         'Denver average list $17,531 at an average 110,014 mi, so expect high mileage at the '
         'top of your budget.', GREEN],
        ['2015-2017', 'JK 3.6', 'BEST',
         'Consistently the highest-rated JK years, and <b>now inside budget</b>: a 2015 '
         'Unlimited Sport books at $13,190-$15,790 private-party, a 2016 Sport 2-dr at '
         '$13,270-$15,620. A clean 2016 or 2017 with the 3.6L is the safest used Wrangler you '
         'can buy. <b>This is the target.</b>', GREEN],
        ['2018', 'JK / JL', 'CAUTION',
         'JL launch year, sold alongside the run-out JK. Steering wander, reported weld '
         'defects, manual-transmission clutch problems. Above budget regardless.', AMBER],
    ]
    s.append(datatable(
        ['Year(s)', 'Gen', 'Verdict', 'Basis'],
        [[Paragraph('<b>%s</b>' % y[0], S['cell']), Paragraph(y[1], S['cell']),
          tag(y[2], y[4]), Paragraph(y[3], S['cell'])] for y in yrs],
        [0.72 * inch, 0.52 * inch, 0.97 * inch, fw - 2.21 * inch]))
    s.append(Spacer(1, 9))

    s.append(callout(
        'The recommendation, revised for an $18,000 ceiling',
        'At $15,000 there was a genuine dilemma: the better engine only came attached to the '
        'worst model years, so the advice was to take a well-kept 2010-2011 with the weak 3.8L '
        'and accept it. <b>At $18,000 that dilemma disappears.</b> '
        '<br/><br/>'
        '<b>Buy a 2015, 2016 or 2017 JK with the 3.6L.</b> These are the best-rated years of '
        'the generation, they have the good engine, they are clear of the Pentastar '
        'cylinder-head defect, and Section 2.1 shows them booking between $13,200 and $15,800 '
        'private-party - inside your ceiling with room for tax and inspection. You are no '
        'longer choosing the least-bad option; you are buying the right one.'
        '<br/><br/>'
        '<b>Two fallbacks, in order.</b> If nothing clean turns up in 2015-2017, a <b>2014</b> '
        'is the same engine and the same defect-free status, just older - but watch the '
        'mileage, because Denver 2014s average 110,014 miles. Failing that, a documented '
        '<b>2010-2011</b> at around $11,000-$12,000 is a deliberate value play that leaves '
        '$6,000-$7,000 of your budget for maintenance and a lift. '
        '<b>What you should no longer do is buy a 2012 or 2013.</b> That was a compromise '
        'forced by the old ceiling, and the extra $3,000 has bought you out of it.',
        accent=GREEN, bg=colors.HexColor('#eaf1ea')))
    return s


# ---------------------------------------------------------- 7. recalls
def section_recalls(fw):
    s = [P('8.  Recalls, warranty extensions, and the VIN checks to run', 'h1'), rule()]
    s.append(P(
        'Recalls are free to fix, permanently attached to the VIN, and never expire. An open '
        'recall on a fifteen-year-old Jeep is still the manufacturer\'s obligation. This is '
        'the single highest-value free check available to you.', 'body'))

    rc = [
        ['Airbag clockspring', '2008-2012 right-hand-drive Wranglers built Feb 2007 - Oct 2011',
         'A broken circuit in the clockspring can prevent the driver airbag deploying. Remedy: '
         'clockspring replaced and a steering-wheel dust shield added, free of charge. RHD '
         'units are rare but were sold to rural postal carriers - and Colorado has them.'],
        ['Transmission oil cooler tube', 'NHTSA 13V-234, automatic-transmission Wranglers',
         'The transmission oil cooler tube can contact the power-steering return tube, wear '
         'through, and leak. A transmission fluid leak onto hot exhaust is a fire path.'],
        ['Automatic transmission skid plate', '2010 models, recall issued May 2012',
         'The skid plate sits close to the catalytic converter and can trap combustible debris.'],
        ['Pentastar left cylinder head', '2011-2013 3.6L (warranty extension, not a recall)',
         'Coverage extended from 5 yr / 100,000 mi to 10 yr / 150,000 mi on the left cylinder '
         'head for a defined vehicle segment. Now time-expired on all affected years - but the '
         'service record of whether it was replaced is the thing you want.'],
    ]
    s.append(datatable(
        ['Campaign', 'Applies to', 'Why it matters'],
        [[Paragraph('<b>%s</b>' % r[0], S['cell']), Paragraph(r[1], S['cell']),
          Paragraph(r[2], S['cell'])] for r in rc],
        [1.28 * inch, 1.55 * inch, fw - 2.83 * inch]))
    s.append(Spacer(1, 9))

    s.append(P('8.1  Free VIN checks to run on every serious candidate', 'h2'))
    checks = [
        ['nhtsa.gov/recalls', 'Open, unrepaired recalls by VIN', 'Free', '1 min'],
        ['vpic.nhtsa.dot.gov', 'Manufacturer-submitted trim, engine, body class, plant',
         'Free', '1 min'],
        ['vehiclehistory.bja.ojp.gov (NMVTIS)',
         'Federal title-brand database - salvage, junk, flood, insurance total loss. Harder to '
         'launder than a private history report.', '$5-$15', '5 min'],
        ['CDJR dealer service dept. (phone)',
         'Factory warranty and campaign history: what was actually repaired, when, and whether '
         'the Pentastar head was replaced', 'Free', '5 min'],
        ['CARFAX or AutoCheck',
         'Accident reports, ownership count, odometer readings over time, service events',
         '$25-$45', '2 min'],
        ['Colorado DMV title check', 'Current brand status on the Colorado title itself',
         'Varies', '10 min'],
    ]
    s.append(datatable(
        ['Where', 'What you learn', 'Cost', 'Time'],
        checks, [1.75 * inch, fw - 3.55 * inch, 0.85 * inch, 0.7 * inch],
        aligns=[('ALIGN', (2, 1), (-1, -1), 'CENTER')]))
    s.append(Spacer(1, 8))
    s.append(callout(
        'Do not rely on the dealer\'s free CARFAX alone',
        'A dealer-supplied history report is real, but it is the report <i>they</i> chose to '
        'show you. CARFAX and AutoCheck draw on overlapping but different data - an accident '
        'reported to one may be absent from the other. On a vehicle you are ready to buy, '
        'the roughly $30 for your own independent report is the cheapest insurance in this '
        'entire process. Buy the one the dealer did not hand you.',
        accent=OLIVE, bg=SAND))
    return s


# ---------------------------------------------------------- 8. colorado
def section_colorado(fw):
    s = [CondPageBreak(3.1 * inch), P('9.  Regional risk: Colorado, California, Texas', 'h1'), rule()]
    s.append(P(
        'Every market carries a signature hazard, and it is different in each. Colorado cars '
        'corrode from de-icer and hide hail behind clean titles; Texas cars hide flood damage; '
        'California cars are cooked by sun rather than eaten by salt. Match the inspection to '
        'the car\'s history, not to a generic checklist.', 'body'))

    s.append(P('9.1  Colorado: magnesium chloride', 'h2'))
    s.append(P(
        'Colorado\'s primary winter de-icer is liquid magnesium chloride rather than rock '
        'salt. It is more effective at low temperatures and it is considerably harder on '
        'vehicles. Mag chloride is <b>hygroscopic</b> - it actively pulls moisture out of the '
        'air and holds it against metal, so a treated undercarriage stays chemically wet long '
        'after the road has dried. Corrosion continues on a clear day in a dry garage.', 'body'))
    s.append(P(
        'It concentrates where spray collects and washing does not reach: the undercarriage, '
        'wheel wells, frame rails, brake lines, fuel lines, suspension components and '
        'brake calipers. The AAA estimate for de-icer-driven vehicle rust damage nationally '
        'is around <b>$3 billion a year</b>.', 'body'))
    s.append(callout(
        'Why this compounds every other risk in this report',
        'Section 6.1 identified TJ frame rot as a structural write-off. Mag chloride is exactly '
        'the mechanism that produces it, and it attacks the same inside-out path - moisture '
        'retained in the lower frame rails where there are no drain holes. A Colorado-history '
        'TJ needs its frame inspected with more suspicion than an identical truck from a dry '
        'state. The same applies to JK brake and fuel lines: a corroded brake line is a '
        'sudden-failure item, not a slow-degradation item.',
        accent=RUST))

    s.append(P('9.2  Colorado: hail, and the title that stays clean', 'h2'))
    s.append(P(
        'The Front Range sits in hail alley and Colorado routinely leads the nation in hail '
        'insurance claims. The specific trap: <b>a hail-damaged vehicle can be declared a '
        'total loss by an insurer without the title receiving a salvage brand.</b> The title '
        'stays clean while the total-loss event still appears in the vehicle history record.',
        'body'))
    s.append(P(
        'The practical consequence is that <b>a clean title is not sufficient evidence.</b> '
        'You must check the title and the history report, and treat a disagreement between '
        'them as the answer. On a Wrangler specifically, inspect the hardtop closely - it is '
        'the largest, most exposed and most expensive-to-replace hail target on the vehicle, '
        'and a dimpled hardtop on an otherwise straight Jeep is a strong hail signal.', 'body'))

    s.append(P('9.3  Texas and California: the hazards that replace hail', 'h2'))
    s.append(P(
        'Section 3.4 sets out the scale of the Texas flood problem. What matters at inspection '
        'time is that <b>flood damage and hail damage fail in exactly the same way</b>: an '
        'uninsured or under-threshold loss produces no title brand at all, so the paperwork is '
        'silent and only the car can tell you. Physical tells, in order of reliability:', 'body'))
    s.append(bullets([
        '<b>Smell before you look.</b> Damp, mildew, or an aggressive air freshener masking '
        'something. Run the heater and the air conditioning at full fan and smell the vents.',
        '<b>Silt and rust where water settles.</b> Under the carpet and padding, in the spare '
        'wheel well, inside the seat rails and seat-belt retractors (pull the belt fully out '
        'and look at the webbing near the spool), and along the underside of the dashboard.',
        '<b>Corrosion in the wrong places.</b> Surface rust on unpainted interior fasteners, '
        'seat frames, door hinges and the underside of the dash is not normal wear - it means '
        'water sat inside the cabin.',
        '<b>Electrical oddities.</b> Flood cars fail slowly and strangely. On a JK this is '
        'genuinely hard to distinguish from the TIPM faults in Section 6.2, which is why the '
        'title history matters so much on a Gulf Coast car.',
        '<b>Fluids.</b> Milky or coffee-coloured engine oil, transmission fluid or differential '
        'fluid indicates water ingress - see also the differential check in Section 11.1.',
    ]))
    s.append(P(
        'California substitutes a slower, more visible hazard. Sun and heat degrade the soft '
        'top and its plastic windows, craze the dashboard, chalk the clear coat and perish every '
        'rubber seal on the vehicle. None of it is structural and none of it is hidden - but on '
        'a Wrangler a replacement soft top or hardtop is a four-figure item, so price it in '
        'rather than waving it through.', 'body'))

    s.append(P('9.4  All markets: title washing and odometer fraud', 'h2'))
    s.append(P(
        'Title washing - moving a vehicle between states to shed a salvage or flood brand - '
        'and odometer rollback are both prohibited under the Colorado Consumer Protection Act, '
        'and odometer tampering with intent to defraud is a federal offence. Buying across '
        'state lines is exactly the situation title washing exists to exploit, so the defences '
        'below matter more now than they did in a purely local search:', 'body'))
    s.append(bullets([
        '<b>Check NMVTIS, not just CARFAX.</b> The National Motor Vehicle Title Information '
        'System is the federal title database that states report into. It is materially harder '
        'to launder a brand out of NMVTIS than out of a commercial history report, and a '
        'lookup costs a few dollars.',
        '<b>Read the odometer as a time series.</b> A history report lists readings by date. '
        'Look for a reading that is lower than an earlier one, or a long gap with implausibly '
        'few miles added. Cross-check against Colorado emissions test records where the '
        'vehicle is subject to them.',
        '<b>Treat an out-of-state title transferred shortly before sale as a question,</b> not '
        'as a problem - but ask it out loud and get the answer in writing.',
    ]))

    s.append(P('9.5  Altitude - wherever you buy it', 'h2'))
    s.append(P(
        'A naturally aspirated engine loses roughly three percent of its rated output per '
        '1,000 feet of elevation. Littleton sits around 5,400 feet. The 3.8L V6\'s 202 hp is '
        'therefore delivering something closer to 170 hp before you leave town, and less again '
        'climbing toward the foothills - which are, presumably, part of why you want a '
        'Wrangler. This is not a defect and it will not appear on any report; it is simply the '
        'strongest practical argument for stretching to the 285 hp 3.6L if the rest of the '
        'car checks out.', 'body'))
    return s


# ---------------------------------------------------------- 9. seller
def section_seller(fw):
    s = [CondPageBreak(3.1 * inch), P('10.  Seller and dealer reliability assessment', 'h1'), rule()]
    s.append(P(
        'You asked to prefer dealers with high reliability. That is the right instinct, and it '
        'needs one correction before the ratings below will be useful to you.', 'body'))

    s.append(callout(
        '"BBB Accredited" is a paid membership, not a quality score',
        'Better Business Bureau accreditation means a business applied and pays dues. It is not '
        'an audit and not a performance measure. Both AutoNation Chrysler Dodge Jeep Ram '
        'Southwest and CarMax - two of the largest and most heavily reviewed sellers in this '
        'market - are <b>not</b> BBB accredited, and that fact on its own says nothing about '
        'either. Conversely, an accredited small lot has bought a logo, not a track record. '
        'Read the complaint <i>narratives</i>; ignore the badge.',
        accent=AMBER, bg=colors.HexColor('#f7f1de')))

    s.append(P('10.1  Named sellers in or near the search radius', 'h2'))
    s.append(P('All ratings graded <b>REPORTED</b> - recovered from search indexes; the review '
               'sites themselves were unreachable for direct confirmation.', 'small'))
    dealers = [
        ['AutoNation Chrysler Dodge Jeep Ram Southwest',
         '7980 W Tufts Ave, Littleton, CO 80123',
         '<b>4.2 / 5</b> across 288 CARFAX reviews. Not BBB accredited.',
         'The Jeep franchise store in your radius, so the best factory campaign-history access '
         'and the deepest Wrangler trade-in flow. Complaint themes: slow service turnaround '
         '(one report of 2.5 days before a vehicle was looked at), $230/hr labour, paperwork '
         'not delivered after sale, and poor responsiveness from sales, finance and management '
         'once the deal closed. <b>Get every promise in writing before signing.</b>'],
        ['AutoNation Chrysler Jeep Broadway',
         '5445 S Broadway, Littleton, CO 80121',
         '<b>4.2 / 5</b> across 260 CARFAX reviews; <b>4.3 / 5</b> across 840 DealerRater '
         'reviews.',
         'The second Jeep franchise store in your radius and the source of the 2016 lead in '
         'Section 4.1 (stock GL246888). Largest new and used inventory in south Denver, so the '
         'best odds of 2015-2017 stock. Complaint themes: the advertised "one price" not '
         'matching the price actually paid, and a certified-used inspection described as '
         'questionable (one buyer took delivery with mismatched tyres). <b>Confirm the '
         'out-the-door figure in writing, and do not treat their CPO inspection as a '
         'substitute for your own.</b>'],
        ['CarMax (Englewood and other metro stores)',
         '6 Colorado stores',
         'Not BBB accredited.',
         'No-haggle pricing, a genuine return window, and standardised reconditioning - which '
         'materially reduces the risk of buying a hail or flood car unknowingly. You pay for '
         'that in price, and there is no negotiating room at all. Reasonable choice if you '
         'value certainty over saving $1,500.'],
        ['Skyline Mitsubishi', 'Denver metro (303-465-5512)',
         'No rating recovered.',
         'Surfaced holding 2013 Wrangler Unlimited Sahara inventory. Non-franchise for Jeep, so '
         'no factory campaign-history access. Verify licence and reviews independently.'],
        ['Schomp Automotive', 'Denver metro',
         'Positive review sentiment; no numeric score recovered.',
         'Consistently well-regarded locally, one-price model. Wrangler inventory in your band '
         'not confirmed.'],
        ['BBB-accredited metro used dealers',
         'Michael Auto Sales, Rocky Mountain Eurosport, Metro Area Auto Sales, Dickensheet &amp; '
         'Associates, Turismo Auto Group',
         'Accredited (paid status).',
         'Listed for completeness. Accreditation alone is not a recommendation - apply the '
         'scorecard in 9.3 to any of them.'],
    ]
    s.append(datatable(
        ['Seller', 'Location', 'Reported standing', 'Assessment'],
        [[Paragraph('<b>%s</b>' % d[0], S['cell']), Paragraph(d[1], S['cell']),
          Paragraph(d[2], S['cell']), Paragraph(d[3], S['cell'])] for d in dealers],
        [1.15 * inch, 1.05 * inch, 1.05 * inch, fw - 3.25 * inch]))
    s.append(Spacer(1, 9))

    s.append(P('10.2  Verifying a Colorado dealer before you visit', 'h2'))
    s.append(P(
        'Every retail motor vehicle dealer in Colorado must be licensed by the Colorado '
        'Department of Revenue, Auto Industry Division. Verification is free and public.',
        'body'))
    verify = [
        ['Colorado DOR - Auto Industry Division',
         'sbg.colorado.gov (Web Lookup / Verification tool)',
         'Confirm the dealer holds a current licence, and check the name on the licence matches '
         'the name on your paperwork.'],
        ['Auto Industry Division - direct',
         '(303) 205-5604  |  dor_dealers@state.co.us',
         'Ask whether there is enforcement history against the dealer. Regulates dealer '
         'transactions and handles enforcement.'],
        ['Colorado Attorney General - Consumer Protection',
         'coag.gov/file-complaint',
         'Investigates dealer fraud, publishes consumer guidance, and is where you file if a '
         'deal goes wrong. Colorado Consumer Protection Act covers odometer fraud, title '
         'washing, bait-and-switch and misrepresentation of history or condition.'],
    ]
    s.append(datatable(
        ['Body', 'Where', 'What to do with it'],
        [[Paragraph('<b>%s</b>' % v[0], S['cell']), Paragraph(v[1], S['cell']),
          Paragraph(v[2], S['cell'])] for v in verify],
        [1.55 * inch, 1.75 * inch, fw - 3.3 * inch]))
    s.append(Spacer(1, 9))

    s.append(P('10.3  Seller scorecard', 'h2'))
    s.append(P(
        'Score each seller out of 100 before you commit. Under 60, walk. This weighting is '
        'built for a $6,000-$18,000 purchase, where the seller\'s honesty matters more than '
        'their showroom.', 'body'))
    score = [
        ['Current Colorado dealer licence verified', '15',
         'Unlicensed "curbstoners" posing as private sellers are the single largest source of '
         'title and odometer fraud. Non-negotiable.'],
        ['Agrees to an independent pre-purchase inspection', '20',
         'The most informative question you will ask. A refusal is a complete answer - end the '
         'conversation.'],
        ['Provides the full VIN before you visit', '10',
         'Lets you run the free federal checks first. Reluctance to give a VIN over the phone '
         'is itself a data point.'],
        ['Service records / documented history', '15',
         'On a 3.8L, oil-change frequency is the whole story. On a Pentastar, cylinder-head '
         'history is.'],
        ['Written disclosure of title brands and prior damage', '15',
         'Especially hail. Get it on paper, not in conversation.'],
        ['Review substance across two or more sites', '10',
         'Look for repeated <i>specific</i> complaints - paperwork failures, undisclosed '
         'damage, post-sale silence. Volume of five-star reviews is close to meaningless.'],
        ['No enforcement history with the AG or Auto Industry Division', '10',
         'One phone call.'],
        ['Franchise CDJR dealer (bonus)', '5',
         'Access to factory campaign and warranty history is genuinely valuable on a Pentastar '
         'car.'],
    ]
    s.append(datatable(
        ['Criterion', 'Pts', 'Why it is weighted this way'],
        [[Paragraph(x[0], S['cell']), Paragraph('<b>%s</b>' % x[1], S['cell']),
          Paragraph(x[2], S['cell'])] for x in score],
        [2.35 * inch, 0.42 * inch, fw - 2.77 * inch],
        aligns=[('ALIGN', (1, 1), (1, -1), 'CENTER')]))
    s.append(Spacer(1, 8))

    s.append(P('10.4  Private sellers', 'h2'))
    s.append(P(
        'A private seller has no reconditioning budget, no warranty obligation and no '
        'reputation to protect, but also no margin to defend - so private-party cars are '
        'genuinely cheaper, and an enthusiast owner often has better records than any lot. '
        'Two hard rules:', 'body'))
    s.append(bullets([
        '<b>The name on the title must match the government ID in their hand.</b> If it does '
        'not, you are dealing with an unlicensed dealer and Colorado\'s dealer protections do '
        'not apply to you. Leave.',
        '<b>Treat prices far below market as a warning, not a bargain.</b> A "$2,000 2010 '
        'Wrangler Unlimited Rubicon with 111,000 miles" surfaced during this research against a '
        'Littleton marketplace listing. Section 2.1 puts that vehicle in the $11,000-$13,000 '
        'range. A figure that far below market is the signature of an advance-fee or '
        'fake-escrow scam, a stolen vehicle, or a listing that no longer exists.',
    ]))
    return s


# ---------------------------------------------------------- 10. PPI
def section_ppi(fw):
    s = [CondPageBreak(3.1 * inch), P('11.  Pre-purchase inspection protocol', 'h1'), rule()]
    s.append(P(
        'On a vehicle this age, in this climate, with these known failure modes, an '
        'independent pre-purchase inspection is not optional. It is the highest-return '
        '$200 in the entire transaction.', 'body'))

    cost = [
        ['Basic independent PPI, Denver metro', '$125 - $155'],
        ['Typical thorough PPI', '$183 - $269'],
        ['Additional diagnostic time', 'Extra - and expect to need it if the Jeep is lifted, '
         'has warning lights, or shows drivability symptoms'],
    ]
    s.append(datatable(['Service', 'Cost'],
                       [[Paragraph(a, S['cell']), Paragraph(b, S['cell'])] for a, b in cost],
                       [2.6 * inch, fw - 2.6 * inch]))
    s.append(Spacer(1, 8))
    s.append(P(
        'Use an independent shop with a lift - ideally one that knows Jeeps - and never the '
        'selling dealer\'s own service department. Colorado shops routinely inspect lifted '
        'trucks and Jeeps and know to look at tyre wear, suspension play, driveline angles and '
        'the quality of aftermarket modifications.', 'body'))

    s.append(P('11.1  Wrangler-specific inspection checklist', 'h2'))
    s.append(P('Hand this list to your inspector. The generic PPI will not cover most of it.',
               'small'))

    ck = [
        ['STRUCTURE', [
            'Frame rails probed under the central skid plate and at rear control-arm mounts - '
            'inside-out rot (critical on any TJ, important on early JK)',
            'Body mounts, fuel tank mounts, rear bumper mounts for corrosion',
            'Brake lines and fuel lines for mag-chloride pitting - a sudden-failure item',
            'Frame VIN stamping present, unaltered, and matching dash plate, door jamb and title',
        ]],
        ['STEERING / SUSPENSION', [
            'Track bar and track bar bushings for play - the leading death-wobble contributor',
            'Ball joints, tie rod ends, drag link, steering damper',
            'Front wheel bearings (unit hubs) for play or noise',
            'Anti-roll bar drop links',
            'If lifted: correct-length brake lines, corrected driveline angles, corrected track '
            'bar geometry, speedometer recalibrated for tyre size. Bad lift work causes death '
            'wobble outright.',
        ]],
        ['ENGINE - 3.8L (2007-2011)', [
            'Oil level and condition; ask the seller directly how much oil it uses per 1,000 mi',
            'Leak-down or compression test if consumption is suspected',
            'Cooling system pressure test',
        ]],
        ['ENGINE - 3.6L (2012+)', [
            'Scan for stored and pending misfire codes, cylinder 2 especially',
            'Cold-start listen for tick or rough idle',
            'Left cylinder-head replacement history pulled from the VIN by a CDJR dealer',
        ]],
        ['ENGINE - 4.0L (TJ)', [
            'Timing cover, rear main, oil pan and valve cover for leaks',
            'On 2005-2006: oil pump drive assembly (OPDA) condition or replacement history',
        ]],
        ['ELECTRICAL', [
            'TIPM behaviour - fuel pump, horn, wipers, exterior lighting all cycled repeatedly',
            'All warning lights illuminate at key-on and extinguish (a bulb removed to hide an '
            'airbag or ABS fault is an old trick)',
            'Full OBD-II scan including stored, pending and history codes',
        ]],
        ['DRIVETRAIN', [
            'Engage 4-High and 4-Low, moving, and confirm clean engagement both ways',
            'Front and rear differential fluid for water contamination (milky) - water crossings',
            'On a Rubicon: front and rear lockers and the electronic sway-bar disconnect all '
            'actually function',
            'Transfer case and differential leaks',
        ]],
        ['OFF-ROAD ABUSE', [
            'Underbody scrapes, dented skid plates, bent control arms, damaged rock rails',
            'Bent or creased frame sections',
            'Aftermarket wiring quality - winches and light bars are where amateur wiring lives',
            'Water line staining inside the cab or in the footwells',
        ]],
        ['FLOOD (any TX or Gulf Coast history)', [
            'Smell test: damp or mildew, or heavy air freshener; run heater and A/C at full fan',
            'Lift carpet and padding - silt, staining, or rust on the floor pan',
            'Spare wheel well and under-seat rails for silt lines and corrosion',
            'Seat-belt webbing pulled fully out - staining or grit near the spool',
            'Surface rust on unpainted interior fasteners, seat frames, dash underside',
            'Engine oil, transmission and differential fluid checked for milky water ingress',
        ]],
        ['SUN (any CA or desert history)', [
            'Soft top fabric and plastic windows for hazing, splits and shrinkage',
            'Hardtop and headliner condition - replacement is a four-figure item',
            'Dashboard for cracking and crazing; paint and clear coat for chalking',
            'All door, window and tailgate rubber seals for perishing and leaks',
        ]],
        ['HAIL / BODY', [
            'Hardtop inspected in raking light for dimpling - largest hail target on the vehicle',
            'Roof, bonnet and wing tops in raking light',
            'Panel gaps and paint-depth variation indicating repair',
        ]],
        ['ROAD TEST', [
            'Deliberately drive rough seams and patches at 45-65 mph to provoke death wobble - '
            'on a route you choose, not the seller\'s',
            'Straight-line tracking, braking without pull, steering return to centre',
            'Full temperature cycle to operating temp and beyond',
        ]],
    ]
    for head, items in ck:
        rows = [[Paragraph('<b>%s</b>' % head, S['cellh'])]]
        for it in items:
            rows.append([Paragraph(
                '<font face="Courier-Bold" color="%s">[&nbsp;&nbsp;]</font>&nbsp;&nbsp;%s'
                % (hx(OLIVE_LT), it), S['cell'])])
        t = Table(rows, colWidths=[fw])
        st = [('BACKGROUND', (0, 0), (0, 0), OLIVE),
              ('GRID', (0, 0), (-1, -1), 0.4, RULE),
              ('VALIGN', (0, 0), (-1, -1), 'TOP'),
              ('LEFTPADDING', (0, 0), (-1, -1), 7),
              ('RIGHTPADDING', (0, 0), (-1, -1), 7),
              ('TOPPADDING', (0, 0), (-1, -1), 4),
              ('BOTTOMPADDING', (0, 0), (-1, -1), 4)]
        for i in range(1, len(rows)):
            if i % 2 == 0:
                st.append(('BACKGROUND', (0, i), (-1, i), SAND))
        t.setStyle(TableStyle(st))
        s.append(KeepTogether([t, Spacer(1, 7)]))

    s.append(callout(
        'The refusal test',
        'Ask every seller, in these words: <i>"I\'d like to take it to my own mechanic for a '
        'pre-purchase inspection at my expense. Is that alright?"</i> A legitimate seller with '
        'a sound vehicle says yes without hesitating. Any variation of no - "we don\'t allow '
        'that", "it\'s sold as-is", "our own techs already checked it", "someone else is coming '
        'at four" - is a complete answer to a different question, and the answer is that you '
        'should leave. There are 60 to 90 other candidates in this market.',
        accent=RUST))
    return s


# ---------------------------------------------------------- 11. negotiation
def section_negotiation(fw):
    s = [CondPageBreak(3.1 * inch), P('12.  Price anchoring and negotiation', 'h1'), rule()]
    s.append(P(
        'Wranglers hold value unusually well, and sellers know it. Two structural facts give '
        'you leverage anyway.', 'body'))
    s.append(bullets([
        '<b>The trade-in to private-party spread is enormous.</b> A 2011 Unlimited Sport trades '
        'at $4,690-$5,765 and retails privately at $9,800-$11,850. On a dealer lot the '
        'acquisition cost is likely near the bottom of that first band. There is real room in '
        'the middle, and the dealer knows exactly how much.',
        '<b>Every defect in this report is a priced line item.</b> You are not haggling on '
        'feel - you are presenting a costed inspection report. A quart-per-750-miles oil '
        'habit, a TIPM that needs $400-$800, a death wobble that needs a track bar and ball '
        'joints, a hail-dimpled hardtop: each is a number, and each comes off the ask.',
    ]))

    s.append(P('12.1  Anchors to bring with you', 'h2'))
    anchors = [
        ['2011 Unlimited Sport', '$4,690 - $5,765', '$9,800 - $11,850',
         'Above $12,000 needs justifying: low miles, Rubicon or Sahara trim, or documented '
         'major work.'],
        ['2012 Unlimited Sport', '$6,515 - $7,915', '$11,330 - $13,680',
         'Only pay the Pentastar premium with cylinder-head history confirmed - and at this '
         'budget, prefer a 2015-2017 instead.'],
        ['2014 Unlimited Sport', '$7,205 - $8,605', '$12,200 - $14,450',
         'Denver dealers average $17,531 on 2014s at 110,014 mi. That is roughly $3,000 over '
         'book. Say so.'],
        ['2015 Unlimited Sport', '$9,005 - $10,830', '$13,190 - $15,790',
         'Your primary target. Anything under $16,000 in good condition is a fair deal; under '
         '$15,000 is a good one.'],
        ['2016 Sport (2-dr)', '$9,990 - $11,840', '$13,270 - $15,620',
         'Same reasoning. Note the trade-in floor is high, so dealers have less room here than '
         'on the older cars.'],
        ['2017 Sport S (2-dr)', '$10,330 - $11,980', '$13,710 - $15,810',
         'Top of your realistic range. Expect firm pricing - these are the most sought-after '
         'JK years.'],
    ]
    s.append(datatable(
        ['Vehicle', 'What a dealer paid (approx.)', 'Fair private-party range',
         'Read'],
        anchors, [1.35 * inch, 1.35 * inch, 1.4 * inch, fw - 4.1 * inch]))
    s.append(Spacer(1, 7))
    s.append(P(
        'One caution specific to the newer cars. On a 2011 the trade-in to private-party spread '
        'is roughly $5,000 - enormous negotiating room. On a 2016 it is closer to $3,000, and '
        'the dealer\'s acquisition cost is high enough that they genuinely cannot move as far. '
        'Expect harder pricing as you move up the years, and do not read firmness on a 2016 as '
        'bad faith the way you should read it on a 2011.', 'body'))
    s.append(Spacer(1, 2))

    s.append(P('12.2  Total cost of ownership, first year', 'h2'))
    s.append(P('Budget realistically. A $13,000 Wrangler is not a $13,000 commitment.', 'small'))
    tco = [
        ['Purchase price', '$6,000 - $18,000', ''],
        ['Colorado sales tax, title, registration', 'Varies by jurisdiction',
         'Jefferson County rates apply; budget several hundred to over a thousand'],
        ['Independent PPI', '$125 - $269', 'Per vehicle inspected - budget for two, you will '
         'walk away from at least one. Out of state, arrange it near the seller.'],
        ['Transport or collection', '$0 / $400-$700 / $700-$1,100',
         'Local / fly-and-drive from CA or TX / open-carrier shipping. Add this to the asking '
         'price before comparing an out-of-state car with a local one.'],
        ['Independent history report', '$25 - $45', 'Buy the one the dealer did not show you'],
        ['NMVTIS title check', '$5 - $15', 'Federal brand database'],
        ['Expected annual repair', '~$987', 'JK generation average - treat as a running cost, '
         'not a worst case'],
        ['Deferred-maintenance reserve', '$1,000 - $2,000',
         'Fluids, tyres, brakes, and the first thing the PPI finds. Buying at 2010-2011 money '
         'instead of 2015-2017 money leaves several thousand more for this.'],
    ]
    s.append(datatable(
        ['Line', 'Amount', 'Note'],
        [[Paragraph('<b>%s</b>' % t[0], S['cell']), Paragraph(t[1], S['cell']),
          Paragraph(t[2], S['cell'])] for t in tco],
        [2.05 * inch, 1.25 * inch, fw - 3.3 * inch]))
    s.append(Spacer(1, 8))
    s.append(callout(
        'Set your walk-away number before the first phone call',
        'Decide your absolute ceiling - purchase plus tax plus inspection plus reserve - and '
        'write it down now, while nothing is at stake. Wranglers are emotional purchases and '
        'sellers price them accordingly. The 30 to 45 candidates in this market are your real '
        'leverage: the ability to leave is worth more than any argument you can make at the '
        'desk.',
        accent=OLIVE, bg=SAND))
    return s


# ---------------------------------------------------------- 12. plan
def section_plan(fw):
    s = [P('13.  Action plan', 'h1'), rule()]
    steps = [
        ['1', 'Re-run the searches yourself, unblocked',
         'Cars.com, CarGurus, Autotrader and iSeeCars, three times over: ZIP 80127 at a '
         '20-mile radius, then California statewide, then Texas. Filter each to 2015-2017 and '
         '$6,000-$18,000. Colorado yields 60-90 candidates in band; California alone lists '
         '4,955 of the 2015 model year. Start with California - Section 3.2 explains why.'],
        ['2', 'Decode every VIN before you contact anyone',
         'vpic.nhtsa.dot.gov for trim and engine, nhtsa.gov/recalls for open recalls. Free, '
         'ninety seconds each. Discard anything whose decoded year contradicts the advert.'],
        ['3', 'Chase the two strongest leads first',
         '1C4BJWDG6FL569653 - 2015 Unlimited Sport, 81,024 mi, La Crescenta CA, the lowest '
         'mileage in-target car found. And stock GL246888, a 2016 at AutoNation Chrysler Jeep '
         'Broadway, 5445 S Broadway, Littleton (Section 4.1) - the best local lead. Get full '
         'VIN, price and mileage for both.'],
        ['4', 'Work the rest of the shortlist',
         '1C4AJWAG9GL189210 (2016 two-door, Upland CA), 1C4BJWEG6EL123953 (2014 Unlimited, '
         'Englewood), 1C4AJWAG1CL117007 (2012 two-door, low miles, Englewood), '
         '1J4AA2D1XAL173194 (2010 two-door, Lakewood). The two Texas cars need NMVTIS before '
         'anything else.'],
        ['5', 'Filter hard by model year',
         'Target 2015-2017 with the 3.6L. Fall back to 2014, then to a documented 2010-2011 as '
         'a value play. Treat 2007, 2012 and 2013 as high risk - at this budget you no longer '
         'need to accept them. Any TJ is frame-first.'],
        ['6', 'Convert every out-of-state price to a landed price',
         'Add $700-$1,100 shipping, or $400-$700 to fly out and drive it back. Compare landed '
         'against landed. Flying out is usually cheaper and always better diligence.'],
        ['7', 'Pull factory campaign history by phone',
         'Any CDJR dealer service department, VIN in hand. Free. Decisive on any 2011-2013 '
         'Pentastar car.'],
        ['8', 'Buy your own history report',
         'CARFAX or AutoCheck - whichever the seller did not provide - plus an NMVTIS title '
         'check. Compare the title brand against the history and treat any disagreement as the '
         'answer.'],
        ['9', 'Score the seller',
         'Verify the Colorado dealer licence through the DOR lookup, then apply the Section 10.3 '
         'scorecard. Under 60, walk.'],
        ['10', 'Independent PPI with the Section 11.1 checklist',
         'Your shop, not theirs. Hand over the checklist. A refusal ends the conversation.'],
        ['11', 'Negotiate from the inspection findings',
         'Anchor on the KBB bands in 11.1 and deduct every costed defect. Hold your walk-away '
         'number.'],
        ['12', 'Before signing',
         'Physically match dash plate, door-jamb sticker, frame stamping and title. Get every '
         'verbal promise in writing - the recurring complaint against the largest dealer in '
         'your radius is post-sale paperwork and silence.'],
    ]
    s.append(datatable(
        ['#', 'Step', 'Detail'],
        [[Paragraph('<b>%s</b>' % x[0], S['cell']), Paragraph('<b>%s</b>' % x[1], S['cell']),
          Paragraph(x[2], S['cell'])] for x in steps],
        [0.3 * inch, 1.75 * inch, fw - 2.05 * inch],
        aligns=[('ALIGN', (0, 1), (0, -1), 'CENTER')]))
    s.append(Spacer(1, 10))
    s.append(callout(
        'The one-line summary',
        'A documented, inspected <b>2015-2017 JK with the 3.6L Pentastar</b> is the best use of '
        '$6,000-$18,000: the best-rated years of the generation, the good engine, clear of the '
        'cylinder-head defect, and booking at $13,200-$15,800 private-party - inside your '
        'ceiling with room for tax and inspection. '
        '<br/><br/>'
        '<b>Search California first, Colorado second, Texas only for a specific car.</b> '
        'California has five times the inventory and the lowest average price of any market '
        'surveyed ($16,889 for a 2015); Colorado gives you a car you can inspect with your own '
        'hands and no transport bill; Texas has the supply but the highest prices and the '
        'flood-title risk. Convert every out-of-state price to a landed price before comparing '
        'it with a local one - and if you do buy remotely, fly out and drive it home rather '
        'than shipping it. It costs less and it doubles as a 1,000-mile inspection.',
        accent=GREEN, bg=colors.HexColor('#eaf1ea')))
    return s


# ---------------------------------------------------------- 13. sources
def section_sources(fw):
    s = [CondPageBreak(3.1 * inch), P('14.  Sources', 'h1'), rule()]
    s.append(P(
        'Recovered through server-side search indexing. The underlying pages could not be '
        'fetched directly from the compilation environment (Section 1.1), so these are cited '
        'as the origin of indexed claims rather than as pages read in full.', 'small'))

    groups = [
        ('Listings and inventory',
         ['cars.com - Wrangler inventory, Littleton / Lakewood / Denver, price-filtered',
          'cargurus.com - Wrangler inventory near Littleton and Denver',
          'truecar.com - Wrangler listings, Littleton',
          'iseecars.com - Wrangler under $15,000, Denver',
          'cargurus.com - used 2014 Wrangler, Littleton',
          'autonationchryslerjeepbroadway.com - used 2016 Wrangler, Littleton',
          'edmunds.com - used Wrangler, Littleton and Denver',
          'autotrader.com - Wrangler, Littleton CO',
          'carfax.com - used Wrangler, Denver CO',
          'autonationchryslerdodgejeepramsouthwest.com - used Wrangler inventory, Littleton']),
        ('Valuation',
         ['kbb.com - 2011 and 2012 Wrangler Unlimited Sport, values and depreciation',
          'kbb.com - 2014 Wrangler Unlimited Sport, values',
          'kbb.com - 2015 Wrangler Unlimited Sport 4D and Sport S 2D, values',
          'kbb.com - 2016 Wrangler Sport 2D and Unlimited Sport 4D, values',
          'kbb.com - 2017 Wrangler Sport S 2D, values',
          'edmunds.com - 2014 Wrangler, Denver average list price and mileage']),
        ('Reliability, defects and recalls',
         ['coveragex.com - Jeep Wrangler problems by year, 2007-2026',
          'jeepjkguide.com - JK common problems by year',
          'realtruck.com / motorverso.com - best and worst Wrangler years',
          'autoevolution.com - early 3.6L Pentastar left cylinder head failure',
          'offroaders.com / jeepfan.com - Chrysler Pentastar warranty extension',
          'extremeterrain.com - JK death wobble; JK VIN decoder guide',
          'go-parts.com / rustbuster.com - TJ frame rust, 1997-2002 and 1997-2006',
          'kbtireandautorepair.com / fatboysoffroad.com - TJ years to avoid, 4.0L weak points',
          'static.nhtsa.gov - RCONL-13V234 transmission oil cooler tube recall',
          'autoguide.com / off-road.com - Wrangler recalls over the years',
          'wranglerforum.com / jk-forum.com - 3.8L oil consumption, VIN structure']),
        ('Colorado-specific',
         ['repautoworks.com / autowashco.com - magnesium chloride deicer and vehicle corrosion',
          'newsroom.aaa.com - road de-icers cause $3bn annually in vehicle rust damage',
          'dmv.colorado.gov - salvage vehicles',
          'snapclaim.com - Colorado salvage title guide; hail total loss without a brand',
          'sbg.colorado.gov - Colorado DOR Auto Industry Division, dealer licensing and lookup',
          'coag.gov - Colorado Attorney General, consumer complaints and protection',
          'vincheckpro.com / rockpointlaw.com - Colorado used-car buyer protections']),
        ('Multi-state markets and logistics',
         ['cargurus.com / edmunds.com / truecar.com - 2015 and 2016 Wrangler average list price '
          'and supply: California statewide, Los Angeles, Sacramento',
          'cargurus.com / edmunds.com / autotrader.com / autonationusa.com - Wrangler supply and '
          'average list price, Houston and Dallas',
          'roadrunnerautotransport.com / sgtautotransport.com / amerifreight.net / '
          'sakaemlogistics.com - 2026 car shipping costs, California and Texas to Colorado',
          'dmv.colorado.gov - VIN inspections and form DR 2698',
          'larimer.gov - titling a vehicle from out of state',
          'dmv.org - Colorado registration and emissions programme areas',
          'dmv.ca.gov (FFVR 29) / etags.com - out-of-state vehicle purchase and registration; '
          'Secure Power of Attorney for remote odometer disclosure',
          'jeepforum.com / wranglerforum.com - regional corrosion comparison, magnesium '
          'chloride versus rock salt']),
        ('Texas flood risk',
         ['texasattorneygeneral.gov - consumer alerts on flood-damaged vehicles and disclosure '
          'obligations under the Deceptive Trade Practices Act',
          'txdmv.gov - water-damaged vehicles and title check',
          'nicb.org - over 637,000 vehicles damaged in Hurricanes Harvey and Irma',
          'consumerreports.org - flooded cars returning to the road; title washing',
          'nhtsa.gov - hurricane and flood-damaged vehicles',
          'vehiclehistory.bja.ojp.gov - NMVTIS for consumers']),
        ('Inspection',
         ['repairpal.com - Jeep Wrangler pre-purchase inspection cost estimate',
          'advancedcarinspections.com - Denver PPI pricing, 2026',
          'topedgeautomotive.com / milehighcarhelper.com - Denver pre-purchase inspection']),
        ('Dealer standing',
         ['carfax.com - AutoNation CDJR Southwest, Littleton, dealership reviews',
          'bbb.org - AutoNation CDJR Southwest business profile, reviews and complaints',
          'carfax.com / dealerrater.com / yelp.com - AutoNation Chrysler Jeep Broadway, '
          'Littleton, dealership reviews',
          'bbb.org - accredited and non-accredited used car dealers, Denver / Littleton / '
          'Lakewood / Englewood',
          'dealerrater.com - CarMax dealership ratings']),
        ('Standards applied offline',
         ['ISO 3779 / 49 CFR Part 565 - VIN structure and check-digit algorithm '
          '(implemented locally in vin_tools.py; no network access required)']),
    ]
    for title, items in groups:
        s.append(P(title, 'h3'))
        s.append(bullets(items, style='small'))

    s.append(Spacer(1, 10))
    s.append(rule())
    s.append(P(
        'This report is research support for a private vehicle purchase. It is not a vehicle '
        'history report, a title search, a mechanical inspection, or professional advice. '
        'Every price, mileage and inventory figure is time-sensitive and graded REPORTED - '
        'confirm each one directly with the seller before acting. The VIN authentication in '
        'Section 4 is reproducible offline and is the only class of claim here that carries '
        'independent proof.', 'small'))
    return s


if __name__ == '__main__':
    out = sys.argv[1] if len(sys.argv) > 1 else 'Jeep_Wrangler_80127_Due_Diligence_Report.pdf'
    print('Built:', build(out))
