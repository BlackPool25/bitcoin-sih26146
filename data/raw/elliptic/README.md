# Elliptic Dataset — data/raw/elliptic

Offline-safe fetch for anchoring synthetic generator (Faker fallback when missing).

## Layout
- `elliptic_txs_features.csv` — 203,769 nodes × 166 features (94 local + 72 aggregated) + 49 timesteps
- `elliptic_txs_edgelist.csv` — 234,355 directed edges (tx → tx)
- `elliptic_txs_classes.csv` — 46,564 labeled nodes (licit / illicit / unknown), covers ~2% illicit
- `SHA256SUMS` — SHA256 hashes for the 3 files (hashlib streaming verify)
- `elliptic.zip` (optional bundle) — zipped archive containing the 3 CSVs

Total: **203K transactions / 234K edges / 49 steps / 166 features** per Elliptic paper.

## Source
- Kaggle: `https://www.kaggle.com/datasets/ellipticco/elliptic-data-set` (dataset `elliptic/elliptic-dataset`)
- Original: Elliptic Data Set (2019), licensed for research — **non-commercial** use only

## License
Non-commercial research only. Do not redistribute without permission. See Kaggle dataset license page and `https://www.elliptic.co/` for terms. Dataset is not bundled in repo by default due to license; fetch at build time or via USB bundle if you have licensed copy.

## Fetch
```bash
# online — try Kaggle CLI then curl mirrors then bundle fallback
python scripts/fetch_elliptic.py --out data/raw/elliptic --verify

# offline — warns and exits 0, fallback Faker will be used
KAGGLE_USERNAME= python scripts/fetch_elliptic.py --out data/raw/elliptic --verify
# -> WARN elliptic missing, fallback Faker will be used (stderr, exit 0)
```

## Verify
```bash
python scripts/fetch_elliptic.py --out data/raw/elliptic --verify
# uses hashlib streaming (8K chunks) against SHA256SUMS; idempotent cache skips if exists+verified
sha256sum -c data/raw/elliptic/SHA256SUMS  # coreutils alternative
```

## Bundle instructions (air-gapped)
1. On online machine with KAGGLE credentials:
   ```bash
   kaggle datasets download -d elliptic/elliptic-dataset -p data/raw/elliptic --unzip
   zip -r bundle/elliptic.zip data/raw/elliptic/elliptic_txs_*.csv
   cp data/raw/elliptic/SHA256SUMS bundle/
   ```
2. Copy `bundle/elliptic.zip` to USB / `bundle/` in repo.
3. On offline target, run fetch — it will auto-extract `bundle/elliptic.zip`:
   ```bash
   python scripts/fetch_elliptic.py --out data/raw/elliptic --verify
   ```
4. Also available as `dist/bundle/elliptic.zip` or `data/bundle/elliptic.zip` fallback paths.

## Offline fallback
If no files present and no network/bundle, `scripts/generate_synthetic.py` uses Faker-only synthetic (50K/80K/5K anchored shape) — see `PROTOTYPE_DECISIONS_FINAL.md §2 Part 2` and `model_card.md` Data section.
