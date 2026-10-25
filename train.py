"""
Assignment 2: training pipeline (skin lesion triage, YOLO11n classification).

Run with:  uv run python main.py train

Steps:
  1. Download the Roboflow dataset (version 2) into datasets/
  2. Finetune yolo11n-cls from its pretrained checkpoint, save to weights/
  3. Predict class probabilities on validation and test
  4. Evaluate against two baselines: zero-shot pretrained model, predict-nothing
  5. Per-class metrics, confusion matrix, dermoscope-frame shortcut check
  6. Cost sweep: one threshold (model alone) and two thresholds (pass/review/fail),
     chosen on VALIDATION at a realistic base rate, reported on TEST
  7. Save everything app.py needs to artifacts/
"""

import json
import shutil
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from PIL import Image
from roboflow import Roboflow
from ultralytics import YOLO

from api_key import load_api_key

WORKSPACE, PROJECT, VERSION = "riteshs-workspace-qkstg", "skin-lesion-classification-sh4sk", 2
DATA = Path("datasets/skin-lesions")
WEIGHTS = Path("weights/skin_yolo11n_cls.pt")
ART = Path("artifacts")
ART.mkdir(exist_ok=True)
WEIGHTS.parent.mkdir(exist_ok=True)

POSITIVE = ["AK", "BCC", "MEL", "SCC"]  # malignant or pre-malignant -> needs a dermatologist in person

# ---------------------------------------------------------------------------
# Business assumptions (justified in REPORT.md, "Cost matrix and operating point")
# ---------------------------------------------------------------------------
APPOINTMENT = 100   # € one in-person dermatologist visit
REVIEW = 4          # € 2 minutes of a dermatologist at ~€120/hour looking at the photo
MISS_COST = {       # € extra cost of finding this cancer months later instead of now
    "MEL": 20_000,  # thin melanoma removed early vs spread melanoma (surgery, scans, immunotherapy)
    "SCC": 3_000,   # bigger surgery, small risk of spread
    "BCC": 1_000,   # grows slowly, bigger excision later
    "AK": 300,      # pre-cancer: cheap to treat now, small chance it becomes SCC
}
BASE_RATE = 0.10    # share of photos in a real inbox that are malignant/pre-malignant
DAILY_PHOTOS = 500  # photos per day the service receives
REVIEWS_PER_DERM_PER_DAY = 120  # 4 hours/day of photo review at 2 minutes each
DERMATOLOGISTS = 2  # dermatologists the service has available for photo review

# ---------------------------------------------------------------------------
# 1. Download dataset
# ---------------------------------------------------------------------------
if not (DATA / "train").exists():
    rf = Roboflow(api_key=load_api_key())
    rf.workspace(WORKSPACE).project(PROJECT).version(VERSION).download("folder", location=str(DATA))

# ---------------------------------------------------------------------------
# 2. Finetune yolo11n-cls
# ---------------------------------------------------------------------------
device = "mps" if torch.backends.mps.is_available() else ("0" if torch.cuda.is_available() else "cpu")
model = YOLO("yolo11n-cls.pt")  # ImageNet-pretrained checkpoint
model.train(
    data=str(DATA.resolve()),
    epochs=40,
    patience=10,       # stop if validation accuracy hasn't improved for 10 epochs
    imgsz=224,         # the dataset is already 224x224
    batch=64,
    flipud=0.5,        # a lesion photo has no "up": vertical flips are as valid as horizontal ones
    device=device,
    seed=0,
    project="runs",
    name="skin",
    exist_ok=True,
)
shutil.copy(Path(model.trainer.best), WEIGHTS)
shutil.copy(Path(model.trainer.save_dir) / "results.csv", ART / "training_curves.csv")
print(f"Saved best weights to {WEIGHTS}")


# ---------------------------------------------------------------------------
# 3. Probabilities on validation and test
# ---------------------------------------------------------------------------
def has_frame(path):
    """True if the top-left corner is black: the round border of a dermoscope."""
    return bool(np.asarray(Image.open(path).convert("L"))[:10, :10].mean() < 20)


def predict_split(m, split):
    files = sorted((DATA / split).glob("*/*"))
    rows = []
    for i in range(0, len(files), 64):
        for f, r in zip(files[i:i + 64], m.predict([str(f) for f in files[i:i + 64]], imgsz=224, verbose=False)):
            probs = r.probs.data.cpu().numpy()
            rows.append({"file": str(f), "true": f.parent.name, "frame": has_frame(f),
                         **{m.names[k]: float(probs[k]) for k in m.names}})
    df = pd.DataFrame(rows)
    classes = list(m.names.values())
    df["pred"] = df[classes].idxmax(axis=1)
    df["score"] = df[POSITIVE].sum(axis=1)         # P(malignant or pre-malignant)
    df["positive"] = df["true"].isin(POSITIVE).astype(int)
    return df


best = YOLO(str(WEIGHTS))
CLASSES = list(best.names.values())
val, test = predict_split(best, "valid"), predict_split(best, "test")
val.to_csv(ART / "predictions_valid.csv", index=False)
test.to_csv(ART / "predictions_test.csv", index=False)


# ---------------------------------------------------------------------------
# 4-5. Metrics, baselines, per class
# ---------------------------------------------------------------------------
def per_class(df, pred_col="pred"):
    out = []
    for c in CLASSES:
        tp = ((df[pred_col] == c) & (df["true"] == c)).sum()
        p = (df[pred_col] == c).sum()
        n = (df["true"] == c).sum()
        out.append({"class": c, "malignant": c in POSITIVE, "test_images": int(n),
                    "precision": round(tp / p, 3) if p else 0.0, "recall": round(tp / n, 3)})
    return pd.DataFrame(out)


per_class(test).to_csv(ART / "per_class_test.csv", index=False)
pd.crosstab(test["true"], test["pred"]).reindex(index=CLASSES, columns=CLASSES, fill_value=0) \
    .to_csv(ART / "confusion_test.csv")

# Zero-shot baseline: the ImageNet-pretrained yolo11n-cls has 1,000 everyday
# classes and none of them is a skin lesion, so it cannot output any of ours.
zs = YOLO("yolo11n-cls.pt")
zs_labels = [zs.names[int(r.probs.top1)] for r in
             zs.predict([f for f in test["file"]], imgsz=224, verbose=False)]
zs_top = pd.Series(zs_labels).value_counts().head(5)

# Trivial baseline: always say the most common class in TRAINING
majority = max(CLASSES, key=lambda c: len(list((DATA / "train" / c).glob("*"))))
baselines = {
    "finetuned yolo11n-cls": {"accuracy": round((test["pred"] == test["true"]).mean(), 3)},
    f"trivial: always '{majority}' (refers nobody)": {"accuracy": round((test["true"] == majority).mean(), 3)},
    "zero-shot ImageNet yolo11n-cls": {"accuracy": 0.0},
}
print("\nTest accuracy:", baselines)
print("Zero-shot model's most common labels on lesions:\n", zs_top)

frame_check = {
    f"{'with' if fr else 'without'} frame": {
        "images": int(len(g)),
        "share_malignant": round(g["positive"].mean(), 3),
        "accuracy": round((g["pred"] == g["true"]).mean(), 3),
        "benign_flagged_malignant": round((g.loc[g["positive"] == 0, "score"] >= 0.5).mean(), 3),
        "malignant_recall": round((g.loc[g["positive"] == 1, "score"] >= 0.5).mean(), 3),
    } for fr, g in test.groupby("frame")
}
print("Dermoscope-frame check:", frame_check)


# ---------------------------------------------------------------------------
# 6. Costs. Every case gets one of three outcomes:
#    score <  low          -> pass   (sent home)
#    low <= score < high   -> review (dermatologist looks at the photo)
#    score >= high         -> fail   (in-person appointment)
# The test/valid sets are 55-57% malignant; a real inbox is ~10%. Each case is
# weighted so positives count for BASE_RATE of the total, then costs are per 1,000 photos.
# ---------------------------------------------------------------------------
def case_weights(df):
    n_pos, n_neg = df["positive"].sum(), (1 - df["positive"]).sum()
    return np.where(df["positive"] == 1, BASE_RATE / n_pos, (1 - BASE_RATE) / n_neg)


def outcome_costs(df):
    """€ for each case under each outcome (the reviewing dermatologist is assumed to decide correctly)."""
    miss = df["true"].map(MISS_COST).fillna(0).values
    pos = df["positive"].values
    return {"pass": miss, "review": REVIEW + pos * APPOINTMENT, "fail": np.full(len(df), APPOINTMENT)}


def evaluate(df, low, high):
    w, c, s = case_weights(df), outcome_costs(df), df["score"].values
    passed, failed = s < low, s >= high
    review = ~passed & ~failed
    cost = np.where(passed, c["pass"], np.where(failed, c["fail"], c["review"]))
    pos = df["positive"].values == 1
    return {
        "low": round(low, 2), "high": round(high, 2),
        "cost_per_1000": round(1000 * float(np.sum(w * cost)), 1),
        "review_share": round(float(np.sum(w * review)), 4),
        "missed_cancer_share": round(float(np.sum(w * (passed & pos)) / BASE_RATE), 4),
        "missed_melanoma": int(np.sum(passed & (df["true"].values == "MEL"))),
    }


grid = np.round(np.arange(0.0, 1.01, 0.01), 2)

# One threshold, no person: below t -> pass, above -> fail
single_val = pd.DataFrame([evaluate(val, t, t) for t in grid])
single_test = pd.DataFrame([evaluate(test, t, t) for t in grid])
t_alone = float(single_val.loc[single_val["cost_per_1000"].idxmin(), "low"])

# Two thresholds: try every pair low <= high on validation, keep the cheapest one
# that sends no more photos to review than the available dermatologists can check
pairs = pd.DataFrame([evaluate(val, lo, hi) for lo in grid for hi in grid if hi >= lo])


def best_within(n_derms):
    cap = n_derms * REVIEWS_PER_DERM_PER_DAY / DAILY_PHOTOS
    ok = pairs[pairs["review_share"] <= cap + 1e-9]
    return ok.loc[ok["cost_per_1000"].idxmin()]


best_pair = best_within(DERMATOLOGISTS)
LOW, HIGH = float(best_pair["low"]), float(best_pair["high"])

# Same choice for other staffing levels, to show what each extra dermatologist is worth
staffing_options = []
for n in [1, 2, 3, DAILY_PHOTOS / REVIEWS_PER_DERM_PER_DAY]:
    b = best_within(n)
    staffing_options.append({"dermatologists": round(n, 2), **evaluate(test, float(b["low"]), float(b["high"]))})
staffing_options = pd.DataFrame(staffing_options)
print(staffing_options.to_string(index=False))

ours = evaluate(test, LOW, HIGH)
alternatives = {
    "do nothing (send everyone home)": evaluate(test, 1.01, 1.01),
    "dermatologist checks every photo": evaluate(test, 0.0, 1.01),
    f"model alone (threshold {t_alone})": evaluate(test, t_alone, t_alone),
    f"model + review band ({LOW}-{HIGH})": ours,
}
reviews_per_day = ours["review_share"] * DAILY_PHOTOS
staffing = {
    "daily_photos": DAILY_PHOTOS,
    "reviews_per_day": round(reviews_per_day, 1),
    "minutes_per_review": 2,
    "reviews_per_dermatologist_per_day": REVIEWS_PER_DERM_PER_DAY,
    "dermatologists_available": DERMATOLOGISTS,
    "dermatologists_needed": round(reviews_per_day / REVIEWS_PER_DERM_PER_DAY, 2),
    "everyone_reviewed_dermatologists": round(DAILY_PHOTOS / REVIEWS_PER_DERM_PER_DAY, 2),
}
print("\nChosen on validation: low", LOW, "high", HIGH, "| model-alone threshold", t_alone)
print(pd.DataFrame(alternatives).T.to_string())
print("Staffing:", staffing)

# ---------------------------------------------------------------------------
# 7. Save for the app
# ---------------------------------------------------------------------------
single_test.to_csv(ART / "cost_sweep_test.csv", index=False)
single_val.to_csv(ART / "cost_sweep_valid.csv", index=False)
pd.DataFrame(alternatives).T.rename_axis("strategy").to_csv(ART / "alternatives_test.csv")
staffing_options.to_csv(ART / "staffing_options_test.csv", index=False)
json.dump({
    "dataset": {"workspace": WORKSPACE, "project": PROJECT, "version": VERSION},
    "classes": CLASSES, "positive_classes": POSITIVE,
    "low": LOW, "high": HIGH, "model_alone_threshold": t_alone,
    "appointment": APPOINTMENT, "review": REVIEW, "miss_cost": MISS_COST,
    "base_rate": BASE_RATE, "daily_photos": DAILY_PHOTOS,
    "reviews_per_derm_per_day": REVIEWS_PER_DERM_PER_DAY, "dermatologists": DERMATOLOGISTS,
    "baselines": baselines, "zero_shot_top_labels": zs_top.to_dict(),
    "frame_check": frame_check, "staffing": staffing,
    "training": {"model": "yolo11n-cls", "epochs_max": 40, "patience": 10, "imgsz": 224,
                 "batch": 64, "device": device, "flipud": 0.5},
}, open(ART / "config.json", "w"), indent=2)
print(f"\nSaved artifacts to {ART}/")
