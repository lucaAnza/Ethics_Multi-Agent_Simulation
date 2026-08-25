## Ethics in Generated Multi-Agent Simulation

### Vision

The goal of this project is to design and implement a simulation environment where autonomous agents will perceive situations, evaluate possible actions, and make decisions according to different ethical frameworks.

The core idea is to move beyond fixed scenarios where **moral situations emerge from the interaction between agents and a stochastic environment**. This allows the study of ethical decision-making under uncertainty, which better reflects real-world conditions.

In addition to traditional rule-based agents, the project will explore the use of **Large Language Models (LLMs)** as decision-making agents. Rather than only evaluating LLMs through static moral questionnaires, the project will test how they behave when placed inside a dynamic simulation and required to act under uncertainty, partial information, and changing conditions.

### Goals

<img src = "src/schema.png" width = 80%>

The project aims to achieve the following objectives:

* **Design a generated simulation environment** ✅
  Create a system that produces dynamic and uncertain scenarios, for example in an autonomous driving context.

* **Model ethical agents**  ✅
  Implement multiple agents, each following a specific ethical framework, such as:

  * **Utilitarianism** (minimizing some specific objective function)
  * **Deontology (Kant)** (rule-based decision-making strict)
  * **Deontology (Constant)** (rule-based decision-making flexible)
  * **Virtue ethics** (make the ai made choose from himself)

* **Integrate LLM-based decision-making** // TODO
  Use one or more Large Language Models as agents operating inside the simulation. These agents will receive partial observations of the environment and will be prompted to make decisions according to a specified ethical perspective.

* **Simulate and compare behaviors** // TODO
  Run multiple simulations across randomly generated scenarios to observe:

  * differences in chosen actions
  * differences in outcomes, such as harm distribution
  * consistency and variability of decisions
  * alignment between declared ethical principles and actual behavior

### Motivation

This project explores the intersection of **software engineering, artificial intelligence, and ethics**, focusing on how _abstract moral principles_ can be translated into _computational decision rules_ and tested in dynamic environments.

By combining a generated simulation environment with LLM-based agents, the project aims to investigate whether language models can consistently enact ethical principles in practice, rather than merely describe them in theory. The comparison between symbolic agents and LLM-based agents can help highlight the practical implications, strengths, and limitations of different approaches to ethical decision-making, especially in safety-critical domains such as autonomous systems.


# IDEAS

1. Define a random scenario that generate himself. He randomly generated number of entities. type of entities (something like a cicle where each time take a different entities). Location that should be in a range
of x,y such that they are always in one of the two street line. In addition there is a variable called
moved_probability that is setted to 0.1 at the beggining that can add a move that could be up,... (there is already this function). for an entities.

2. Set in the simulation automated possibility to activate random max_shift and set an interval of the possible value. Same for the other decision_distance,...

3. Unibo university in the background


SCENARIO:

1. One person cross the road not in the crossing line
2. Family person vs 4 child
3. A familiar and 20 child
4. A familiar and 1 child
5. 2 person in my line vs 1 person in the other