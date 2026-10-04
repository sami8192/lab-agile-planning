#!/usr/bin/env python3
"""
Automatic filter for a nationwide Jeep Wrangler search (teen driver, $7,000-$12,000).

Every decision is made from the VIN first and the listing second, because
listing text is often wrong: model year, engine and generation all come from
the VIN. The listing supplies only price, mileage, location and sale channel.

    python3 wrangler_filter.py                    # run the researched candidate set
    python3 wrangler_filter.py VIN [--price N] [--miles N] [--state XX] [--city NAME]
                                   [--year YYYY] [--channel dealer|private|auction]

Policy lives in the constants below, so changing a rule is a one-line edit.
"""
import argparse
import sys

from vin_tools import check_digit, decode

BUDGET_MIN, BUDGET_MAX = 7000, 12000

# --- model-year policy --------------------------------------------------------
# Only these years can reach the shortlist. Tier A = the most reliable years.
APPROVED = {
    2003: ('TJ', 'A', 'Best TJ year: after the 0331 cylinder-head fix, before the '
                      '2005-06 oil pump drive failures'),
    2004: ('TJ', 'A', 'Best TJ year: after the 0331 cylinder-head fix, before the '
                      '2005-06 oil pump drive failures'),
    2014: ('JK', 'B', 'First JK year clear of the Pentastar cylinder-head defect; good '
                      'rather than best'),
    2015: ('JK', 'A', 'Highest-rated JK years'),
    2016: ('JK', 'A', 'Highest-rated JK years'),
    2017: ('JK', 'A', 'Highest-rated JK years'),
}
# Allowed only once a human confirms the named repair; never auto-shortlisted.
CONDITIONAL = {
    2005: ('TJ', 'Needs documented oil pump drive assembly (OPDA) replacement'),
    2006: ('TJ', 'Needs documented oil pump drive assembly (OPDA) replacement'),
}
EXCLUDED_YEARS = {
    1997: 'TJ launch year',
    1998: 'Older TJ, not among the best-rated years',
    1999: 'Older TJ, not among the best-rated years',
    2000: '0331 cylinder head prone to cracking',
    2001: '0331 cylinder head prone to cracking',
    2002: 'Not among the best-rated TJ years',
    2007: 'JK launch year: pronounced death wobble, airbag warning faults',
    2008: '3.8L V6 years: oil consumption past 100k mi, TIPM failures',
    2009: '3.8L V6 years: oil consumption past 100k mi, TIPM failures',
    2010: '3.8L V6 years: oil consumption past 100k mi, TIPM failures',
    2011: '3.8L V6 years: oil consumption past 100k mi, TIPM failures',
    2012: 'Worst-rated JK year: ~10 recalls, early Pentastar cylinder-head defect',
    2013: 'Transmission failures and engine stalling reported',
    2018: 'Run-out JK / JL launch: steering, weld and clutch complaints',
}

# VIN position 8 engine codes. This pattern held on every Wrangler VIN examined
# in this repository's research; the federal decoder (vpic.nhtsa.dot.gov) is
# authoritative and should confirm any car you are serious about.
REQUIRED_ENGINE = {'TJ': ('S', '4.0L inline six'), 'JK': ('G', '3.6L Pentastar V6')}

# --- price sanity -------------------------------------------------------------
# Lowest KBB private-party figure sourced for each year's 2-door. A reliable-year
# JK priced well under this is usually hiding a branded title or major fault.
BOOK_FLOOR_2DR = {2014: 10930, 2015: 11440, 2016: 13270, 2017: 13710}
BOOK_FLOOR_UNLIMITED = {2014: 12200, 2015: 13190}
BELOW_BOOK_RATIO = 0.85
HIGH_MILES = 150000

# --- geography ------------------------------------------------------------------
HEAVY_SALT = {'CT', 'DE', 'IA', 'IL', 'IN', 'MA', 'MD', 'ME', 'MI', 'MN', 'NH', 'NJ',
              'NY', 'OH', 'PA', 'RI', 'VT', 'WI', 'WV', 'VA'}
MODERATE_SALT = {'NC', 'KY', 'TN', 'MO', 'KS', 'NE', 'UT', 'CO'}
DRY = {'AZ', 'NM', 'NV', 'CA'}
DRY_TX_CITIES = {'El Paso', 'Lubbock', 'Midland', 'Odessa', 'Amarillo', 'San Angelo'}
FLOOD_STATES = {'FL', 'LA', 'MS'}
FLOOD_TX_CITIES = {'Houston', 'Galveston', 'League City', 'Beaumont', 'Corpus Christi'}
# TJ frames rot from the inside out (see the Jeep report, Section 6.1). A TJ that
# has lived in a heavy-salt state is excluded outright; set False to review them.
EXCLUDE_TJ_FROM_HEAVY_SALT = True

# The buyer prefers the JK; it is also the only generation with stability control.
JK_PREFERENCE_BONUS = 10

SHORTLIST, CONDITIONAL_D, REVIEW, EXCLUDED = 'SHORTLIST', 'CONDITIONAL', 'REVIEW', 'EXCLUDED'


def body_style(vin, gen):
    """2-door vs Unlimited from VIN position 4 on 2012+ JKs (observed pattern)."""
    if gen == 'TJ':
        return '2-dr'
    if vin.startswith('1C4'):
        return 'Unlimited' if vin[3] in 'BH' else '2-dr'
    return '?'


def generation(vin, year):
    if not isinstance(year, int):
        return None
    if 1997 <= year <= 2006:
        return 'TJ'
    if 2007 <= year <= 2017:
        return 'JK'
    if year == 2018:
        return 'JL' if vin[5] == 'X' else 'JK'
    return 'JL'


def evaluate(c):
    """Return the candidate dict enriched with decision, reasons, flags and score."""
    vin = c['vin'].upper()
    out = dict(c, vin=vin, hard=[], flags=[])
    want, err = check_digit(vin)
    if err or want != vin[8]:
        out['hard'].append('VIN fails the check digit - not a genuine VIN')
        out.update(decision=EXCLUDED, year=None, gen=None, body='?', score=0, tier='-')
        return out

    d = decode(vin)
    year = d['year']
    gen = generation(vin, year)
    out.update(year=year, gen=gen, body=body_style(vin, gen), tier='-')

    # 1. Model year - the core rule.
    conditional = False
    if year in APPROVED:
        out['tier'] = APPROVED[year][1]
        out['year_reason'] = APPROVED[year][2]
    elif year in CONDITIONAL:
        conditional = True
        out['year_reason'] = CONDITIONAL[year][1]
    else:
        out['hard'].append('%s: %s' % (year, EXCLUDED_YEARS.get(
            year, 'JL generation - outside this search' if gen == 'JL' else 'not an '
            'approved year')))

    # 2. Engine - must be the inline six (TJ) or the Pentastar (JK).
    if gen in REQUIRED_ENGINE and vin[7] != REQUIRED_ENGINE[gen][0]:
        out['hard'].append('Engine code %r is not the %s' % (vin[7], REQUIRED_ENGINE[gen][1]))

    # 3. Listing facts that disqualify outright.
    if c.get('country', 'US') != 'US':
        out['hard'].append('Listed outside the US (%s)' % c['country'])
    if c.get('channel') == 'insurance-auction':
        out['hard'].append('Insurance auction - total-loss vehicle')
    if c.get('channel') == 'sold':
        out['hard'].append('Historical sale, not a current listing')
    if c.get('title') in ('salvage', 'rebuilt', 'flood'):
        out['hard'].append('Branded title: %s' % c['title'])
    price, miles = c.get('price'), c.get('miles')
    if price and price > BUDGET_MAX:
        out['hard'].append('Price $%s is over the $%s ceiling' % (format(price, ','),
                                                                  format(BUDGET_MAX, ',')))
    state, city = c.get('state'), c.get('city', '')
    if gen == 'TJ' and state in HEAVY_SALT and EXCLUDE_TJ_FROM_HEAVY_SALT:
        out['hard'].append('TJ from a heavy road-salt state (%s) - frame-rot risk' % state)

    # 4. Flags - the car survives, but a person has to resolve these.
    serious = False
    ry = c.get('reported_year')
    if ry and ry != year:
        out['flags'].append('Listing says %s; VIN proves %s' % (ry, year))
    if price is None:
        out['flags'].append('No price indexed')
        floor = (BOOK_FLOOR_UNLIMITED if out['body'] == 'Unlimited' else {}).get(year)
        if floor and floor > BUDGET_MAX:
            out['flags'].append('Unlimited book value starts at $%s - expect over budget'
                                % format(floor, ','))
            serious = True
    else:
        floor = (BOOK_FLOOR_UNLIMITED if out['body'] == 'Unlimited'
                 else BOOK_FLOOR_2DR).get(year)
        if floor and price < floor * BELOW_BOOK_RATIO:
            out['flags'].append('Priced %d%% below book - assume a branded title until '
                                'NMVTIS proves otherwise' % round(100 - 100.0 * price / floor))
            serious = True
        if price < BUDGET_MIN:
            out['flags'].append('Below the $%s budget floor' % format(BUDGET_MIN, ','))
    if miles is None:
        out['flags'].append('Mileage not indexed')
    elif miles > HIGH_MILES:
        out['flags'].append('High mileage (%s)' % format(miles, ','))
    if state in FLOOD_STATES or (state == 'TX' and city in FLOOD_TX_CITIES):
        out['flags'].append('Flood region - NMVTIS and a physical flood check are mandatory')
        serious = True
    if gen == 'JK' and state in HEAVY_SALT:
        out['flags'].append('Heavy road-salt state - inspect frame and brake lines')
    if state in MODERATE_SALT:
        out['flags'].append('Winter road treatment in %s - inspect the frame underside' % state)
    if c.get('channel') == 'auction':
        out['flags'].append('Online auction - limited recourse, inspect before bidding')
        serious = True
    if c.get('modified'):
        out['flags'].append('Modified - verify lift geometry (death-wobble risk)')
        serious = True
    if c.get('location_unknown'):
        out['flags'].append('Location not indexed')

    # 5. Decision and ranking score.
    if out['hard']:
        out['decision'], out['score'] = EXCLUDED, 0
        return out
    out['decision'] = CONDITIONAL_D if conditional else (REVIEW if serious else SHORTLIST)
    score = 100 + {'A': 20, 'B': 10}.get(out['tier'], -15)
    score += 10 if price else -10
    score += -miles / 10000.0 if miles else -8
    score += JK_PREFERENCE_BONUS if gen == 'JK' else 0
    score -= 8 if c.get('location_unknown') else 0
    if state in DRY or (state == 'TX' and city in DRY_TX_CITIES):
        score += 10
    score -= 10 if state in HEAVY_SALT else (5 if state in MODERATE_SALT else 0)
    score -= 20 if serious else 0
    out['score'] = round(score, 1)
    return out


def run(candidates):
    order = {SHORTLIST: 0, CONDITIONAL_D: 1, REVIEW: 2, EXCLUDED: 3}
    res = [evaluate(c) for c in candidates]
    return sorted(res, key=lambda r: (order[r['decision']], -r['score']))


# --------------------------------------------------------------------------
# Nationwide candidates recovered from search indexes (October 2026), plus the
# Colorado / CA / TX VINs from the earlier reports so their exclusion is shown.
# Price, mileage and location are REPORTED, unverified listing data.
# --------------------------------------------------------------------------
CANDIDATES = [
    # ---- JK, approved years
    dict(vin='1C4AJWAG4GL250009', reported_year=2016, trim='Sport', price=9995, miles=108449,
         location_unknown=True, channel='dealer'),
    dict(vin='1C4GJWAG1GL219309', reported_year=2016, trim='Sport S', price=11999,
         miles=141399, city='Chantilly', state='VA', channel='dealer'),
    dict(vin='1C4AJWAGXFL566836', reported_year=2015, trim='Sport', price=11499,
         location_unknown=True, channel='dealer'),
    dict(vin='1C4AJWAG9GL189210', reported_year=2016, trim='Sport', miles=91322,
         city='Upland', state='CA', channel='dealer'),
    dict(vin='1C4AJWAG7FL574988', reported_year=2014, trim='Sport, automatic', city='Mesa',
         state='AZ', channel='dealer'),
    dict(vin='1C4AJWAG1EL160345', reported_year=2014, trim='Sport, manual',
         city='Apache Junction', state='AZ', channel='dealer'),
    dict(vin='1C4AJWAG8EL147494', reported_year=2014, trim='Sport', city='Mesa', state='AZ',
         channel='dealer'),
    dict(vin='1C4AJWAG7EL190529', reported_year=2015, trim='6-speed manual', miles=118489,
         city='Woods Cross', state='UT', channel='dealer'),
    dict(vin='1C4AJWAG9FL630283', reported_year=2015, trim='Sport', price=10995, miles=51900,
         city='Sherbrooke', state='QC', country='Canada', channel='dealer'),
    dict(vin='1C4BJWDG6FL569653', reported_year=2015, trim='Unlimited Sport', miles=81024,
         city='La Crescenta', state='CA', channel='dealer'),
    dict(vin='1C4BJWDG2FL735814', reported_year=2015, trim='Unlimited Willys Wheeler',
         miles=84824, city='Houston', state='TX', channel='dealer'),
    dict(vin='1C4HJWDG0FL604925', reported_year=2015, trim='Unlimited Sport', state='TX',
         channel='auction', modified=True),
    dict(vin='1C4BJWEG6EL123953', reported_year=2014, trim='Unlimited', miles=122634,
         city='Englewood', state='CO', channel='dealer'),
    # ---- JK, excluded years (from the earlier Colorado search)
    dict(vin='1J4AA2D1XAL173194', reported_year=2010, trim='Sport', price=10700,
         miles=111535, city='Lakewood', state='CO'),
    dict(vin='1J4BA6H17BL574757', reported_year=2011, trim='Unlimited Rubicon', price=11899,
         miles=99127, city='Denver', state='CO'),
    dict(vin='1J4BA3H13BL589979', reported_year=2023, trim='Unlimited', city='Littleton',
         state='CO'),
    dict(vin='1C4AJWAG1CL117007', reported_year=2012, trim='2-door, manual', miles=54371,
         city='Englewood', state='CO'),
    dict(vin='1C4HJXDN9LW170163', reported_year=2020, trim='Unlimited Willys (JL)',
         price=23500, miles=71424, city='Littleton', state='CO'),
    # ---- TJ inline six
    dict(vin='1J4FA49S34P771921', reported_year=2004, trim='Sport 4.0, 5-speed manual',
         price=10859, miles=135658, city='Garner', state='NC', channel='dealer'),
    dict(vin='1J4FA39S83P324624', reported_year=2003, trim='X 4.0, 5-speed, hardtop',
         miles=60830, city='Jacksonville', state='FL', channel='dealer'),
    dict(vin='1J4FA49S53P346697', reported_year=2003, trim='Sport 4.0, 5-speed',
         miles=145000, channel='auction', location_unknown=True),
    dict(vin='1J4FA39S73P368341', reported_year=2003, trim='X 4.0, manual', price=10500,
         miles=188500, city='Hagerstown', state='MD', channel='dealer'),
    dict(vin='1J4FA49S03P360197', reported_year=2003, trim='Sport 4.0, automatic',
         miles=142571, city='Cleveland', state='OH', channel='dealer'),
    dict(vin='1J4FA39S33P331285', reported_year=2003, trim='X 4.0', miles=98065,
         channel='insurance-auction'),
    dict(vin='1J4FA39S13P308152', reported_year=2003, trim='X 4.0', price=12100,
         channel='sold'),
    dict(vin='1J4FA69S34P755746', reported_year=2004, trim='Rubicon', price=28900,
         miles=65388, channel='dealer', location_unknown=True),
    dict(vin='1J4FA49S46P788486', reported_year=2023, trim='Sport 4.0',
         city='Colorado Springs', state='CO'),
    # Its indexed price/mileage ($28,549 / 50,425 mi) belonged to a different car
    # (Jeep report, Section 1.3), so they are deliberately omitted.
    dict(vin='1J4FA49S31P347487', reported_year=2022, trim='Sport 4.0',
         city='Colorado Springs', state='CO'),
]


def _fmt(r):
    loc = ', '.join(x for x in (r.get('city'), r.get('state')) if x) or 'location n/a'
    p = '$' + format(r['price'], ',') if r.get('price') else 'price n/a'
    m = format(r['miles'], ',') + ' mi' if r.get('miles') else 'miles n/a'
    head = '%-11s %s  %s %s %-9s %s | %s | %s' % (
        r['decision'], r['vin'], r['year'] or '----', r['gen'] or '--', r['body'], p, m, loc)
    lines = [head]
    lines += ['            x %s' % h for h in r['hard']]
    lines += ['            ! %s' % f for f in r['flags']]
    return '\n'.join(lines)


def main(argv):
    if len(argv) > 1:
        ap = argparse.ArgumentParser(description='Evaluate one Wrangler listing.')
        ap.add_argument('vin')
        ap.add_argument('--price', type=int)
        ap.add_argument('--miles', type=int)
        ap.add_argument('--state')
        ap.add_argument('--city', default='')
        ap.add_argument('--year', type=int, dest='reported_year')
        ap.add_argument('--channel', choices=['dealer', 'private', 'auction',
                                              'insurance-auction'], default='dealer')
        a = ap.parse_args(argv[1:])
        print(_fmt(evaluate(vars(a))))
        return 0
    results = run(CANDIDATES)
    for r in results:
        print(_fmt(r))
    tally = {}
    for r in results:
        tally[r['decision']] = tally.get(r['decision'], 0) + 1
    print('-' * 72)
    print('  '.join('%s %d' % (k, tally.get(k, 0))
                    for k in (SHORTLIST, CONDITIONAL_D, REVIEW, EXCLUDED)))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
