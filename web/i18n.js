/* GamePulse interface translations (English source -> French, Spanish, Arabic).
   Every visible text node and placeholder is translated by exact match, or by pattern when it contains numbers ({0}, {1}...).
   New nodes are translated as they appear, so the dynamic panels follow the selected language too. */
const I18N = {
  // header, tabs
  "Live match": ["Match en direct", "Partido en directo", "مباراة مباشرة"],
  "Tactics": ["Tactiques", "Tácticas", "الخطط"],
  "Tactic Lab": ["Labo tactique", "Laboratorio táctico", "مختبر الخطط"],
  "Realism": ["Réalisme", "Realismo", "الواقعية"],
  "Language": ["Langue", "Idioma", "اللغة"],
  // live bar
  "Data source": ["Source des données", "Fuente de datos", "مصدر البيانات"],
  "Simulated match": ["Match simulé", "Partido simulado", "مباراة محاكاة"],
  "Real match with tracking (Bundesliga)": ["Vrai match avec tracking (Bundesliga)", "Partido real con tracking (Bundesliga)", "مباراة حقيقية مع تتبع اللاعبين (البوندسليغا)"],
  "Real match: Spain": ["Vrai match : Espagne", "Partido real: España", "مباراة حقيقية: إسبانيا"],
  "Real match: Italy": ["Vrai match : Italie", "Partido real: Italia", "مباراة حقيقية: إيطاليا"],
  "Real match: France": ["Vrai match : France", "Partido real: Francia", "مباراة حقيقية: فرنسا"],
  "Real match: Germany": ["Vrai match : Allemagne", "Partido real: Alemania", "مباراة حقيقية: ألمانيا"],
  "Real match: England": ["Vrai match : Angleterre", "Partido real: Inglaterra", "مباراة حقيقية: إنجلترا"],
  "Home tactic": ["Tactique domicile", "Táctica local", "خطة صاحب الأرض"],
  "Home level": ["Niveau domicile", "Nivel local", "مستوى صاحب الأرض"],
  "Away tactic": ["Tactique extérieur", "Táctica visitante", "خطة الضيف"],
  "Away level": ["Niveau extérieur", "Nivel visitante", "مستوى الضيف"],
  "View": ["Vue", "Vista", "العرض"],
  "Casual fan": ["Fan", "Aficionado", "مشجع"],
  "Analyst": ["Analyste", "Analista", "محلل"],
  "Scenario": ["Scénario", "Escenario", "السيناريو"],
  "Speed (live)": ["Vitesse (direct)", "Velocidad (directo)", "السرعة (مباشر)"],
  "Seed": ["Graine", "Semilla", "البذرة"],
  "Match #": ["Match n°", "Partido n.º", "المباراة رقم"],
  "Kick off": ["Coup d'envoi", "Saque inicial", "انطلاق"],
  "Pause": ["Pause", "Pausa", "إيقاف مؤقت"],
  "Resume": ["Reprendre", "Reanudar", "استئناف"],
  "Stop": ["Arrêter", "Parar", "إيقاف"],
  "Describe your own scenario (AI)": ["Décris ton propre scénario (IA)", "Describe tu propio escenario (IA)", "صف السيناريو الخاص بك (ذكاء اصطناعي)"],
  "Interpret": ["Interpréter", "Interpretar", "تفسير"],
  "e.g. red card for my centre-back at 30', then the opponent scores at 40'": ["ex. carton rouge pour mon défenseur central à la 30e, puis l'adversaire marque à la 40e", "p. ej. roja para mi central en el 30 y luego el rival marca en el 40", "مثال: بطاقة حمراء لقلب دفاعي في الدقيقة 30 ثم يسجل المنافس في الدقيقة 40"],
  "Custom (described below)": ["Personnalisé (décrit ci-dessous)", "Personalizado (descrito abajo)", "مخصص (موصوف أدناه)"],
  "Interpreting…": ["Interprétation…", "Interpretando…", "جارٍ التفسير…"],
  "No running match.": ["Aucun match en cours.", "No hay ningún partido en curso.", "لا توجد مباراة جارية."],
  "No event found in this sentence. Try: 'red card for the opponent at 55', 'we go 0-2 down'.": ["Aucun événement trouvé dans cette phrase. Essaie : « carton rouge pour l'adversaire à la 55e », « on est mené 0-2 ».", "No se ha encontrado ningún evento. Prueba: «roja para el rival en el 55», «perdemos 0-2».", "لم يُعثر على حدث في هذه الجملة. جرّب: «بطاقة حمراء للمنافس في الدقيقة 55»، «نتأخر 0-2»."],
  "or describe what he does…": ["ou décris ce qu'il fait…", "o describe lo que hace…", "أو صِف ما يفعله…"],
  "Why it matters:": ["Pourquoi c'est important :", "Por qué importa:", "لماذا يهم:"],
  "now": ["maintenant", "ahora", "الآن"],
  "No scenario (open match)": ["Aucun scénario (match ouvert)", "Sin escenario (partido abierto)", "بدون سيناريو (مباراة مفتوحة)"],
  "✎ My own scenario (described above)": ["✎ Mon propre scénario (décrit ci-dessus)", "✎ Mi propio escenario (descrito arriba)", "✎ السيناريو الخاص بي (الموصوف أعلاه)"],
  // pitch, coaching
  "Home": ["Domicile", "Local", "صاحب الأرض"],
  "Away": ["Extérieur", "Visitante", "الضيف"],
  "○ pressure zone around the ball carrier · hover a player for details": ["○ zone de pression autour du porteur · survole un joueur pour les détails", "○ zona de presión alrededor del portador · pasa sobre un jugador para ver detalles", "○ منطقة الضغط حول حامل الكرة · مرّر المؤشر على لاعب للتفاصيل"],
  "Live coaching": ["Coaching en direct", "Dirección en directo", "التدريب المباشر"],
  "change anything while the match runs": ["change tout pendant le match", "cambia lo que quieras durante el partido", "غيّر أي شيء أثناء المباراة"],
  "Team": ["Équipe", "Equipo", "الفريق"],
  "Formation": ["Système", "Sistema", "الخطة"],
  "Switch to tactic": ["Passer à la tactique", "Cambiar a la táctica", "التبديل إلى خطة"],
  "Switch": ["Changer", "Cambiar", "تبديل"],
  "Inject": ["Injecter", "Inyectar", "تطبيق"],
  "Tell the AI what happens now: 'red card for the opponent', 'we go all out attack'…": ["Dis à l'IA ce qui se passe maintenant : « carton rouge pour l'adversaire », « on attaque à fond »…", "Dile a la IA qué pasa ahora: «roja para el rival», «vamos todos al ataque»…", "أخبر الذكاء الاصطناعي بما يحدث الآن: «بطاقة حمراء للمنافس»، «هجوم شامل»…"],
  "Live coaching and scenarios only apply to simulated matches.": ["Le coaching en direct et les scénarios ne s'appliquent qu'aux matchs simulés.", "La dirección en directo y los escenarios solo se aplican a partidos simulados.", "التدريب المباشر والسيناريوهات تنطبق على المباريات المحاكاة فقط."],
  "I couldn't find an event in this sentence.": ["Je n'ai trouvé aucun événement dans cette phrase.", "No he encontrado ningún evento en esta frase.", "لم أجد أي حدث في هذه الجملة."],
  "Line height": ["Hauteur du bloc", "Altura de la línea", "ارتفاع الخط"], "Pressing": ["Pressing", "Presión", "الضغط"],
  "Width": ["Largeur", "Amplitud", "العرض"], "Tempo": ["Tempo", "Ritmo", "الإيقاع"], "Directness": ["Jeu direct", "Juego directo", "اللعب المباشر"],
  "deep ↔ high": ["bas ↔ haut", "baja ↔ alta", "منخفض ↔ مرتفع"], "passive ↔ intense": ["passif ↔ intense", "pasiva ↔ intensa", "سلبي ↔ مكثف"],
  "narrow ↔ wide": ["étroit ↔ large", "estrecho ↔ amplio", "ضيق ↔ واسع"], "slow ↔ fast": ["lent ↔ rapide", "lento ↔ rápido", "بطيء ↔ سريع"],
  "short ↔ direct": ["court ↔ direct", "corto ↔ directo", "قصير ↔ مباشر"],
  // insights, charts, stats
  "Live insights": ["Analyses en direct", "Análisis en directo", "تحليلات مباشرة"],
  "Why it matters: {0}": ["Pourquoi c'est important : {0}", "Por qué importa: {0}", "لماذا يهم: {0}"],
  "Possession": ["Possession", "Posesión", "الاستحواذ"],
  "Expected goals (cumulative)": ["Expected goals (cumulés)", "Goles esperados (acumulados)", "الأهداف المتوقعة (تراكمي)"],
  "Pressing actions / 5 min": ["Actions de pressing / 5 min", "Acciones de presión / 5 min", "محاولات الضغط / 5 دقائق"],
  "Momentum": ["Dynamique", "Impulso", "الزخم"],
  "Match stats": ["Statistiques du match", "Estadísticas del partido", "إحصاءات المباراة"],
  "Shots": ["Tirs", "Tiros", "التسديدات"], "On target": ["Cadrés", "A puerta", "على المرمى"], "Pass accuracy %": ["Passes réussies %", "Precisión de pase %", "دقة التمرير %"],
  "Tackles won": ["Tacles gagnés", "Entradas ganadas", "الافتكاكات الناجحة"], "Pressures": ["Pressions", "Presiones", "الضغطات"], "Fouls": ["Fautes", "Faltas", "الأخطاء"],
  // ask boxes
  "Ask the match analyst": ["Demande à l'analyste du match", "Pregunta al analista del partido", "اسأل محلل المباراة"],
  "Ask the tactics coach": ["Demande au coach tactique", "Pregunta al entrenador táctico", "اسأل المدرب التكتيكي"],
  "AI agents · tools · fact-checked": ["agents IA · outils · faits vérifiés", "agentes IA · herramientas · datos verificados", "وكلاء ذكاء اصطناعي · أدوات · حقائق موثّقة"],
  "AI agents · simulations · fact-checked": ["agents IA · simulations · faits vérifiés", "agentes IA · simulaciones · datos verificados", "وكلاء ذكاء اصطناعي · محاكاة · حقائق موثّقة"],
  "Ask": ["Demander", "Preguntar", "اسأل"],
  "Who is on top? What were the key moments? How is Okoye playing?": ["Qui domine ? Quels sont les moments clés ? Comment joue Okoye ?", "¿Quién domina? ¿Cuáles fueron los momentos clave? ¿Cómo juega Okoye?", "من المسيطر؟ ما أبرز اللحظات؟ كيف يلعب أوكويه؟"],
  "How does my tactic do against a Low block 5-3-2 of a title team? What if we get a red card at 30?": ["Que donne ma tactique contre un bloc bas 5-3-2 d'une équipe qui joue le titre ? Et si on prend un rouge à la 30e ?", "¿Cómo rinde mi táctica contra un bloque bajo 5-3-2 de un aspirante al título? ¿Y si nos expulsan en el 30?", "كيف تؤدي خطتي أمام تكتل 5-3-2 لفريق منافس على اللقب؟ وماذا لو تلقينا بطاقة حمراء في الدقيقة 30؟"],
  "Thinking: routing the question, calling the tools…": ["Réflexion : choix de l'agent, appel des outils…", "Pensando: eligiendo el agente, llamando a las herramientas…", "جارٍ التفكير: اختيار الوكيل واستدعاء الأدوات…"],
  "every number traced to a tool result": ["chaque chiffre vient d'un résultat d'outil", "cada cifra procede de una herramienta", "كل رقم مصدره نتيجة أداة"],
  "unverified numbers: {0}": ["chiffres non vérifiés : {0}", "cifras no verificadas: {0}", "أرقام غير موثّقة: {0}"],
  "model: {0}": ["modèle : {0}", "modelo: {0}", "النموذج: {0}"],
  "match analyst": ["analyste du match", "analista del partido", "محلل المباراة"],
  "tactics coach": ["coach tactique", "entrenador táctico", "المدرب التكتيكي"],
  "no tool": ["aucun outil", "ninguna herramienta", "بدون أداة"],
  "understood by the Azure AI model": ["compris par le modèle d'IA Azure", "entendido por el modelo de IA de Azure", "فهمه نموذج الذكاء الاصطناعي من Azure"],
  "keywords only (AI model offline)": ["mots-clés uniquement (modèle d'IA hors ligne)", "solo palabras clave (modelo de IA sin conexión)", "كلمات مفتاحية فقط (النموذج غير متصل)"],
  // tactics editor
  "Start from": ["Partir de", "Partir de", "ابدأ من"], "Name": ["Nom", "Nombre", "الاسم"], "or any shape": ["ou n'importe quel système", "o cualquier sistema", "أو أي خطة"],
  "Use": ["Utiliser", "Usar", "استخدام"], "Player roles": ["Rôles des joueurs", "Roles de los jugadores", "أدوار اللاعبين"],
  "Pick a preset role, or": ["Choisis un rôle prédéfini, ou", "Elige un rol predefinido, o", "اختر دوراً جاهزاً، أو"],
  "describe in your own words": ["décris avec tes propres mots", "descríbelo con tus palabras", "صِف بكلماتك"],
  "what the player should do and let the AI translate it (e.g. “stay wide, beat his man, cross early, don't track back”).": ["ce que le joueur doit faire et laisse l'IA le traduire (ex. « reste large, élimine son vis-à-vis, centre tôt, ne redescend pas »).", "lo que debe hacer el jugador y deja que la IA lo traduzca (p. ej. «abierto, encarar, centrar pronto, no bajar»).", "ما يجب أن يفعله اللاعب ودع الذكاء الاصطناعي يترجمه (مثال: «ابقَ على الطرف، راوغ، أرسل العرضيات مبكراً، لا ترجع للدفاع»)."],
  "Team instructions": ["Consignes d'équipe", "Instrucciones del equipo", "تعليمات الفريق"],
  "Save tactic": ["Enregistrer la tactique", "Guardar táctica", "حفظ الخطة"], "Delete": ["Supprimer", "Eliminar", "حذف"],
  "Export JSON": ["Exporter en JSON", "Exportar JSON", "تصدير JSON"], "Import JSON": ["Importer un JSON", "Importar JSON", "استيراد JSON"],
  "Saved tactics live in your browser and appear in the Live match and Tactic Lab selectors.": ["Les tactiques enregistrées restent dans ton navigateur et apparaissent dans le match en direct et le labo.", "Las tácticas guardadas se quedan en tu navegador y aparecen en el partido en directo y el laboratorio.", "تُحفظ الخطط في متصفحك وتظهر في المباراة المباشرة والمختبر."],
  "Shape preview": ["Aperçu du bloc", "Vista previa del dibujo", "معاينة الشكل"],
  "Positions shown when your team has the ball, with the current line height and width.": ["Positions quand ton équipe a le ballon, avec la hauteur et la largeur actuelles.", "Posiciones con balón, con la altura y amplitud actuales.", "المواقع عند امتلاك فريقك للكرة، مع الارتفاع والعرض الحاليين."],
  "AI": ["IA", "IA", "ذكاء اصطناعي"],
  "Describe what this player should do…": ["Décris ce que ce joueur doit faire…", "Describe lo que debe hacer este jugador…", "صف ما يجب أن يفعله هذا اللاعب…"],
  // lab
  "Your tactic": ["Ta tactique", "Tu táctica", "خطتك"], "Your level": ["Ton niveau", "Tu nivel", "مستواك"],
  "Opponents' level": ["Niveau des adversaires", "Nivel de los rivales", "مستوى المنافسين"], "Opponents": ["Adversaires", "Rivales", "المنافسون"], "all": ["tous", "todos", "الكل"],
  "Scenario to test": ["Scénario à tester", "Escenario a probar", "سيناريو للاختبار"],
  "or describe it: 'we go 0-2 down, then press high from 60'": ["ou décris-le : « on est mené 0-2, puis on presse haut dès la 60e »", "o descríbelo: «perdemos 0-2 y presionamos arriba desde el 60»", "أو صِفه: «نتأخر 0-2 ثم نضغط عالياً من الدقيقة 60»"],
  "Compare with / without (what-if)": ["Comparer avec / sans (et si…)", "Comparar con / sin (¿y si…?)", "قارن مع / بدون (ماذا لو)"],
  "Matches per opponent": ["Matchs par adversaire", "Partidos por rival", "مباريات لكل منافس"],
  "Run simulations": ["Lancer les simulations", "Lanzar simulaciones", "تشغيل المحاكاة"], "Simulating…": ["Simulation…", "Simulando…", "جارٍ المحاكاة…"],
  "Simulating {0} matches…": ["Simulation de {0} matchs…", "Simulando {0} partidos…", "جارٍ محاكاة {0} مباراة…"],
  "Each opponent is played n times (half at home, half away) with different seeds.": ["Chaque adversaire est affronté n fois (moitié à domicile, moitié à l'extérieur) avec des tirages différents.", "Cada rival se juega n veces (mitad en casa, mitad fuera) con semillas distintas.", "تُلعب كل مواجهة n مرات (نصفها على الأرض ونصفها خارجها) ببذور مختلفة."],
  "Pick your tactic, choose the opponents it must survive, and run the Lab. You get win/draw/loss rates per opponent, the expected goals balance and a plain-language diagnosis of what breaks.": ["Choisis ta tactique et les adversaires qu'elle doit affronter, puis lance le labo. Tu obtiens les taux de victoire, nul et défaite par adversaire, le bilan d'expected goals et un diagnostic clair de ce qui casse.", "Elige tu táctica y los rivales a los que debe resistir, y lanza el laboratorio. Obtienes victorias, empates y derrotas por rival, el balance de goles esperados y un diagnóstico claro de lo que falla.", "اختر خطتك والمنافسين الذين يجب أن تصمد أمامهم ثم شغّل المختبر. ستحصل على نسب الفوز والتعادل والخسارة لكل منافس، وميزان الأهداف المتوقعة، وتشخيص واضح لنقاط الضعف."],
  "Solid": ["Solide", "Sólida", "متينة"], "Fragile in places": ["Fragile par endroits", "Frágil en algunos aspectos", "هشة في بعض الجوانب"], "Doesn't hold up": ["Ne tient pas", "No se sostiene", "لا تصمد"],
  "{0} points per game over {1} matches.": ["{0} points par match sur {1} matchs.", "{0} puntos por partido en {1} partidos.", "{0} نقطة في المباراة على مدى {1} مباراة."],
  "Best vs": ["Meilleur contre", "Mejor contra", "الأفضل أمام"], "· worst vs": ["· pire contre", "· peor contra", "· الأسوأ أمام"],
  "Opponent": ["Adversaire", "Rival", "المنافس"], "W / D / L": ["V / N / D", "G / E / P", "ف / ت / خ"], "Pts/g": ["Pts/m", "Pts/p", "نقاط/م"],
  "Goals": ["Buts", "Goles", "الأهداف"], "Poss.": ["Poss.", "Pos.", "استحواذ"], "Robustness": ["Robustesse", "Solidez", "الصلابة"],
  "Diagnosis": ["Diagnostic", "Diagnóstico", "التشخيص"], "Matchups": ["Confrontations", "Enfrentamientos", "المواجهات"],
  "Pts/g before → after": ["Pts/m avant → après", "Pts/p antes → después", "النقاط قبل → بعد"], "Goal diff": ["Diff. de buts", "Dif. de goles", "فارق الأهداف"],
  "xG diff": ["Diff. d'xG", "Dif. de xG", "فارق xG"], "Win %": ["Victoires %", "Victorias %", "الفوز %"], "Loss %": ["Défaites %", "Derrotas %", "الخسارة %"],
  "What was simulated": ["Ce qui a été simulé", "Qué se simuló", "ما تمت محاكاته"],
  "This scenario helps": ["Ce scénario aide", "Este escenario ayuda", "هذا السيناريو يساعد"], "This scenario hurts": ["Ce scénario pénalise", "Este escenario perjudica", "هذا السيناريو يضر"],
  "This scenario makes little difference": ["Ce scénario change peu de choses", "Este escenario apenas cambia nada", "هذا السيناريو لا يغيّر كثيراً"],
  "Same seeds with and without it: the matches are identical until the first scripted action, so every difference after that comes from it.": ["Mêmes tirages avec et sans : les matchs sont identiques jusqu'à la première action scriptée, donc chaque différence ensuite vient d'elle.", "Mismas semillas con y sin él: los partidos son idénticos hasta la primera acción programada, así que toda diferencia posterior viene de ella.", "البذور نفسها مع السيناريو وبدونه: المباريات متطابقة حتى أول حدث مبرمج، لذا كل فرق بعده سببه هذا الحدث."],
  // levels
  "Title contender (1st-2nd)": ["Candidat au titre (1er-2e)", "Aspirante al título (1.º-2.º)", "منافس على اللقب (1-2)"],
  "European places (3rd-5th)": ["Places européennes (3e-5e)", "Puestos europeos (3.º-5.º)", "المراكز الأوروبية (3-5)"],
  "Upper half (6th-8th)": ["Première moitié (6e-8e)", "Mitad alta (6.º-8.º)", "النصف العلوي (6-8)"],
  "Mid-table (9th-12th)": ["Milieu de tableau (9e-12e)", "Mitad de la tabla (9.º-12.º)", "وسط الترتيب (9-12)"],
  "Lower half (13th-16th)": ["Seconde moitié (13e-16e)", "Mitad baja (13.º-16.º)", "النصف السفلي (13-16)"],
  "Relegation battle (17th-20th)": ["Lutte pour le maintien (17e-20e)", "Lucha por la permanencia (17.º-20.º)", "صراع الهبوط (17-20)"],
  // roles
  "Goalkeeper": ["Gardien", "Portero", "حارس مرمى"], "Sweeper keeper": ["Gardien libéro", "Portero líbero", "حارس متقدم"], "Stopper CB": ["Défenseur stoppeur", "Central marcador", "قلب دفاع ضاغط"],
  "Covering CB": ["Défenseur de couverture", "Central de cobertura", "قلب دفاع مغطٍّ"], "Ball-playing CB": ["Défenseur relanceur", "Central con salida", "قلب دفاع صانع"],
  "Full-back": ["Latéral", "Lateral", "ظهير"], "Attacking wing-back": ["Piston offensif", "Carrilero ofensivo", "ظهير جناح هجومي"], "Defensive full-back": ["Latéral défensif", "Lateral defensivo", "ظهير دفاعي"],
  "Anchor man": ["Sentinelle", "Ancla", "لاعب ارتكاز"], "Deep playmaker": ["Meneur reculé", "Organizador retrasado", "صانع لعب متأخر"], "Box-to-box": ["Box-to-box", "Box-to-box", "لاعب وسط شامل"],
  "Advanced playmaker": ["Meneur avancé", "Mediapunta organizador", "صانع لعب متقدم"], "Wide midfielder": ["Milieu excentré", "Interior abierto", "لاعب وسط طرفي"],
  "Shadow striker": ["Attaquant de soutien", "Segundo delantero", "مهاجم ظل"], "Poacher": ["Renard des surfaces", "Delantero de área", "مهاجم صندوق"], "Target man": ["Pivot", "Delantero referencia", "مهاجم محوري"],
  "False nine": ["Faux neuf", "Falso nueve", "مهاجم وهمي"], "Winger": ["Ailier", "Extremo", "جناح"], "Inside forward": ["Ailier rentrant", "Extremo a pierna cambiada", "جناح داخلي"], "Pressing forward": ["Attaquant presseur", "Delantero presionante", "مهاجم ضاغط"],
  // realism tab
  "Loading the comparison with real matches…": ["Chargement de la comparaison avec les vrais matchs…", "Cargando la comparación con partidos reales…", "جارٍ تحميل المقارنة مع المباريات الحقيقية…"],
  "Is it real football?": ["Est-ce du vrai football ?", "¿Es fútbol de verdad?", "هل هذه كرة قدم حقيقية؟"],
  "Every number on this page compares the simulator with real matches: 1,446 league games of event data and 7 Bundesliga games with full tracking.\n      Nothing here is hand-picked: the same checks run in the test suite.": ["Chaque chiffre de cette page compare le simulateur à de vrais matchs : 1 446 matchs de championnat (données d'événements) et 7 matchs de Bundesliga avec tracking complet. Rien n'est choisi à la main : les mêmes vérifications tournent dans les tests.", "Cada cifra de esta página compara el simulador con partidos reales: 1.446 partidos de liga (datos de eventos) y 7 partidos de la Bundesliga con tracking completo. Nada está elegido a mano: las mismas comprobaciones se ejecutan en los tests.", "كل رقم في هذه الصفحة يقارن المحاكي بمباريات حقيقية: 1446 مباراة دوري (بيانات أحداث) و7 مباريات من البوندسليغا مع تتبع كامل. لا شيء مختار يدوياً: الفحوص نفسها تُشغَّل في الاختبارات."],
  "match totals within tolerance": ["totaux de match dans la marge", "totales del partido dentro del margen", "إجماليات المباراة ضمن الهامش"],
  "pitch-location checks within tolerance": ["contrôles de position dans la marge", "controles de posición dentro del margen", "فحوص المواقع ضمن الهامش"],
  "mean player placement error (a fixed formation: {0} m)": ["erreur moyenne de placement des joueurs (formation figée : {0} m)", "error medio de colocación de los jugadores (formación fija: {0} m)", "متوسط خطأ تموضع اللاعبين (خطة ثابتة: {0} م)"],
  "wins for a much stronger side (real: {0}%)": ["victoires d'une équipe bien plus forte (réel : {0} %)", "victorias de un equipo mucho más fuerte (real: {0}%)", "انتصارات فريق أقوى بكثير (حقيقي: {0}%)"],
  "Match totals": ["Totaux de match", "Totales del partido", "إجماليات المباراة"], "per team and match": ["par équipe et par match", "por equipo y partido", "لكل فريق ومباراة"],
  "Real": ["Réel", "Real", "حقيقي"], "Sim": ["Simu", "Simul.", "محاكاة"], "match": ["conforme", "coincide", "مطابق"], "gap": ["écart", "diferencia", "فجوة"],
  "Where the ball goes": ["Où va le ballon", "Dónde va el balón", "أين تذهب الكرة"], "Team level": ["Niveau des équipes", "Nivel de los equipos", "مستوى الفرق"],
  "what a strength gap does": ["l'effet d'un écart de niveau", "el efecto de una diferencia de nivel", "تأثير فارق المستوى"],
  "Goals scored": ["Buts marqués", "Goles marcados", "الأهداف المسجلة"], "Goals conceded": ["Buts encaissés", "Goles encajados", "الأهداف المستقبلة"],
  "Share of the passes %": ["Part des passes %", "Porcentaje de pases %", "حصة التمريرات %"], "Share of the shots %": ["Part des tirs %", "Porcentaje de tiros %", "حصة التسديدات %"],
  "Real leagues (2,892 team-matches)": ["Vrais championnats (2 892 matchs d'équipe)", "Ligas reales (2.892 partidos de equipo)", "دوريات حقيقية (2892 مباراة فريق)"], "Simulator": ["Simulateur", "Simulador", "المحاكي"],
  "Strength gap: log of the ratio of expected goals between the two sides, from a Poisson model fitted on each league season. Left: much weaker side, right: much stronger.": ["Écart de niveau : logarithme du rapport des buts attendus entre les deux équipes, d'après un modèle de Poisson ajusté sur chaque saison. À gauche : équipe bien plus faible ; à droite : bien plus forte.", "Diferencia de nivel: logaritmo del cociente de goles esperados entre los dos equipos, según un modelo de Poisson ajustado a cada temporada. Izquierda: equipo mucho más débil; derecha: mucho más fuerte.", "فارق المستوى: لوغاريتم نسبة الأهداف المتوقعة بين الفريقين وفق نموذج بواسون لكل موسم. اليسار: فريق أضعف بكثير، اليمين: أقوى بكثير."],
  "Do tactics change the game?": ["Les tactiques changent-elles le match ?", "¿Cambian las tácticas el partido?", "هل تغيّر الخطط المباراة؟"], "10th–90th percentile": ["10e–90e centile", "percentil 10–90", "المئين 10–90"],
  "Real teams": ["Vraies équipes", "Equipos reales", "فرق حقيقية"], "Sim tactics": ["Tactiques simulées", "Tácticas simuladas", "خطط محاكاة"],
  "78 real teams (season averages)": ["78 vraies équipes (moyennes de saison)", "78 equipos reales (medias de temporada)", "78 فريقاً حقيقياً (معدلات الموسم)"], "48 random tactics": ["48 tactiques aléatoires", "48 tácticas aleatorias", "48 خطة عشوائية"],
  "Defending": ["Défense", "Defensa", "الدفاع"], "outfield defenders goal-side of the ball": ["défenseurs entre le ballon et leur but", "defensores entre el balón y su portería", "المدافعون بين الكرة ومرماهم"],
  "Ball distance from goal": ["Distance du ballon au but", "Distancia del balón a la portería", "بُعد الكرة عن المرمى"], "{0} (of 100)": ["{0} (sur 100)", "{0} (de 100)", "{0} (من 100)"],
  "Formations": ["Systèmes", "Sistemas", "الخطط"], "effect on the share of passes, equal strength": ["effet sur la part des passes, à niveau égal", "efecto en el porcentaje de pases, a igual nivel", "التأثير على حصة التمريرات بمستوى متساوٍ"],
  "Real (matches)": ["Réel (matchs)", "Real (partidos)", "حقيقي (مباريات)"],
  "In points of the share of passes, against an average opponent. In real matches the formation alone changes little (±2 points); the simulator stays in the same small range, but does not reproduce the sign for back-three systems.": ["En points de part des passes, contre un adversaire moyen. En réel, le système seul change peu (±2 points) ; le simulateur reste dans la même petite plage, sans reproduire le signe pour les défenses à trois.", "En puntos de porcentaje de pases, frente a un rival medio. En partidos reales el sistema solo cambia poco (±2 puntos); el simulador se mantiene en ese rango, sin reproducir el signo en las defensas de tres.", "بنقاط حصة التمريرات أمام منافس متوسط. في المباريات الحقيقية لا تغيّر الخطة وحدها إلا قليلاً (±2 نقطة)، ويبقى المحاكي ضمن النطاق نفسه دون أن يعكس الاتجاه في خطط الدفاع الثلاثي."],
  "Sources": ["Sources", "Fuentes", "المصادر"],
  "Passes per team": ["Passes par équipe", "Pases por equipo", "التمريرات لكل فريق"], "Mean pass length (m)": ["Longueur moyenne des passes (m)", "Longitud media de pase (m)", "متوسط طول التمريرة (م)"],
  "Forward passes %": ["Passes vers l'avant %", "Pases hacia delante %", "التمريرات الأمامية %"], "Shots per team": ["Tirs par équipe", "Tiros por equipo", "التسديدات لكل فريق"],
  "Goals per team": ["Buts par équipe", "Goles por equipo", "الأهداف لكل فريق"], "Shot conversion %": ["Tirs convertis %", "Conversión de tiros %", "نسبة تحويل التسديدات %"], "Fouls per team": ["Fautes par équipe", "Faltas por equipo", "الأخطاء لكل فريق"],
  "passes starting in own third %": ["passes depuis son tiers défensif %", "pases desde el propio tercio %", "تمريرات من الثلث الدفاعي %"], "passes starting in final third %": ["passes depuis le dernier tiers %", "pases desde el último tercio %", "تمريرات من الثلث الأخير %"],
  "passes starting in the last 20 units %": ["passes depuis les 20 derniers mètres %", "pases desde los últimos 20 metros %", "تمريرات من آخر 20 متراً %"], "spread of pass start y (std)": ["étalement en largeur des passes (écart-type)", "dispersión lateral de los pases (desv.)", "انتشار التمريرات عرضياً (انحراف)"],
  "passes starting wide %": ["passes depuis les côtés %", "pases desde las bandas %", "تمريرات من الأطراف %"], "forward passes %": ["passes vers l'avant %", "pases hacia delante %", "تمريرات أمامية %"],
  "backward passes %": ["passes en retrait %", "pases hacia atrás %", "تمريرات خلفية %"], "lateral passes %": ["passes latérales %", "pases laterales %", "تمريرات عرضية %"],
  "passes per defender (% of team)": ["passes par défenseur (% de l'équipe)", "pases por defensa (% del equipo)", "تمريرات كل مدافع (% من الفريق)"], "passes per midfielder (% of team)": ["passes par milieu (% de l'équipe)", "pases por centrocampista (% del equipo)", "تمريرات كل لاعب وسط (% من الفريق)"],
  "passes per forward (% of team)": ["passes par attaquant (% de l'équipe)", "pases por delantero (% del equipo)", "تمريرات كل مهاجم (% من الفريق)"], "accuracy, own third %": ["précision, tiers défensif %", "precisión, propio tercio %", "الدقة، الثلث الدفاعي %"],
  "accuracy, middle third %": ["précision, tiers central %", "precisión, tercio medio %", "الدقة، الثلث الأوسط %"], "accuracy, final third %": ["précision, dernier tiers %", "precisión, último tercio %", "الدقة، الثلث الأخير %"],
  "mean shot distance (m)": ["distance moyenne des tirs (m)", "distancia media de tiro (m)", "متوسط مسافة التسديد (م)"], "shots from inside the box %": ["tirs dans la surface %", "tiros dentro del área %", "تسديدات من داخل المنطقة %"],
  "share of all passes %": ["part de toutes les passes %", "porcentaje de todos los pases %", "حصة كل التمريرات %"], "passes per match": ["passes par match", "pases por partido", "تمريرات في المباراة"],
  "pass accuracy %": ["précision des passes %", "precisión de pase %", "دقة التمرير %"], "mean pass start x (0-100)": ["position moyenne des passes (0-100)", "posición media de los pases (0-100)", "متوسط موقع التمرير (0-100)"],
  "mean pass length (m)": ["longueur moyenne des passes (m)", "longitud media de pase (m)", "متوسط طول التمريرة (م)"], "shots per match": ["tirs par match", "tiros por partido", "تسديدات في المباراة"],
};
const LANG_INDEX = { fr: 0, es: 1, ar: 2 };
let UI_LANG = "en";
const _patterns = Object.keys(I18N).filter(k => k.includes("{0}")).map(k => {
  const rx = new RegExp("^" + k.replace(/[.*+?^$()|[\]\\]/g, "\\$&").replace(/\{(\d)\}/g, "(.+?)") + "$");
  return [rx, k];
});
function T(s) {
  if (UI_LANG === "en" || s == null) return s;
  const i = LANG_INDEX[UI_LANG], key = s.trim();
  if (!key) return s;
  const pre = s.slice(0, s.indexOf(key[0])), post = s.slice(s.lastIndexOf(key[key.length - 1]) + 1);
  if (I18N[key]) return pre + I18N[key][i] + post;
  for (const [rx, k] of _patterns) {
    const m = key.match(rx);
    if (m) return pre + I18N[k][i].replace(/\{(\d)\}/g, (_, n) => T(m[+n + 1])) + post;
  }
  return s;
}
function translateNode(root) {
  const walk = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
  const nodes = [];
  while (walk.nextNode()) nodes.push(walk.currentNode);
  nodes.forEach(n => {
    const p = n.parentNode;
    if (!p || ["SCRIPT", "STYLE", "CODE"].includes(p.nodeName) || p.closest(".ans,.overlay,.notrans")) return;
    if (n.__en === undefined) n.__en = n.nodeValue;
    const t = T(n.__en);
    if (n.nodeValue !== t) n.nodeValue = t;
  });
  (root.querySelectorAll ? root.querySelectorAll("[placeholder],[title]") : []).forEach(el => {
    ["placeholder", "title"].forEach(a => {
      if (!el.hasAttribute(a)) return;
      const k = "data-en-" + a;
      if (!el.hasAttribute(k)) el.setAttribute(k, el.getAttribute(a));
      el.setAttribute(a, T(el.getAttribute(k)));
    });
  });
}
function setUiLang(lang) {
  UI_LANG = ["fr", "es", "ar"].includes(lang) ? lang : "en";
  document.documentElement.lang = UI_LANG;
  document.documentElement.dir = UI_LANG === "ar" ? "rtl" : "ltr";
  translateNode(document.body);
}
new MutationObserver(muts => {
  if (UI_LANG === "en") return;
  muts.forEach(m => m.addedNodes.forEach(n => {
    if (n.nodeType === 1) translateNode(n);
    else if (n.nodeType === 3 && n.parentNode) translateNode(n.parentNode);
  }));
}).observe(document.documentElement, { childList: true, subtree: true });
