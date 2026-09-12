"""Conservative, unvalidated four-label adapter around PR #15's rules.

The existing lexicon remains a candidate generator. Explicit aim passages
control the new category. This is a baseline for human review, not evidence
of classifier accuracy. It consumes all text in the frozen corpus.
"""
import hashlib
import json
import re
from pathlib import Path

from ratio import classify as legacy

HERE = Path(__file__).resolve().parent
TAXONOMY = json.loads((HERE / 'taxonomy.json').read_text())
VERSION = TAXONOMY['version']
LABELS = tuple(item['id'] for item in TAXONOMY['labels'])
LEGACY_MAP = {'fundamental_aging': 'preventing_slowing', 'intervention': 'preventing_slowing',
              'age_related_disease': 'consequences', 'care': 'consequences',
              'social_population_aging': 'consequences', 'not_relevant': 'neither',
              'ambiguous': 'ambiguous'}
AIM = re.compile(r'\b(aim\w*|objective\w*|we (?:will|propose|seek|study|investigate|test)|'
                 r'our (?:goal|project|study)|this (?:project|study|proposal) (?:will|aims|investigates)|'
                 r'syft\w*|målet|mål med|vi (?:ska|kommer|undersöker|studerar))\b', re.I)
BIO_AGE = re.compile(r'\b(geroscien\w*|geroprotec\w*|inflammaging|'
                     r'(?:biolog\w*|cellular|molecular|epigenetic) ag(?:e)?ing|'
                     r'ag(?:e)?ing (?:biolog\w*|mechanism\w*|process\w*|pathway\w*)|'
                     r'mechanisms? (?:of|underlying|driving) (?:\w+ ){0,3}ag(?:e)?ing|'
                     r'(?:slow\w*|revers\w*|delay\w*|prevent\w*|modif\w*) (?:\w+ ){0,2}ag(?:e)?ing|'
                     r'(?:extend\w*|increas\w*|regulat\w*) (?:\w+ ){0,2}(?:lifespan|healthspan)|'
                     r'biologiskt åldrande|åldrandets (?:biologi|mekanismer)|'
                     r'(?:bromsa|fördröja) åldrand\w*|gerovetenskap)\b', re.I)
AGE = re.compile(r'\b(ag(?:e)?ing|age[- ]related|older (?:adults?|people|patients?)|elderly|'
                 r'late life|later life|old age|geriatric\w*|åldr\w*|äldre|åldersrelater\w*)\b', re.I)
CONSEQUENCE = re.compile(r'\b(dementia|alzheimer\w*|cancer|diabet\w*|cardiovascular|'
                         r'frailty|disabilit\w*|caregiv\w*|care|retirement|pension\w*|'
                         r'loneliness|social isolation|cognitive decline|functional decline|'
                         r'social|disease\w*|demens\w*|omsorg\w*|sjukdom\w*|ensamhet)\b', re.I)
NONBIO = re.compile(r'\b(batter(?:y|ies)|electrolyte\w*|electrode\w*|polymer\w*|'
                    r'supercapacitor\w*|bridge\w*|semiconductor\w*|leaf senescence|'
                    r'forestry|livestock|batteri\w*|elektrod\w*|korrosion|träds? livslängd)\b', re.I)
NEGATED = re.compile(r'\b(not|no|without|neither|inte|ej)\b', re.I)


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                     separators=(',', ':')).encode()).hexdigest()


def source_version(record):
    return digest({k: record.get(k) for k in ('record_id', 'source', 'title', 'abstract',
                                             'url', 'retrieved_at', 'year')})


def aim_passages(title, abstract):
    # Title plus complete sentences containing aims; never truncate the abstract.
    sentences = re.split(r'(?<=[.!?])\s+|\n\s*\n', abstract or '')
    return [title] + [s for s in sentences if AIM.search(s)]


def classify(record, ruleset=None):
    title, abstract = record.get('title') or '', record.get('abstract') or ''
    candidate = legacy.classify(title, abstract, ruleset or legacy.load_ruleset())
    passages = [p for p in aim_passages(title, abstract) if p.strip()]
    aims = '\n'.join(passages)
    slow = [p for p in passages if BIO_AGE.search(p)]
    consequences = [p for p in passages if AGE.search(p) and CONSEQUENCE.search(p)]
    engineering = [p for p in passages if NONBIO.search(p)]
    flags = []
    if not abstract.strip():
        flags.append('missing_abstract')
    if len(abstract) >= 6000:
        flags.append('collection_text_may_be_truncated')
    if not any(AIM.search(p) for p in passages):
        flags.append('no_explicit_aim_sentence')
    label, why, evidence = 'ambiguous', 'The stated aims need human interpretation.', []
    if not abstract.strip():
        why = 'No abstract is available; title-only classification is insufficient.'
    elif slow and engineering:
        why, evidence = 'Biological and non-biological aims overlap; review their relationship.', slow + engineering
    elif slow and consequences:
        why, evidence = 'Ageing biology and its consequences both appear in the aims; review the primary purpose.', slow + consequences
    elif slow:
        label, why, evidence = 'preventing_slowing', 'An aim passage explicitly addresses biological ageing or modifying ageing.', slow
    elif consequences:
        label, why, evidence = 'consequences', 'An aim passage links disease, care or social outcomes to ageing.', consequences
    elif engineering:
        label, why, evidence = 'neither', 'The stated purpose concerns material or non-biomedical ageing.', engineering
    elif candidate['label'] != 'ambiguous':
        why = 'Legacy keywords suggest a category, but do not establish the purpose under the new rubric.'
        flags.append('keyword_candidate_only')
    else:
        flags.append('unclear_aim')
    if any(NEGATED.search(p) for p in evidence):
        label, why = 'ambiguous', 'Negation appears in the candidate evidence; inspect its scope before assigning a category.'
        flags.append('negation_requires_review')
    evidence = list(dict.fromkeys(evidence))
    return {'record_id': record['record_id'], 'label': label,
            'low_confidence': bool(flags), 'uncertainty_reasons': flags,
            'reason': why, 'evidence': evidence, 'label_origin': 'rule',
            'human_verified': False, 'taxonomy_version': VERSION,
            'source_version': source_version(record),
            'legacy_candidate': candidate['label'],
            'legacy_reason': candidate['reason']}
