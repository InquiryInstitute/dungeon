# Dungeon World Model Benchmark (DWMB): Structured Adversarial Environments for Evaluating Latent World Models  
**Authors (unspecified)**; **Affiliations (unspecified)**

**Abstract:** World-model learning and planning are widely viewed as prerequisites for robust intelligent behavior[6][10]. However, most RL benchmarks allow agents to succeed without truly understanding hidden structure. We introduce the **Dungeon World Model Benchmark (DWMB)**: a suite of compact, procedurally generated grid-world POMDPs explicitly designed to require inferring latent hazards, topology, and non-local causal triggers. Key hazards share the same visible token as safe tiles, and switches far from traps may enable or disable them. DWMB includes a machine-readable JSON schema, defined difficulty tiers (T1–T5), and canonical “unit-test” dungeons to minimize confounds. We propose **Preemptive Inference Rate (PIR)**: the fraction of hazards whose danger was predicted above threshold *before* first activation, distinguishing safe latent inference from “unsafe success” via trial-and-error damage. **This document is a benchmark definition and preregistered evaluation protocol; no empirical results are reported.** We specify: baselines (model-free RL, MuZero-style planners[10], recurrent world models, and LLM agents with memory), a uniform **belief-extraction convention** so PIR is comparable across methods, proposed latent-model+planner architectures (JEPA-style[27]), loss functions (latent prediction and belief-consistency via KL), and statistical tests (paired Wilcoxon, mixed-effects models, FDR correction). DWMB’s goal is to measure whether agents maintain coherent beliefs over hidden structure and plan accordingly; the hypothesis that belief-based agents achieve higher PIR is falsifiable and pending validation.

## Executive Summary  
DWMB is a benchmark suite with a clear operational target: *agents that explicitly represent and update beliefs over latent structure should achieve higher Preemptive Inference Rate (PIR) than purely reactive agents, at matched goal-success rates*. The environments are adversarially designed: hidden traps and switches are visually indistinguishable from safe elements, and causal triggers (e.g. a lever disabling a distant trap) are non-local. Reward is sparse (goal reward + small step cost), with separate safety constraints (e.g. “no trap triggered”) to prevent reward-hacking. DWMB reports multiple metrics (goal success, survival, hazard activations, PIR/AUPIR, calibration curves, topology/causal F1), decoupling success from safe inference. We include:
- **Formal definitions (POMDP)**: state = (agent_pose, static_layout, latent_state); observations = local egocentric view; Bayes filter belief update formula (standard POMDP filtering) to track hidden state.
- **JSON environment schema**: explicit lists of walls, secret doors, traps, switches, with `eval.hazards_for_PIR` annotation. (Appendix A shows a schema excerpt and minimal example.)
- **Worked example dungeon**: a 16×16 map (Fig.2) with a hidden trap on the short path and a remote switch that disarms it, illustrating how belief over “is-the-corridor-trapped” evolves.
- **Metrics**: Preemptive Inference Rate (PIR): the proportion of hazards for which the agent’s predicted probability $\hat p(hazard) \ge \delta$ **before** the first step on the hazard, with a **uniform belief-extraction convention** (see Metrics) so PIR is comparable across methods. Also AUPIR, calibration as a secondary diagnostic, goal completion, survival, trap counts, topology/causal discovery F1, and sample-efficiency AUCs.
- **Baselines**: (a) Model-free RL (e.g. PPO+LSTM), expected to achieve some success but low PIR (risk-taking); (b) Implicit planning (MuZero-like[10]); (c) Recurrent world-model (Dreamer/RSSM[30]) with latent-state rollout; (d) LLM agents with external memory and belief tracker.
- **Proposed architecture**: JEPA-style encoder and predictor[27] producing latent forecasts, combined with a search/planning module.
- **Losses**: latent prediction loss (mask-and-predict in latent space) and KL-based belief-consistency loss between inference network and dynamics prior.
- **Tests**: Paired Wilcoxon tests on PIR across instances, mixed-effects models with instance random effects, and FDR control for multiple comparisons.
- **Hypothesis (pending validation):** Effective latent-inference agents will exhibit *higher PIR and robustness under counterfactual swaps of hazards* than purely reactive agents at matched goal-success rates. DWMB is designed to measure this difference; the claim is falsifiable once experiments are run.
  
## Introduction  
Reinforcement learning (RL) has seen remarkable success in perception-dominated tasks, but *truly autonomous intelligence* likely requires internal world models and planning[6][27]. World models (latent representations of dynamics) enable agents to simulate and plan under uncertainty[6][27]. MuZero-style agents show that even without explicit reconstruction, learning a model of rewards, values, and policies can support planning[10]. However, standard benchmarks (Atari, Procgen, MuJoCo, etc.) often allow reactive policies to succeed via memoryless strategies or luck, because hidden state is rare or irrelevant[17][27].  

The Dungeon World Model Benchmark (DWMB) aims to **isolate latent inference**. Each instance is a grid-world with partial observability (local view), hidden hazards, and latent triggers. Traps look identical to safe floor, and some must be disarmed by a distant switch. The agent must balance exploration (information gathering) vs. exploitation (pursuing the goal safely) – a hallmark of POMDP planning[17][12]. Fig.1 illustrates how an agent’s local observation (a) reveals little of the latent map (b), but a competent agent maintains a belief (c) over possible maps. PIR quantifies whether that belief becomes accurate *before* activation of hazards.  

**Contributions:** We define DWMB as a formal POMDP distribution with explicit latent variables and adversarial constraints. We release a JSON schema, **explicit difficulty tiers (T1–T5)**, and canonical instances (Fig.2). We propose diagnostic metrics (PIR, calibration as a secondary diagnostic, topology/causal F1) and a **uniform belief-extraction convention** so that PIR is well-defined and comparable across agent families. We outline a preregistered evaluation with baselines, hypothesized outcomes, and statistics. We propose candidate architectures combining JEPA-style latent prediction[27] with planning. This document is a **benchmark definition and protocol**; empirical validation is pending.

## Related Work  
**World models and planning:** Ha & Schmidhuber (2018) demonstrated that an unsupervised latent dynamics model can be learned and used to train policies “in the agent’s own hallucinated dream”[6]. Dreamer/RSSM methods (Hafner et al.) extend this, optimizing latent representations for RL performance across domains[30]. MuZero (Schrittwieser et al., 2020) achieved planning without an explicit environment model by learning to predict rewards, values, and policies in latent space[10]. These works motivate DWMB: a benchmark where latent prediction *quality* and belief-state planning are essential.  

**JEPA and predictive representations:** Yann LeCun (2022) proposed the Joint Embedding Predictive Architecture (JEPA) idea: learn world models by predicting abstract representations of masked future observations, not raw pixels[27]. Recent implementations (e.g. Meta’s V-JEPA for video[28]) mask spatiotemporal latent features. JEPA-like methods emphasize abstraction and efficiency, which is why we propose a JEPA-style latent predictor in DWMB: it must predict hidden map features without explicit pixel generation.  

**POMDPs and belief-state control:** POMDPs are the canonical model for partial observability[12][17]. The belief state (posterior over hidden states) is a sufficient statistic, updated by the Bayes filter (e.g. $b_{t+1}(s') \propto \Omega(o_{t+1}|s') \sum_s T(s'|s,a_t) b_t(s)$)[12][17]. Kaelbling *et al.* discuss that actions simultaneously change the world and reveal information[17]. DWMB explicitly uses POMDP structure: e.g. $b_t(h)=P(h\text{ active})$ is tracked, and we evaluate it via PIR.  

**Generalization benchmarks:** Existing benchmarks test some aspect of generalization or partial observability. DeepMind Lab offers 3D partially-observed tasks[17]; Procgen (Cobbe et al.) focuses on generalization via procedural content[23]. MiniGrid (Chevalier-Boisvert et al.) has modular grid tasks with some hidden state[24]. NetHack Learning Environment (NLE) and TextWorld provide very complex, textual dungeon domains with hidden state and long horizons[25][26]. DWMB differs by being *intentionally adversarial*: every layout includes decoy paths and ambiguous hazards to defeat shortcuts (see Table 1). It trades high fidelity for *diagnostic clarity* of latent inference.  

|Benchmark      | Partial Obs. | Hidden Hazards | Non-local Causality | Adversarial Design | Fast Sim. | Example Ref.|
|---------------|:-----------:|:-------------:|:-------------------:|:------------------:|:---------:|------------|
|Atari (ALE)    | ✔           | ✘             | ✘                   | ✘                  | ✔         | [22]      |
|Procgen        | ✔           | ✘             | ✘                   | ✘                  | ✔         | [23]      |
|DeepMind Lab   | ✔           | ✘             | ✘/✔                 | ✘                  | ✘         | [17]      |
|MiniGrid       | ✔           | ✘/✔           | ✘/✔                 | ✘                  | ✔         | [24]      |
|NetHack (NLE)  | ✔           | ✔             | ✔                   | ✔                  | ✔         | [25]      |
|TextWorld      | ✔           | ✔             | ✔                   | ✔                  | ✔         | [26]      |
|**DWMB (Ours)**| ✔           | ✔             | ✔                   | ✔                  | ✔         | This work |

*Table 1: Benchmark comparison (conceptual). “Adversarial Design” means the environment includes intentionally misleading affordances (e.g. false paths, indistinguishable traps). Symbols indicate typical properties; a checkmark means “generally present” in that benchmark. DWMB is designed to *require* hidden-state inference. “Fast sim” for DWMB refers to small grid instances (e.g. 16×16); NLE and TextWorld are heavier (language, long horizons).*  

## DWMB Definition and Environment Specification  
DWMB is formally a **distribution $\mathcal{D}$** over episodic POMDPs $\mathcal{M}=(S,A,O,T,\Omega,R,\gamma)$. A random seed $\xi$ generates a map and latent variables via generator $G$: $\mathcal{M}_\xi = G(\xi)$.  
- **States:** $s=(x,\theta,h)$, where $x$ is the agent’s (row,col) position, $\theta$ is static map topology (walls, doors, secret edges, item locations), and $h$ is dynamic hidden state (which traps are armed, which switches toggled, etc.).  
- **Topology ( $\theta$ ):** In the **standard evaluation**, $\theta$ (walls, doors, secret-edge existence, item locations) is **not** given to the agent; it must be inferred from \texttt{View} and \texttt{Inspect}. Optionally we support an **oracle-topology** regime where $\theta$ is provided, isolating belief over $h$ only. All reported results must state which regime is used.  
- **Actions:** $\{\texttt{Move}(N,S,E,W),\;\texttt{Inspect},\;\texttt{Interact},\;\texttt{UseItem}\}$. Moves respect walls/doors. \texttt{Inspect} targets the current tile or an adjacent tile and has **low success probability** (e.g. $p_{\text{reveal}}=0.15$ per use, tier-dependent) to reveal a secret door or trap; failure gives no information. This prevents “Inspect-spam” from dominating; systematic belief updating and exploration are required. \texttt{Interact} toggles a switch or opens a door; \texttt{UseItem} uses an inventory item (e.g. a key).  
- **Observations:** $o_t = (\text{View}_r(\theta, x_t),\;\text{Event}_t)$. $\text{View}_r$ returns an egocentric radius-$r$ grid (typical $r=2$) showing visible tiles/objects (walls, floor, doors, keys, goal). **Crucially**, hidden hazards (traps) are *visually identical to floor* in $\text{View}$. $\text{Event}_t$ gives immediate feedback: e.g. “you hear a click,” damage from trap, or “you picked up a key.” High tiers may disable explicit cues to increase ambiguity.  
- **Dynamics:** The transition $T(s'|s,a)$ is deterministic given $h$ and $\theta$. For example, stepping on a tile with an armed trap leads to a damage event and (depending on rules) either remains alive or dies (end episode). Toggling a switch in $\theta$ updates $h$ by disarming/arming distant traps or opening secret passages.  
- **Reward:** Sparse: typically $+1$ for reaching the goal, a small step cost (e.g. $-0.001$), and negative cost for trap damage (constraint regime scores survival separately). Episodes end on goal or death. We support two evaluation regimes: (1) **Sparse goal regime** where agent maximizes total reward; (2) **Constraint regime** where goal success and safety (no trap activation, no death) are reported separately to avoid reward hacking.  

**Latent Inference:** The generator enforces adversarial constraints: (a) *Indistinguishability:* at least one trap has no unique visual hint; (b) *Alternate safe path:* there exists a detour avoiding at least one trap; (c) *Non-local causality (Tier4+):* at least one switch far away affects a hazard with no local visual cue; (d) *Distractors (Tier5):* plausible dead-end corridors or rooms that waste time.  

**Difficulty tiers (T1–T5):** Tier definitions are required for reproducibility. We define: **T1** — single hazard, no switch; **T2** — 1–2 hazards, optional local switch; **T3** — multiple hazards, at least one switch, short path may be trapped; **T4** — non-local causality (at least one switch controls a distant trap with no local cue); **T5** — T4 plus distractors (dead-ends, longer horizon). Map size and visibility radius may scale with tier (e.g. T1–T2: up to 12×12, $r=2$; T4–T5: up to 20×20, $r=2$). Exact generator parameters (e.g. max traps, min switch–trap distance) are fixed in the released code.  

**Belief and Bayes Filter:** A Bayes-optimal agent maintains belief $b_t(s)$, a distribution over states. In practice we factor beliefs as $b_t(x,\theta,h) = \delta(x_t)\delta(\theta) b_t(h)$ (static topology known or learned once) and update:  
\[b_{t+1}(h') \propto \sum_{h} T((x_{t+1},\theta,h') \mid (x_t,\theta,h), a_t)\;\Omega(o_{t+1}\mid x_{t+1},\theta,h')\;b_t(h),\]  
where $\Omega(o\mid s)$ is the observation likelihood and $T$ acts on hidden state deterministically given $(x,a)$. (This is the standard POMDP belief update[12].) In DWMB, computing $b_t(h)$ may be intractable for large maps, but agents may approximate it.  

**Environment Schema (Appendix A):** Each instance is a JSON file specifying height, width, tile map, visibility range, agent/goal positions, lists of doors (with locks), secret edges, traps (with type, armed-flag, and associated switch), and switches (with id, location, and list of trap effects). An excerpt in Appendix A shows format. The `eval` field lists coordinates of “hazards for PIR” so evaluation scripts know which traps count.  

## Worked Example Dungeon  
Figure 2 shows a minimal DWMB-T3/T4 level illustrating key ideas: a hidden **Trap** on the short path to the Goal, and a remote **Switch** that disarms it. The agent (Start) must either gamble across the trap, explore to find the switch, or use \texttt{Inspect} on the corridor. This requires reasoning: simply heading straight can kill the agent.  

![Figure 2: Worked example dungeon with latent trap and switch.](dwmb_figs/fig2_worked_example_dungeon_map.pdf) **Figure 2**: A toy DWMB dungeon (16×16 grid). The tile marked “Trap” is visually identical to others until stepped on. The “Switch” tile, if interacted, disarms the trap. The blue corridor is the shortest path. A safe agent will infer the trap’s presence (PIR) and/or find the switch before crossing.  

**Belief Update Walk-through:** Denote $h$ = boolean “is trap at (r,c) armed?”. Initially $\Pr(h=1)=0.5$ (uniform). After moving 2 steps along the blue path, the agent inspects the corridor tile but sees no change; the posterior $\Pr(h=1)$ may increase slightly (inspection gives noisy evidence). If it backtracks and finds the switch via a longer route, then upon toggling it, the agent should set $\Pr(h=1)=0$ before returning. A model-free agent would only learn by getting damaged. We evaluate **PIR**: if the agent’s belief $\hat p(h)$ crosses threshold (say 0.9) before stepping on the trap, that counts as preemptive inference.  

## Metrics  

- **Preemptive Inference Rate (PIR):** Let $\mathcal{H}$ be hidden hazards. For each hazard $h$, let $\tau(h)$ be the first time the agent visits that tile. Let $\hat p_t(h)$ be the agent’s predicted probability it is dangerous. Then for threshold $\delta$,  
\[
\mathrm{PIR}_\delta = \frac{1}{|\mathcal{H}|}\sum_{h\in\mathcal{H}} \mathbf{1}\big[\hat p_{\tau(h)-1}(h)\ge\delta\big].
\]  
This measures how often agents correctly predict hazards *before* encountering them.  

**Belief extraction ( $\hat p_t(h)$ ):** PIR is only comparable across methods if $\hat p_t(h)$ is defined consistently. We require every submitted agent to expose **per-hazard probabilities** at each step, as follows. (1) **Belief-native agents** (e.g. explicit belief or latent-state trackers): report the marginal probability of “hazard at $(r,c)$ dangerous” from the agent’s belief or decoder. (2) **Model-free RL / MuZero-like:** add an auxiliary **belief head** trained (e.g. with BCE or log loss) to predict hazard presence from the same features used for the policy; the head’s output is $\hat p_t(h)$. (3) **Dreamer/RSSM:** use a decoder or auxiliary head from $z_t$ to per-tile hazard probability; do not use value at the tile as a proxy for belief. (4) **LLM agents:** extract or prompt for a numerical probability per eval hazard at each step and log it. Evaluation scripts will only use these logged values; agents that do not provide them cannot receive a PIR score.  

We also report **AUPIR** (area under PIR vs. $\delta$ curve). **Calibration** (comparing $\hat p$ to empirical frequencies over many steps/trials) is a **secondary diagnostic**: good calibration does not imply high PIR, and high PIR does not require perfect calibration; we report it to detect overconfident or underconfident beliefs. High PIR (especially at high $\delta$) means safe inference rather than luck.  

- **Success and Safety:** Report goal completion rate and survival rate (avoiding death). Also count total **hazard activations** and damage taken (safety signals decoupled from reward).  

- **Map Reconstruction F1:** If the agent attempts to explicitly map the dungeon, we compute F1 score on discovered doors/secret edges.  

- **Causal Discovery F1:** If the agent outputs a graph of switch→trap connections, we compute F1 against ground truth.  

- **Sample Efficiency:** Area under learning curves (agent performance vs. environment steps) for both goal success and PIR (to compare how quickly belief-learning emerges).  

These metrics distinguish behaviors: e.g. one method might reach the goal often (high success) yet have low PIR (tolerating many traps), whereas an agent that actively infers traps will show high PIR.  

## Agent Architectures and Learning Objectives  
DWMB is algorithm-agnostic, but we outline candidate families and losses.  

- **Model-free RL:** Policies (e.g. PPO or A2C) with partial observations and memory (LSTM or GRU, perhaps external memory). Expectation: can learn goal-reaching but often at cost of safety.  

- **Implicit-model planning (MuZero-like):** Agents that learn to predict reward, value, and policy logits in a latent tree-search model[10]. These agents can plan without explicit latent variable semantics, so they may fail if reward is too sparse or delayed by switches.  

- **Latent world models (Dreamer/RSSM):** Train a recurrent latent state-space model end-to-end (e.g. RSSM) to predict future latents and rewards. Use imagined rollouts to train policy[30]. Without special structure, these may struggle to capture discrete triggers or long causal chains.  

- **LLM + Memory:** A language-agent reading textual descriptions of the map (e.g. “You see a corridor to east; it seems normal”) and using an LLM (e.g. GPT-4 with memory) to form hypotheses and plan. We include this to test strong priors. Likely failure: hallucinated consistent world models and poor calibration of beliefs.  

- **Proposed JEPA-style world model + planner (sketch):** Based on predictive representations[27].  
  - *Encoder* $E_\phi(o_t)$ maps observation to token embeddings $y_t$ (one vector per visible tile).  
  - *Context RNN* $C_\psi$ aggregates $\{y_{1:t}\}$ and actions into latent state $z_t$.  
  - *Predictor* $P_\omega$ takes $z_t$ and predicts future embeddings for masked/unseen regions (or future time steps).  
  - *Planner* uses $P_\omega$ as a dynamics model (e.g. via Model Predictive Control or latent-tree search) to select actions.  
  - For PIR, $z_t$ must be mapped to per-hazard probabilities: e.g. an auxiliary **decoder** or **belief head** $D(z_t, \text{pos})$ that outputs $\hat p_t(h)$ for each hazard position, trained with the same latent-prediction and belief-consistency losses. Without this, the architecture does not yield a comparable PIR. Implementation details (masking scheme, regularization to avoid collapse) are left to the release.  

**Losses:**  
- *Latent prediction loss:* For masked tiles (e.g. hidden trap locations) or future steps, use $L_2$ or contrastive loss:  
\[
\mathcal{L}_{pred} = \sum_t \sum_{i\in m} \|P_\omega(z_t)_{i} - \mathrm{sg}(y_{t,i})\|^2,
\]  
where $m$ indexes masked positions and sg() denotes stop-gradient. This encourages the model to predict latent features (analogous to V-JEPA for video[28]).  

- *Belief consistency (KL) loss:* If using an inference network $q_\varphi(z_{t+1}|o_{1:t+1},a_{1:t})$ and a transition prior $p_\omega(z_{t+1}|z_t,a_t)$, enforce  
\[
\mathcal{L}_{belief} = \sum_t D_{KL}\big(q_\varphi(z_{t+1}|o_{1:t+1}) \,\|\, p_\omega(z_{t+1}|z_t,a_t)\big),
\]  
so the model’s predictive belief matches the posterior given new observation. This penalizes collapsing the belief.  

*(Hyperparameters, architectures, and optimization are left for implementation. Appendix E gives a timeline to complete these steps.)*

![Figure 1: Observed vs. latent vs. belief states.](dwmb_figs/fig1_observed_latent_belief.pdf) **Figure 1**: (a) Agent’s local observation (gray = unknown). (b) True latent map (walls, goal, hidden traps/switch). (c) Agent’s belief distribution (blue = high probability of trap). DWMB evaluates how quickly the belief (c) aligns with the latent traps (b) *before* activation (PIR).  

## Experimental Protocol and Analysis Plan (no results)  
We present a preregistered-style evaluation. **No empirical results are reported in this document;** the following are hypotheses and analysis plans to be executed upon running the benchmark.  

**Benchmark Suite:** We recommend 200 training instances per tier (T2–T5). Each tier has difficulty constraints above. Splits: (i) *Train seeds* (seen during training); (ii) *Test seeds* (held-out but same generator); (iii) *Counterfactual tests*: for each test dungeon, randomly permute which tile is the trap or which switch controls which trap (preserving geometry) to catch agents that use spurious cues.  

**Baselines:** Table 2 outlines methods and expected failures.

|Method                 | Expected Strength                | Expected Failure Mode (DWMB)         |
|-----------------------|----------------------------------|--------------------------------------|
|Model-free RL (PPO+LSTM)| Robust policy learning           | Low PIR; may “tank” to proceed (risk-taking) |
|MuZero-like            | Adaptive planning                | May ignore trap semantics; mis-assign credit over many steps |
|RSSM/Dreamer world-model| Imagination for efficiency      | Difficulty with discrete triggers; belief collapse in ambiguity |
|LLM + memory           | Strong priors and language reasoning | Hallucinated/spurious maps; inconsistent beliefs |
|JEPA-style + planner   | Semantically rich latent model   | Requires careful design; can collapse without regularizers |

*Table 2: Baselines and hypothesized weaknesses in DWMB.*  

**Hypotheses:** We will test: (H1) At similar goal-success rates, explicit belief/planning agents (world-model, JEPA-planner) will have significantly higher PIR than model-free agents. (H2) On T4–T5, planners will exhibit better causal-discovery F1 than reactive methods. (H3) On counterfactual tests, agents relying on shortcuts will fail (sharp PIR drop), whereas true-belief agents will generalize better.  

**Statistics:** Run each method with $K \geq 10$ random seeds per instance. For PIR and other continuous metrics, use paired Wilcoxon signed-rank tests across methods on each instance. Use mixed-effects regression of PIR or success with fixed effect Method and random intercept per dungeon. Correct for multiple comparisons (Benjamini–Hochberg). Report effect sizes (Cliff’s delta for PIR, odds-ratio for success). 

**Expected Outcomes:** DWMB is designed so that reaching the goal is *possible* without full inference (by risking traps), but mastering latent inference is needed for high PIR. We expect model-free RL to achieve moderate success but low PIR (many trap hits). MuZero-like may get higher success, but still limited PIR since it does not explicitly model hidden state[10]. Recurrent world models should improve PIR somewhat, but may learn spurious correlations. JEPA-style agents should achieve the highest PIR and robustness on counterfactual tests if properly trained. Figure 4 shows an illustrative (mock) metric outcome: two methods with similar success but different PIR curves.  

![Figure 4: Mockup of goal success vs. PIR.](dwmb_figs/fig4_metric_mockups.pdf) **Figure 4** (illustrative only): Success rates may saturate, but PIR (shaded region) distinguishes safe vs. unsafe strategies. 

## Discussion and Limitations  
DWMB prioritizes *diagnostic clarity* over realism. The gridworld abstraction allows full control and observability of hidden state, enabling rigorous audits (e.g. counterfactual hazard swaps). However, this abstraction ignores perception and low-level dynamics. Success on DWMB is necessary but not sufficient for general intelligence.  

**Failure modes to watch:** (1) *Unsafe policies:* Agents might learn to take damage (violating safety) to reach goals. We mitigate by separate scoring of hazards and survival. (2) *Representation collapse:* Without regularization, latent models (JEPA or RSSM) may collapse to trivial solutions. (3) *Spurious cues:* Generators must avoid obvious patterns; we use counterfactual tests to catch reliance on geometry. (4) *Overfitting to small domains:* We encourage seed diversity and held-out tests.  

**Hypothesis and testable claim:** DWMB is designed to test “Does the agent build and use a coherent belief over the hidden dungeon structure?” A high goal rate with low PIR would indicate “unsafe” or purely reactive success; high PIR and stable performance under counterfactual layouts would support true latent inference. The hypothesis that belief-based agents achieve higher PIR (and better counterfactual robustness) than reactive agents at matched goal success is **falsifiable** and will be tested by the planned analysis once experiments are run. We do not assert it as an established result.  

## Data and Code Availability  
No empirical data are reported here. We will open-source: (i) the DWMB generator and JSON schema; (ii) fixed-train/test seed splits; (iii) baseline agent code; (iv) evaluation scripts for PIR and other metrics. All should be released under an open license upon benchmark release.  

## Acknowledgements  
*Unspecified.* (To be filled.)  

## Competing Interests  
*None declared.*  

## References  
- [6] D. Ha & J. Schmidhuber, *World Models*, arXiv:1803.10122 (2018).  
- [10] J. Schrittwieser *et al.*, *Mastering Atari, Go, Chess and Shogi by Planning with a Learned Model*, Nature 588, 604–609 (2020).  
- [12] L.P. Kaelbling, M.L. Littman, A.R. Cassandra, *Planning and acting in partially observable stochastic domains*, Artif. Intell. 101, 99–134 (1998).  
- [17] *Ibid.*  
- [22] M.G. Bellemare *et al.*, *The Arcade Learning Environment: An Evaluation Platform for General Agents*, JAIR 47 (2013).  
- [23] K. Cobbe *et al.*, *Leveraging Procedural Generation to Benchmark Reinforcement Learning*, arXiv:1912.01588 (2019).  
- [24] M. Chevalier-Boisvert *et al.*, *Minigrid & Miniworld: Modular Reinforcement Learning Environments*, NeurIPS 2023 Datasets & Benchmarks.  
- [25] H. K\"uttler *et al.*, *The NetHack Learning Environment*, NeurIPS 2020.  
- [26] M.-A. C\^ot\'e *et al.*, *TextWorld: A Learning Environment for Text-based Games*, arXiv:1806.11532 (2018).  
- [27] Y. LeCun, *A Path Towards Autonomous Machine Intelligence* (essay, 2022).  
- [28] V-JEPA (video), Meta.  
- [30] D. Hafner *et al.*, *Mastering Diverse Domains through World Models (DreamerV3)*, arXiv:2301.04104 (2023).  
- C. Beattie *et al.*, *DeepMind Lab*, arXiv:1612.03801 (2016).

<details><summary><b>Appendix A: JSON Schema Excerpt (DWMB-0.1)</b></summary>

```json
{
  "version": "dwmb-0.1",
  "grid": {"height": H, "width": W, "tiles": "..."},
  "visibility": {"radius": r, "line_of_sight": true},
  "entities": {"agent_start": [r,c], "goal": [r,c]},
  "topology": {
    "doors": [{"pos":[r,c],"type":"locked","key_id":"k1"}],
    "secret_edges": [{"from":[r,c], "to":[r,c], "discover":"inspect"}]
  },
  "hidden_state": {
    "traps": [{"pos":[r,c], "kind":"pit",
               "armed":true, "disarm_switch":"s1"}],
    "switches": [{"id":"s1","pos":[r,c],
                  "effects":[{"trap_pos":[r,c], "armed":false}]}]
  },
  "reward": {"goal": +1.0, "step": -0.001, "trap": -0.2},
  "terminal": {"goal": true, "death_on_trap": false},
  "eval": {"hazards_for_PIR": [[r,c], ...]}
}
```
*Example DWMB instance: hidden traps and switches with effects. ‘hazards_for_PIR’ lists which trap tiles contribute to PIR.*  

</details>

<details><summary><b>Appendix B: Generator Flowchart (Mermaid)</b></summary>

```mermaid
flowchart LR
  Seed[Seed \u03be] --> Gen[Generator G(\u03be)]
  Gen --> Topo[Static topology \u03b8]
  Gen --> Haz[Hidden variables h]
  Topo --> Instance[\u1e26_{\u03be}: POMDP instance]
  Haz --> Instance
  Instance --> Agent[Train/Test Agents]
  Agent --> Eval[Compute metrics (PIR, success, etc.)]
  Eval --> Results
```
*Figure: The DWMB generator takes a seed \u03be to produce a POMDP instance (\u1e26_{\u03be}). Agents run on this instance, and evaluation computes PIR and other metrics.*  
</details>

<details><summary><b>Appendix C: Evaluation Pseudocode (Sketch)</b></summary>

```python
for instance in DWMB_suite:
    load(instance)
    for agent in agent_list:
        b = agent.init_belief()
        done = False
        t = 0
        while not done:
            o = observe()
            a = agent.act(o, b)
            done = step(a)  # applies action, returns done flag
            o_new = observe()
            b = agent.update_belief(a, o_new)
            log(b)  # e.g., predicted hazard probs
            t += 1
        metrics = compute_metrics(agent.log, ground_truth)
        record(metrics)
aggregate_and_analyze_results()
```
*Each agent updates its belief and logs predicted hazards (per the belief-extraction convention) before activation. After each trial, compute PIR, success, F1 scores, etc.*  
</details>

<details><summary><b>Appendix D: Example Instance (Worked Dungeon)</b></summary>

```json
{
 "version":"dwmb-0.1",
 "grid":{"height":16,"width":16,"tiles":"(omitted)"},
 "visibility":{"radius":2,"line_of_sight":true},
 "entities":{"agent_start":[2,2],"goal":[13,12]},
 "hidden_state":{
   "traps":[{"pos":[2,6],"kind":"slick",
             "armed":true,"disarm_switch":"s1"}],
   "switches":[{"id":"s1","pos":[3,13],
               "effects":[{"trap_pos":[2,6],"armed":false}]}]
 },
 "eval":{"hazards_for_PIR":[[2,6]]}
}
```
*Minimal JSON for the worked example (agent at [2,2], goal at [13,12]). A slick pit at [2,6] is armed; switch “s1” at [3,13] disarms it. This teaches latent reasoning.*  
</details>

<details><summary><b>Appendix E: Timeline (Proposed 12-week Plan)</b></summary>

1. **Weeks 1–2:** Implement DWMB core engine, JSON schema, and simulation (fast C/Python).
2. **Weeks 3–4:** Develop tiered generators (T2–T5 constraints) and unit-test dungeons.
3. **Weeks 5–7:** Implement baseline agents (PPO+LSTM, MuZero, RSSM); build training/eval pipeline; sanity-check on trivial tasks.
4. **Weeks 8–9:** Prototype JEPA-style agent with latent predictor and planning (latent MPC or search).
5. **Weeks 10–11:** Run experiments, collect metrics; perform statistical analysis; conduct ablations (e.g., remove belief loss).
6. **Week 12:** Prepare artifacts (code, data); finalize paper draft and camera-ready revisions.

*Deliverables:* Code release with generator, baselines, evaluation scripts; dataset splits; manuscript.

</details>

