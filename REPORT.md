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

*Which model and task (detection or classification) and why. A results table on
the same test split: your finetuned model, the pretrained COCO model zero-shot,
and a trivial baseline. What changed, and whether the gap is as large as you
expected.*

## Per-class evaluation and failure modes

*Per-class AP50, or per-class precision/recall and the confusion matrix.
Which class carries the headline number, which one is dragging, and what the
model actually confuses with what. Show where it breaks, not just that it
works.*

## Cost matrix and operating point

*Your euro cost for each kind of error and where each figure came from. The
base rate you assumed. The cost-against-threshold sweep, and the operating
point you chose. State the assumption that would most change your answer if it
were wrong.*

## What a person still has to check

*Your two thresholds, and what share of cases they send to a person. How many
that is per day, how long one takes to check, and how many people that needs.
Is that realistic? Then your design priced against the three alternatives:
doing nothing, having a person check everything, and letting the model decide
on its own.*

## Limitations & next steps

*Real limitations you found, and concretely how you'd address each one with
more time or data. Not generic hedging.*

## Generative AI use disclosure

*Per the syllabus AI Policy: what you used and how, or "no AI content used."*
