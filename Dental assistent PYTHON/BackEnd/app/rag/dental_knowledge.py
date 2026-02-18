"""
Seed dental knowledge base for RAG-enhanced SmartNotes.

Contains foundational dental guidelines, common procedures,
drug interactions, and clinical protocols in French.

This is indexed on first startup to provide immediate RAG value.
Dentists can expand the knowledge base by uploading their own documents.
"""

from haystack import Document

DENTAL_KNOWLEDGE: list[Document] = [
    # ------------------------------------------------------------------
    # Urgences dentaires
    # ------------------------------------------------------------------
    Document(
        content=(
            "Protocole d'urgence pour pulpite aigue irreversible: "
            "Douleur spontanee, pulsatile, exacerbee par le chaud. "
            "Traitement d'urgence: pulpotomie ou pulpectomie sous anesthesie locale. "
            "Prescription: Ibuprofene 400mg toutes les 6h (en l'absence de contre-indication) "
            "ou Paracetamol 1g toutes les 6h. Eviter les antibiotiques sauf en cas de signes "
            "d'infection (fievre, tumefaction, adenopathie). "
            "Revoir le patient sous 48-72h pour traitement endodontique definitif."
        ),
        meta={"source": "Protocole clinique", "category": "Urgences"},
    ),
    Document(
        content=(
            "Urgence traumatisme dentaire - Avulsion: "
            "Reimplanter la dent dans les 60 minutes si possible. "
            "Conserver la dent dans du lait, serum physiologique ou salive. "
            "Ne pas toucher la racine. Rincer delicatement sans frotter. "
            "Contention souple 2 semaines (sauf fracture alveolaire: 4 semaines). "
            "Antibiotherapie: Amoxicilline 2g/j pendant 7 jours. "
            "Verifier vaccination antitetanique. Controle clinique et radiographique a J7, J30, "
            "3 mois, 6 mois, 1 an puis annuellement pendant 5 ans."
        ),
        meta={"source": "Protocole clinique", "category": "Urgences - Traumatisme"},
    ),
    Document(
        content=(
            "Abces periapical aigu: Signes - douleur intense, tumefaction, "
            "mobilite dentaire, douleur a la percussion, possible fievre. "
            "Traitement: Drainage par voie endodontique (trepanation) ou chirurgical "
            "(incision). Antibiotherapie: Amoxicilline 2g/j pendant 7 jours, "
            "ou Clindamycine 1200mg/j si allergie aux penicillines. "
            "Antalgique: Paracetamol 1g x 4/j +/- Ibuprofene 400mg x 3/j. "
            "Revoir sous 48h. Extraction ou traitement endodontique selon pronostic."
        ),
        meta={"source": "Protocole clinique", "category": "Urgences - Infection"},
    ),
    # ------------------------------------------------------------------
    # Pharmacologie dentaire
    # ------------------------------------------------------------------
    Document(
        content=(
            "Interactions medicamenteuses en odontologie: "
            "Patients sous anticoagulants (AVK, AOD): INR < 4 pour les actes simples. "
            "NE PAS prescrire d'AINS. Utiliser Paracetamol comme antalgique. "
            "Patients sous antiaggregants (Aspirine, Clopidogrel): ne pas interrompre "
            "pour les extractions simples, assurer hemostase locale (acide tranexamique, "
            "compresses d'Exacyl). "
            "Patients sous bisphosphonates: risque d'osteonecrose. Evaluation du risque "
            "avant tout acte invasif. Antibiotherapie prophylactique si extraction necessaire."
        ),
        meta={"source": "Pharmacologie", "category": "Interactions medicamenteuses"},
    ),
    Document(
        content=(
            "Prescription antibiotique en odontologie (recommandations ANSM/HAS): "
            "Premiere intention: Amoxicilline 2g/j en 2 prises pendant 7 jours. "
            "Allergie penicilline: Clindamycine 1200mg/j en 2 prises pendant 7 jours, "
            "ou Azithromycine 500mg/j pendant 3 jours. "
            "Infection severe: Amoxicilline + Metronidazole (1500mg/j). "
            "Antibioprophylaxie endocardite: Amoxicilline 2g en dose unique 1h avant "
            "le geste, ou Clindamycine 600mg si allergie. "
            "NE PAS prescrire d'antibiotiques pour: pulpite, alveolite seche, gingivite simple."
        ),
        meta={"source": "ANSM/HAS", "category": "Prescription antibiotique"},
    ),
    Document(
        content=(
            "Anesthesie locale en odontologie: "
            "Articaine 4% avec adrenaline 1/200 000: anesthesique de reference. "
            "Dose maximale: 7mg/kg (adulte ~500mg soit ~12 carpules). "
            "Contre-indications adrenaline: allergie aux sulfites, "
            "pheochromocytome, tachycardie paroxystique. "
            "Precautions: patients cardiaques (limiter l'adrenaline a 0.04mg), "
            "femmes enceintes (eviter les vasoconstricteurs au 1er trimestre). "
            "Mepivacaine 3% sans vasoconstricteur: alternative si CI a l'adrenaline. "
            "Duree d'action plus courte (20-40 min pulpaire)."
        ),
        meta={"source": "Protocole clinique", "category": "Anesthesie"},
    ),
    # ------------------------------------------------------------------
    # Parodontologie
    # ------------------------------------------------------------------
    Document(
        content=(
            "Classification parodontale (2018 - AAP/EFP): "
            "Stade I: Perte d'attache 1-2mm, perte osseuse < tiers coronaire. "
            "Stade II: Perte d'attache 3-4mm, perte osseuse tiers coronaire. "
            "Stade III: Perte d'attache >= 5mm, perte osseuse moitie ou plus, "
            "perte de dents (<=4) par parodontite. "
            "Stade IV: Comme stade III + effondrement occlusal, migration, "
            "perte de >= 5 dents par parodontite. "
            "Grades: A (progression lente), B (progression moderee), C (progression rapide). "
            "Facteurs de risque: tabac (Grade C si > 10 cig/j), diabete non equilibre (HbA1c > 7%)."
        ),
        meta={"source": "AAP/EFP 2018", "category": "Parodontologie"},
    ),
    Document(
        content=(
            "Protocole de traitement parodontal: "
            "Phase 1 (etiologique): Education hygiene, motivation, "
            "detartrage/surfacage radiculaire sous anesthesie locale. "
            "Reevaluation a 6-8 semaines. "
            "Phase 2 (chirurgicale si necessaire): Lambeau d'assainissement, "
            "regeneration tissulaire guidee (RTG), greffe osseuse. "
            "Phase 3 (maintenance): Controle tous les 3-4 mois, "
            "indice de plaque, sondage, radiographies de controle annuelles. "
            "Objectif: profondeur de poche <= 4mm sans saignement au sondage."
        ),
        meta={"source": "Protocole clinique", "category": "Parodontologie"},
    ),
    # ------------------------------------------------------------------
    # Endodontie
    # ------------------------------------------------------------------
    Document(
        content=(
            "Indications et contre-indications du traitement endodontique: "
            "Indications: pulpite irreversible, necrose pulpaire, granulome/kyste periapical, "
            "resorption interne, traumatisme avec exposition pulpaire. "
            "Contre-indications relatives: dent non restaurable, fracture verticale, "
            "poche parodontale profonde (lesion endo-paro), support osseux insuffisant. "
            "Protocole: radiographie preoperatoire, anesthesie, mise en place du champ "
            "operatoire (digue obligatoire), acces cameral, localisation des canaux, "
            "instrumentation, irrigation NaOCl 2.5-5.25%, obturation (gutta-percha + ciment), "
            "radiographie de controle, restauration coronaire etanche."
        ),
        meta={"source": "Protocole clinique", "category": "Endodontie"},
    ),
    # ------------------------------------------------------------------
    # Prothese
    # ------------------------------------------------------------------
    Document(
        content=(
            "Etapes prothese fixee (couronne/bridge): "
            "1. Examen clinique et radiographique, plan de traitement. "
            "2. Preparation (reduction axiale 1.5mm, occlusale 2mm pour ceramique). "
            "3. Empreinte (silicone addition ou numerique). "
            "4. Prothese provisoire (resine, scellement temporaire). "
            "5. Essayage bisque ou framework. "
            "6. Scellement/collage definitif (CVI, CVIMAR ou colle composite). "
            "7. Controle occlusion et points de contact. "
            "8. Rendez-vous de controle a 1 semaine puis 6 mois. "
            "Codes CCAM: HBLD038 (couronne metallique), HBLD036 (couronne ceramo-metallique), "
            "HBLD040 (couronne ceramique)."
        ),
        meta={"source": "Protocole clinique", "category": "Prothese fixee"},
    ),
    Document(
        content=(
            "Implantologie - Protocole standard: "
            "Bilan pre-implantaire: panoramique + CBCT, analyse osseuse, "
            "guide chirurgical si necessaire. "
            "Contre-indications: bisphosphonates IV, radiotherapie cervico-faciale "
            "recente (< 2 ans), diabete non equilibre, tabagisme actif (risque relatif). "
            "Chirurgie: lambeau, forage progressif, mise en place implant, "
            "sutures. Antibioprophylaxie: Amoxicilline 2g 1h avant. "
            "Cicatrisation: 3-6 mois (mise en charge conventionnelle) "
            "ou mise en charge immediate si conditions favorables "
            "(torque > 35 Ncm, stabilite primaire). "
            "Phase prothetique: empreinte, pilier, couronne sur implant."
        ),
        meta={"source": "Protocole clinique", "category": "Implantologie"},
    ),
    # ------------------------------------------------------------------
    # Odontologie pediatrique
    # ------------------------------------------------------------------
    Document(
        content=(
            "Specificites odontologie pediatrique: "
            "Chronologie eruption: incisives temporaires 6-12 mois, "
            "1ere molaire permanente 6 ans, incisives permanentes 6-8 ans. "
            "Carie precoce de l'enfance (CPE): diagnostic des que carie sur "
            "dent temporaire avant 6 ans. Traitement conservateur privilegie. "
            "Fluorures: vernis fluore (22 600 ppm) 2-4x/an des eruption. "
            "Scellements de sillons: des eruption des 1eres molaires permanentes "
            "si sillons anfractueux. "
            "Anesthesie: adapter les doses au poids (Articaine 5mg/kg max). "
            "Coiffage pulpaire indirect sur dent temporaire: MTA ou CaOH2."
        ),
        meta={"source": "Protocole clinique", "category": "Odontologie pediatrique"},
    ),
    # ------------------------------------------------------------------
    # Radiologie
    # ------------------------------------------------------------------
    Document(
        content=(
            "Indications radiologiques en odontologie (recommandations HAS): "
            "Radiographie retroalveolaire: diagnostic carie proximale, "
            "evaluation periapicale, controle endodontique, sondage osseux. "
            "Panoramique (OPT): bilan initial, evaluation generale, "
            "dents de sagesse, orthodontie, traumatisme. "
            "CBCT (cone beam): implantologie, chirurgie complexe, "
            "endodontie complexe, pathologie sinusienne. "
            "Principe ALARA: justification de chaque cliche, "
            "limiter l'exposition, pas de radiographie systematique sans indication. "
            "Femme enceinte: reporter si possible, tablier plombe si urgent."
        ),
        meta={"source": "HAS", "category": "Radiologie"},
    ),
    # ------------------------------------------------------------------
    # Hygiene et sterilisation
    # ------------------------------------------------------------------
    Document(
        content=(
            "Protocole d'hygiene et asepsie au cabinet dentaire: "
            "Desinfection des surfaces entre chaque patient (spray + essuyage). "
            "Sterilisation des instruments: pre-desinfection, nettoyage "
            "(ultrasons ou thermolaveur), conditionnement (sachets), "
            "sterilisation autoclave classe B (134C, 18 min). "
            "Test de Bowie-Dick quotidien, indicateurs physiques et chimiques, "
            "controle biologique mensuel (spores). "
            "Port EPI obligatoire: gants, masque FFP2/chirurgical, lunettes, surblouse. "
            "Hygiene des mains: SHA entre chaque patient, lavage chirurgical avant actes invasifs."
        ),
        meta={"source": "ADF/DGS", "category": "Hygiene et sterilisation"},
    ),
]


def get_seed_knowledge() -> list[Document]:
    """Return the seed dental knowledge documents for initial indexing."""
    return DENTAL_KNOWLEDGE
