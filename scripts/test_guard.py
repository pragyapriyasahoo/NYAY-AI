"""
Hallucination guard test.
Out-of-scope questions MUST return not_found. Any mode=llm there is a hallucination.

Usage (from project root):
    python scripts\\test_guard.py
"""
from rag_query import answer_query

OUT_OF_SCOPE = [
    "cricket world cup kisne jeeta",
    "bitcoin ka price aaj kya hai",
    "shadi ke liye kitne din ki chhutti milti hai",
    "ghar ka vastu kaise theek karein",
    "pizza kaise banate hain",
]

IN_SCOPE = [
    "ghar khali karne ko bola, bina notice ke nahi nikal sakte",
    "landlord ne bijli aur paani band kar diya",
    "security deposit kitna le sakte hain",
]


def run(label, queries, expect_found):
    print(f"\n===== {label} =====")
    bad = 0
    for q in queries:
        res = answer_query(q)
        mode = res["mode"]
        src = ""
        if res["chosen"]:
            c = res["chosen"]
            src = f"s{c['section']}" if c["section"] else c["source"][:20]
        s = res["chosen"]["rerank"] if res["chosen"] else float("nan")
        print(f"mode={mode:<11} score={s:6.2f} {src:<12} | {q}")
        if expect_found and mode == "not_found":
            bad += 1
        if not expect_found and mode == "llm":
            bad += 1
    print(f"Problems: {bad}/{len(queries)}")
    return bad


if __name__ == "__main__":
    h = run("OUT OF SCOPE (should be not_found)", OUT_OF_SCOPE, expect_found=False)
    run("IN SCOPE (should not be not_found)", IN_SCOPE, expect_found=True)
    print(f"\nHallucination cases (llm on out-of-scope): {h}")