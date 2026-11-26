"""
Retrieval eval.
  python scripts\\eval_retrieval.py --set gold       # tuning set (already seen)
  python scripts\\eval_retrieval.py --set heldout    # honest set, do not tune on it
  add --no-rewrite to compare without the LLM rewrite
"""
import argparse
from rag_query import retrieve, DEFAULT_MODEL

GOLD = [
    {"q": "ghar khali karne ko bola, bina notice ke nahi nikal sakte", "act": "Landlords", "sections": {"21"}},
    {"q": "kiraya nahi diya to ghar se nikal sakta hai", "act": "Landlords", "sections": {"21"}},
    {"q": "security deposit kitna le sakte hain", "act": "Landlords", "sections": {"11"}},
    {"q": "landlord ne advance rent wapas nahi kiya", "act": "Landlords", "sections": {"24"}},
    {"q": "landlord ne bijli aur paani band kar diya", "act": "Landlords", "sections": {"20"}},
    {"q": "kiraya kitne saal baad badh sakta hai", "act": "Landlords", "sections": {"9"}},
    {"q": "rent ki receipt nahi di", "act": "Landlords", "sections": {"13"}},
    {"q": "landlord repair nahi karwa raha", "act": "Landlords", "sections": {"15"}},
    {"q": "tenant ghar chhodna chahta hai, kitne din pehle batana hoga", "act": "Landlords", "sections": {"29"}},
    {"q": "tenancy agreement registration kab karana hai", "act": "Landlords", "sections": {"4", "12"}},
    {"q": "landlord bina bataye ghar mein ghus gaya", "act": "Landlords", "sections": {"17"}},
    {"q": "consumer complaint kahan file karein", "act": "consumer", "sections": {"34", "35"}},
    {"q": "defective product ka refund kaise milega", "act": "consumer", "sections": {"39"}},
]

# Write these yourself, or keep this list in a separate file you do not edit while tuning.
HELDOUT = [
    {"q": "landlord ne 2 mahine ka kiraya nahi liya, kya ghar khali karwa sakta hai", "act": "Landlords", "sections": {"21"}},
    {"q": "ghar chhodne ke baad security deposit kitne din mein wapas milega", "act": "Landlords", "sections": {"11"}},
    {"q": "landlord rent lene se mana kare to kya karein", "act": "Landlords", "sections": {"14"}},
    {"q": "tenant ne bina permission ghar kisi aur ko de diya", "act": "Landlords", "sections": {"7"}},
    {"q": "rent agreement ki copy kitne din mein deni hoti hai", "act": "Landlords", "sections": {"12"}},
    {"q": "eviction order ke khilaf kitne din mein appeal karein", "act": "Landlords", "sections": {"30", "36"}},
]


def rank_of_hit(chunks, case):
    for rank, c in enumerate(chunks, 1):
        if case["act"] in c["source"] and c["section"] in case["sections"]:
            return rank, c["distance"]
    return None, None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", choices=["gold", "heldout"], default="gold")
    ap.add_argument("--k", type=int, default=5)
    ap.add_argument("--no-rewrite", action="store_true")
    ap.add_argument("--model", default=DEFAULT_MODEL)
    args = ap.parse_args()

    cases = GOLD if args.set == "gold" else HELDOUT
    use_rewrite = not args.no_rewrite
    mode = "NO REWRITE" if args.no_rewrite else "WITH REWRITE"
    print(f"=== set={args.set} | {mode} | k={args.k} | model={args.model} ===\n")

    hits, rr, hit_dists = 0, 0.0, []
    for case in cases:
        chunks, keywords = retrieve(case["q"],
                                    use_rewrite=use_rewrite, model=args.model)
        rank, _ = rank_of_hit(chunks, case)
        top = chunks[0]
        if rank:
            hits += 1
            rr += 1 / rank
            hit_dists.append(chunks[rank - 1]["distance"])
        status = "OK  " if rank else "MISS"
        print(f"{status} rank={rank}  top=s{top['section']}({top['distance']:.3f}) | {case['q']}")
        if use_rewrite:
            print(f"       keywords: {keywords or '(empty: rewrite failed)'}")

    n = len(cases)
    print(f"\nRecall@{args.k}: {hits}/{n} = {hits / n:.2f}    MRR: {rr / n:.2f}")
    if hit_dists:
        print(f"Distances of correct hits: min={min(hit_dists):.3f} max={max(hit_dists):.3f}")


if __name__ == "__main__":
    main()