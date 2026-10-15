"""Build the fine-tuning data for the GamePulse model (Azure OpenAI supervised fine-tuning, chat format with tools).

Two kinds of examples, both produced from the engine so that every number is true:
- commentator: the exact system + facts prompt the overlay narrator sends (`NarratorAgent.prompt`), answered with 1-2 sentences in
  English, French, Spanish or Arabic, for a casual fan or an analyst, using only numbers present in the facts;
- agents: a question, the tool call the agent should make, the real tool result, and an answer that quotes only that result.
Every example is checked with the same fact-checker as the app; failing examples are dropped.

    python tools/build_finetune_data.py      # writes data/finetune/train.jsonl and valid.jsonl
"""
from __future__ import annotations

import asyncio
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
OUT = ROOT / "data" / "finetune"

LANGS = ("en", "fr", "es", "ar")

# ------------------------------------------------------------------------------------------------ commentator answers
OUTCOME = {"en": {"saved": "saved", "blocked": "blocked", "off_target": "off target"},
           "fr": {"saved": "arrêtée", "blocked": "contrée", "off_target": "à côté"},
           "es": {"saved": "atajada", "blocked": "bloqueada", "off_target": "desviada"},
           "ar": {"saved": "تصدى لها الحارس", "blocked": "صُدّت", "off_target": "خارج المرمى"}}
CAUSE = {"en": {"its tactical change": "their tactical change", "the red card": "the red card"},
         "fr": {"its tactical change": "leur changement tactique", "the red card": "le carton rouge"},
         "es": {"its tactical change": "su cambio táctico", "the red card": "la tarjeta roja"},
         "ar": {"its tactical change": "التغيير التكتيكي", "the red card": "البطاقة الحمراء"}}
CTX = {"en": {"level": "levels the match", "ahead": "puts them ahead", "extend": "extends the lead", "back": "pulls one back"},
       "fr": {"level": "remet les deux équipes à égalité", "ahead": "les met devant", "extend": "creuse l'écart", "back": "relance le match"},
       "es": {"level": "iguala el partido", "ahead": "los pone por delante", "extend": "amplía la ventaja", "back": "recorta distancias"},
       "ar": {"level": "يعيد التعادل", "ahead": "يمنحهم التقدم", "extend": "يوسّع الفارق", "back": "يقلّص الفارق"}}

T = {  # kind -> lang -> mode -> templates
    "goal": {
        "en": {"casual": ["{player} scores for {team}! The goal {ctx}: {score}.", "Goal! {player} {ctx} for {team} - it's {score}."],
               "analyst": ["{player} finishes a {xg} xG chance and {ctx} for {team}: {score}.", "{team} score through {player} ({xg} xG); the goal {ctx}, {score}."]},
        "fr": {"casual": ["But de {player} pour {team} ! Ce but {ctx} : {score}.", "{player} fait trembler les filets et {ctx} pour {team}, {score}."],
               "analyst": ["{player} convertit une occasion à {xg} xG et {ctx} pour {team} : {score}.", "{team} marque par {player} ({xg} xG) ; ce but {ctx}, {score}."]},
        "es": {"casual": ["¡Gol de {player} para {team}! El tanto {ctx}: {score}.", "¡{player} marca y {ctx} para {team}! {score}."],
               "analyst": ["{player} transforma una ocasión de {xg} xG y {ctx} para {team}: {score}.", "{team} marca con {player} ({xg} xG); el gol {ctx}, {score}."]},
        "ar": {"casual": ["هدف! {player} يسجل لـ{team} والهدف {ctx}: {score}.", "{player} يهز الشباك لـ{team}، والهدف {ctx}: {score}."],
               "analyst": ["{player} يحول فرصة بقيمة {xg} xG إلى هدف لـ{team}، والهدف {ctx}: {score}.", "{team} يسجل عبر {player} ({xg} xG)، والهدف {ctx}: {score}."]},
    },
    "big_chance": {
        "en": {"casual": ["What a chance for {player}! It was {outcome}.", "{player} should have scored there - {outcome}."],
               "analyst": ["{player} had a {xg} xG chance and it was {outcome}.", "A {xg} xG opportunity for {player}, {outcome}: the kind usually converted more than 1 time in 4."]},
        "fr": {"casual": ["Quelle occasion pour {player} ! Elle est {outcome}.", "{player} aurait dû marquer, mais la frappe est {outcome}."],
               "analyst": ["{player} avait une occasion à {xg} xG, finalement {outcome}.", "Une occasion à {xg} xG pour {player}, {outcome} : ce genre de situation finit au fond plus d'1 fois sur 4."]},
        "es": {"casual": ["¡Qué ocasión para {player}! Fue {outcome}.", "{player} pudo marcar, pero el disparo fue {outcome}."],
               "analyst": ["{player} tuvo una ocasión de {xg} xG y fue {outcome}.", "Una oportunidad de {xg} xG para {player}, {outcome}: suele acabar en gol más de 1 vez de cada 4."]},
        "ar": {"casual": ["يا لها من فرصة لـ{player}! لكنها {outcome}.", "كان على {player} أن يسجل هنا، لكن التسديدة {outcome}."],
               "analyst": ["فرصة بقيمة {xg} xG لـ{player}، لكنها {outcome}.", "{player} أتيحت له فرصة بقيمة {xg} xG، {outcome}، ومثلها يُسجَّل عادة أكثر من مرة من كل 4."]},
    },
    "momentum_swing": {
        "en": {"casual": ["{team} have taken control of the game.", "The momentum is with {team} now."],
               "analyst": ["Momentum swung from {before} to {after}: {team} now dominate territory and pressure.", "{team} take over: the momentum index moved from {before} to {after} in a few minutes."]},
        "fr": {"casual": ["{team} a pris le contrôle du match.", "La dynamique est désormais du côté de {team}."],
               "analyst": ["La dynamique est passée de {before} à {after} : {team} domine le terrain et la pression.", "{team} prend le dessus : l'indice de dynamique est passé de {before} à {after} en quelques minutes."]},
        "es": {"casual": ["{team} se ha hecho con el control del partido.", "El impulso ahora es de {team}."],
               "analyst": ["El impulso pasó de {before} a {after}: {team} domina el terreno y la presión.", "{team} toma el mando: el índice de impulso pasó de {before} a {after} en pocos minutos."]},
        "ar": {"casual": ["{team} يسيطر الآن على المباراة.", "الزخم الآن لصالح {team}."],
               "analyst": ["تحول الزخم من {before} إلى {after}: {team} يسيطر على المساحات والضغط.", "{team} يفرض إيقاعه: مؤشر الزخم انتقل من {before} إلى {after} خلال دقائق."]},
    },
    "key_player": {
        "en": {"casual": ["{player} is everywhere: {team}'s game goes through him.", "Everything {team} do runs through {player} right now."],
               "analyst": ["{player} is involved in {share}% of {team}'s passing (a typical player: about {typical}%).", "{team} rely on {player}: {share}% of their passing goes through him, against about {typical}% for a typical player."]},
        "fr": {"casual": ["{player} est partout : tout le jeu de {team} passe par lui.", "En ce moment, tout ce que fait {team} passe par {player}."],
               "analyst": ["{player} participe à {share} % des passes de {team} (un joueur type : environ {typical} %).", "{team} dépend de {player} : {share} % de ses passes passent par lui, contre environ {typical} % pour un joueur type."]},
        "es": {"casual": ["{player} está en todas partes: el juego de {team} pasa por él.", "Todo lo que hace {team} pasa ahora por {player}."],
               "analyst": ["{player} participa en el {share}% de los pases de {team} (un jugador típico: alrededor del {typical}%).", "{team} depende de {player}: el {share}% de sus pases pasa por él, frente a un {typical}% de un jugador típico."]},
        "ar": {"casual": ["{player} في كل مكان: لعب {team} يمر عبره.", "كل ما يفعله {team} الآن يمر عبر {player}."],
               "analyst": ["{player} يشارك في {share}% من تمريرات {team} (اللاعب المعتاد: نحو {typical}%).", "{team} يعتمد على {player}: {share}% من تمريراته تمر عبره، مقابل نحو {typical}% للاعب المعتاد."]},
    },
    "unlucky": {
        "en": {"casual": ["{team} are playing better than the score says and could be rewarded soon.", "{team} deserve more than this score."],
               "analyst": ["{team} lead the expected goals {xgf} to {xga} but the score is {score}.", "On chances it's {xgf} to {xga} for {team}; the {score} scoreline flatters their opponents."]},
        "fr": {"casual": ["{team} joue mieux que ne le dit le score et pourrait vite être récompensé.", "{team} mérite mieux que ce score."],
               "analyst": ["{team} domine aux expected goals, {xgf} contre {xga}, mais le score est de {score}.", "Aux occasions, c'est {xgf} à {xga} pour {team} ; le {score} flatte l'adversaire."]},
        "es": {"casual": ["{team} juega mejor de lo que dice el marcador y podría tener premio pronto.", "{team} merece más que este resultado."],
               "analyst": ["{team} gana en goles esperados, {xgf} a {xga}, pero el marcador es {score}.", "En ocasiones va {xgf} a {xga} para {team}; el {score} favorece al rival."]},
        "ar": {"casual": ["{team} يلعب أفضل مما تقوله النتيجة وقد يُكافأ قريباً.", "{team} يستحق أكثر من هذه النتيجة."],
               "analyst": ["{team} يتفوق في الأهداف المتوقعة {xgf} مقابل {xga}، لكن النتيجة {score}.", "في الفرص الأفضلية لـ{team} بـ{xgf} مقابل {xga}، والنتيجة {score} تنصف المنافس."]},
    },
    "pressing_fade": {
        "en": {"casual": ["{team} are running out of steam: they press much less than earlier.", "The pressing of {team} is fading."],
               "analyst": ["{team}'s pressing dropped from {pb} to {pn} actions per 10 minutes; the opponent's pass accuracy moved from {ab}% to {an}%.", "Fewer presses from {team} ({pb} then {pn} per 10 minutes) and more time on the ball for the opponent ({ab}% to {an}% accuracy)."]},
        "fr": {"casual": ["{team} commence à fatiguer : son pressing a nettement baissé.", "Le pressing de {team} s'essouffle."],
               "analyst": ["Le pressing de {team} est passé de {pb} à {pn} actions par 10 minutes ; la précision adverse est passée de {ab} % à {an} %.", "Moins de pressing de {team} ({pb} puis {pn} par 10 minutes) et plus de temps pour l'adversaire ({ab} % à {an} % de passes réussies)."]},
        "es": {"casual": ["{team} se está quedando sin fuerzas: presiona mucho menos que antes.", "La presión de {team} se apaga."],
               "analyst": ["La presión de {team} bajó de {pb} a {pn} acciones cada 10 minutos; la precisión del rival pasó del {ab}% al {an}%.", "Menos presión de {team} ({pb} y luego {pn} cada 10 minutos) y más tiempo para el rival ({ab}% a {an}% de acierto)."]},
        "ar": {"casual": ["{team} بدأ يفقد طاقته: الضغط أقل بكثير من قبل.", "ضغط {team} يتراجع."],
               "analyst": ["ضغط {team} انخفض من {pb} إلى {pn} محاولة كل 10 دقائق، ودقة تمرير المنافس انتقلت من {ab}% إلى {an}%.", "ضغط أقل من {team} ({pb} ثم {pn} كل 10 دقائق) ووقت أكثر للمنافس (من {ab}% إلى {an}% دقة)."]},
    },
    "turning_point": {
        "en": {"casual": ["The match changed after {cause} at {at}': {team} {trend_en}.", "Since {cause} ({at}'), {team} {trend_en}."],
               "analyst": ["Since {cause} at {at}', {team}'s expected-goals balance moved from {before} to {after} per 10 minutes.", "Turning point at {at}': after {cause}, {team} went from {before} to {after} xG difference per 10 minutes."]},
        "fr": {"casual": ["Le match a basculé après {cause} à la {at}e minute : {team} {trend_fr}.", "Depuis {cause} ({at}e), {team} {trend_fr}."],
               "analyst": ["Depuis {cause} à la {at}e minute, la balance d'expected goals de {team} est passée de {before} à {after} par 10 minutes.", "Tournant à la {at}e : après {cause}, {team} est passé de {before} à {after} de différence d'xG par 10 minutes."]},
        "es": {"casual": ["El partido cambió tras {cause} en el minuto {at}: {team} {trend_es}.", "Desde {cause} (minuto {at}), {team} {trend_es}."],
               "analyst": ["Desde {cause} en el minuto {at}, el balance de goles esperados de {team} pasó de {before} a {after} cada 10 minutos.", "Punto de inflexión en el {at}: tras {cause}, {team} pasó de {before} a {after} de diferencia de xG cada 10 minutos."]},
        "ar": {"casual": ["تغيرت المباراة بعد {cause} في الدقيقة {at}: {team} {trend_ar}.", "منذ {cause} (الدقيقة {at})، {team} {trend_ar}."],
               "analyst": ["منذ {cause} في الدقيقة {at}، انتقل فارق الأهداف المتوقعة لـ{team} من {before} إلى {after} كل 10 دقائق.", "نقطة تحول في الدقيقة {at}: بعد {cause}، انتقل {team} من {before} إلى {after} في فارق xG كل 10 دقائق."]},
    },
    "red_card": {
        "en": {"casual": ["Red card for {player}! {team} are down to ten men.", "{player} is sent off - {team} will have to suffer."],
               "analyst": ["{player} sees red: {team} play with ten from minute {minute}, expect a deeper block.", "Down to ten at minute {minute} after {player}'s red card, {team} will have to defend deeper."]},
        "fr": {"casual": ["Carton rouge pour {player} ! {team} se retrouve à dix.", "{player} est expulsé, {team} va devoir souffrir."],
               "analyst": ["{player} est expulsé : {team} joue à dix dès la {minute}e minute, attendez-vous à un bloc plus bas.", "À dix dès la {minute}e après le rouge de {player}, {team} va devoir défendre plus bas."]},
        "es": {"casual": ["¡Tarjeta roja para {player}! {team} se queda con diez.", "{player} es expulsado y {team} tendrá que sufrir."],
               "analyst": ["{player} ve la roja: {team} juega con diez desde el minuto {minute}, espere un bloque más bajo.", "Con diez desde el minuto {minute} tras la roja a {player}, {team} tendrá que defender más atrás."]},
        "ar": {"casual": ["بطاقة حمراء لـ{player}! {team} يكمل بعشرة لاعبين.", "طرد {player} و{team} سيعاني."],
               "analyst": ["{player} يُطرد: {team} يلعب بعشرة منذ الدقيقة {minute}، توقعوا تكتلاً دفاعياً أعمق.", "بعشرة لاعبين منذ الدقيقة {minute} بعد طرد {player}، على {team} أن يدافع في مناطق أعمق."]},
    },
    "tactic_change": {
        "en": {"casual": ["{team} change their approach - watch the next minutes.", "Tactical switch for {team}."],
               "analyst": ["{team} change their approach at minute {minute}: shape, pressing and tempo will shift.", "Tactical change for {team} ({minute}'): expect a different shape and rhythm."]},
        "fr": {"casual": ["{team} change d'approche, à surveiller dans les prochaines minutes.", "Changement tactique pour {team}."],
               "analyst": ["{team} change d'approche à la {minute}e minute : organisation, pressing et rythme vont évoluer.", "Changement tactique de {team} ({minute}e) : attendez-vous à un autre bloc et un autre rythme."]},
        "es": {"casual": ["{team} cambia su planteamiento: atentos a los próximos minutos.", "Cambio táctico de {team}."],
               "analyst": ["{team} cambia su planteamiento en el minuto {minute}: dibujo, presión y ritmo van a cambiar.", "Cambio táctico de {team} (minuto {minute}): espere otro dibujo y otro ritmo."]},
        "ar": {"casual": ["{team} يغير أسلوبه، تابعوا الدقائق القادمة.", "تغيير تكتيكي لـ{team}."],
               "analyst": ["{team} يغير أسلوبه في الدقيقة {minute}: الشكل والضغط والإيقاع ستتغير.", "تغيير تكتيكي لـ{team} (الدقيقة {minute}): توقعوا شكلاً وإيقاعاً مختلفين."]},
    },
    "injury": {
        "en": {"casual": ["{player} is hurt - a blow for {team}.", "Worrying moment for {team}: {player} is injured."],
               "analyst": ["{player} is hurt at minute {minute}: expect gaps on that side for {team}.", "{team} lose {player}'s mobility ({minute}'), fewer high-intensity runs on that flank."]},
        "fr": {"casual": ["{player} est touché, un coup dur pour {team}.", "Moment inquiétant pour {team} : {player} est blessé."],
               "analyst": ["{player} est touché à la {minute}e minute : attendez-vous à des espaces de ce côté pour {team}.", "{team} perd la mobilité de {player} ({minute}e), moins de courses à haute intensité sur ce côté."]},
        "es": {"casual": ["{player} está lesionado, un golpe para {team}.", "Momento preocupante para {team}: {player} se ha lesionado."],
               "analyst": ["{player} se lesiona en el minuto {minute}: espere huecos en esa banda para {team}.", "{team} pierde la movilidad de {player} (minuto {minute}), menos carreras intensas por ese costado."]},
        "ar": {"casual": ["{player} مصاب، ضربة موجعة لـ{team}.", "لحظة مقلقة لـ{team}: {player} مصاب."],
               "analyst": ["{player} يتعرض لإصابة في الدقيقة {minute}: توقعوا مساحات في تلك الجهة لـ{team}.", "{team} يفقد حركية {player} (الدقيقة {minute})، وجري أقل بسرعة عالية في تلك الجهة."]},
    },
}
TREND = {"up": {"en": "are now creating more", "fr": "crée désormais davantage", "es": "genera ahora más", "ar": "يصنع الآن فرصاً أكثر"},
         "down": {"en": "have lost their edge", "fr": "a perdu son avantage", "es": "ha perdido su ventaja", "ar": "فقد أفضليته"}}


def _fmt(x) -> str:
    return f"{x:g}" if isinstance(x, (int, float)) else str(x)


def commentator_answer(m, names, teams, state, lang: str, mode: str, rng: random.Random) -> str | None:
    tmpl = T.get(m.kind, {}).get(lang, {}).get(mode)
    if not tmpl:
        return None
    f = m.facts
    team = teams[m.team]
    v = {"team": team, "player": names.get(m.player or "", team), "minute": m.minute}
    if m.kind == "goal":
        if f.get("own_goal"):
            return None
        sc = f["score"]
        a, b = list(sc)
        diff = sc[m.team] - sc[a if m.team == b else b]
        v["ctx"] = CTX[lang]["level" if diff == 0 else "ahead" if diff == 1 else "extend" if diff > 1 else "back"]
        v["score"] = f"{teams[a]} {sc[a]}-{sc[b]} {teams[b]}"
        v["xg"] = f"{(f.get('xg') or 0):.2f}"
    elif m.kind == "big_chance":
        if f["outcome"] not in OUTCOME[lang]:
            return None
        v["xg"], v["outcome"] = f"{f['xg']:.2f}", OUTCOME[lang][f["outcome"]]
    elif m.kind == "momentum_swing":
        v["before"], v["after"] = f"{f['before']:+.0f}", f"{f['after']:+.0f}"
    elif m.kind == "key_player":
        v["share"], v["typical"] = f["share"], f["typical"]
    elif m.kind == "unlucky":
        a, b = state.home, state.away
        v["xgf"], v["xga"] = f"{f['xg_for']:.1f}", f"{f['xg_against']:.1f}"
        v["score"] = f"{teams[a]} {state.score[a]}-{state.score[b]} {teams[b]}"
    elif m.kind == "pressing_fade":
        v.update(pb=f["before"], pn=f["now"], ab=f["opp_acc_before"], an=f["opp_acc_now"])
    elif m.kind == "turning_point":
        v.update(cause=CAUSE[lang][f["cause"]], at=f["at"], before=f"{f['before']:+.1f}", after=f"{f['after']:+.1f}")
        trend = "up" if f["after"] > f["before"] else "down"
        v.update({f"trend_{k}": t for k, t in TREND[trend].items()})
    return rng.choice(tmpl).format(**{k: _fmt(x) if not isinstance(x, str) else x for k, x in v.items()})


def commentator_examples(n_matches: int, rng: random.Random) -> list[dict]:
    from gamepulse.agents.pipeline import ExplainerAgent, NarratorAgent, Viewer
    from gamepulse.agents.team import fact_check
    from gamepulse.agents.llm import LLM
    from gamepulse.engine.state import MatchState
    from gamepulse.feed import SimulatorFeed
    from gamepulse.tactics import PRESETS

    presets = list(PRESETS)
    scenarios = [None, {"rules": [{"trigger": {"minute": 35}, "action": {"type": "red_card", "team": "away"}}]},
                 {"rules": [{"trigger": {"minute": 55}, "action": {"type": "tactic_change", "team": "home", "changes": {"pressing": 0.9, "line_height": 0.8}}}]},
                 {"rules": [{"trigger": {"minute": 40}, "action": {"type": "injury", "team": "home"}}]}]
    out, seen = [], {}
    offline = LLM()
    offline.endpoint = offline.key = None  # build prompts only, never call a model here
    for s in range(n_matches):
        feed = SimulatorFeed(seed=7000 + s, home_tactic=rng.choice(presets), away_tactic=rng.choice(presets), scenario=scenarios[s % len(scenarios)])
        home, away = feed.teams
        teams = {home.id: home.name, away.id: away.name}
        names = {p.id: p.name for t in feed.teams for p in t.players}
        state = MatchState(home.id, away.id)
        state.roster = {p.id: {"name": p.name, "line": p.position} for t in feed.teams for p in t.players}
        explainer = ExplainerAgent(offline, {home.id: home, away.id: away})
        narrator = NarratorAgent(offline, {home.id: home, away.id: away})
        for tk in feed.ticks():
            if tk.frame:
                state.observe_frame(tk.t, tk.frame["poss"])
            for ev in tk.events:
                for m in state.ingest(ev):
                    if seen.get(m.kind, 0) >= 14:  # keep the kinds balanced
                        continue
                    seen[m.kind] = seen.get(m.kind, 0) + 1
                    why = explainer.run(m, state)
                    for lang in rng.sample(LANGS, 2):
                        mode = rng.choice(("casual", "analyst"))
                        system, facts = narrator.prompt(m, why, Viewer(mode=mode, lang=lang), state)
                        ans = commentator_answer(m, names, teams, state, lang, mode, rng)
                        if ans and fact_check(ans, [("facts", facts)], "")["grounded"]:
                            out.append({"messages": [{"role": "system", "content": system}, {"role": "user", "content": facts},
                                                     {"role": "assistant", "content": ans}]})
    return out


# ------------------------------------------------------------------------------------------------ agent examples
ANALYST_Q = {"en": ["Who is on top?", "What's the score and who is creating more?", "What were the key moments so far?",
                    "Who has made the most passes?", "Who has the most shots?", "How is {player} playing?"],
             "fr": ["Qui domine le match ?", "Quel est le score et qui se crée le plus d'occasions ?", "Quels ont été les moments clés ?",
                    "Qui a fait le plus de passes ?", "Comment joue {player} ?"]}
COACH_Q = {"en": ["How does {mine} do against {opp}?", "How would {mine} cope with a {opp} of a title contender?",
                  "What if we get a red card at minute 30?", "How realistic is the simulator?"],
           "fr": ["Que donne {mine} contre {opp} ?", "Comment {mine} s'en sort face à un {opp} d'une équipe qui joue le titre ?",
                  "Et si on prend un carton rouge à la 30e minute ?", "À quel point le simulateur est-il réaliste ?"]}


def fr_answer(name: str, r) -> str:
    """French answers built from the tool result (same facts as the English writers)."""
    if name == "match_snapshot":
        (h, gh), (a, ga) = list(r["score"].items())
        p, sh, xg = list(r["possession_pct"].values()), list(r["shots"].values()), list(r["expected_goals"].values())
        lead = h if xg[0] >= xg[1] else a
        return (f"Après {r['minute']} minutes, c'est {h} {gh}-{ga} {a}. Possession {p[0]} % contre {p[1]} %, tirs {sh[0]} contre {sh[1]}, "
                f"expected goals {xg[0]} contre {xg[1]} : {lead} se crée les meilleures occasions.")
    if name == "key_moments":
        if not r:
            return "Aucun moment clé détecté pour l'instant."
        kinds = {"goal": "but", "big_chance": "grosse occasion", "momentum_swing": "changement de dynamique", "key_player": "joueur clé",
                 "unlucky": "domination non récompensée", "pressing_fade": "pressing en baisse", "turning_point": "tournant",
                 "red_card": "carton rouge", "tactic_change": "changement tactique", "injury": "blessure"}
        return " ".join(f"{m['minute']}e : {kinds.get(m['kind'], m['kind'])} ({m.get('player') or m['team']})." for m in r[-3:])
    if name == "top_players":
        stat = [k for k in r[0] if k not in ("player", "team")][0]
        label = {"passes": "de passes", "shots": "de tirs", "xg": "d'expected goals", "goals": "de buts"}[stat]
        return "Le plus " + label + " : " + ", ".join(f"{x['player']} ({x['team']}) {_fmt(x[stat])}" for x in r) + "."
    if name == "player_report":
        st = r["stats"]
        bits = [f"{_fmt(st[k])} {w}" for k, w in (("passes", "passes"), ("shots", "tirs"), ("goals", "buts")) if st.get(k)]
        if st.get("passes"):
            bits.append(f"{_fmt(st['pass_acc'])} % de passes réussies")
        return f"{r['player']} ({r['team']}) : " + (", ".join(bits) if bits else "peu impliqué pour l'instant") + "."
    if name == "test_tactic":
        m = sorted(r["matchups"], key=lambda x: x["ppg"])[0]
        return (f"Sur {r['matches_per_opponent']} matchs simulés, {r['tactic']} prend {_fmt(r['points_per_game'])} points par match. "
                f"Contre {m['opponent']} : {m['win']} % de victoires, {m['draw']} % de nuls, xG {_fmt(m['xgf'])} pour et {_fmt(m['xga'])} contre, "
                f"{_fmt(m['possession'])} % de possession.")
    if name == "what_if":
        verdict = {"helps": "aide", "hurts": "pénalise", "makes little difference": "change peu de choses"}[r["verdict"]]
        return (f"Sur les mêmes {r['matches']} matchs simulés contre {r['opponent']}, {r['tactic']} passe de {_fmt(r['points_per_game_before'])} "
                f"à {_fmt(r['points_per_game_after'])} points par match (victoires {r['win_pct_before']} % puis {r['win_pct_after']} %) : "
                f"le changement {verdict}.")
    if name == "realism":
        return (f"Le simulateur respecte {r['match_totals_within_tolerance']} totaux de match et {r['pitch_checks_within_tolerance']} contrôles "
                f"de position sur le terrain ; les joueurs sont placés à {_fmt(r['placement_error_m'])} m près en moyenne.")
    return ""


async def agent_examples(rng: random.Random) -> list[dict]:
    from gamepulse.agents import team as TM
    from gamepulse.agents.pipeline import Orchestrator, Viewer
    from gamepulse.agents.tools import MatchContext, make_lab_tools, make_match_tools
    from gamepulse.feed import SimulatorFeed
    from gamepulse.tactics import PRESETS

    out = []
    presets = list(PRESETS)
    for s in range(10):  # live-match questions at different minutes of different matches
        feed = SimulatorFeed(seed=8000 + s, home_tactic=rng.choice(presets), away_tactic=rng.choice(presets))
        orch = Orchestrator(*feed.teams)
        stop = rng.choice((25, 50, 70, 88)) * 60
        for tk in feed.ticks():
            orch.process_tick(tk, Viewer())
            if tk.t > stop:
                break
        ctx = MatchContext(orch.state, *feed.teams)
        tools = make_match_tools(ctx)
        for lang in ("en", "fr"):
            q = rng.choice(ANALYST_Q[lang]).format(player=rng.choice(list(ctx.names.values())))
            out.append(await _agent_example(TM, "analyst", TM.analyst_planner(ctx), tools, q, lang))
    lab_tools = make_lab_tools()
    for s in range(8):
        mine, opp = rng.sample(presets, 2)
        for lang in ("en", "fr"):
            q = rng.choice(COACH_Q[lang]).format(mine=mine, opp=opp)
            out.append(await _agent_example(TM, "coach", TM.coach_planner({"tactic": mine}), lab_tools, q, lang, mine))
    return [e for e in out if e]


async def _agent_example(TM, kind, planner, tools, question, lang, tactic=None):
    by_name = {t.name: t for t in tools}
    plan = planner(question if lang == "en" else _en_hint(question), list(by_name))
    if not plan:
        return None
    calls, results = [], []
    for i, (name, args) in enumerate(plan):
        res = by_name[name].func(**args)
        calls.append({"id": f"call_{i + 1}", "type": "function", "function": {"name": name, "arguments": json.dumps(args)}})
        results.append((name, res))
    if lang == "en":
        answer = (TM.analyst_writer if kind == "analyst" else TM.coach_writer)(question, results)
    else:
        answer = " ".join(fr_answer(n, r) for n, r in results)
    if not answer or not TM.fact_check(answer, results, question)["grounded"]:
        return None
    system = (TM.ANALYST_INSTRUCTIONS if kind == "analyst" else TM.COACH_INSTRUCTIONS
              + (f" The coach's current tactic is {tactic}." if tactic else "")) + f" Answer in {TM.LANG_NAMES[lang]}."
    msgs = [{"role": "system", "content": system}, {"role": "user", "content": question},
            {"role": "assistant", "content": None, "tool_calls": calls}]
    for c, (_, r) in zip(calls, results):
        msgs.append({"role": "tool", "tool_call_id": c["id"], "content": json.dumps(r, ensure_ascii=False, default=str)})
    msgs.append({"role": "assistant", "content": answer})
    return {"messages": msgs, "tools": [t.to_json_schema_spec() for t in tools]}


def _en_hint(q: str) -> str:
    """The offline planner reads English keywords: map the French questions to the same intent."""
    ql = q.lower()
    for fr, en in (("domine", "on top"), ("score", "score"), ("moments clés", "key moments"), ("plus de passes", "most passes"),
                   ("comment joue", "how is"), ("carton rouge", "red card at minute 30"), ("réaliste", "realistic"),
                   ("que donne", "how does"), ("s'en sort", "how does"), ("titre", "title")):
        if fr in ql:
            q = q + " " + en
    return q


def main() -> None:
    rng = random.Random(7)
    com = commentator_examples(60, rng)
    ag = asyncio.run(agent_examples(rng))
    data = com + ag
    rng.shuffle(data)
    n_valid = max(10, len(data) // 10)
    OUT.mkdir(parents=True, exist_ok=True)
    for name, rows in (("valid.jsonl", data[:n_valid]), ("train.jsonl", data[n_valid:])):
        (OUT / name).write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
    chars = sum(len(json.dumps(r, ensure_ascii=False)) for r in data)
    kinds = {}
    for r in com:
        k = r["messages"][1]["content"].split(" at minute")[0]
        kinds[k] = kinds.get(k, 0) + 1
    print(f"{len(com)} commentator + {len(ag)} agent examples -> {OUT} (train {len(data) - n_valid}, valid {n_valid}); "
          f"about {chars // 4:,} tokens; commentator kinds {kinds}")


if __name__ == "__main__":
    main()
