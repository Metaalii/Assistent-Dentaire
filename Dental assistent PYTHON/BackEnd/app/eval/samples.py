"""
Gold-standard evaluation samples for SmartNote quality testing.

Each sample provides:
- transcription: realistic French dental consultation transcript
- reference_note: a high-quality SmartNote (human-written gold standard)
- key_terms: clinical terms that MUST appear in any acceptable SmartNote
- scenario: short label for reporting

These cover the main consultation types: routine, emergency, complex
medical history, and minimal/short input (an edge case).
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class EvalSample:
    scenario: str
    transcription: str
    reference_note: str
    key_terms: list[str] = field(default_factory=list)


SAMPLES: list[EvalSample] = [
    # ------------------------------------------------------------------
    # 1. Routine checkup with cavity finding
    # ------------------------------------------------------------------
    EvalSample(
        scenario="routine_checkup",
        transcription=(
            "Bonjour madame Dupont, comment allez-vous aujourd'hui ? "
            "Bien merci docteur, je viens pour mon controle annuel. "
            "D'accord, installez-vous. Alors, je vois que votre dernier "
            "detartrage date de quatorze mois. On va commencer par un examen "
            "complet. Ouvrez grand. Alors, les incisives superieures sont "
            "bien, les canines aussi. Premolaire 24, je vois un debut de "
            "carie occlusale. La 25 est saine. Cote droit tout est bon. "
            "En bas, je note un peu de tartre lingual sur les incisives. "
            "Les molaires 36 et 46 sont bien. La gencive est legerement "
            "inflammee en bas a gauche, secteur 3. Je vais vous faire un "
            "detartrage complet aujourd'hui et on programmera une obturation "
            "composite sur la 24 la prochaine fois. Le devis pour le "
            "composite sera de soixante-quinze euros, avec prise en charge "
            "secu a soixante-dix pourcent. Prochain rendez-vous dans deux "
            "semaines pour le soin. Pensez a bien brosser le secteur 3, "
            "matin et soir, avec une brosse souple."
        ),
        reference_note=(
            "- Motif : Controle annuel\n"
            "- Antecedents : Dernier detartrage il y a 14 mois\n"
            "- Examen : Carie occlusale debutante sur 24, tartre lingual "
            "incisives inferieures, inflammation gingivale secteur 3\n"
            "- Plan : Detartrage complet (realise), obturation composite 24\n"
            "- Risques : Progression carie 24, parodontite si inflammation "
            "non traitee\n"
            "- Recommandations : Brossage souple matin et soir secteur 3\n"
            "- Prochain RDV : 2 semaines pour composite 24\n"
            "- Admin : Devis composite 75 euros, prise en charge SS 70%"
        ),
        key_terms=[
            "controle", "detartrage", "carie", "24", "composite",
            "gencive", "secteur 3", "75", "incisive",
        ],
    ),

    # ------------------------------------------------------------------
    # 2. Emergency: acute toothache
    # ------------------------------------------------------------------
    EvalSample(
        scenario="emergency_toothache",
        transcription=(
            "Docteur, j'ai tres mal depuis hier soir, c'est insupportable, "
            "je n'ai pas dormi de la nuit. La douleur est pulsatile, surtout "
            "du cote gauche en bas. J'ai pris de l'ibuprofene 400 mais ca "
            "ne passe pas. Voyons ca. Ouvrez la bouche. La 36 a une grosse "
            "carie mesiale, je vois que l'email est effondre. Je vais faire "
            "un test au froid. Aie ! Oui, reaction tres vive et la douleur "
            "persiste apres le retrait du stimulus. Ca ressemble a une "
            "pulpite irreversible. On va faire une radiographie pour "
            "confirmer. Effectivement, la radio montre une lesion carieuse "
            "profonde qui atteint la pulpe, pas de lesion periapicale pour "
            "le moment. Je vais vous devitaliser la dent aujourd'hui en "
            "urgence. On fait une anesthesie locale, puis on ouvre la "
            "chambre pulpaire pour soulager la douleur. Il faudra revenir "
            "pour terminer le traitement endodontique et poser une "
            "couronne. Je vous prescris du paracetamol mille milligrammes, "
            "un toutes les six heures. Evitez de manger du cote gauche. "
            "Revenez dans une semaine."
        ),
        reference_note=(
            "- Motif : Douleur aigue pulsatile molaire 36\n"
            "- Antecedents : Prise ibuprofene 400 sans effet\n"
            "- Examen : Carie mesiale profonde 36, test froid positif "
            "persistent, radio confirme atteinte pulpaire sans lesion "
            "periapicale\n"
            "- Plan : Devitalisation urgence 36 (realise), traitement "
            "endodontique complet + couronne a programmer\n"
            "- Risques : Necrose pulpaire, infection periapicale\n"
            "- Recommandations : Paracetamol 1000mg/6h, eviter mastication "
            "cote gauche\n"
            "- Prochain RDV : 1 semaine pour suite endodontique\n"
            "- Admin : Non mentionne"
        ),
        key_terms=[
            "douleur", "36", "carie", "pulpite", "radio",
            "devitalisation", "anesthesi", "endodont", "couronne",
            "ibuprofene",
        ],
    ),

    # ------------------------------------------------------------------
    # 3. Complex case: patient on anticoagulants needing extraction
    # ------------------------------------------------------------------
    EvalSample(
        scenario="complex_anticoagulant",
        transcription=(
            "Monsieur Martin, soixante-douze ans, vous venez pour cette "
            "dent qui bouge, c'est ca ? Oui docteur, la dent en bas a "
            "droite, elle bouge beaucoup et ca me gene pour manger. Je "
            "rappelle que vous prenez du Xarelto pour votre fibrillation "
            "auriculaire, c'est bien ca ? Oui, rivaroxaban vingt "
            "milligrammes par jour. Et vous avez aussi du diabete de type "
            "deux sous metformine. Pas d'allergie ? Non, aucune allergie "
            "connue. D'accord. Examinons. La 45 presente une mobilite de "
            "grade trois, il y a une poche parodontale de huit millimetres "
            "en distal. La radiographie montre une perte osseuse terminale "
            "autour de la 45. L'extraction est indiquee. Concernant votre "
            "anticoagulant, on ne va pas arreter le Xarelto, les "
            "recommandations actuelles disent de maintenir le traitement. "
            "On va utiliser des mesures d'hemostase locale : compression, "
            "eponge hemostatique, sutures. Je vous prescris de "
            "l'amoxicilline deux grammes une heure avant l'extraction en "
            "antibioprophylaxie vu votre diabete. L'extraction est prevue "
            "mardi prochain. Pas de bain de bouche a l'aspirine apres "
            "l'intervention. Rincez doucement avec de la chlorhexidine."
        ),
        reference_note=(
            "- Motif : Mobilite dentaire 45 genante a la mastication\n"
            "- Antecedents : Fibrillation auriculaire sous Xarelto "
            "(rivaroxaban 20mg/j), diabete type 2 sous metformine, pas "
            "d'allergie\n"
            "- Examen : Mobilite grade 3 sur 45, poche parodontale 8mm "
            "distale, perte osseuse terminale (radio)\n"
            "- Plan : Extraction 45, hemostase locale (compression + "
            "eponge + sutures), maintien anticoagulant\n"
            "- Risques : Hemorragie post-operatoire sous anticoagulant, "
            "retard cicatrisation (diabete)\n"
            "- Recommandations : Amoxicilline 2g antibioprophylaxie 1h "
            "avant, rincer chlorhexidine, pas de bain de bouche aspirine\n"
            "- Prochain RDV : Mardi prochain pour extraction\n"
            "- Admin : Non mentionne"
        ),
        key_terms=[
            "45", "mobilite", "extraction", "anticoagulant",
            "parodont", "amoxicilline", "radio",
            "diabete", "hemostase",
        ],
    ),

    # ------------------------------------------------------------------
    # 4. Edge case: very short / minimal transcription
    # ------------------------------------------------------------------
    EvalSample(
        scenario="minimal_input",
        transcription=(
            "Bonjour, je viens pour un detartrage. Pas de probleme "
            "particulier, tout va bien. D'accord, on fait le detartrage. "
            "Voila c'est termine, bonne journee."
        ),
        reference_note=(
            "- Motif : Detartrage\n"
            "- Antecedents : Aucun probleme signale\n"
            "- Examen : Non detaille\n"
            "- Plan : Detartrage realise\n"
            "- Risques : Aucun identifie\n"
            "- Recommandations : Non precisees\n"
            "- Prochain RDV : Non mentionne\n"
            "- Admin : Non mentionne"
        ),
        key_terms=["detartrage"],
    ),

    # ------------------------------------------------------------------
    # 5. Pediatric consultation
    # ------------------------------------------------------------------
    EvalSample(
        scenario="pediatric",
        transcription=(
            "Bonjour, c'est la maman du petit Lucas, six ans. Il a mal a "
            "une dent de lait en bas depuis deux jours. Il a du mal a "
            "manger. Voyons ca Lucas, ouvre grand la bouche. La 75, la "
            "deuxieme molaire de lait inferieure gauche, est tres cariee, "
            "il y a un abces gingival en regard. La dent permanente "
            "successionnelle, la 35, est visible a la radio, elle est en "
            "cours de formation. On va traiter l'infection avec de "
            "l'amoxicilline sirop, vingt-cinq milligrammes par kilo par "
            "jour pendant sept jours. Puis on reviendra pour extraire la "
            "75 quand l'infection sera calmee, dans dix jours. En "
            "attendant, alimentation molle, brossage doux, et doliprane "
            "si douleur."
        ),
        reference_note=(
            "- Motif : Douleur molaire de lait 75 chez enfant 6 ans\n"
            "- Antecedents : Aucun signale\n"
            "- Examen : Carie profonde 75, abces gingival, dent "
            "permanente 35 en formation (radio)\n"
            "- Plan : Antibiotherapie puis extraction 75\n"
            "- Risques : Extension infection, atteinte germe permanent 35\n"
            "- Recommandations : Amoxicilline sirop 25mg/kg/j 7 jours, "
            "alimentation molle, brossage doux, Doliprane si douleur\n"
            "- Prochain RDV : 10 jours pour extraction 75\n"
            "- Admin : Non mentionne"
        ),
        key_terms=[
            "douleur", "75", "carie", "abces", "extraction",
            "amoxicilline", "35",
        ],
    ),
]
