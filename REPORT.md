# Assignment 2 Report

- **Name**: Adolfo Gutierrez de GAndarilla Dominguez
- **Student ID**: 19003
- **Email**: fgutierrezde.ieu2022@student.ie.edu
- **Group**: BBADBA 5B

## Business problem, and the cost of being wrong

> This is a university exercise. The model is not a medical device and must
> not be used to diagnose anyone.

**The decision.** A teledermatology service receives photos of skin lesions
(moles, spots) from patients who are worried about them. Today a
dermatologist looks at every photo and decides whether the patient needs an
in-person appointment. The model looks at the photo first and gives each
case one of three outcomes:

| Outcome | What happens | Who acts |
|---|---|---|
| 🟢 **Pass** | Probably benign. The patient gets advice to watch the lesion and send a new photo if it changes. No appointment. | Automatic message |
| 🟡 **Review** | The model isn't sure. A dermatologist looks at the photo (about 2 minutes) and decides. | Dermatologist |
| 🔴 **Fail** | Probably malignant. The patient gets a priority in-person appointment. | Clinic booking |

**Positive class = "malignant or pre-malignant"**: melanoma (MEL), basal
cell carcinoma (BCC), squamous cell carcinoma (SCC) and actinic keratosis
(AK, pre-cancerous). These are the lesions a dermatologist must see in
person. The other four classes are benign: nevus/mole (NV), benign keratosis
(BKL), dermatofibroma (DF) and vascular lesion (VASC). The model's score for
a case is the sum of the probabilities of the four positive classes.

**Why the two mistakes cost very different amounts:**

- **False negative (cancer sent home).** The diagnosis is delayed until the
  patient comes back, often months later. For melanoma this is the
  difference between removing a thin lesion in a short outpatient procedure
  and treating a melanoma that has spread, which can mean surgery, scans and
  years of immunotherapy, with a much lower survival rate. The other cancers
  grow more slowly, so a delay costs less, but it still means bigger surgery.
- **False positive (benign lesion sent to an appointment).** One unnecessary
  dermatologist visit and some worry for the patient. That is roughly the
  price of a consultation.

So a missed melanoma is **hundreds of times** more expensive than an
unnecessary appointment, and the cost of a miss also depends on **which**
cancer is missed. That is why the costs are set per class (section *Cost
matrix and operating point*), and why melanoma gets its own analysis even
though it is grouped with the other positives.

**What this framing decides later:**

1. **The metric that matters is recall on the positive class, above all on
   melanoma**, not accuracy. Accuracy treats a missed melanoma and an
   unnecessary visit as the same mistake.
2. **The thresholds are chosen by minimising expected cost**, which will push
   them low: the model should send a case on whenever there is a real chance
   it is cancer.
3. **The base rate must be the real one, not the dataset's.** The dataset has
   far more cancers than a real teledermatology inbox (see *Dataset*), so
   costs are re-weighted to a realistic share of positives before choosing a
   threshold.
4. **The review band is limited by dermatologist time.** A threshold that
   sends half the photos to a person is not a solution if there aren't
   enough dermatologists to look at them.

## Dataset

- **Workspace / project / version:** `riteshs-workspace-qkstg` /
  `skin-lesion-classification-sh4sk` / **version 2**
- **Link:** <https://universe.roboflow.com/riteshs-workspace-qkstg/skin-lesion-classification-sh4sk/dataset/2>
- **Licence:** CC BY 4.0, public, used as it is (not forked).
- **Task:** image classification, 8 classes, colour images resized to 224×224.
- **One image** is a close-up of a single skin lesion. The class names
  (AK, BCC, BKL, DF, MEL, NV, SCC, VASC) are those of the ISIC 2019
  challenge, the main public collection of labelled skin-lesion images.

**Why this dataset and not another one.** I compared the public skin-cancer
datasets on Roboflow Universe:

- The largest one (HAM10000, 9,900 images) is stored in **grayscale**. Colour
  is one of the main signs a dermatologist uses (the "C" in the ABCDE rule:
  several colours inside one lesion), so I rejected it.
- Others had fewer than 2,000 images, or mixed in an "Unlabeled" class.
- **Version 2** of this project has **no augmentation**, so every image is a
  real one. Version 1 adds flipped/rotated copies to the training set, which
  makes the dataset look bigger than it is.

**Does it serve the problem or just resemble it?** It covers exactly the
decision: the classes include the cancers that need an appointment and the
benign lesions that don't. But there is one important mismatch, discussed in
the next section: these are mostly **dermoscopic** images (taken through a
magnifying lens in a clinic), while patients would send **phone photos**.

## What the dataset's composition implies

I downloaded version 2 and counted the images myself (one image = one
lesion = one label, since this is classification).

| Class | Malignant? | Train | Valid | Test | Total | Share |
|---|---|---|---|---|---|---|
| AK – actinic keratosis | 🟠 pre-malignant | 455 | 130 | 66 | 651 | 12.9% |
| BCC – basal cell carcinoma | 🔴 yes | 562 | 185 | 74 | 821 | 16.3% |
| MEL – melanoma | 🔴 yes | 582 | 170 | 83 | 835 | 16.6% |
| SCC – squamous cell carcinoma | 🔴 yes | 405 | 112 | 62 | 579 | 11.5% |
| NV – nevus (mole) | 🟢 no | 590 | 171 | 95 | 856 | 17.0% |
| BKL – benign keratosis | 🟢 no | 570 | 151 | 85 | 806 | 16.0% |
| DF – dermatofibroma | 🟢 no | 156 | 54 | 29 | 239 | 4.7% |
| VASC – vascular lesion | 🟢 no | 197 | 33 | 23 | 253 | 5.0% |
| **Total** | | **3,517** | **1,006** | **517** | **5,040** | |

- **Split:** 70% / 20% / 10%. Every class appears in every split.
- **Image size:** all 224×224 pixels, colour.
- **Object size:** this is classification, so there are no boxes. Every image
  is a close-up centred on one lesion, which fills most of the frame. The
  catch is the resolution: at 224×224, fine details a dermatologist looks for
  (small dots, thin lines) are partly lost.

**What this implies**

1. **Positives are far over-represented.** 57% of the images (and 55% of the
   test set: 285 of 517) are malignant or pre-malignant. In a real
   teledermatology inbox most photos are of harmless moles, and only a small
   share are cancer. The dataset was clearly balanced on purpose (NV, the most
   common lesion in real life, has about the same count as melanoma). So
   **costs measured directly on the test set would be wrong**: before choosing
   thresholds I re-weight the test cases to a realistic base rate (see *Cost
   matrix and operating point*).
2. **Some per-class numbers are too thin to trust.** The test set has only
   **23 VASC and 29 DF** images. One more or one fewer mistake moves their
   recall by 3–4 points, so I won't draw conclusions about those two classes.
   Melanoma (83 test images) is enough for a rough number, but its recall
   still has an uncertainty of several points.
3. **Duplicates across splits.** File names never repeat across splits, but
   comparing the centre of every image I found **6 near-identical pairs in
   different splits**, the same lesion saved under two ISIC numbers. **5 of
   them are test images that also appear in training** (4 SCC, 1 BKL). That is
   1% of the test set, so it inflates the results only slightly, but SCC's
   test number is the most affected (4 of its 62 test images were seen in
   training).
4. **A possible shortcut: the dermoscope frame.** A third of the images (1,685)
   have the round black border of a dermoscope. It is much more common in the
   cancer classes than in the benign ones:

   | AK | BCC | SCC | MEL | DF | BKL | VASC | NV |
   |---|---|---|---|---|---|---|---|
   | 53% | 45% | 40% | 37% | 27% | 26% | 19% | 12% |

   A model could learn "black frame → cancer" instead of looking at the
   lesion. I check this after training (*Per-class evaluation and failure
   modes*).
5. **The test set doesn't look like production.** These are dermoscopic
   images taken by clinicians: lit evenly, in focus, lesion centred. Patients
   would send phone photos, with shadows, blur, hair and different skin
   tones. **So the test results are an upper bound** on how well the model
   would really work, and I can't conclude it is ready for patient photos.

## Finetuning and baselines

**Task: image classification**, because each photo shows one lesion and the
decision is about the whole photo (does this lesion need a dermatologist?).
There is nothing to locate, so boxes would add work without adding
information. **Model: `yolo11n-cls`**, the smallest YOLO11 classifier
(1.5 million parameters), finetuned from its ImageNet-pretrained checkpoint.
A small model is enough for 3,517 training images and trains quickly.

**Where and how I trained it.** On my laptop (MacBook, Apple M3, 16 GB),
using the Mac GPU (PyTorch MPS), in about 14 minutes:
`epochs=40, patience=10, imgsz=224, batch=64, seed=0, flipud=0.5`, with all
other settings at the Ultralytics defaults. I turned on vertical flips
because a photo of a lesion has no "up", so a flipped lesion is still a
realistic example. The best epoch (chosen on validation accuracy) is saved
as `weights/skin_yolo11n_cls.pt`.

**Results on the same test split (517 images):**

| Model | 8-class accuracy | What it does |
|---|---|---|
| **Finetuned yolo11n-cls** | **66.2%** (top-5: 98.6%) | Learns the 8 lesion types |
| Trivial baseline: always "NV" | 18.4% | Calls everything a mole (the most common training class), so it **refers nobody** |
| Pretrained model, zero-shot | 0% | Its 1,000 ImageNet classes contain no skin lesions. It called 210 of the 517 lesions a **"tick"**, 75 "face powder" and 52 "velvet" |

For the business decision (malignant vs benign), the finetuned model's
malignant score has a **ROC AUC of 0.897** on the test set: it ranks a random
cancer above a random benign lesion about 90% of the time.

**Was the gap as large as expected?** The gap to the baselines is huge, as
expected: the zero-shot model simply has no way to name a lesion, and the
trivial one never refers anybody (it would send every cancer home). What
surprised me is that 66% is **lower than I hoped** for 8 classes. Validation
accuracy stopped improving at about 65% after ~30 epochs, so more epochs
would not help much. The limits are probably the small 224-pixel images and
the classes that genuinely look alike (see next section).

## Per-class evaluation and failure modes

**Positive class:** malignant or pre-malignant (AK + BCC + MEL + SCC).

**Per class (test set):**

| Class | Malignant? | Test images | Precision | Recall |
|---|---|---|---|---|
| VASC | no | 23 | 0.92 | **1.00** |
| NV | no | 95 | **0.81** | 0.70 |
| SCC | yes | 62 | 0.67 | 0.69 |
| BKL | no | 85 | 0.56 | 0.67 |
| AK | yes | 66 | 0.66 | 0.67 |
| BCC | yes | 74 | 0.57 | 0.65 |
| DF | no | 29 | 0.78 | 0.62 |
| **MEL** | **yes** | **83** | 0.61 | **0.52** |

**Confusion matrix (rows = true class, columns = predicted):**

| true \ pred | AK | BCC | BKL | DF | MEL | NV | SCC | VASC |
|---|---|---|---|---|---|---|---|---|
| AK | **44** | 7 | 10 | 0 | 1 | 0 | 4 | 0 |
| BCC | 10 | **48** | 3 | 3 | 4 | 0 | 6 | 0 |
| BKL | 3 | 5 | **57** | 1 | 10 | 4 | 5 | 0 |
| DF | 1 | 5 | 0 | **18** | 1 | 1 | 2 | 1 |
| MEL | 3 | 5 | **17** | 0 | **43** | **10** | 4 | 1 |
| NV | 1 | 5 | 10 | 1 | 12 | **66** | 0 | 0 |
| SCC | 5 | 9 | 4 | 0 | 0 | 1 | **43** | 0 |
| VASC | 0 | 0 | 0 | 0 | 0 | 0 | 0 | **23** |

**Which class carries the headline number.** VASC (100% recall: vascular
lesions are red/purple, easy to tell apart) and NV (the highest precision).
But VASC has only 23 test images, so its perfect score is not reliable.

**Which class drags it down, and it is the one that matters most: melanoma.**
Recall is only **52%**. Of 83 melanomas, **28 were called benign** (17
benign keratosis, 10 mole, 1 vascular lesion). This is the dangerous mistake: melanoma, BKL and
NV are all brown, irregular spots, and at 224×224 pixels the fine details
that tell them apart are partly lost. Worse, some melanomas get a malignant
score **close to 0** (e.g. 0.0005 and 0.0013): the model is confidently
wrong, not just unsure. That is why no threshold can safely send people home
(see the next sections).

**Mistakes that don't matter for the decision.** Many errors are between
the malignant classes themselves (AK, BCC and SCC confused with each other
in 41 cases). For the business they are harmless: all of them lead to an
appointment. For the binary decision at a 0.5 cut-off the model catches
**83.5% of malignant lesions** and correctly clears **79.7% of benign ones**.

**The dermoscope-frame shortcut is real.** I compared test images with and
without the black dermoscope border:

| | Images | Benign flagged as malignant (score ≥ 0.5) | Malignant caught |
|---|---|---|---|
| Without frame | 356 | **14%** | 81% |
| With frame | 161 | **51%** | 87% |

A benign lesion photographed **with the frame is almost 4 times more likely**
to be flagged as cancer. The model partly learned "black frame → cancer",
because cancers have the frame more often in this dataset. Patients' phone
photos have no frame, so this shortcut won't help in production, and part
of the model's apparent skill will disappear.

## Cost matrix and operating point

**Costs per case (my assumptions):**

| Outcome | Benign lesion | Malignant lesion |
|---|---|---|
| 🟢 Pass (sent home) | €0 (correct) | **missed cancer**: MEL €20,000 · SCC €3,000 · BCC €1,000 · AK €300 |
| 🟡 Review (dermatologist looks at the photo) | €4 | €4 + €100 appointment |
| 🔴 Fail (appointment) | €100 (wasted visit) | €100 |

Where each figure comes from:

- **€100 appointment:** roughly the price of one private dermatology
  consultation in Spain. For a correctly referred cancer I don't count the
  treatment, because it would be needed anyway.
- **€4 review:** 2 minutes of a dermatologist's time at about €120/hour.
- **Missed cancer:** the extra cost of finding it months later instead of now.
  Melanoma is by far the highest: caught early, it is a short excision;
  caught late, it can mean major surgery, scans and immunotherapy, and a
  much lower chance of survival. SCC can spread but rarely does; BCC grows
  slowly and almost never spreads (a later diagnosis mostly means a bigger
  excision); AK is a pre-cancer that is cheap to treat. I chose round
  numbers that keep this order and size, not exact prices.
- I assume the **reviewing dermatologist decides correctly**. In reality
  they would miss some cancers from a photo (see Limitations).

**Base rate: 10%** of the photos the service receives are malignant or
pre-malignant (melanoma about 3%, since it is 29% of the positives in the
test set). The test set is 55% malignant, so every test image is
**re-weighted** so that positives count for 10% of the total, and costs are
given per 1,000 photos.

**The sweep.** For one threshold (model alone: below → home, above →
appointment) I tried every threshold from 0 to 1 in steps of 0.01 on the
**validation** set and kept the cheapest. For two thresholds I tried every
pair (5,151 pairs) on validation, kept the cheapest one that fits the
dermatologists available (next section), then measured it **once** on the
test set. The dashboard shows the cost curve with the chosen point marked.

**What the sweep found:**

- **Model alone:** the cheapest threshold is **0.01**, which sends almost
  everybody to an appointment, and it still costs **€92,240 per 1,000
  photos**. Even at 0.01 it sends 4 of the 83 test melanomas home, because
  the model is confidently wrong about them.
- **Chosen operating point (2 dermatologists): pass below 0.01, appointment
  from 0.92, review in between.** On the test set this costs **€46,950 per
  1,000 photos**: 35.8% of photos pass, 50.9% go to review and 13.2% go
  straight to an appointment.

**The assumption that would most change the answer** is the cost of a missed
melanoma, together with the base rate. I re-ran the choice with other values:

| Change | Thresholds (pass / appointment) | Test cost per 1,000 |
|---|---|---|
| As assumed (MEL €20,000, base rate 10%) | 0.01 / 0.92 | €46,950 |
| MEL miss €5,000 | 0.04 / 0.99 (more people pass) | €28,671 |
| MEL miss €50,000 | **nobody passes** / 0.04 | €57,931 |
| Base rate 5% | 0.01 / 0.91 | €29,190 |
| Base rate 20% | **nobody passes** / 0.06 | €58,983 |
| Review €10 or €20 instead of €4 | 0.01 / 0.92 (no change) | €50,007 / €55,101 |

So: **if a missed melanoma costs more than about €50,000, or if more than
about 20% of photos are cancers, the model should never send anyone home**,
and its only job is to choose who gets an appointment directly. The price of
a review hardly matters.

## What a person still has to check

**Thresholds: pass below 0.01, appointment from 0.92, review in between.**

- **Volume:** I assume the service receives **500 photos a day**.
- **Review share:** **50.9%** of photos → about **255 photos a day**.
- **Time:** about **2 minutes** per photo → 8.5 hours of dermatologist time a day.
- **People:** if each dermatologist spends 4 hours a day on photo review
  (120 photos), that needs **2.1 dermatologists**.
- **Is it realistic?** I assumed the service has **2 dermatologists** for
  review and chose the thresholds so the review share fits that on the
  validation set (≤ 48%). On the test set it came out slightly higher
  (51%, or 2.1 people), so in practice the team would be **at capacity**
  with no slack for busy days. It is realistic only if both dermatologists
  really commit 4 hours a day.

**Compared with the alternatives (test set, 10% base rate, per 1,000 photos):**

| Strategy | Cost | Reviewed | Cancers sent home | Melanomas sent home (of 83) |
|---|---|---|---|---|
| Do nothing (everyone home) | €680,632 | 0% | 100% | 83 |
| Model alone (threshold 0.01) | €92,240 | 0% | 1.4% | 4 |
| **Model + review band (2 dermatologists)** | **€46,950** | **51%** | **1.4%** | **4** |
| Dermatologist checks every photo | **€14,000** | 100% | 0% | 0 |

And the best design for each number of reviewing dermatologists:

| Dermatologists | Thresholds | Cost per 1,000 | Reviewed | Melanomas sent home |
|---|---|---|---|---|
| 1 | 0.01 / 0.21 | €68,441 | 26% | 4 |
| **2 (chosen)** | **0.01 / 0.92** | **€46,950** | **51%** | **4** |
| 3 | nobody passes / 0.43 | €33,772 | 71% | 0 |
| 4.2 (everything) | — | €14,000 | 100% | 0 |

**What this means.** With these costs the honest conclusion is that **the
model does not beat a dermatologist looking at every photo**. A review costs
€4 and a missed melanoma €20,000, and the model gives some melanomas a score
near 0, so letting it send people home is always more expensive than paying
a dermatologist to look. The model is still very useful when dermatologists
are **scarce**: compared with doing nothing it cuts the cost by 93%, and it
puts the clearest cancers (13% of photos) straight into appointments.

**My recommendation.** Each extra reviewing dermatologist saves roughly
€13,000–21,000 per 1,000 photos (€6,500+ a day at 500 photos), while 4 hours
of their time costs about €480 a day. So the service should **staff the
review**: with 3 dermatologists no melanoma in the test set is sent home. I
would **not ship the "pass" band** (sending patients home automatically)
until the model's melanoma recall is much better.

## Limitations & next steps

- **Confident mistakes on melanoma.** 28 of 83 melanomas are called benign,
  some with a score near 0. *Next step:* train at a higher resolution (e.g.
  384 or 512 pixels, from the original ISIC images) and try `yolo11s-cls`;
  give melanoma a higher weight in the training loss so mistaking it costs
  the model more.
- **The dermoscope-frame shortcut.** Benign lesions with a frame are flagged
  as cancer 51% of the time vs 14% without. *Next step:* crop or mask the
  black border before training and testing, so the model has to look at the
  lesion.
- **Dermoscope images, not phone photos.** The test set doesn't look like
  what patients send, so all results are an upper bound. *Next step:* before
  any real use, collect a few hundred phone photos with a confirmed
  diagnosis and measure the model on those.
- **The costs and the base rate are my assumptions.** The answer changes if
  a missed melanoma costs more than ~€50,000 or the base rate is above ~20%.
  *Next step:* get the real share of cancers among the photos the service
  receives, and the real cost of late vs early treatment from the clinic.
- **I assume the reviewing dermatologist is always right.** Judging from a
  photo, they would miss some cancers, which makes "review" more expensive
  than I assume. *Next step:* add the dermatologist's own miss rate on
  photos to the cost of the review outcome.
- **Small classes and small test set.** DF (29) and VASC (23) test images are
  too few to trust their numbers, and the chosen thresholds sit at the edge
  of the score range (0.01, 0.92), where a handful of images decide the
  result. *Next step:* use cross-validation and report confidence intervals.
- **Five test images also appear in training** (4 SCC, 1 BKL). *Next step:*
  remove the near-duplicates from the test set and report both numbers.

## Generative AI use disclosure

I used **Claude (Anthropic), through Claude Code**, throughout this
assignment, as allowed by the professor for this assignment. It helped me
compare and choose the Roboflow dataset, analyse the dataset (class counts,
duplicates and the dermoscope-frame check), write `train.py` and `app.py`,
run the training and the cost sweeps, test the dashboard, and draft this
report. I reviewed the framing, the cost assumptions, the choice of 2
reviewing dermatologists and the conclusions, and I can explain them.
