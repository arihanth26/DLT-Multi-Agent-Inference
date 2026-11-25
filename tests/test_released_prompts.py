"""GSM8K prompts must match Du et al.'s released gen_gsm.py (commit 9846749) character for character.

The two reference strings below are built exactly as gen_gsm.py builds them.
Run with python -m pytest tests/test_released_prompts.py.
"""

from pilot.debate import round1_prompt, round2_released


def released_round1(question):
    return """Can you solve the following math problem? {} Explain your reasoning. Your final answer should be a single numerical number, in the form \\boxed{{answer}}, at the end of your response. """.format(question)


def released_round2(others, question):
    prefix_string = "These are the solutions to the problem from other agents: "
    for agent_response in others:
        prefix_string = prefix_string + "\n\n One agent solution: ```{}```".format(agent_response)
    return prefix_string + """\n\n Using the solutions from other agents as additional information, can you provide your answer to the math problem? \n The original math problem is {}. Your final answer should be a single numerical number, in the form \\boxed{{answer}}, at the end of your response.""".format(question)


def test_gsm8k_prompts_match_released_code():
    q = "Janet has 3 apples and buys 2 more. How many apples does she have?"
    assert round1_prompt("gsm8k", {"question": q}) == released_round1(q)
    others = ["I think 5. \\boxed{5}", "3 + 2 = 5, so \\boxed{5}"]
    assert round2_released("gsm8k", others, q) == released_round2(others, q)
