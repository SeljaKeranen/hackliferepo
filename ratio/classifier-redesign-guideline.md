# SweCRIS classifier redesign guideline

Redesign the public research-funding classification pipeline for the current SweCRIS dataset. The current dataset contains Swedish research grants only. Inspect its fields, coverage, collection filters, and existing classification code before proposing changes.

The goal is a reusable, human-validated method for estimating public research funding devoted to ageing, healthy longevity, and geroscience. Prioritise a small, testable framework for the Demo Day components covering architecture, evidence, success metrics, and limitations.

Apply the following methodological requirements directly.

1. Define the research question and funding measure.

   Distinguish broad ageing research, fundamental ageing biology, and interventions intended to modify ageing. Define their inclusion boundaries with examples.

   Report total funding for each agreed definition. Preserve the existing funding-gap ratio as a separate measure: fundamental ageing biology plus ageing interventions, divided by all classified ageing-related research funding.

   Choose a complete historical year supported by the SweCRIS data, such as 2023 or 2024 after checking completeness. Specify whether the estimate measures awards made that year or expenditure during that year. Document the handling of multi-year grants, renewals, duplicate records, missing amounts, and currency.

   Describe the estimate as covering the included SweCRIS records and funders. Establish database coverage before making claims about all Swedish government research spending.

2. Audit the current SweCRIS dataset.

   Check whether records contain full abstracts, titles only, or extracted quotations. Use full abstracts where available and retain the original Swedish or English text. Document any translations.

   Determine whether the dataset was collected through ageing-related keyword searches. If so, identify the resulting coverage limitation: relevant grants may exist outside the retrieved collection.

   Design a sampling route into the wider SweCRIS population, including records excluded by the current search. Until that population is available, report results as estimates within the collected dataset.

   Record source URLs, retrieval dates, licences, collection queries, and text versions.

3. Classify research aims and preserve overlap.

   Use an LLM to assess ageing relevance and cancer relevance independently. Allow a project to qualify for both. Cancer is a comparison category; define it consistently enough to support a later funding benchmark.

   For ageing-relevant grants, assign a primary research category when the aims support it. Preserve secondary categories where needed.

   Base decisions on the stated research question, aims, and intended outputs. Distinguish these from background mentions of ageing, funder names, and general motivation.

   Return supporting quotations, a concise decision reason, and an explicit indication of missing evidence.

4. Separate uncertainty from research category.

   Replace the single ambiguous bucket with reasons that distinguish insufficient text, unclear relevance, competing categories, and multidisciplinary scope.

   Store model uncertainty and human expert disagreement separately. An unresolved subtype must not automatically erase established ageing relevance.

   Define when each uncertainty state requires more source text, expert review, or special treatment in aggregation. Do not describe keyword scores or model confidence as calibrated probabilities without testing calibration.

5. Build a practical human-labeling workflow.

   Ageing-related grants may be rare in the wider database. Use a review sample covering grants the model considers likely, uncertain, and unlikely to concern ageing.

   Select records randomly within defined strata and record their selection probabilities. Include checks on grants with large funding amounts because a few mistakes could substantially change the estimate.

   Provide a quick interface showing the title and abstract, with ageing and cancer judgments, an insufficient-evidence option, and a short reason field. Hide model predictions during the initial human judgment.

   Have multiple human specialists independently label an overlapping sample. Preserve their individual judgments and disagreement before adjudication. Record whether each label came from a human, a model, or adjudication; model-generated “expert” labels are development material, not human ground truth.

6. Separate prompt development from final evaluation.

   Split records before refining prompts or thresholds. Use development data to improve the rubric and classifier. Keep a test set untouched until the pipeline is frozen, then conduct the final evaluation once.

   Keep duplicate records, related projects, and renewals in the same split. Treat previously inspected or mined records as development data.

   Specify acceptance criteria before opening the final test results. Report precision, recall, abstention, and funding-weighted errors. Account for unequal sampling probabilities when estimating population performance.

7. Aggregate funding with explicit uncertainty.

   Use the human-reviewed sample to assess wrongly included and missed funding. Explain how these errors affect the total estimate.

   Separate sampling uncertainty, classification error, expert disagreement, and sensitivity to the definition of ageing research. Expert disagreement should inform the reported uncertainty, but does not by itself capture every source of error.

   Report unresolved funding and its possible effect on each measure. Label sensitivity ranges separately from statistical confidence intervals.

8. Design a valid cancer-funding comparison.

   Identify whether a published cancer-research funding estimate matches the Swedish jurisdiction, funders, period, and accounting basis covered by the dataset.

   If a comparable estimate exists, use it as an external cross-check. Explain discrepancies rather than adjusting the classifier to reproduce the benchmark.

   A UK cancer-funding estimate cannot directly validate a Swedish funding total. If no comparable Swedish benchmark is available, mark this validation step as pending. Agreement on cancer funding also does not independently establish accuracy for ageing research.

9. Deliver a minimal migration proposal.

   Provide the revised rubric, output schema, classifier prompt, human-review workflow, sampling plan, evaluation protocol, and implementation sequence.

   The immediate deliverable is a working analytical framework: SweCRIS ingestion and cleaning, initial classification, expert labeling, prompt evaluation, and funding aggregation. Applying it at scale depends on meeting the predefined validation criteria.

   Identify reusable components and preserve the independence of the existing map and standalone eval workflow. State what works with verification evidence, which examples are fixtures or simulations, and what remains incomplete. Do not present funding estimates as validated before human review and final evaluation are complete.
