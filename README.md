# lab-agile-planning

Repository lab for agile planning.

---

## iPhone price watch

A dependency-free Python watcher that tracks **brand-new, unlocked, large-screen iPhones
with at least 256 GB of storage** and sends a **push notification to your phone** the
moment a price drops.

* **New only** — refurbished, renewed, open-box and used listings are filtered out.
* **Large screen only** — a listing qualifies when the model's display is at least
  6.5″ (configurable). Today that means **iPhone Air** (6.5″), every ***Plus*** (6.7″,
  e.g. iPhone 16 Plus) and every ***Pro Max*** (6.7–6.9″); run `iphone-watch models` to
  see the full table. The Air sits exactly on the threshold, so raising
  `min_screen_inches` above 6.5 drops it.
* **256 GB minimum** — configurable, `1TB`/`2TB` titles are understood.
* **Three models** — the committed `config.json` narrows the watch to
  `["Air", "16 Plus", "Pro Max"]`: iPhone Air, iPhone 16 Plus and any *Pro Max*
  generation. Empty the `models` list to watch every phone that clears the screen and
  storage rules, or change `"Pro Max"` to `"17 Pro Max"` to pin the current one.
* **Unlocked, or T-Mobile** — anything locked to another carrier (AT&T, Verizon,
  Cricket, Metro, Xfinity…) is skipped. T-Mobile listings are kept, because they can be
  activated on an existing T-Mobile line. Listings that don't state a lock status are
  watched by default; set `allow_unknown_carrier: false` to require an explicit
  "unlocked".
* **No new-line pricing** — offers whose price only applies with a new line, a port-in,
  a new account or a trade-in are skipped, so the alert is the price you would actually
  pay activating on the line you already have.
* **Real drops only** — the price is compared against the history stored on disk, with
  a minimum drop in both percent and currency, plus a cooldown so one sale doesn't
  spam you.

### Quick start

```bash
git clone https://github.com/sami8192/lab-agile-planning.git
cd lab-agile-planning

# 1. try it offline against the bundled demo listings
python -m iphone_watch -c config.example.json check --dry-run --explain

# 2. get pushes on your phone (see "Push notifications" below)
export NTFY_TOPIC="iphone-drops-$(openssl rand -hex 6)"
python -m iphone_watch test-notify

# 3. add credentials for the live sources, then watch
export EBAY_CLIENT_ID=… EBAY_CLIENT_SECRET=… BESTBUY_API_KEY=…
python -m iphone_watch check --explain      # one pass, shows what was skipped
python -m iphone_watch watch --interval 900 # keep going
```

`config.json` is the live configuration (already narrowed to the three models);
`config.example.json` documents every option and keeps the offline demo source.
Credentials are never stored in either file — they are read from the environment
through `${VAR}` placeholders.

Python 3.9+ and no third-party packages. `pip install -e .` also installs an
`iphone-watch` command that is equivalent to `python -m iphone_watch`.

### Push notifications

| Notifier | Setup |
| --- | --- |
| `ntfy` *(default)* | Install the free [ntfy](https://ntfy.sh) app (iOS/Android), subscribe to a **private, unguessable topic name**, and put that name in `NTFY_TOPIC`. No account needed. Self-hosted servers work via `server`, protected topics via `token`. |
| `pushover` | Create an application at [pushover.net](https://pushover.net); set `PUSHOVER_TOKEN` and `PUSHOVER_USER`. |
| `webhook` | POSTs JSON to any URL (Slack, Discord, Home Assistant, IFTTT…). Use `template` to shape the body, e.g. `{"text": "{title}\n{message}"}`. |
| `console` | Prints to stdout — for dry runs and CI logs. |

The topic name in ntfy *is* the secret: anyone who knows it can read your alerts, so
generate a random one and keep it in an environment variable rather than in the config
file. Every config value supports `${ENV_VAR}` and `${ENV_VAR:-default}` expansion.

Alerts are grouped: several drops in one pass become a single push such as

```
3 iPhone price drops (best -12%)
• iPhone 17 Pro Max 256GB (Unlocked): $1,199 → $1,049 (-12.5%)
  at Demo Store
  https://example.com/…
```

### Where prices come from

Configure one or more entries under `sources`. Each has a `type`, a `name` (used in the
listing key, so keep it stable) and `enabled`.

| Type | What it does | Needs |
| --- | --- | --- |
| `bestbuy` | Searches the official Best Buy Products API, `condition=new`. | `BESTBUY_API_KEY` from [developer.bestbuy.com](https://developer.bestbuy.com) |
| `ebay` | eBay Browse API, restricted to `conditionIds:{1000}` (brand new) fixed-price listings; shipping cost is added to the price. | `EBAY_CLIENT_ID` / `EBAY_CLIENT_SECRET` from [developer.ebay.com](https://developer.ebay.com) |
| `custom_json` | Generic adapter for any JSON price API — you map its fields with dotted paths. | endpoint URL |
| `custom_html` | Watches one product page: reads the page's own schema.org/JSON-LD offer, falls back to a `price_regex`. | page URL |
| `sample` | Reads a local JSON fixture. Used by the demo and the tests. | — |

Prefer an official API where one exists, and check a retailer's Terms of Service and
`robots.txt` before pointing `custom_html` at it. Keep the polling interval modest
(15 minutes is plenty for phone prices) so you stay a good citizen.

`custom_json` example — everything is config, no code:

```json
{
  "type": "custom_json",
  "name": "my-retailer",
  "url": "https://api.example.com/v1/search",
  "params": { "q": "iphone", "condition": "new" },
  "headers": { "Authorization": "Bearer ${RETAILER_TOKEN}" },
  "items_path": "data.products",
  "fields": {
    "id": "sku", "title": "name", "price": "price.amount",
    "currency": "price.currency", "url": "links.web", "in_stock": "availability.online"
  }
}
```

Model, storage size, screen size, condition, carrier and new-line terms are parsed out
of the listing title when the source doesn't provide them, so a plain title like
`Apple iPhone 17 Pro Max 256GB Deep Blue (Unlocked) - New` is enough. Sources that do
expose the data (Best Buy's `carrier` attribute, or a `carrier` / `needs_new_line` field
you map in `custom_json`) are trusted over the title, and `custom_html` takes
`"carrier": "unlocked"` from its config for pages that don't say.

### Configuration

`config.json` (falls back to `config.example.json`). See that file for a fully
populated example.

**`criteria`** — what to watch

| Key | Default | Meaning |
| --- | --- | --- |
| `min_screen_inches` | `6.5` | Minimum display size; the model→screen table is built in. |
| `min_storage_gb` | `256` | Minimum storage. |
| `conditions` | `["new"]` | Allowed conditions (`new`, `refurbished`, `used`). |
| `require_unlocked` | `true` | Skip phones locked to a carrier outside `allowed_carriers`. |
| `allowed_carriers` | `["unlocked", "t-mobile"]` | Carriers that still work for you. Sub-brands (`metro`, `cricket`, `visible`…) are treated as their own carriers, since their phones stay locked. |
| `allow_unknown_carrier` | `true` | Keep listings that never state a lock status (most retail listings). Set to `false` to require the word "unlocked". |
| `exclude_new_line_offers` | `true` | Skip prices conditional on a new line, port-in or trade-in. |
| `models` / `exclude_models` | `[]` | Optional allow/deny substrings, e.g. `["Pro Max"]`. |
| `max_price` | `null` | Ignore anything above this price. |
| `currency` | `"USD"` | Listings in another currency are skipped. |
| `require_in_stock` | `true` | Skip out-of-stock listings. |
| `allow_unknown_models` | `false` | Allow phones outside the built-in table when the title states a screen size. |

**`alerts`** — when to push

| Key | Default | Meaning |
| --- | --- | --- |
| `min_drop_percent` | `2.0` | Minimum fall, in percent. |
| `min_drop_amount` | `10.0` | Minimum fall, in currency units. Both must be met. |
| `baseline` | `"best"` | Compare against the lowest price ever seen (`best`) or the previous price (`last`). |
| `notify_cooldown_hours` | `12` | Don't re-alert the same listing within this window unless it falls further. |
| `notify_on_first_seen` | `false` | Alert the first time a matching listing appears. |
| `group_notifications` | `true` | One push per pass instead of one per listing. |
| `max_items_per_notification` | `5` | Listings shown in a grouped push before "…and N more". |

Top-level: `state_file` (price history, default `state/prices.json`) and
`interval_seconds` (default for `watch`).

### Commands

```bash
iphone-watch check                 # one pass now
iphone-watch check --explain       # also show what was skipped and why
iphone-watch check --json          # machine-readable result
iphone-watch check --dry-run       # detect drops, send nothing, keep state unchanged
iphone-watch watch --interval 900  # keep checking (Ctrl-C to stop)
iphone-watch state                 # the tracked price history
iphone-watch models                # screen size per model, ✓ = counts as large
iphone-watch backends              # available source and notifier types
iphone-watch test-notify           # send a test push through every notifier
```

Exit codes: `0` success, `1` a source or notifier failed, `2` bad configuration.

### Running it unattended

**GitHub Actions** — `.github/workflows/iphone-price-watch.yml` runs a check every 30
minutes against `config.json`, keeps the price history in the Actions cache between
runs, and reads credentials from repository secrets. Add these under
*Settings → Secrets and variables → Actions* and it works with no server of your own:

| Secret | Needed for |
| --- | --- |
| `NTFY_TOPIC` | the push itself — required |
| `EBAY_CLIENT_ID`, `EBAY_CLIENT_SECRET` | the three eBay sources |
| `BESTBUY_API_KEY` | the Best Buy source |

Until a source's secret exists that source reports a clear error and the run exits `1`;
the other sources still run. Disable the ones you don't want in `config.json`.

**cron** — one pass per invocation:

```cron
*/15 * * * * cd /opt/iphone-watch && NTFY_TOPIC=… /usr/bin/python3 -m iphone_watch check >> watch.log 2>&1
```

**systemd / container** — run `python -m iphone_watch watch` as a long-lived process; it
handles SIGINT/SIGTERM cleanly and survives individual source failures.

### How a drop is decided

1. Every source is fetched; a failing source is logged and the pass continues.
2. Listings are enriched (model, storage, screen, condition, carrier, activation terms)
   and filtered by `criteria`.
3. Each surviving listing is compared with its own history under `state_file`, keyed by
   `source:listing_id`. A first sighting is recorded, never alerted (unless
   `notify_on_first_seen`).
4. A fall below the baseline that clears **both** `min_drop_percent` and
   `min_drop_amount`, and is outside the cooldown, becomes an alert.
5. Alerts are pushed, then the history is written atomically. If every notifier fails,
   the history is deliberately *not* updated, so the next pass retries the alert instead
   of losing it.

### Tests

```bash
python -m pytest        # 159 tests, no network access required
```
