# The Dungeon World Model Benchmark (DWMB): Crafting Treacherous Labyrinths to Test an Adventurer's True Understanding of Hidden Dangers  
**Author of record:** Daniel C. McShan, PhD (custodian). *In voce* Gary Gygax.

**Abstract:** A true adventurer, a cunning player, must master the art of understanding the dungeon's very nature and plotting their course accordingly. Such mastery of the world's ways and strategic planning are the very heart of a cunning adventurer, separating a true hero from a mere delver[6][10]. Yet, too many of these so-called "benchmarks" allow a player to blunder through, succeeding by sheer luck or brute force, never truly grasping the dungeon's hidden ways. We present the **Dungeon World Model Benchmark (DWMB)**: a collection of compact, procedurally generated grid-map dungeons – partially observed labyrinths, mind you – explicitly crafted to demand that an adventurer infer unseen dangers, the true layout of the passages, and the distant, hidden levers that spring the traps. The most dangerous traps look just like safe floor, and a lever in one chamber might arm or disarm a pitfall far across the dungeon. DWMB includes a precise, machine-readable JSON blueprint, difficulty tiers (T1–T5), and canonical "unit-test" dungeons to ensure a fair test. We propose **Preemptive Inference Rate (PIR)**: the fraction of dangers whose true nature was grasped *before* the adventurer stumbled into them, distinguishing true, safe foresight from "unsafe success" achieved by learning through lost hit points. Because we have no results to share *yet*, we provide our battle plan: starting points (the 'Brute Force' method, MuZero-style intuitive planners[10], 'Dreamer' adventurers, and Sages with scrolls of lore), proposed architectures for those who truly seek to understand (our 'Joint Embarkation & Predictive Acumen' (JEPA)-style approach[27]), lessons learned (hidden-feature prediction and 'map consistency' via KL), and our rigorous dice rolls (paired Wilcoxon, mixed-effects models, FDR correction). DWMB's purpose is to gauge whether an adventurer can maintain a true understanding of the dungeon's hidden secrets and plot a wise course of action.

## Executive Summary  
DWMB is a benchmark suite with a clear quest target: *adventurers who explicitly map and update their understanding of the dungeon's hidden mechanisms should achieve a higher Preemptive Inference Rate (PIR) than those who merely react, all while reaching their goal with equal consistency*. The dungeon environments are *treacherously* designed: hidden traps and switches are visually indistinguishable from safe elements, and causal triggers (e.g., a lever disabling a distant pit) are non-local. Treasure is sparse (reaching the goal yields XP, with a small penalty for each step), and survival is measured separately (e.g., "no traps sprung") to prevent adventurers from simply taking damage to win. DWMB reports multiple scores (goal completion, survival, trap springs, PIR/AUPIR, calibration curves, topology/causal F1), distinguishing between sheer luck and true cunning. We include:
- **Formal definitions (Partially Observed Labyrinth)**: state = (adventurer's position, fixed dungeon layout, hidden dungeon secrets); observations = what the adventurer sees in their immediate vicinity; the Dungeon Master's filter (our standard for tracking hidden state) for updating their understanding.
- **Dungeon Blueprint (JSON schema)**: precise listings of walls, secret doors, traps, switches, with a special `eval.hazards_for_PIR` annotation for which dangers truly test their cunning. (Appendix A shows a schema excerpt and minimal example.)
- **A Sample Dungeon Crawl**: a 16×16 grid-map (Fig.2) with a hidden **Trap** on the short path and a remote **Switch** that disarms it, illustrating how their understanding of "is-the-corridor-trapped" evolves.
- **Metrics**: **Preemptive Inference Rate (PIR)**: the proportion of dangers for which the adventurer's cunning estimate $p(hazard) \ge \delta$ **before** they set foot upon it. Also AUPIR (area under PIR vs. threshold), calibration plots, plus goal completion, survival, trap counts, topology/causal discovery F1, and expedition efficiency AUCs.
- **Starting Points**: (a) The 'Brute Force' Method (e.g., PPO+LSTM), expected to find the goal sometimes but with low PIR (a high tolerance for taking damage); (b) The 'Intuitive Planner' (MuZero-style[10]); (c) The 'Dreamer' (RSSM-style[30]) with imagined rollouts; (d) Sages with scrolls of lore and an external memory for tracking their understanding.
- **Our Proposed Scheme**: A 'Joint Embarkation & Predictive Acumen' (JEPA)-style encoder and diviner[27] crafting foresight into the dungeon's secrets, combined with a tactical planning module.
- **The Lessons Learned**: Hidden-feature prediction loss (masking and divining unseen areas) and a 'map consistency' (KL-based) loss between their inferred map and the dungeon's true nature.
- **Our Rigorous Dice Rolls**: Paired Wilcoxon 'Saving Throw' tests on PIR across instances, mixed-effects models with dungeon random effects, and FDR control for multiple comparisons.
- **Our Claim**: Adventurers who truly infer the dungeon's secrets will show *high PIR and remain cunning even when the DM subtly shifts the dungeon's dangers*, whereas those who merely react will have low PIR. DWMB measures exactly this difference.
  
## Introduction  
Reinforcement learning, bless its heart, has shown prowess in tasks demanding keen senses, but *a truly autonomous intelligence* – the kind of adventurer we seek – demands an inner map of the world and a solid plan[6][27]. These 'world models' (latent representations of dynamics) enable adventurers to simulate and plan amidst uncertainty[6][27]. MuZero-style adventurers, for instance, demonstrate that even without drawing a perfect map, learning the value of treasure, the worth of a path, and the best course of action can guide their steps[10]. However, most standard proving grounds (Atari, Procgen, MuJoCo, etc.) too often let a reactive adventurer win through sheer dumb luck or by ignoring the unseen, because hidden dangers are too rare or simply don't matter[17][27].

The Dungeon World Model Benchmark (DWMB) aims to **test the adventurer's cunning in discerning the unseen**. Each instance is a grid-map dungeon with partial observability (a local view), hidden dangers, and unseen triggers. Traps look identical to safe floor, and some must be disarmed by a distant switch. The adventurer must weigh exploration (gathering knowledge) against exploitation (reaching the goal safely) – a classic dilemma in any true Partially Observed Labyrinth[17][12]. Fig.1 illustrates how an adventurer’s local observation (a) reveals little of the true, hidden map (b), but a competent adventurer maintains an understanding (c) over possible maps. PIR measures if their understanding of the dungeon's true nature becomes accurate *before* a trap springs.

**Our Contributions:** We define DWMB as a formal distribution of Partially Observed Labyrinths, complete with explicit hidden variables and deliberate traps for the unwary. We release a JSON blueprint and canonical instances (Fig.2) and propose diagnostic scores (PIR, calibration, topology/causal F1). We outline our battle plan for evaluation with starting points, anticipated results, and statistical divinations. We propose candidate architectures combining 'Joint Embarkation & Predictive Acumen' (JEPA)-style latent prediction[27] with tactical planning. This blueprint is meant as a proving ground to quantify how well adventurers learn and use the dungeon's hidden nature, **before** we unleash them.

## Related Work  
**Dungeon Lore and Tactics:** Ha & Schmidhuber (2018) demonstrated that an unsupervised model of hidden dungeon dynamics can be learned and used to train tactics "within the adventurer's own imagined dream-dungeon"[6]. Dreamer/RSSM methods (Hafner et al.) extend this, optimizing these hidden representations for adventurer performance across various domains[30]. MuZero (Schrittwieser et al., 2020) achieved planning without an explicit dungeon model by learning to predict treasure, path values, and optimal actions in a hidden space[10]. These works inspire DWMB: a benchmark where the *quality* of foresight and belief-state planning are essential.

**The 'Joint Embarkation & Predictive Acumen' (JEPA) and Foresight:** Yann LeCun (2022) put forth the 'Joint Embarkation & Predictive Acumen' (JEPA) idea: to learn dungeon lore by divining abstract representations of masked future observations, not just raw sights and sounds[27]. Recent implementations (e.g., Meta’s V-JEPA for video[28]) mask spatiotemporal hidden features. JEPA-like methods emphasize abstraction and efficiency, which is why we propose a JEPA-style latent diviner in DWMB: it must predict hidden map features without explicitly rendering every pixel.

**Partially Observed Labyrinths and Mastering the Unseen:** Partially Observed Labyrinths (POMDPs) are the canonical model for partial observability[12][17]. The adventurer's current understanding (their posterior over hidden states) is the key statistic, updated by the Dungeon Master's filter (e.g., $b_{t+1}(s') \propto \Omega(o_{t+1}|s') \sum_s T(s'|s,a_t) b_t(s)$)[12][17]. Kaelbling *et al.* observed that an adventurer's actions both alter the dungeon and reveal its secrets[17]. DWMB explicitly uses the Partially Observed Labyrinth structure: e.g., $b_t(h)=P(h\text{ active})$ is tracked, and we evaluate it via PIR.

**Proving Grounds for Cunning:** Existing benchmarks test some aspect of generalization or partial observability. DeepMind Lab offers 3D partially-observed tasks[17]; Procgen (Cobbe et al.) focuses on generalization via procedural content[23]. MiniGrid (Chevalier-Boisvert et al.) has modular grid tasks with some hidden state[24]. NetHack Learning Environment (NLE) and TextWorld provide very complex, textual dungeon domains with hidden state and long horizons[25][26]. DWMB differs by being *intentionally treacherous*: every layout includes false paths and ambiguous dangers to thwart lazy shortcuts (see Table 1). It trades high fidelity for *diagnostic clarity* of latent inference.

|Benchmark      | Partial Obs. | Hidden Dangers | Non-local Levers | Crafted to Mislead | Fast Sim. | Example Ref.|
|---------------|:-----------:|:-------------:|:-------------------:|:------------------:|:---------:|------------|
|Atari (ALE)    | ✔           | ✘             | ✘                   | ✘                  | ✔         | [22]      |
|Procgen        | ✔           | ✘             | ✘                   | ✘                  | ✔         | [23]      |
|DeepMind Lab   | ✔           | ✘             | ✘/✔                 | ✘                  | ✘         | [17]      |
|MiniGrid       | ✔           | ✘/✔           | ✘/✔                 | ✘                  | ✔         | [24]      |
|NetHack (NLE)  | ✔           | ✔             | ✔                   | ✔                  | ✔         | [25]      |
|TextWorld      | ✔           | ✔             | ✔                   | ✔                  | ✔         | [26]      |
|**DWMB (Ours)**| ✔           | ✔             | ✔                   | ✔                  | ✔         | This work |

*Table 1: Benchmark comparison (conceptual). "Crafted to Mislead" means the environment includes intentionally misleading affordances (e.g., false paths, indistinguishable traps). Symbols indicate typical properties; a checkmark means "generally present" in that benchmark. DWMB is designed to *demand* hidden-state inference.*  

## DWMB Definition and Environment Specification  
DWMB is formally a **distribution $\mathcal{D}$** over episodic Partially Observed Labyrinths $\mathcal{M}=(S,A,O,T,\Omega,R,\gamma)$. A random seed $\xi$ generates a map and hidden variables via generator $G$: $\mathcal{M}_\xi = G(\xi)$.  
- **States:** $s=(x,\theta,h)$, where $x$ is the adventurer’s (row,col) position, $\theta$ is the fixed dungeon layout (walls, doors, secret passages, treasure locations), and $h$ is the dynamic hidden state (which traps are armed, which levers have been pulled, and so on).  
- **Actions:** $\{\texttt{Move}(N,S,E,W),\;\texttt{Scrutinize},\;\texttt{Manipulate},\;\texttt{EmployItem}\}$. Moves respect walls/doors. \texttt{Scrutinize} might reveal information (e.g., detect a secret door or trap with a low chance of success, like a saving throw), \texttt{Manipulate} toggles a switch or opens a door, \texttt{EmployItem} uses an inventory item (e.g., a key).  
- **Observations:** $o_t = (\text{View}_r(\theta, x_t),\;\text{Event}_t)$. $\text{View}_r$ returns an egocentric radius-$r$ grid (typical $r=2$) showing visible tiles/objects (walls, floor, doors, keys, goal). **Crucially**, hidden dangers (traps) are *visually identical to ordinary floor* in their immediate $\text{View}$. $\text{Event}_t$ provides immediate feedback: e.g., "you hear a click," "you take damage from a trap," or "you picked up a key." High tiers may disable explicit cues to increase ambiguity.  
- **Dynamics:** The transition $T(s'|s,a)$ is deterministic, given the dungeon's secrets $h$ and its layout $\theta$. For example, stepping on a tile with an armed trap leads to a damage event and (depending on rules) either remains alive or dies (end episode). Manipulating a switch in $\theta$ updates $h$ by disarming or arming distant traps, or perhaps revealing secret passages.  
- **Treasure:** Sparse: typically $+1$ XP for reaching the goal, a small penalty for each step (e.g. $-0.001$), and a negative cost for trap damage (in the 'survival mode,' we track their Hit Points separately). Episodes end on goal or death. We support two evaluation regimes: (1) **Sparse Goal Regime** where the adventurer maximizes total XP; (2) **Survival Regime** where goal completion and safety (no trap activation, no death) are reported separately to avoid adventurers exploiting damage.  

**Hidden Inference:** The generator enforces treacherous constraints: (a) *Indistinguishability:* at least one trap has no unique visual hint; (b) *Alternate safe path:* there exists a detour avoiding at least one trap; (c) *Non-local causality (Tier4+):* at least one switch far away affects a danger with no local visual cue; (d) *Distractors (Tier5):* plausible dead-end corridors or rooms that waste precious time.  

**Understanding and the Dungeon Master's Filter:** A truly cunning adventurer maintains their understanding $b_t(s)$, a distribution over states. In practice we factor understandings as $b_t(x,\theta,h) = \delta(x_t)\delta(\theta) b_t(h)$ (fixed dungeon layout known or learned once) and update:  
\[b_{t+1}(h') \propto \sum_{h} T((x_{t+1},\theta,h') \mid (x_t,\theta,h), a_t)\;\Omega(o_{t+1}\mid x_{t+1},\theta,h')\;b_t(h),\]  
where $\Omega(o\mid s)$ is the observation likelihood and $T$ acts on hidden state deterministically given $(x,a)$. (This is the standard Partially Observed Labyrinth belief update[12].) In DWMB, calculating $b_t(h)$ might be too complex for truly vast maps, but adventurers can approximate it.  

**Dungeon Blueprint (Appendix A):** Each instance is a JSON file specifying height, width, tile map, visibility range, adventurer/goal positions, lists of doors (with locks), secret passages, traps (with type, armed-flag, and associated switch), and switches (with id, location, and list of trap effects). An excerpt in Appendix A shows format. The `eval` field lists coordinates of "hazards for PIR" so our scribes know which traps count towards their foresight score.  

## Worked Example Dungeon  
Figure 2 shows a minimal DWMB-T3/T4 level illustrating key ideas: a hidden **Trap** on the short path to the Goal, and a remote **Switch** that disarms it. The adventurer (Start) must either gamble across the trap, explore to find the switch, or use \texttt{Scrutinize} on the corridor. This demands true reasoning: simply heading straight can kill the adventurer.  

![Figure 2: Worked example dungeon with latent trap and switch.](dwmb_figs/fig2_worked_example_dungeon_map.pdf) **Figure 2**: A toy DWMB dungeon (16×16 grid). The tile marked "Trap" appears identical to ordinary floor until an adventurer steps upon it. The "Switch" tile, if manipulated, disarms the trap. The blue corridor is the shortest path. A wise adventurer will infer the trap’s presence (PIR) and/or find the switch before daring to cross.  

**Understanding the Dungeon's Secrets:** Let $h$ be a boolean: "is the trap at (r,c) armed?" Initially, $\Pr(h=1)=0.5$ (a coin flip, for all they know). After moving 2 steps along the blue path, the adventurer scrutinizes the corridor tile but sees no change; their posterior $\Pr(h=1)$ may increase slightly (scrutiny gives noisy evidence). If they backtrack, finding the switch via a longer route, then upon manipulating it, the adventurer *should* then know to set $\Pr(h=1)=0$ before returning. A 'Brute Force' adventurer would only learn by losing Hit Points. We evaluate **PIR**: if the adventurer’s belief $\hat p(h)$ crosses a threshold (say 0.9) before stepping on the trap, that counts as preemptive inference.  

## Metrics  

- **Preemptive Inference Rate (PIR): How Well They Foresee Danger:** Let $\mathcal{H}$ be the hidden dangers. For each danger $h$, let $\tau(h)$ be the first moment the adventurer steps upon that tile. Let $\hat p_t(h)$ be the adventurer’s estimated probability that it is dangerous. Then for threshold $\delta$,  
\[
\mathrm{PIR}_\delta = \frac{1}{|\mathcal{H}|}\sum_{h\in\mathcal{H}} \mathbf{1}\big[\hat p_{\tau(h)-1}(h)\ge\delta\big].
\]  
This measures how often adventurers correctly divine dangers *before* they are sprung. We also report **AUPIR** (the total area under the PIR vs. $\delta$ curve) and calibration plots comparing their estimated $\hat p$ to the actual frequency of sprung traps. High PIR (especially at high $\delta$) means true cunning, not mere luck.  

- **Goal Completion and Survival:** Report goal completion rate and survival rate (avoiding death). Also count total **trap springs** and damage taken (safety signals decoupled from XP).  

- **Dungeon Mapping F1:** If the adventurer attempts to explicitly map the dungeon, we compute F1 score on discovered doors/secret passages.  

- **Hidden Mechanism F1:** If the adventurer outputs a graph of switch→trap connections, we compute F1 against the Dungeon Master's truth.  

- **Expedition Efficiency:** Area under learning curves (adventurer performance vs. environment steps) for both goal completion and PIR (to compare how quickly true understanding emerges).  

These scores distinguish behaviors: e.g., one method might reach the goal often (high success) yet have low PIR (tolerating many traps), whereas an adventurer that actively infers traps will show high PIR.  

## Adventurer Approaches and Learning Objectives  
DWMB is algorithm-agnostic, but we outline candidate families and the lessons we expect them to learn.  

- **The 'Brute Force' Adventurer:** Policies (e.g., PPO or A2C) with partial observations and memory (LSTM or GRU, perhaps external memory). Expectation: can learn goal-reaching but often at the cost of their own safety.  

- **The 'Intuitive Planner' (MuZero-style):** Adventurers that learn to predict treasure, path values, and optimal actions within a hidden tree-search model[10]. These adventurers can plan without explicit understanding of hidden variable semantics, so they may fail if treasure is too sparse or delayed by hidden switches.  

- **The 'Dreamer' (RSSM-style) Adventurer:** Trains a recurrent latent state-space model end-to-end (e.g., RSSM) to predict future hidden states and treasure. Uses imagined rollouts to train their tactics[30]. Without special structure, these may struggle to capture discrete triggers or long causal chains.  

- **The 'Sage' with Scrolls and Memory:** A language-agent reading textual descriptions of the map (e.g., "You see a corridor to the east; it seems normal") and using a powerful language model (e.g., GPT-4 with external memory) to form hypotheses and plan. We include this to test strong priors. Likely weakness: hallucinated consistent world models and poor calibration of their beliefs.  

- **Our Proposed 'Joint Embarkation & Predictive Acumen' (JEPA)-style Adventurer and Planner:** Based on predictive representations[27].  
  - An *Encoder* $E_\phi(o_t)$ maps what the adventurer observes to abstract tokens $y_t$ (one vector for each visible tile).  
  - A *Context Scrutinizer* $C_\psi$ gathers $\{y_{1:t}\}$ and actions into a hidden state $z_t$.  
  - A *Diviner* $P_\omega$ takes $z_t$ and foresees future embeddings for masked/unseen regions (or future moments in time).  
  - A *Tactician* uses $P_\omega$ as a model of the dungeon's dynamics (e.g., via Model Predictive Control or a hidden-path search) to choose their next move.  
  - This explicitly models a latent "map belief" and uses it for planning.  

**The Lessons Learned:**  
- *Hidden-feature Prediction Loss:* For masked tiles (e.g., hidden trap locations) or future steps, use $L_2$ or contrastive loss:  
\[
\mathcal{L}_{pred} = \sum_t \sum_{i\in m} \|P_\omega(z_t)_{i} - \mathrm{sg}(y_{t,i})\|^2,
\]  
where $m$ indexes masked positions and sg() denotes stop-gradient. This encourages the model to predict hidden features (analogous to V-JEPA for video[28]).  

- *Map Consistency (KL) Loss:* If using an inference network $q_\varphi(z_{t+1}|o_{1:t+1},a_{1:t})$ and a transition prior $p_\omega(z_{t+1}|z_t,a_t)$, enforce  
\[
\mathcal{L}_{belief} = \sum_t D_{KL}\big(q_\varphi(z_{t+1}|o_{1:t+1}) \,\|\, p_\omega(z_{t+1}|z_t,a_t)\big),
\]  
so the model’s predictive understanding matches the posterior given new observation. This penalizes collapsing the understanding.  

*(Hyperparameters, architectures, and optimization are left for implementation. Appendix E gives a campaign timeline to complete these steps.)*

![Figure 1: Observed vs. latent vs. belief states.](dwmb_figs/fig1_observed_latent_belief.pdf) **Figure 1**: (a) Adventurer’s local observation (gray = unknown). (b) True latent map (walls, goal, hidden traps/switch). (c) Adventurer’s belief distribution (blue = high probability of trap). DWMB evaluates how swiftly the adventurer's understanding (c) aligns with the dungeon's true, hidden traps (b) *before* they are sprung (PIR).  

## Experimental Protocol and Analysis Plan (no results)  
We present a preregistered-style evaluation.  

**The Dungeon Collection:** We recommend 200 training instances per tier (T2–T5). Each tier has difficulty constraints above. Splits: (i) *Train seeds* (seen during training); (ii) *Test seeds* (held-out but same generator); (iii) *Counterfactual tests*: for each test dungeon, we'll randomly reshuffle which tile holds a trap or which lever controls which trap (keeping the layout the same) to catch adventurers who rely on flimsy assumptions.  

**Starting Points:** Table 2 outlines methods and expected weaknesses.

|Adventurer Approach    | Expected Strength                | Expected Weakness (DWMB)         |
|-----------------------|----------------------------------|--------------------------------------|
|The 'Brute Force' (PPO+LSTM)| Robust tactic learning           | Low PIR; may "take damage" to proceed (risk-taking) |
|The 'Intuitive Planner' (MuZero-like)| Adaptive strategy                | May ignore trap semantics; misattribute cause and effect over many steps |
|The 'Dreamer' (RSSM-style)| Imagination for efficiency      | Difficulty with discrete triggers; understanding falters in ambiguity |
|The 'Sage' + memory    | Strong priors and language reasoning | Imagined/false maps; inconsistent beliefs |
|JEPA-style + planner   | Semantically rich hidden model   | Requires careful design; can falter without regularizers |

*Table 2: Baselines and hypothesized weaknesses in DWMB.*  

**Our Guesses:** We will test: (H1) At similar goal completion rates, explicit understanding/planning adventurers (world-model, JEPA-planner) will have significantly higher PIR than 'Brute Force' adventurers. (H2) On T4–T5, planners will exhibit better hidden-mechanism F1 than reactive methods. (H3) On counterfactual tests, adventurers relying on flimsy shortcuts will fail (sharp PIR drop), whereas true-belief adventurers will generalize better.  

**Our Rigorous Dice Rolls:** Run each method with $K \geq 10$ random seeds per instance. For PIR and other continuous scores, use paired Wilcoxon 'Saving Throw' tests across methods on each instance. Use mixed-effects regression of PIR or success, with 'Adventurer Approach' as a fixed effect and a random 'dungeon quirk' intercept. Correct for multiple comparisons (Benjamini–Hochberg). Report effect sizes (Cliff’s delta for PIR, odds-ratio for success). 

**Anticipated Results:** DWMB is designed so that reaching the goal is *possible* without full inference (by risking traps), but mastering hidden inference is needed for high PIR. We expect the 'Brute Force' adventurers to achieve moderate success but low PIR (many trap hits). MuZero-like may get higher success, but still limited PIR since it does not explicitly model hidden state[10]. 'Dreamer' adventurers should improve PIR somewhat, but may learn spurious correlations. JEPA-style adventurers should achieve the highest PIR and robustness on counterfactual tests if properly trained. Figure 4 shows an illustrative (mock) metric outcome: two methods with similar success but different PIR curves.  

![Figure 4: Mockup of goal success vs. PIR.](dwmb_figs/fig4_metric_mockups.pdf) **Figure 4** (illustrative only): Goal completion rates may reach their peak, but PIR (the shaded region) distinguishes between a wise, safe strategy and a reckless one. 

## Discussion and Limitations  
DWMB champions *diagnostic clarity* over mere realism. The grid-map abstraction grants us full control and sight over the dungeon's hidden nature, enabling rigorous audits (e.g., counterfactual hazard swaps). However, this abstraction overlooks the nuances of perception and the fine details of movement. Success in DWMB is vital, but it is not the sole measure of a truly general intelligence.  

**Pitfalls to Avoid:** (1) *Reckless tactics:* Adventurers might learn to take damage (ignoring their own safety) simply to reach the goal. We mitigate by separate scoring of dangers and survival. (2) *Understanding falters:* Without proper guidance, their inner maps (JEPA or RSSM) might collapse into trivial, useless forms. (3) *False trails:* Our dungeon generators must avoid obvious patterns; we use counterfactual tests to catch adventurers who rely on mere geometry rather than true understanding. (4) *Overfitting to small domains:* We encourage seed diversity and held-out tests.  

**Our Testable Proclamation:** DWMB directly asks, "Does the adventurer forge and employ a coherent understanding of the dungeon's hidden structure?" A high goal rate with low PIR indicates "unsafe" or purely reactive success. Conversely, high PIR and stable performance under counterfactual layouts indicates true latent inference. This proclamation – that adventurers relying on true understanding will outperform others on these scores – can be disproven by our planned analysis.  

## Data and Code Availability  
No empirical scrolls are reported here. We shall open-source: (i) the DWMB dungeon generator and its JSON blueprint; (ii) fixed training and testing dungeon seeds; (iii) baseline adventurer code; (iv) evaluation scripts for PIR and other scores. All should be released under an open license upon benchmark release.  

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

<details><summary><b>Appendix A: Dungeon Blueprint Excerpt (DWMB-0.1)</b></summary>

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

<details><summary><b>Appendix B: Dungeon Generator Flowchart (Mermaid)</b></summary>

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
*Figure: The DWMB generator takes a seed \u03be to produce a Partially Observed Labyrinth instance (\u1e26_{\u03be}). Adventurers run on this instance, and evaluation computes PIR and other metrics.*  
</details>

<details><summary><b>Appendix C: Evaluation Scrolls (Sketch)</b></summary>

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
*Each adventurer updates their understanding and logs predicted dangers before activation. After each trial, compute PIR, success, F1 scores, etc.*  
</details>

<details><summary><b>Appendix D: Sample Dungeon (Worked Example)</b></summary>

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
*Minimal JSON for the worked example (adventurer at [2,2], goal at [13,12]). A slick pit at [2,6] is armed; switch “s1” at [3,13] disarms it. This teaches latent reasoning.*  
</details>

<details><summary><b>Appendix E: Campaign Timeline (Proposed 12-week Plan)</b></summary>

1.  **Weeks 1–2:** Implement DWMB core engine, JSON blueprint, and simulation (fast C/Python).
2.  **Weeks 3–4:** Develop tiered dungeon generators (T2–T5 constraints) and unit-test dungeons.
3.  **Weeks 5–7:** Implement baseline adventurers (PPO+LSTM, MuZero, RSSM); build training/eval pipeline; sanity-check on trivial tasks.
4.  **Weeks 8–9:** Prototype JEPA-style adventurer with latent diviner and planning (latent MPC or search).
5.  **Weeks 10–11:** Run expeditions, collect scores; perform statistical analysis; conduct ablations (e.g., remove belief loss).
6.  **Week 12:** Prepare artifacts (code, data); finalize paper draft and camera-ready revisions.

*Deliverables:* Code release with generator, baselines, evaluation scripts; dataset splits; manuscript.

</details>