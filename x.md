Post
user avatar
cvxv666
@antpalkin
The most powerful tool in quant trading right now isn't AI. It's a piece of math from 1906 called a Markov chain.

Citadel runs it inside the algorithms behind roughly 20% of all US stock trades - and never lets it outside the building. 

Somebody just rebuilt the whole thing where anyone can see it.

There's now an app that runs all this math in two clicks.

Full breakdown below. Save it before you need it.
user avatar
cvxv666
@antpalkin
Jul 2
Your strategy isn't losing because it's bad. It's losing because the market changed and nobody told you.

Markets have moods: trend, chop, panic. Every strategy only works inside one of them. 

And when the mood flips, no bell rings. Your equity curve is the bell - by the time it
8:09 PM · Jul 2, 2026
46.9K
Views
Don't miss what's happening
People on X are the first to know.
Log in
Sign up
cvxv666 on X: "The most powerful tool in quant trading right now isn't AI. It's a piece of math from 1906 called a Markov chain. Citadel runs it inside the algorithms behind roughly 20% of all US stock trades - and never lets it outside the building. Somebody just rebuilt the whole thing https://t.co/MRLAZQwpdy" / X

----

To view keyboard shortcuts, press question mark
View keyboard shortcuts
Article
Conversation
Ruuj
@RuujSs
Image
How To Use The Hidden Markov Model To Detect Market Regimes (Complete Framework)
The market never tells you which regime it is in. It leaves fingerprints. Here is how to read them and build a system that trades on it.
Every trading strategy you have ever built carries an unspoken assumption.
A trend-following system assumes the market persists in a direction long enough to profit from following it. A mean-reversion system assumes the opposite that deviations correct rather than compound. Both assumptions are correct some of the time. Neither is correct all of the time. The strategy that made you money for six months and then quietly bled for the next three did not stop working because the logic broke. The market changed underneath it.
This is the single most important idea in this article: Markets do not announce a regime change. There is no signal that says "risk-off begins now." But they leave fingerprints. Returns become more erratic. Volatility clusters. Drawdowns deepen and rebounds shorten. Correlations across assets tighten. The fingerprints are there in the data. The question is how to read them systematically instead of by feel.
This is the third article in a series I have been building. The first covered pairs trading how to find genuinely anchored relationships between assets using cointegration. The second covered the Kalman filter how to estimate a hidden state, like a true hedge ratio, from noisy observations that update continuously. This article completes the trilogy with the Hidden Markov Model the framework for detecting which of several hidden regimes the market is currently in, and exactly how confident you should be about that.
Ruuj
@RuujSs
·
Jun 23
Article cover image
How To Use The Kalman Filter To Build Smarter Trading Systems (Complete Framework)
NASA used it to navigate to the moon. Quant funds use it to navigate markets. Here is exactly how it works and how to build it.
The problem was simple to state and hard to solve. You are tracking...
If you have not read the first two, you must read them after this article. Together they form a complete picture of how serious systematic operations think about hidden state estimation in markets.
A 2025 study applying HMMs to Bitcoin markets found the model outperformed alternative approaches specifically in detecting transitions among bullish, bearish, and neutral phases information the researchers described as crucial for strategic trading decisions. A separate paper on regime-switching factor investing confirmed that strategies incorporating HMM-based regime predictions achieve both higher absolute and risk-adjusted returns compared to static approaches. This is active, current research producing measurable results, not a technique being revisited for nostalgia.
By the end of this article you will understand exactly what a Hidden Markov Model is and why "hidden" is the operative word, how the model learns regimes directly from data without ever being told what a regime looks like, the two distinct questions every HMM can answer and the two algorithms that answer them, how to correctly decide how many regimes actually exist in your data, and the specific documented failure points that separate a regime detector you can trust from one producing confident-looking noise.

    Note: This article builds the complete framework. What the model is actually doing, the full mathematics, and how to detect, and validate hidden market regimes. Read it in order every Chapter connects to the next.

Part 1: Why "Hidden" Is the Entire Point
Start with the Markov chain you may already know. A Markov chain describes a system moving between observable states, where the probability of the next state depends only on the current state not the full history that led there. Weather is a simple example. If it is sunny today, there is some probability it stays sunny tomorrow and some probability it rains. You observe the state directly. Sunny is sunny.
Markets do not work this way, and the reason is the entire motivation for this model.
You cannot observe "the market is in a bull regime" directly. What you observe is price. Returns. Volatility. The regime. The underlying state generating those observations is hidden. You infer it from its effects, the same way a doctor infers a diagnosis from symptoms without directly observing the disease itself.
This is the core structural difference. In a standard Markov chain, the state is the observation. In a Hidden Markov Model, a hidden state sequence generates observations, and a separate observation sequence is what you actually see. The hidden states transition according to their own rules. Each hidden state, while active, generates observations according to its own statistical profile.
You never see the regime directly only the returns it produces. The model's job is inferring the hidden chain from the visible outputs.
The hidden state generates what you observe
Concretely: imagine the market has three hidden regimes calm, transitional, crisis. Each is a genuine statistical entity with its own return distribution. The calm regime produces small positive mean returns with low variance. The crisis regime produces negative mean returns with high variance. You never see "calm" or "crisis" labeled anywhere. You see a sequence of daily returns. The model's job is to infer, at each point, which regime was most likely active and how regimes transition into each other over time.
Here is a minimal illustration of the structure before the full mathematics:
python

import numpy as np

regime_names = ['Calm', 'Transitional', 'Crisis']
regime_profile = {
    'Calm':         (0.0008, 0.006),
    'Transitional': (0.0000, 0.014),
    'Crisis':       (-0.0025, 0.030),
}
observed_returns = np.array([0.004, -0.002, 0.011, -0.031, -0.018, 0.006])

That gap a hidden structure you never see, versus an observed sequence you always see is what the entire model exists to bridge.
Part 2: What the Model Actually Learns
An HMM is defined by three sets of parameters. Understanding what each one represents is what makes everything after this section click.
The transition matrix describes the probability of moving from any regime to any other in one time step, including staying put. If the market is currently calm, the matrix tells you the probability it remains calm tomorrow versus shifts to transitional versus jumps straight to crisis. Regimes typically have high probability of persisting markets do not flip between calm and crisis on a coin flip day to day.
The emission distributions describe what each regime looks like statistically when it is active. In the simplest version this is a Gaussian defined by a mean and variance per regime. More sophisticated implementations feed multiple observed features simultaneously returns, realized volatility, volume with a full covariance matrix describing how these features move together within each regime.
Calm is tight and positive, transitional widens out near zero, crisis skews negative with fat tails, the regimes aren't just labels, they're statistically distinct.
Three regimes, three very different distributions
The initial state distribution is the probability of being in each regime at the very start of the observed history, before any data has been seen.
None of these are set by hand. You never decide in advance that the crisis regime has a mean return of negative 0.25% daily. The model learns all of it directly from data, through an algorithm called Baum-Welch a specific application of the more general Expectation-Maximization technique.
The process is iterative. Start with a rough initial guess for all parameters. Compute, given those parameters, how likely each observation is to belong to each regime this is the expectation step. Update the parameters to better explain the data given those probability-weighted assignments this is the maximization step. Repeat until the improvement between iterations becomes negligible.
Here is a complete, working implementation using hmmlearn, the standard Python library for this actively maintained:
python

import numpy as np
import pandas as pd
from hmmlearn.hmm import GaussianHMM

def fit_regime_model(returns: pd.Series, n_states: int = 3,
                      n_restarts: int = 10, random_state: int = 42):
    X = returns.values.reshape(-1, 1)
    best_model = None
    best_score = -np.inf

    for seed in range(n_restarts):
        try:
            model = GaussianHMM(
                n_components=n_states,
                covariance_type="full",
                n_iter=1000,
                random_state=random_state + seed
            )
            model.fit(X)
            score = model.score(X)
        except Exception:
            continue

        if score > best_score:
            best_score = score
            best_model = model

    return best_model, best_score

Ten independent restarts, keeping the one with the highest final log-likelihood, is the current documented practice for avoiding a common and well-known failure of this algorithm one covered fully in Chapter 5.
Part 3: The Two Questions Every HMM Answers
Once fitted, a model can answer two genuinely different questions. Conflating them is one of the most common and consequential mistakes in practical implementations.
The decoding question: what regime was the market in at each point in the past?
Given the full observed sequence and a fitted model, what is the single most likely sequence of hidden regimes that produced it? The Viterbi algorithm answers this efficiently, searching through the space of possible regime sequences and identifying the one with the highest overall probability rather than checking every combination individually.
python

def decode_historical_regimes(model, returns: pd.Series) -> pd.Series:
    X = returns.values.reshape(-1, 1)
    hidden_states = model.predict(X)
    return pd.Series(hidden_states, index=returns.index)

This gives a clean regime label for every historical time point, genuinely useful for understanding how a strategy performed across different historical regimes, or building the shaded-region regime chart you have likely seen in research reports.
Viterbi doesn't just label each day independently, it finds the single sequence of regimes (calm → transitional → crisis) that's most probable given the whole path, not just one point in time.
Finding the most likely path through time
The filtering question: what regime is the market in right now, given only what has happened up to today?
This is the computation that actually matters for live trading, and it is structurally different. The forward algorithm computes the probability of being in each regime at the current time step using only observations up to and including today, nothing beyond it.
python

from scipy.stats import multivariate_normal

def filtered_regime_probabilities(model, data) -> pd.DataFrame:
    X = data.values.reshape(-1, 1) if data.ndim == 1 else data.values
    n_obs, n_states = X.shape[0], model.n_components

    emission_probs = np.zeros((n_obs, n_states))
    for i in range(n_states):
        emission_probs[:, i] = multivariate_normal.pdf(
            X, mean=model.means_[i], cov=model.covars_[i]
        )

    filtered = np.zeros((n_obs, n_states))
    alpha = model.startprob_ * emission_probs[0]
    alpha /= alpha.sum()
    filtered[0] = alpha

    for t in range(1, n_obs):
        alpha = (filtered[t - 1] @ model.transmat_) * emission_probs[t]
        alpha /= alpha.sum()
        filtered[t] = alpha

    return pd.DataFrame(
        filtered, index=data.index,
        columns=[f'Regime_{i}' for i in range(n_states)]
    )

Here is the single most important practical distinction in this entire article, stated plainly: smoothed probabilities use the entire dataset, including observations occurring after the point being evaluated, and are appropriate only for historical analysis. Filtered probabilities use only data available up to the current point and are the only appropriate choice for live decision-making.
Using smoothed probabilities to backtest a strategy that is meant to run live is a lookahead bias error. It is one of the most common mistakes in published research on this exact topic. A strategy that looks excellent in a backtest using smoothed regime labels can perform completely differently once deployed, because live trading only ever has access to filtered information the model on any given day has not yet seen tomorrow's return.
If you take one rule from this article, take this one: for anything touching live capital, use filtered probabilities computed incrementally as each new observation arrives. Reserve the Viterbi decoded path and smoothed probabilities strictly for research, historical labeling, and diagnostics.
Part 4: Choosing How Many Regimes Actually Exist
This has no clean textbook answer, and every serious implementation confronts it directly.
The number of hidden states is not learned by the model, it is chosen before fitting begins. Fit too few and you blend genuinely distinct market conditions together. Fit too many and you carve genuine regimes into statistically unstable fragments that do not generalize.
The standard approach combines two things. First, an information criterion - typically the Bayesian Information Criterion, which penalizes model complexity so you are not simply rewarded for adding states that fit noise better.
python

def select_regime_count(returns: pd.Series, state_range=range(2, 7),
                         n_restarts: int = 10) -> pd.DataFrame:
    T = len(returns)
    results = []

    for n_states in state_range:
        best_model, best_logL = fit_regime_model(
            returns, n_states=n_states, n_restarts=n_restarts
        )
        if best_model is None:
            continue

        n_params = (
            n_states * (n_states - 1)
            + n_states
            + n_states
            + (n_states - 1)
        )
        bic = -2 * best_logL + n_params * np.log(T)

        results.append({
            'n_states': n_states,
            'log_likelihood': best_logL,
            'bic': bic
        })

    return pd.DataFrame(results).sort_values('bic')

In practice, BIC alone is rarely decisive. Financial HMM literature generally finds performance concentrated in the two-to-four state range, and BIC scores are frequently similar across three, four, and five states meaning the statistical criterion often does not cleanly point to one right answer. This is where a second consideration becomes essential: interpretability and stability. A three-state model that cleanly separates into calm, transitional, and crisis regimes, each with an intuitive economic story and each persisting for a reasonable duration, is more useful than a four-state model with a marginally better BIC score that produces regimes flickering back and forth every few days.
There is a documented empirical pattern worth internalizing: models with four or more states often reduce BIC only marginally while producing unstable smoothed probabilities and states difficult to justify economically. Published research has explicitly chosen a two-state model over a marginally better four-state model specifically because portfolio performance built on the two-state regimes was materially better and the states themselves were more interpretable.
python

def check_regime_stability(model, returns: pd.Series,
                           min_avg_duration_days: float = 3.0) -> dict:
    """
    Validate that detected regimes persist for economically sensible
    durations rather than flickering between states rapidly.
    """
    states = decode_historical_regimes(model, returns)
    durations = []
    current_state = states.iloc[0]
    current_duration = 1

    for i in range(1, len(states)):
        if states.iloc[i] == current_state:
            current_duration += 1
        else:
            durations.append(current_duration)
            current_state = states.iloc[i]
            current_duration = 1
    durations.append(current_duration)

    avg_duration = np.mean(durations)
    is_stable = avg_duration >= min_avg_duration_days

    print(f"Average regime duration : {avg_duration:.1f} days")
    print(f"Number of transitions   : {len(durations)}")
    print(f"Stable                  : {is_stable}")

    return {'avg_duration': avg_duration, 'is_stable': is_stable,
            'durations': durations}

The practical workflow current research converges on: fit models across a small range of state counts, typically two through six, each with multiple random restarts. Compare BIC across state counts as one input, not the deciding factor. Check whether the resulting regimes are persistent and economically interpretable. Only commit to a state count when the statistical criterion and the qualitative inspection agree.
Part 5: Where the Model Genuinely Struggles
Every serious treatment of this topic in current literature is direct about specific, well-documented weak points. Knowing them precisely is what separates a regime detector you can trust from one producing confident-looking numbers that mislead you.
Baum-Welch finds a local maximum, not a global one.
The likelihood surface Expectation-Maximization climbs is not smooth, it has many local peaks. Starting from a poor initial guess, the algorithm can converge to a solution that is mathematically stable, the likelihood stops improving between iterations while still being a substantially worse explanation of the data than a different solution reachable from a different starting point. This matters enormously in finance specifically, because different local optima can correspond to genuinely different regime interpretations of the same data. One fit might identify a clean three-regime structure; a different fit on identical data from a different starting point might converge to a degenerate solution where one regime absorbs almost no observations.
A poorly initialized EM run can converge to a local maximum that looks like a good fit but isn't — this is the silent failure mode nobody checks for.
Why initialization matters
Fit from multiple random initializations, ten independent restarts is the commonly documented figure and retain the highest final log-likelihood. A single fit from a single starting point should never inform a decision that matters.
Regime persistence is not always what the standard model assumes.
The basic HMM assumes that once in a regime, the probability of leaving it next period is constant which implies expected regime duration follows a geometric distribution. This is mathematically convenient but not always realistic. Crisis regimes especially often have duration patterns that do not match this assumption well. The check_regime_stability function above is a practical guard: if detected regimes are flickering at durations far shorter than economically sensible, this assumption is being violated in a way that matters, and either the feature set or the state count needs reconsidering before the model is trusted.
The features you feed the model matter more than the algorithm choice.
An HMM fitted only on daily returns finds regimes defined purely by return characteristics. Legitimate, but only one of many possible regime definitions. Feeding the model realized volatility, volume, or cross-asset correlation alongside returns produces a genuinely richer regime structure.
python

def build_multivariate_features(prices: pd.DataFrame,
                                 vol_window: int = 20) -> pd.DataFrame:
    returns = prices['close'].pct_change()
    realized_vol = returns.rolling(vol_window).std() * np.sqrt(252)
    volume_z = (
        (prices['volume'] - prices['volume'].rolling(vol_window).mean())
        / prices['volume'].rolling(vol_window).std()
    )

    features = pd.DataFrame({
        'returns': returns,
        'realized_vol': realized_vol,
        'volume_z': volume_z
    }).dropna()

    return features


def fit_multivariate_regime_model(features: pd.DataFrame,
                                   n_states: int = 3,
                                   n_restarts: int = 10):
    X = features.values
    best_model, best_score = None, -np.inf

    for seed in range(n_restarts):
        try:
            model = GaussianHMM(
                n_components=n_states,
                covariance_type="full",
                n_iter=1000,
                random_state=seed
            )
            model.fit(X)
            score = model.score(X)
        except Exception:
            continue

        if score > best_score:
            best_score, best_model = score, model

    return best_model, best_score

Current research on Bitcoin regime detection specifically incorporates market sentiment, regulatory developments, and macroeconomic conditions precisely because pure price-based features miss structural shifts that these additional dimensions capture. The choice of what to feed the model is a design decision with as much impact on the outcome as the choice of state count.
A detected regime is a statistical summary, not a discovered physical fact.
This is worth internalizing conceptually. Hidden states in an HMM are not objects waiting to be found the way a hidden planet is found through its gravitational pull on other bodies. They are model-based summaries of changing statistical behavior, and what you find depends on your assumptions, your features, your chosen state count, and your validation discipline. Used well, an HMM is a structured way of asking a genuinely useful question, what kind of market am I probably trading in right now, and how should that change my risk posture rather than a claim to have discovered one true regime structure underlying markets.
The Summary
Markets do not announce their regime. This entire article is built on that observation and what follows from taking it seriously.
A Hidden Markov Model does not predict where the market is going. It answers a more modest and more useful question: given everything observed up to this moment, what is the most statistically coherent explanation of the hidden state currently generating those observations, and how confident should that explanation be. The transition matrix and emission distributions are learned entirely from data through Baum-Welch. The current regime is inferred through the forward algorithm for live use, or the Viterbi algorithm for historical analysis and confusing the two, using smoothed probabilities where filtered ones belong, is the most common and most consequential mistake in practical implementations.
Research published this year confirms the framework is not a historical artifact. It is active and producing measurably better risk-adjusted outcomes than static approaches when applied with the discipline this article has laid out.
Cointegration confirms the relationship exists, the Kalman filter tracks it continuously, and the HMM adds regime context, together they feed the trading decision.
The three-layer pipeline
Three articles. Cointegration establishes whether a relationship between two assets is real. The Kalman filter tracks how that relationship continuously evolves. The Hidden Markov Model tracks the discrete regime the broader market is currently operating in. Together they form a genuinely complete framework for the question every systematic trader eventually has to confront: not just what is the signal, but what kind of market is this signal currently operating in, and how much should that change what I do.

    I’m Ruuj a backend developer, researcher, and working on quant systems. DMs are open for thoughtful discussions and collaborations.

Here is the question I want you to think about.
In your own systematic work right now, where are you currently applying one fixed strategy logic across all market conditions, when the honest answer is that the market has been quietly operating in several distinct regimes the whole time? The Hidden Markov Model is the right tool whenever that answer is: my strategy assumes one kind of market, and I am not tracking when that assumption stops being true.
That answer comes up more often than most people expect.
Want to publish your own Article?
Upgrade to Premium
5:38 PM · Jul 7, 2026
·
169.2K
 
Views
View quotes
Mulham Fetna


