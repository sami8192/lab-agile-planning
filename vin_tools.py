#!/usr/bin/env python3
"""
Offline VIN authentication and Jeep Wrangler decoding.

No network access required. The check digit (ISO 3779 / 49 CFR Part 565) is
computed purely from the VIN's own characters, which is what makes it useful
for auditing VINs recovered from untrusted sources: a fabricated or
mis-transcribed 17-character string satisfies it only about 1 time in 11.

    python3 vin_tools.py                      # audit the report's candidates
    python3 vin_tools.py 1J4AA2D1XAL173194    # audit specific VINs
"""
import sys

# Character -> numeric value. I, O and Q are never valid anywhere in a VIN.
TRANSLIT = dict(
    [(str(d), d) for d in range(10)] +
    list(zip('ABCDEFGH', [1, 2, 3, 4, 5, 6, 7, 8])) +
    list(zip('JKLMNP',   [1, 2, 3, 4, 5, 7])) +
    list(zip('RSTUVWXYZ', [9, 2, 3, 4, 5, 6, 7, 8, 9])))

# Positional weights. Position 9 carries weight 0 so the check digit never
# participates in its own calculation.
WEIGHTS = [8, 7, 6, 5, 4, 3, 2, 10, 0, 9, 8, 7, 6, 5, 4, 3, 2]

MODEL_YEAR = dict(zip(
    'VWXY123456789ABCDEFGHJKLMNPRST',
    list(range(1997, 2027))))

PLANT = {
    'P': ('Toledo North', 'Toledo North Assembly, Toledo OH'),
    'L': ('Toledo South', 'Toledo South / Toledo Supplier Park, Toledo OH'),
    'W': ('Toledo Assy', 'Toledo Assembly Complex, Toledo OH'),
    'C': ('Jefferson N', 'Jefferson North Assembly, Detroit MI'),
    'D': ('Belvidere', 'Belvidere Assembly, Belvidere IL'),
}

WMI = {
    '1J4': 'Chrysler Group LLC / Jeep, USA-built MPV (through MY2011)',
    '1J8': 'Chrysler Group LLC / Jeep, USA-built MPV',
    '1C4': 'FCA US LLC / Chrysler Group, USA-built MPV (MY2012 onward)',
}


def check_digit(vin):
    """Return (expected_position_9_character, error_message).

    On success error_message is None. Compare the returned character against
    vin[8] to decide pass/fail.
    """
    vin = (vin or '').upper().strip()
    if len(vin) != 17:
        return None, 'wrong length (%d characters, expected 17)' % len(vin)
    for bad in 'IOQ':
        if bad in vin:
            return None, 'contains illegal letter %r (I, O and Q never appear in a VIN)' % bad
    try:
        total = sum(TRANSLIT[c] * w for c, w in zip(vin, WEIGHTS))
    except KeyError as exc:
        return None, 'illegal character %s' % exc
    remainder = total % 11
    return ('X' if remainder == 10 else str(remainder)), None


def decode(vin):
    """Decode the positions that are unambiguous across all Wrangler generations."""
    vin = vin.upper().strip()
    plant_short, plant_long = PLANT.get(vin[10], ('unknown', 'unknown plant code %r' % vin[10]))
    return {
        'vin': vin,
        'wmi': vin[:3],
        'wmi_desc': WMI.get(vin[:3], 'unrecognised WMI'),
        'vds': vin[3:8],
        'check': vin[8],
        'year': MODEL_YEAR.get(vin[9], '?'),
        'year_code': vin[9],
        'plant_code': vin[10],
        'plant_short': plant_short,
        'plant': plant_long,
        'serial': vin[11:],
    }


def audit(vin, label=''):
    """Print a full audit line for one VIN. Returns True if the check digit passes."""
    vin = vin.upper().strip()
    expected, err = check_digit(vin)
    print('=' * 72)
    print('VIN   : %s%s' % (vin, ('   ' + label) if label else ''))
    if err:
        print('RESULT: INVALID - %s' % err)
        return False
    d = decode(vin)
    ok = (d['check'] == expected)
    print("CHECK : position 9 is %r, algorithm requires %r  ->  %s"
          % (d['check'], expected, 'PASS' if ok else 'FAIL'))
    print('WMI   : %s = %s' % (d['wmi'], d['wmi_desc']))
    print("YEAR  : pos10 %r = %s" % (d['year_code'], d['year']))
    print("PLANT : pos11 %r = %s" % (d['plant_code'], d['plant']))
    print('VDS   : %s (pos 4-8: GVWR/restraint, line, series, body, engine)' % d['vds'])
    print('SERIAL: %s' % d['serial'])
    return ok


# --------------------------------------------------------------------------
# Candidates recovered from Colorado, California and Texas listing indexes.
#
# 'reported' is UNVERIFIED search-snippet data and is reproduced only so it can
# be challenged against the VIN. Where the snippet's claimed model year
# contradicts VIN position 10, the VIN wins -- see the report, Section 1.3.
#
# 'region' is the market the listing was indexed against, not where the vehicle
# was built -- every Wrangler here was assembled in Toledo, Ohio.
# --------------------------------------------------------------------------
CANDIDATES = [
    # ---- California: rust-free climate, deepest supply, lowest average price
    {
        'vin': '1C4BJWDG6FL569653',
        'reported': 'Unlimited Sport 4WD, 81,024 mi, La Crescenta CA',
        'region': 'CA',
        'verdict': 'GO',
        'note': 'Year matches VIN. A 2015 Unlimited Sport is the report\'s primary target, and '
                '81k mi is the lowest of any in-target candidate found. Southern California '
                'car - no road salt exposure. No price indexed; get it.',
    },
    {
        'vin': '1C4AJWAG9GL189210',
        'reported': '2-dr Sport 4WD, stock #260383A, 91,322 mi, Upland CA',
        'region': 'CA',
        'verdict': 'GO',
        'note': 'Year matches VIN. 2016 is a best-rated year. Same VDS (AJWAG) as the Englewood '
                '2012 two-door, which corroborates the trim decode. Inland-empire car, dry '
                'climate. No price indexed.',
    },
    # ---- Texas: huge supply, but the flood-title capital of the search
    {
        'vin': '1C4BJWDG2FL735814',
        'reported': 'Unlimited Willys Wheeler 4WD, stock #TG2FL7358, 84,824 mi, Houston TX',
        'region': 'TX',
        'verdict': 'CHECK',
        'note': 'Year matches VIN and the spec is desirable. But Houston is the epicentre of '
                'US flood-title risk - run NMVTIS before anything else, and treat a clean '
                'title as insufficient (Section 9.3).',
    },
    {
        'vin': '1C4HJWDG0FL604925',
        'reported': 'Unlimited Sport 4x4, Cars & Bids auction, "mostly Texas-owned", '
                    'off-road modifications',
        'region': 'TX',
        'verdict': 'CHECK',
        'note': 'Year matches VIN. Two compounding risks: online auction (limited recourse, '
                'often no inspection contingency) and disclosed off-road modification. Badly '
                'executed lifts cause death wobble outright - see Section 6.4.',
    },
    # ---- Colorado: local, inspectable in person, no transport cost
    {
        'vin': '1C4BJWEG6EL123953',
        'reported': 'Unlimited 4-dr, 122,634 mi, 3.6L V6, Englewood. A 2014 Unlimited at '
                    '147k mi / $15,999 was separately indexed in Englewood.',
        'region': 'CO',
        'verdict': 'GO',
        'note': 'Year matches VIN. Brought into range by the $18,000 ceiling, and 2014 is the '
                'first year clear of the Pentastar head defect. High miles - price accordingly.',
    },
    {
        'vin': '1C4AJWAG1CL117007',
        'reported': '2-dr, 54,371 mi, 3.6L V6, manual, Englewood. No price stated.',
        'region': 'CO',
        'verdict': 'GO',
        'note': 'Year matches VIN. Lowest mileage found and the good engine, but 2012 is a '
                'Pentastar cylinder-head year. Get price and head history.',
    },
    {
        'vin': '1J4AA2D1XAL173194',
        'reported': '2-dr Sport, $10,700, 111,535 mi, Lakewood area',
        'region': 'CO',
        'verdict': 'GO',
        'note': 'Year matches VIN. Now well under budget, which makes it a value play rather '
                'than a stretch. 3.8L - ask about oil use.',
    },
    {
        'vin': '1J4BA6H17BL574757',
        'reported': 'Unlimited Rubicon. Indexed twice: $11,899 / 99,127 mi / Denver AND '
                    '$12,599 / 123,567 mi / Centennial.',
        'region': 'CO',
        'verdict': 'CHECK',
        'note': 'Year matches VIN, but one car cannot have two odometer readings. Establish '
                'actual mileage before anything else. Rubicon at Sport money is attractive.',
    },
    {
        'vin': '1J4BA3H13BL589979',
        'reported': 'Labelled "2023 Wrangler Sport 4xe, $23,991, 43,814 mi, Littleton".',
        'region': 'CO',
        'verdict': 'CHECK',
        'note': 'VIN proves 2011 Unlimited, not 2023. The price shown belongs to a different '
                'vehicle. Real car, unknown price - worth a lookup, not a drive.',
    },
    {
        'vin': '1J4FA49S46P788486',
        'reported': 'Labelled "2023 Wrangler Sahara, 42,483 mi, Aurora".',
        'region': 'CO',
        'verdict': 'SKIP',
        'note': 'VIN proves a 2006 TJ Sport, 4.0L. Credible buy in principle, but indexed '
                'against a Colorado Springs listing - outside the 20-mile radius.',
    },
    {
        'vin': '1J4FA49S31P347487',
        'reported': 'Labelled "2022 Wrangler Sahara, $28,549, 50,425 mi, Colorado Springs".',
        'region': 'CO',
        'verdict': 'SKIP',
        'note': 'VIN proves a 2001 TJ Sport, 4.0L - off by 21 model years. Outside radius.',
    },
    {
        'vin': '1C4HJXDN9LW170163',
        'reported': 'Unlimited Willys, $23,500, 71,424 mi, Littleton',
        'region': 'CO',
        'verdict': 'SKIP',
        'note': 'Year matches VIN - a genuine 2020 JL. Still 31% over the raised $18,000 '
                'ceiling. Out of scope.',
    },
]


def main(argv):
    if len(argv) > 1:
        items = [(v, '') for v in argv[1:]]
    else:
        items = [(c['vin'], c['verdict']) for c in CANDIDATES]
    passed = sum(audit(v, label) for v, label in items)
    print('=' * 72)
    print('%d of %d VINs passed the check digit.' % (passed, len(items)))
    return 0 if passed == len(items) else 1


if __name__ == '__main__':
    sys.exit(main(sys.argv))
