# `f`, `R`, `P(ruin)`, `P(dd≥50%)`, RISK-01, GAP-02 — three languages
# ‏`f` و `R` و احتمال الإفلاس واحتمال الهبوط — بثلاث لغات

**Date / التاريخ:** 2026-07-29

**Contents:** [Part 1 — Professional English](#part-1--professional-english) ·
[Part 2 — Baby English](#part-2--baby-english) · [Part 3 — العربية](#part-3--العربية)

---

# ⚠️ READ FIRST — THE GOVERNANCE ANSWER

**You asked whether a position-sizing decision layer was added to your system without your approval.**

**It was not. I verified this in the code, and here is the proof:**

| check | result |
|---|---|
| does the engine compute a position size? | **No.** `strategy.py:424` — `pnl = pnl_points × pv`. There is no quantity term anywhere. |
| does the engine know your account balance? | **No.** There is no capital, account or equity input. |
| the standing constraint in `optimize/TASK.md:24` | *"1 contract only, NQ, point value $20 (**standing constraint — no scaling/ladder**)"* |
| where does `f` exist? | **5 offline research scripts only** — `study_kelly.py`, `study_kelly_pnldd.py`, `study_ruin.py`, `risk_recut_v2.py`, `risk_ruin_v3.py` |
| what the sizing workstream says about itself | SIZE-00, its own summary line: *"**Nothing adopted; production byte-identical; $0.**"* |

**Your description of the system is exactly correct:** *if the multi-layer algorithm approves the entry,
you enter — one contract, whatever the price.* That is what the code does. Nothing was implanted.

**But you have found something real, and it is more important than the missing permission.**

The entire sizing workstream — SIZE-00 through SIZE-05, RISK-01, and **RISK-02 which I closed for you
today** — answers a question your system **cannot act on**. Every one of those studies assumes you can
choose *how much* to bet. You cannot. You bet one contract or you bet nothing.

**So `f` is not a setting you forgot about. It is a hypothetical in a research simulation.** And I should
have told you that when I closed #3, instead of handing you a recommendation of "risk 0.3% on gas" for a
system with no risk-percentage dial.

### The same finding, translated into your actual system

The right question for a 1-contract system is not *"what fraction do I risk?"* but **"can my account
survive the worst single trade?"** Same data, re-expressed:

| market | worst single trade, **1 contract** | which timeframe |
|---|---:|---|
| **CL** (oil) | **−$7,710** | 4h |
| **NQ** (Nasdaq) | **−$7,420** | 15m |
| SI (silver) | −$3,850 | 2h |
| GC (gold) | −$3,760 | 2m |
| **NG** (gas) | **−$3,660** | 4h |
| ES (S&P) | −$3,038 | 4h |
| YM (Dow) | −$2,525 | 4h |
| RTY (Russell) | −$2,250 | 15m |
| HG (copper) | −$1,650 | 2h |
| **all nine on their worst day** | **−$35,863** | |

⭐ **Look at natural gas.** In "risk units" it was the catastrophe of the whole report — **183×**. In
actual dollars on one contract it is **fifth, at −$3,660**. Ordinary.

**Why the difference?** Because `R` divides by the stop size, and gas's stop is *microscopic*
(0.001017). A perfectly normal dollar loss becomes an enormous multiple of a tiny stop. The 183× is real
arithmetic, but it only becomes *dangerous* in a system that would have sized the position **up** to make
that tiny stop equal 1% of capital — and then been destroyed by the gap.

**Your system never does that.** So RISK-02's headline — *"natural gas caps the whole book"* — is an
artifact of a sizing model you do not use.

**What survives, and matters to you:** with one contract, **your true constraint is about $7,700 from a
single trade, and about $35,863 if everything goes wrong at once.** On a $10,000 account, one bad oil
trade is **77% of your money.** That is the real, actionable number — and it is nothing to do with `f`.

**Your instinct to stop and ask was correct.** I was answering the wrong question carefully.

---

# PART 1 — PROFESSIONAL ENGLISH

## 1.1 `f` — the risk fraction

**Definition.** The proportion of total capital deliberately placed at risk on a single trade, such that
a full adverse excursion to the hard stop realises a loss of exactly `f × capital`.

**Status in this project: NOT IMPLEMENTED.** It is a free parameter swept in Monte-Carlo sizing studies.
The production engine has no position-sizing stage; it evaluates a fixed single contract.

**Mechanics (had it been implemented).** Given capital `C`, hard stop distance `s` in points, and point
value `v`, the position size would be `n = (f · C) / (s · v)`. For NQ with `s = 109.7`, `v = $20`, one
contract carries $2,194 of risk; `f = 1%` on $100,000 therefore admits `n = 0.456` contracts — i.e. the
smallest tradeable unit already exceeds the intended risk budget.

> **That last observation is the real reason `f` is unusable here, independent of anything else:** at
> realistic account sizes, one contract *is* the minimum granularity, and it frequently represents more
> risk than any sensible fraction would allow. Fractional sizing is a large-account instrument.

## 1.2 `R` — the risk multiple

**Definition.** A completed trade's result expressed in units of its own intended risk:
`R = pnl_points / sl_hard`. A trade closing exactly at its hard stop yields `R = −1`.

**Purpose.** Scale-free pooling. Hard stops across the book span four orders of magnitude (NG 0.001017 →
YM 10.246); raw points or dollars cannot be aggregated across instruments, whereas `R` can.

### ⚠️ 1.2.1 This is NOT the `R` you remember

You are right to query it. There are **two distinct quantities** in this project sharing the letter:

| | **R:R** (early, yours) | **R** (sizing studies, 2026-07) |
|---|---|---|
| meaning | **risk-to-reward ratio** — target distance ÷ stop distance | **risk multiple** — realised result ÷ stop distance |
| computed | **before** the trade, from parameters | **after** the trade, from its outcome |
| typical value | `1.2 : 1` | `−1`, `+2.4`, `−183` |
| where in the repo | `optimize/sl_tp_bounds.py`, `docs/PLAYBOOK_abdulfattah1.md:102` | `RISK-01`, `RISK-02` only |
| is it in the engine? | **yes** — it is what tuning SL/TP produces | **no** — offline analysis only |

`R:R ≈ 1.2:1 with a 64% win-rate is the edge` (PLAYBOOK line 102) is **your** R. It is a *design ratio*.
The sizing `R` is a *result measure* introduced on 2026-07-22 and used in exactly two documents. **The
collision is unfortunate and undocumented; this note is the first place both are defined together.**

## 1.3 `P(ruin)`

**Definition.** The probability that equity reaches zero at least once over a defined horizon — here
1,000 sequential trades, estimated over 4,000 bootstrap paths. Ruin is **absorbing**: the path terminates.

**Methodological note.** The inherited Z2/Z4 simulator computed `cumprod(max(1 + f·R, 1e-9))` and
reported the median. Flooring wealth above zero makes ruin non-absorbing, and the median path never
realises a rare catastrophic draw. Both are benign under bounded loss (`R ≥ −1`), which held while the
engine filled gapped stops at the line. Under honest fills, `R` is unbounded below and both assumptions
fail — the corrected estimator makes bankruptcy terminal and reports tail probabilities directly.

## 1.4 `P(dd ≥ 50%)`

**Definition.** Probability that peak-to-trough equity decline reaches 50% at any point in the horizon.
Drawdown is measured from the running maximum, not from initial capital.

**Relationship to `P(ruin)`.** Drawdown is recoverable; ruin is not. Under bounded per-trade loss the two
are monotonically related and drawdown is a sufficient risk constraint. Under unbounded loss they
decouple, and **only `P(ruin)` binds.**

## 1.5 RISK-01 (2026-07-22)

**Objective.** Re-derive the per-trade risk fraction on honest fills.
**Method — sound, and reused unchanged in RISK-02:** per-trade normalisation by each champion's own hard
stop (correcting a prior hardcoded 40-point normaliser), plus a mandatory 8-seed noise check on the
location of the PnL:DD optimum.
**Inputs — invalid on four counts:** it resolved `wsh4_*` as the deployed champion set (superseded on
2026-07-14); it covered 8 of 54 slots; it omitted NG entirely; and it ran a cap-blind ledger, though the
deployed set's principal difference from `wsh4` is precisely its time-caps (NQ 4h: 213 of 541 exits).
**Finding.** Operating range 0.25–0.5% — retained. Ceiling ~1% — **rejected**: `P(ruin) = 1.67%`.

## 1.6 GAP-02 (2026-07-20)

**The defect corrected.** When a 1-minute bar opens beyond a hard stop or target, that level never
traded. The pre-2026-07-20 engine nevertheless recorded a fill *at the level*. Honest execution fills at
the bar's open — worse on a stop, better on a target, hence applied symmetrically to avoid injecting
pessimistic bias.
**Measurement.** All 54 champions, before/after: aggregate P&L **−0.2%** (immaterial); maximum drawdown
**+9.8%**; NG **+148%**.
**Interpretation.** The prior model did not overstate profitability — it **understated risk**.
**Its own defect (identified 2026-07-29).** GAP-02 also measured `wsh4_*`. The comparison is internally
valid (identical champions both sides, so the *direction* holds), but the magnitudes describe a retired
book.

---

# PART 2 — BABY ENGLISH

## 2.1 What is `f`?

`f` means: **"how much of my money do I agree to lose on one trade?"**

If you have **$100,000** and you say `f = 1%`, you are saying: *"if this trade goes wrong, I lose
**$1,000**, and I am fine with that."*

**But your system does not do this.** Your system does one thing: **the robot says yes → you buy ONE
contract.** It never asks how much money you have. It never asks how many to buy.

So `f` is a number from a *"what if"* study. **It is not a button in your system, and nobody added one.**

And here is the funny part: even if we wanted it, **it does not fit**. One Nasdaq contract already risks
**$2,194**. If you said "risk only $1,000", the answer would be *"buy half a contract"* — and you cannot
buy half a contract. **The smallest thing you can buy is already bigger than the bet you wanted.**

## 2.2 What is `R`?

`R` means: **"how many times bigger than my planned loss was the real loss?"**

You planned to lose $1,000 if wrong.

| what happened | `R` | your money |
|---|---|---|
| lost exactly what you planned | **−1** | −$1,000 ✅ the stop worked |
| made double | **+2** | +$2,000 |
| **the market jumped over your stop** | **−183** | **−$183,000** ❌ |

**`R = −1` is good news** — it means your safety net caught you. **Anything past −1 means the safety net
tore.**

### ⚠️ 2.2.1 This is a DIFFERENT `R` from the one you remember

You remember `R` from the beginning of the project. **You are right, and it is not this one.**

- **Your R** = **R:R**, "risk to reward". *"I risk 40 points to make 48 points → 1.2 to 1."* You decide
  it **before** the trade. It is part of the strategy.
- **This new R** = *"how bad was it compared to plan?"* You know it only **after** the trade. It is only
  used in two risk documents from last week.

**Same letter. Two different things.** Nobody wrote that down before. Now it is written down.

## 2.3 What is `P(ruin)`?

**"What is the chance I lose EVERYTHING?"**

Not "a bad month". Not "I feel sad". **Zero. Finished. You cannot trade tomorrow.**

We pretend to trade 1,000 times, and we do that 4,000 times over, and we count how many of those 4,000
lives ended in total loss.

> **`P(ruin) = 1.67%` means: out of 60 people doing this, 1 loses everything.**

## 2.4 What is `P(dd ≥ 50%)`?

**"What is the chance my account halves?"**

"Drawdown" = how far you fell **from your best day**, not from your first day.

> You start with $100,000. You grow to **$150,000**. You fall to **$75,000**.
> Your drawdown is **50%** — measured from $150,000, your best day.

You are still alive. You can keep going. But almost nobody keeps trading after losing half.

**The difference in one line:**
- **Drawdown = you are hurt.** You can heal.
- **Ruin = you are dead.** There is no healing.

## 2.5 What was RISK-01?

A study from 22 July that asked: **"how much should we bet?"**

**The maths was correct. The ingredients were wrong.** Like a chef who cooks perfectly — using
yesterday's shopping list.

Four wrong ingredients:
1. It used our **old** strategy list. We changed it on 14 July.
2. It looked at **8 strategies out of 54**.
3. It **completely skipped natural gas** — the most dangerous one.
4. It **ignored our "close before the day ends" rule**, which ends **213 out of 541** trades on one
   Nasdaq strategy.

**Its answer:** bet 0.25%–0.5%, never more than 1%.
**The truth:** 0.25–0.5% was fine. **But "1% maximum" was dangerous — at 1%, 1 person in 60 loses
everything.**

## 2.6 What was GAP-02?

**Our test computer used to cheat.**

You own gas. You leave an order: *"if it drops to $3.00, sell me."* Friday it closes at **$3.05**.
Over the weekend, bad news. Monday it opens at **$2.80** — **it never touched $3.00 at all. It jumped
over it.**

- **The old test computer said:** *"you sold at $3.00."* ← a price that never existed
- **Real life says:** *"you sold at $2.80."* ← the first real price

GAP-02 stopped the cheating and re-measured all 54 strategies:

| | result |
|---|---|
| money made | **−0.2%** — basically the same |
| worst fall | **9.8% worse** |
| natural gas worst fall | **148% worse** |

**The one sentence:** **we were never making less money than we thought — we were in more danger than we
thought.**

---

# PART 3 — العربية

## ⚠️ ٣.٠ الإجابة الحوكمية أولًا

**سألتَ: هل أُضيفت طبقة قرار لتحديد حجم الصفقة إلى نظامك دون موافقتك؟**

**لا. تحقّقتُ من ذلك في الشيفرة، وهذا هو الدليل:**

| الفحص | النتيجة |
|---|---|
| هل يحسب المحرّك حجم الصفقة؟ | **لا.** في `strategy.py:424` يكون `الربح = النقاط × قيمة النقطة`. لا يوجد أي حدّ للكمية إطلاقًا. |
| هل يعرف المحرّك رصيد حسابك؟ | **لا.** لا يوجد أي مُدخَل لرأس المال أو الحساب. |
| القيد الثابت في `optimize/TASK.md:24` | «**عقد واحد فقط**، NQ، قيمة النقطة ٢٠ دولارًا — قيد ثابت، **بلا توسيع أو تدرّج**» |
| أين يوجد `f`؟ | **في خمسة ملفات بحثية خارج النظام فقط**، ولا شيء منها يمسّ التداول |
| ماذا يقول مشروع تحديد الحجم عن نفسه؟ | في تقريره الخاص: «**لم يُعتمد شيء؛ الإنتاج مطابق تمامًا؛ التكلفة صفر**» |

**وصفك لنظامك دقيق تمامًا:** *إذا وافقت الخوارزمية متعدّدة الطبقات على الدخول، فأنت تدخل — عقد واحد،
مهما كان السعر.* هذا بالضبط ما تفعله الشيفرة. **لم يُزرع شيء.**

**لكنك اكتشفت أمرًا حقيقيًا، وهو أهمّ من مسألة الإذن.**

مشروع تحديد الحجم بأكمله — ومنه **RISK-02 الذي أغلقته لك اليوم** — يجيب عن سؤال **لا يستطيع نظامك
تنفيذه**. كل تلك الدراسات تفترض أنك تستطيع اختيار **كم** تراهن. وأنت لا تستطيع: إمّا عقد واحد، أو لا شيء.

**إذن `f` ليس إعدادًا نسيتَه، بل هو فرضية داخل محاكاة بحثية.** وكان عليّ أن أخبرك بذلك عند إغلاق المسألة
رقم ٣، بدل أن أقدّم لك توصية «خاطر بنسبة ٠٫٣٪ في الغاز» لنظام لا يملك أصلًا مِقبضًا للنِّسَب.

### النتيجة نفسها، مترجَمة إلى نظامك الفعلي

السؤال الصحيح لنظام «العقد الواحد» ليس *«ما النسبة التي أخاطر بها؟»* بل **«هل يصمد حسابي أمام أسوأ صفقة
منفردة؟»** — البيانات ذاتها، بصياغة أخرى:

| السوق | أسوأ صفقة منفردة، **بعقد واحد** |
|---|---:|
| **النفط CL** | **−٧٬٧١٠ دولارًا** |
| **ناسداك NQ** | **−٧٬٤٢٠ دولارًا** |
| الفضة SI | −٣٬٨٥٠ |
| الذهب GC | −٣٬٧٦٠ |
| **الغاز NG** | **−٣٬٦٦٠** |
| ‏S&P ES | −٣٬٠٣٨ |
| داو YM | −٢٬٥٢٥ |
| راسل RTY | −٢٬٢٥٠ |
| النحاس HG | −١٬٦٥٠ |
| **الأسواق التسعة في أسوأ يوم** | **−٣٥٬٨٦٣ دولارًا** |

⭐ **انظر إلى الغاز الطبيعي.** بوحدات المخاطرة كان كارثة التقرير كلّه — **١٨٣ ضعفًا**. أمّا بالدولار وبعقد
واحد فهو **الخامس فقط، بخسارة ٣٬٦٦٠ دولارًا**. عاديّ تمامًا.

**لماذا هذا الفرق؟** لأنّ `R` يقسم على حجم وقف الخسارة، ووقف الغاز **متناهي الصِّغَر** (٠٫٠٠١٠١٧). فخسارة
دولارية عادية تمامًا تتحوّل إلى مضاعف هائل لوقفٍ ضئيل. الرقم ١٨٣ صحيح حسابيًا، لكنه لا يصبح **خطِرًا** إلا
في نظام كان سيُكبِّر حجم الصفقة حتى يجعل ذلك الوقف الضئيل يساوي ١٪ من رأس المال — ثم تُدمّره الفجوة.

**نظامك لا يفعل ذلك أبدًا.** لذا فإنّ عنوان RISK-02 — *«الغاز الطبيعي يحدّ المحفظة كلها»* — هو أثر جانبي
لنموذج تحجيم **أنت لا تستخدمه**.

**وما يبقى صحيحًا ومهمًّا لك:** بعقد واحد، **قيدك الحقيقي هو نحو ٧٬٧٠٠ دولار من صفقة واحدة، ونحو ٣٥٬٨٦٣
دولارًا لو ساء كل شيء دفعةً واحدة.** وبحساب قدره ١٠٬٠٠٠ دولار، فإنّ صفقة نفط واحدة سيّئة تعادل **٧٧٪ من
مالك**. هذا هو الرقم الحقيقي القابل للتنفيذ — ولا علاقة له بـ `f` إطلاقًا.

**حدسك بالتوقّف والسؤال كان صائبًا.** كنتُ أجيب عن السؤال الخطأ بعناية.

## ٣.١ ما هو `f`؟

**بلغة مبسّطة:** `f` يعني: **«كم من مالي أوافق على خسارته في صفقة واحدة؟»**

لو كان لديك **١٠٠٬٠٠٠ دولار** وقلت `f = ١٪`، فأنت تقول: *«إن فشلت هذه الصفقة أخسر **١٬٠٠٠ دولار**، وهذا
مقبول لديّ.»*

**لكن نظامك لا يعمل هكذا.** نظامك يفعل شيئًا واحدًا: **الخوارزمية توافق ← تشتري عقدًا واحدًا.** لا يسأل عن
رصيدك، ولا عن عدد العقود.

**بلغة مهنية:** `f` هو نسبة رأس المال المعرَّضة للخطر في صفقة واحدة، بحيث يحقّق الوصول الكامل إلى وقف
الخسارة خسارةً مقدارها `f × رأس المال`. **حالته في المشروع: غير مُنفَّذ إطلاقًا.**

**والمفارقة:** حتى لو أردناه **فإنه لا يناسبنا**. عقد ناسداك واحد يخاطر أصلًا بـ **٢٬١٩٤ دولارًا**. فلو
قلت «خاطر بألف دولار فقط» لكان الجواب *«اشترِ نصف عقد»* — ولا يمكنك شراء نصف عقد. **أصغر وحدة قابلة
للشراء أكبر من الرهان الذي أردتَه.** التحجيم الجزئي أداة للحسابات الضخمة.

## ٣.٢ ما هو `R`؟

**بلغة مبسّطة:** **«كم ضِعفًا كانت الخسارة الحقيقية مقارنةً بالخسارة المخطَّطة؟»**

خطّطتَ لخسارة ١٬٠٠٠ دولار عند الخطأ:

| ما حدث | `R` | مالك |
|---|---|---|
| خسرتَ ما خطّطتَ له بالضبط | **−١** | −١٬٠٠٠ ✅ الوقف عمل |
| ربحتَ الضِّعف | **+٢** | +٢٬٠٠٠ |
| **السوق قفز فوق وقفك** | **−١٨٣** | **−١٨٣٬٠٠٠** ❌ |

**`R = −١` خبر جيّد** — يعني أنّ شبكة الأمان أمسكت بك. **وأيّ شيء بعد −١ يعني أنّ الشبكة تمزّقت.**

**بلغة مهنية:** `R = الربح بالنقاط ÷ وقف الخسارة الصلب`. الغرض منه **التجميع المستقلّ عن المقياس**: أوقاف
الخسارة تمتدّ عبر أربع مراتب عشرية (الغاز ٠٫٠٠١٠١٧ ← داو ١٠٫٢٤٦)، فلا يمكن جمع النقاط أو الدولارات عبر
الأسواق، بينما يمكن جمع `R`.

### ⚠️ ٣.٢.١ هذا `R` **مختلف** عن الذي تتذكّره

تذكر `R` من بداية المشروع. **أنت محقّ، وهو ليس هذا.**

| | **R:R** (القديم، الخاص بك) | **R** (دراسات الحجم، تموز ٢٠٢٦) |
|---|---|---|
| المعنى | **نسبة المخاطرة إلى العائد** — الهدف ÷ الوقف | **مضاعف المخاطرة** — النتيجة ÷ الوقف |
| متى يُحسب | **قبل** الصفقة، من الإعدادات | **بعد** الصفقة، من نتيجتها |
| قيمة نموذجية | `١٫٢ : ١` | `−١`، `+٢٫٤`، `−١٨٣` |
| هل هو داخل المحرّك؟ | **نعم** — هو ناتج ضبط الوقف والهدف | **لا** — تحليل خارجي فقط |

**الحرف نفسه. شيئان مختلفان.** لم يُوثَّق هذا من قبل. الآن وُثِّق.

## ٣.٣ ما هو `P(ruin)` — احتمال الإفلاس؟

**بلغة مبسّطة:** **«ما احتمال أن أخسر كلّ شيء؟»** ليس «شهرًا سيّئًا»، بل **صفر. انتهى. لا تستطيع التداول غدًا.**

نتظاهر بالتداول ١٬٠٠٠ مرة، ونكرّر ذلك ٤٬٠٠٠ مرة، ونعدّ كم «حياة» انتهت بالخسارة الكاملة.

> **`P(ruin) = ١٫٦٧٪` تعني: من كل ٦٠ شخصًا، واحد يخسر كلّ شيء.**

**بلغة مهنية:** احتمال بلوغ حقوق الملكية الصفر مرّة واحدة على الأقل خلال ١٬٠٠٠ صفقة، مُقدَّرًا عبر ٤٬٠٠٠
مسار. **الإفلاس ماصّ (absorbing)**: المسار ينتهي ولا يتعافى.

**ملاحظة منهجية جوهرية:** المحاكي الموروث كان يحسب `cumprod(max(1 + f·R, 1e-9))` ويُبلِّغ عن **الوسيط**.
تثبيت الثروة فوق الصفر يجعل الإفلاس **غير ماصّ**، والمسار الوسيط **لا يمرّ أصلًا** بالصفقة الكارثية
النادرة. الافتراضان سليمان عندما تكون الخسارة **محدودة** (`R ≥ −١`)، وهو ما كان يتحقّق حين كان المحرّك
يملأ الأوامر عند الخط. أمّا مع التنفيذ الأمين فالخسارة **غير محدودة**، فينهار الافتراضان معًا.

## ٣.٤ ما هو `P(dd ≥ 50%)`؟

**بلغة مبسّطة:** **«ما احتمال أن ينخفض حسابي إلى النصف؟»**

«الهبوط» يُقاس من **أفضل يوم لك**، لا من يومك الأول:

> تبدأ بـ ١٠٠٬٠٠٠ دولار. تصل إلى **١٥٠٬٠٠٠**. ثم تهبط إلى **٧٥٬٠٠٠**.
> هبوطك **٥٠٪** — محسوبًا من ١٥٠٬٠٠٠، أفضل أيامك.

أنت حيّ وتستطيع الاستمرار، لكن نادرًا ما يستمرّ أحد بعد خسارة النصف.

**الفرق في سطر واحد:**
- **الهبوط = أنت مُصاب.** يمكن أن تتعافى.
- **الإفلاس = أنت ميّت.** لا تعافي.

**بلغة مهنية:** الهبوط قابل للتعافي، والإفلاس غير قابل. وتحت الخسارة المحدودة يرتبطان ارتباطًا رتيبًا
ويكفي الهبوط كقيد. أمّا تحت الخسارة غير المحدودة فينفصلان، **ولا يبقى مُقيِّدًا إلا احتمال الإفلاس**.

## ٣.٥ ما هي دراسة RISK-01؟

**بلغة مبسّطة:** دراسة من ٢٢ تموز سألت: **«كم يجب أن نراهن؟»**
**الحساب كان صحيحًا، والمكوّنات كانت خاطئة** — كطاهٍ يطبخ بإتقان، لكن بقائمة تسوّق الأمس.

أربعة مكوّنات خاطئة:
1. استخدمت قائمة الاستراتيجيات **القديمة**؛ وقد غيّرناها في ١٤ تموز.
2. نظرت في **٨ استراتيجيات من أصل ٥٤**.
3. **تجاهلت الغاز الطبيعي تمامًا** — وهو الأخطر.
4. **أهملت قاعدة «الإغلاق قبل نهاية اليوم»**، التي تُنهي **٢١٣ من ٥٤١** صفقة في إحدى استراتيجيات ناسداك.

**جوابها:** خاطر بـ ٠٫٢٥٪–٠٫٥٪، ولا تتجاوز ١٪ أبدًا.
**الحقيقة:** النطاق ٠٫٢٥–٠٫٥٪ سليم. **أمّا سقف ١٪ فكان خطِرًا: عنده يخسر شخص من كل ٦٠ كلَّ شيء.**

## ٣.٦ ما هي دراسة GAP-02؟

**بلغة مبسّطة: حاسوب الاختبار لدينا كان يغشّ.**

تملك غازًا وتترك أمرًا: *«إن هبط إلى ٣٫٠٠ دولار فبِع».* يغلق الجمعة عند **٣٫٠٥**. وفي عطلة نهاية الأسبوع
تأتي أخبار سيّئة، فيفتح الاثنين عند **٢٫٨٠** — **ولم يلمس ٣٫٠٠ إطلاقًا، بل قفز فوقه.**

- **الحاسوب القديم قال:** *«بِعتَ عند ٣٫٠٠»* ← سعر لم يوجد قط
- **الواقع يقول:** *«بِعتَ عند ٢٫٨٠»* ← أول سعر حقيقي

أوقفت GAP-02 هذا الغشّ وأعادت قياس الاستراتيجيات الـ٥٤ جميعًا:

| | النتيجة |
|---|---|
| الأرباح | **−٠٫٢٪** — دون تغيير يُذكر |
| أسوأ هبوط | **أسوأ بنسبة ٩٫٨٪** |
| هبوط الغاز الطبيعي | **أسوأ بنسبة ١٤٨٪** |

**الجملة الواحدة:** **لم نكن نربح أقلّ ممّا ظننّا قط — بل كنّا في خطر أكبر ممّا ظننّا.**

**بلغة مهنية:** يُطبَّق التصحيح **بشكل متماثل** (الفجوة فوق الهدف تدفع أكثر، وفوق الوقف تكلّف أكثر) تفاديًا
لإدخال تحيّز تشاؤمي. **وعيبها الخاص (اكتُشف في ٢٩ تموز):** أنّها قاست هي أيضًا قائمة `wsh4_*` المتقاعدة؛
فالمقارنة سليمة داخليًا (نفس الاستراتيجيات على الطرفين، فيبقى **الاتجاه** صحيحًا) لكنّ **المقادير** تصف
كتابًا لم يعد مستخدَمًا.

---

## Appendix — where every claim here comes from

| claim | source |
|---|---|
| no position sizing in the engine | `strategy.py:424`, `optimize/fast_engine.py` — no quantity term |
| 1 contract is a standing constraint | `optimize/TASK.md:24` |
| `f` only in research | `study_kelly.py`, `study_kelly_pnldd.py`, `study_ruin.py`, `risk_recut_v2.py`, `risk_ruin_v3.py` |
| "Nothing adopted; production byte-identical; $0" | `docs/superpowers/SIZE-00-WORKSTREAM-REPORT.md` |
| `R:R` is the early concept | `optimize/sl_tp_bounds.py:14`, `docs/PLAYBOOK_abdulfattah1.md:102` |
| point values | `optimize/instruments.py: point_value()` |
| worst single trade per market | `optimize/reports/risk_recut/` (cap-aware ledger, honest fills) |
| GAP-02 figures | `optimize/reports/gap_fills/champion_gap_compare.json` |
| RISK-01 defects | `docs/superpowers/RISK-02-ruin-bound-honest-fills.md` §1 |
