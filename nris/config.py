"""
Configuration management and translations for NRIS.
"""

import json
from typing import Dict
from pathlib import Path

# File paths
DB_FILE = "nipt_registry_v2.db"
CONFIG_FILE = "nris_config.json"
BACKUP_DIR = "backups"
MAX_BACKUPS = 10

DEFAULT_CONFIG = {
    'QC_THRESHOLDS': {
        'MIN_CFF': 3.5,
        'MAX_CFF': 50.0,
        'GC_RANGE': [37.0, 44.0],
        'MIN_UNIQ_RATE': 68.0,
        'MAX_ERROR_RATE': 1.0,
        'QS_LIMIT_NEG': 1.7,
        'QS_LIMIT_POS': 2.0
    },
    'PANEL_READ_LIMITS': {
        "NIPT Basic": 5,
        "NIPT Standard": 7,
        "NIPT Plus": 12,
        "NIPT Pro": 20
    },
    'CLINICAL_THRESHOLDS': {
        'TRISOMY_LOW': 2.58,
        'TRISOMY_AMBIGUOUS': 6.0,
        'SCA_THRESHOLD': 4.5,
        'SCA_XY_THRESHOLD': 6.0,
        'RAT_POSITIVE': 8.0,
        'RAT_AMBIGUOUS': 4.5
    },
    'TEST_SPECIFIC_THRESHOLDS': {
        'TRISOMY': {
            1: {'low': 2.58, 'ambiguous': 6.0},
            2: {'low': 2.58, 'medium': 3.0, 'high': 4.0, 'positive': 6.0},
            3: {'low': 2.58, 'medium': 3.0, 'high': 4.0, 'positive': 6.0}
        },
        'RAT': {
            1: {'low': 4.5, 'positive': 8.0},
            2: {'low': 4.5, 'positive': 8.0},
            3: {'low': 4.5, 'positive': 8.0}
        },
        'SCA': {
            1: {'xx_threshold': 4.5, 'xy_threshold': 6.0},
            2: {'xx_threshold': 4.5, 'xy_threshold': 6.0},
            3: {'xx_threshold': 4.5, 'xy_threshold': 6.0}
        },
        'CNV': {
            1: {'>= 10': 6.0, '> 7': 8.0, '> 3.5': 10.0, '<= 3.5': 12.0},
            2: {'>= 10': 6.0, '> 7': 8.0, '> 3.5': 10.0, '<= 3.5': 12.0},
            3: {'>= 10': 6.0, '> 7': 8.0, '> 3.5': 10.0, '<= 3.5': 12.0}
        }
    },
    'REPORT_LANGUAGE': 'en',
    'ALLOW_ALPHANUMERIC_MRN': False,
    'DEFAULT_SORT': 'id'
}

TRANSLATIONS = {
    'en': {
        'lab_title': 'CLINICAL GENETICS LABORATORY',
        'report_title': 'Non-Invasive Prenatal Testing (NIPT) Report',
        'report_id': 'Report ID:',
        'report_date': 'Report Date:',
        'panel_type': 'Panel Type:',
        'report_time': 'Report Time:',
        'test_number': 'Test Number:',
        'first_test': '1st Test',
        'second_test': '2nd Test',
        'third_test': '3rd Test',
        'patient_info': 'PATIENT INFORMATION',
        'name': 'Name:',
        'mrn': 'MRN:',
        'maternal_age': 'Maternal Age:',
        'gestational_age': 'Gestational Age:',
        'weight': 'Weight:',
        'height': 'Height:',
        'bmi': 'BMI:',
        'years': 'years',
        'weeks': 'weeks',
        'qc_assessment': 'QUALITY CONTROL ASSESSMENT',
        'qc_status': 'QC Status',
        'parameter': 'Parameter',
        'value': 'Value',
        'reference_range': 'Reference Range',
        'status': 'Status',
        'fetal_fraction': 'Fetal Fraction (Cff)',
        'gc_content': 'GC Content',
        'seq_reads': 'Sequencing Reads',
        'unique_rate': 'Unique Read Rate',
        'error_rate': 'Error Rate',
        'quality_score': 'Quality Score',
        'qc_recommendation': 'QC Recommendation:',
        'qc_override_applied': 'QC Override Applied:',
        'original_status': 'Original status was',
        'validated_by': 'Validated by',
        'reason': 'Reason:',
        'override': 'Override',
        'pass': 'PASS',
        'fail': 'FAIL',
        'warning': 'WARNING',
        'aneuploidy_results': 'ANEUPLOIDY SCREENING RESULTS',
        'condition': 'Condition',
        'result': 'Result',
        'z_score': 'Z-Score',
        'reportable': 'Reportable',
        'ref': 'Ref',
        'trisomy_21': 'Trisomy 21 (Down Syndrome)',
        'trisomy_18': 'Trisomy 18 (Edwards Syndrome)',
        'trisomy_13': 'Trisomy 13 (Patau Syndrome)',
        'sca': 'Sex Chromosome Aneuploidy',
        'fetal_sex': 'Fetal Sex:',
        'male': 'Male',
        'female': 'Female',
        'undetermined': 'Undetermined',
        'cnv_findings': 'COPY NUMBER VARIATION (CNV) FINDINGS',
        'rat_findings': 'RARE AUTOSOMAL TRISOMY (RAT) FINDINGS',
        'finding': 'Finding',
        'clinical_significance': 'Clinical Significance',
        'maternal_factors': 'MATERNAL FACTORS & AGE-BASED RISK',
        'bmi_underweight': '(Underweight)',
        'bmi_normal': '(Normal)',
        'bmi_overweight': '(Overweight)',
        'bmi_obese': '(Obese - may affect fetal fraction)',
        'age_risk_text': 'Based on maternal age of {age} years, the a priori risks are: Trisomy 21: 1 in {t21}, Trisomy 18: 1 in {t18}, Trisomy 13: 1 in {t13}',
        'final_interpretation': 'FINAL INTERPRETATION',
        'clinical_recommendations': 'CLINICAL RECOMMENDATIONS',
        'no_high_risk': 'No high-risk findings detected. Continue standard prenatal care.',
        'nipt_screening': 'NIPT is a screening test. It does not diagnose chromosomal abnormalities.',
        'rec_t21_positive': 'Confirmatory diagnostic testing (amniocentesis or CVS) is strongly recommended. Genetic counseling should be offered.',
        'rec_t18_positive': 'Confirmatory diagnostic testing (amniocentesis or CVS) is strongly recommended. Detailed ultrasound and genetic counseling advised.',
        'rec_t13_positive': 'Confirmatory diagnostic testing (amniocentesis or CVS) is strongly recommended. Detailed ultrasound and genetic counseling advised.',
        'rec_sca_positive': 'Genetic counseling recommended. Confirmatory testing may be considered based on clinical judgment.',
        'rec_cnv_positive': 'Detailed ultrasound recommended. Genetic counseling and possible confirmatory testing advised.',
        'rec_rat_positive': 'Genetic counseling recommended. Clinical correlation and possible confirmatory testing advised.',
        'rec_high_risk': 'Re-analysis recommended. If persistent, consider confirmatory diagnostic testing.',
        'rec_low_risk': 'No additional testing indicated based on NIPT result alone. Standard prenatal care recommended.',
        'clinical_notes': 'CLINICAL NOTES & OBSERVATIONS',
        'key_markers': 'Key clinical markers:',
        'nt_noted': 'Nuchal Translucency noted',
        'ff_concerns': 'Fetal Fraction concerns noted',
        'ivf_noted': 'ART/IVF conception noted',
        'multiple_noted': 'Multiple gestation noted',
        'limitations': 'LIMITATIONS AND DISCLAIMER',
        'important_info': 'Important Information:',
        'disclaimer_1': 'NIPT is a screening test, not a diagnostic test. Positive results should be confirmed with diagnostic testing (amniocentesis or CVS).',
        'disclaimer_2': 'False positive and false negative results can occur. A negative result does not eliminate the possibility of chromosomal abnormalities.',
        'disclaimer_3': 'This test screens for specific chromosomal conditions and does not detect all genetic disorders.',
        'disclaimer_4': 'Results should be interpreted in conjunction with other clinical findings, ultrasound, and maternal history.',
        'disclaimer_5': 'Test performance may be affected by factors including: low fetal fraction, maternal chromosomal abnormalities, confined placental mosaicism, vanishing twin, or maternal malignancy.',
        'disclaimer_6': 'Genetic counseling is recommended for all patients, especially those with positive or inconclusive results.',
        'authorization': 'AUTHORIZATION',
        'performed_by': 'Performed by:',
        'reviewed_by': 'Reviewed by:',
        'approved_by': 'Approved by:',
        'date': 'Date:',
        'clinical_pathologist': 'Clinical Pathologist',
        'lab_director': 'Laboratory Director',
        'lab_staff': 'Laboratory Staff',
        'report_generated': 'Report generated:',
        'version': 'NRIS v2.4 Enhanced Edition',
    },
    'fr': {
        'lab_title': 'LABORATOIRE DE GENETIQUE CLINIQUE',
        'report_title': 'Rapport de Depistage Prenatal Non Invasif (DPNI)',
        'report_id': 'ID du rapport:',
        'report_date': 'Date du rapport:',
        'panel_type': 'Type de panel:',
        'report_time': 'Heure du rapport:',
        'test_number': 'Numéro de test:',
        'first_test': '1er Test',
        'second_test': '2ème Test',
        'third_test': '3ème Test',
        'patient_info': 'INFORMATIONS PATIENTE',
        'name': 'Nom:',
        'mrn': 'NDM:',
        'maternal_age': 'Age maternel:',
        'gestational_age': 'Age gestationnel:',
        'weight': 'Poids:',
        'height': 'Taille:',
        'bmi': 'IMC:',
        'years': 'ans',
        'weeks': 'semaines',
        'qc_assessment': 'EVALUATION DU CONTROLE QUALITE',
        'qc_status': 'Statut CQ',
        'parameter': 'Parametre',
        'value': 'Valeur',
        'reference_range': 'Plage de reference',
        'status': 'Statut',
        'fetal_fraction': 'Fraction foetale (Cff)',
        'gc_content': 'Contenu GC',
        'seq_reads': 'Lectures de sequencage',
        'unique_rate': 'Taux de lectures uniques',
        'error_rate': "Taux d'erreur",
        'quality_score': 'Score de qualite',
        'qc_recommendation': 'Recommandation CQ:',
        'qc_override_applied': 'Derogation CQ appliquee:',
        'original_status': 'Le statut original etait',
        'validated_by': 'Valide par',
        'reason': 'Raison:',
        'override': 'Derogation',
        'pass': 'CONFORME',
        'fail': 'NON CONFORME',
        'warning': 'ATTENTION',
        'aneuploidy_results': 'RESULTATS DU DEPISTAGE DES ANEUPLOIDIES',
        'condition': 'Condition',
        'result': 'Resultat',
        'z_score': 'Score Z',
        'reportable': 'Rapportable',
        'ref': 'Ref',
        'trisomy_21': 'Trisomie 21 (Syndrome de Down)',
        'trisomy_18': 'Trisomie 18 (Syndrome d\'Edwards)',
        'trisomy_13': 'Trisomie 13 (Syndrome de Patau)',
        'sca': 'Aneuploidie des chromosomes sexuels',
        'fetal_sex': 'Sexe foetal:',
        'male': 'Masculin',
        'female': 'Feminin',
        'undetermined': 'Indetermine',
        'cnv_findings': 'RESULTATS DES VARIATIONS DU NOMBRE DE COPIES (CNV)',
        'rat_findings': 'RESULTATS DES TRISOMIES AUTOSOMIQUES RARES (TAR)',
        'finding': 'Resultat',
        'clinical_significance': 'Signification clinique',
        'maternal_factors': 'FACTEURS MATERNELS ET RISQUE LIE A L\'AGE',
        'bmi_underweight': '(Insuffisance ponderale)',
        'bmi_normal': '(Normal)',
        'bmi_overweight': '(Surpoids)',
        'bmi_obese': '(Obesite - peut affecter la fraction foetale)',
        'age_risk_text': 'Selon l\'age maternel de {age} ans, les risques a priori sont: Trisomie 21: 1 sur {t21}, Trisomie 18: 1 sur {t18}, Trisomie 13: 1 sur {t13}',
        'final_interpretation': 'INTERPRETATION FINALE',
        'clinical_recommendations': 'RECOMMANDATIONS CLINIQUES',
        'no_high_risk': 'Aucun resultat a haut risque detecte. Poursuivre les soins prenataux standards.',
        'nipt_screening': 'Le DPNI est un test de depistage. Il ne diagnostique pas les anomalies chromosomiques.',
        'rec_t21_positive': 'Un test diagnostique de confirmation (amniocent&egrave;se ou biopsie de villosites choriales) est fortement recommande. Un conseil genetique devrait etre propose.',
        'rec_t18_positive': 'Un test diagnostique de confirmation (amniocent&egrave;se ou biopsie de villosites choriales) est fortement recommande. Une echographie detaillee et un conseil genetique sont conseilles.',
        'rec_t13_positive': 'Un test diagnostique de confirmation (amniocent&egrave;se ou biopsie de villosites choriales) est fortement recommande. Une echographie detaillee et un conseil genetique sont conseilles.',
        'rec_sca_positive': 'Conseil genetique recommande. Un test de confirmation peut etre envisage selon le jugement clinique.',
        'rec_cnv_positive': 'Echographie detaillee recommandee. Conseil genetique et eventuel test de confirmation conseilles.',
        'rec_rat_positive': 'Conseil genetique recommande. Correlation clinique et eventuel test de confirmation conseilles.',
        'rec_high_risk': 'Re-analyse recommandee. Si le resultat persiste, envisager un test diagnostique de confirmation.',
        'rec_low_risk': 'Aucun test supplementaire indique sur la seule base du resultat DPNI. Soins prenataux standards recommandes.',
        'clinical_notes': 'NOTES CLINIQUES ET OBSERVATIONS',
        'key_markers': 'Marqueurs cliniques cles:',
        'nt_noted': 'Clarte nucale notee',
        'ff_concerns': 'Preoccupations concernant la fraction foetale notees',
        'ivf_noted': 'Conception par PMA/FIV notee',
        'multiple_noted': 'Grossesse multiple notee',
        'limitations': 'LIMITES ET AVERTISSEMENT',
        'important_info': 'Informations importantes:',
        'disclaimer_1': 'Le DPNI est un test de depistage, pas un test diagnostique. Les resultats positifs doivent etre confirmes par un test diagnostique (amniocent&egrave;se ou biopsie de villosites choriales).',
        'disclaimer_2': 'Des faux positifs et faux negatifs peuvent survenir. Un resultat negatif n\'elimine pas la possibilite d\'anomalies chromosomiques.',
        'disclaimer_3': 'Ce test depiste des conditions chromosomiques specifiques et ne detecte pas tous les troubles genetiques.',
        'disclaimer_4': 'Les resultats doivent etre interpretes en conjonction avec d\'autres donnees cliniques, l\'echographie et l\'historique maternel.',
        'disclaimer_5': 'La performance du test peut etre affectee par des facteurs incluant: faible fraction foetale, anomalies chromosomiques maternelles, mosaicisme placentaire confine, jumeau evanescent ou malignite maternelle.',
        'disclaimer_6': 'Un conseil genetique est recommande pour toutes les patientes, en particulier celles avec des resultats positifs ou non concluants.',
        'authorization': 'AUTORISATION',
        'performed_by': 'Realise par:',
        'reviewed_by': 'Revise par:',
        'approved_by': 'Approuve par:',
        'date': 'Date:',
        'clinical_pathologist': 'Medecin responsable',
        'lab_director': 'Directeur du laboratoire',
        'lab_staff': 'Personnel du laboratoire',
        'report_generated': 'Rapport genere:',
        'version': 'NRIS v2.4 Edition Amelioree',
    }
}


def get_translation(key: str, lang: str = 'en') -> str:
    """Get translated text for a given key and language."""
    return TRANSLATIONS.get(lang, TRANSLATIONS['en']).get(key, TRANSLATIONS['en'].get(key, key))


def load_config() -> Dict:
    """Load configuration from file or return defaults."""
    try:
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    except Exception:
        return DEFAULT_CONFIG.copy()


def save_config(config: Dict) -> bool:
    """Save configuration to file."""
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=2)
        return True
    except Exception:
        return False
