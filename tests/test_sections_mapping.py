from paperslicer.utils.sections_mapping import canonical_section_name, NON_CONTENT_KEYS


def test_common_synonyms_map_to_methods():
    assert canonical_section_name("Statistical analysis") == "materials_and_methods"
    assert canonical_section_name("Sample Preparation") == "materials_and_methods"
    assert canonical_section_name("Eligibility Criteria") == "materials_and_methods"
    assert canonical_section_name("Inclusion and Exclusion Criteria") == "materials_and_methods"


def test_intro_discussion_conclusions_mappings():
    assert canonical_section_name("Background") == "introduction"
    assert canonical_section_name("Limitations") == "discussion"
    assert canonical_section_name("Clinical Significance") == "conclusions"


def test_non_content_remains_flagged():
    assert canonical_section_name("Funding") in NON_CONTENT_KEYS
    assert canonical_section_name("Acknowledgements") in NON_CONTENT_KEYS


def test_specific_titles_do_not_become_canonical():
    # Specific, idiosyncratic titles should fall back to normalized tokens
    s = canonical_section_name("Epidemiology of benign oesophageal strictures")
    assert s not in {"introduction", "materials_and_methods", "results", "discussion", "conclusions", "results_and_discussion"}


def test_added_review_and_clinical_synonyms():
    assert canonical_section_name("Risk of Bias Assessment") == "materials_and_methods"
    assert canonical_section_name("Search Strategy") == "materials_and_methods"
    assert canonical_section_name("Study Selection") == "materials_and_methods"
    assert canonical_section_name("Data Extraction") == "materials_and_methods"
    assert canonical_section_name("Preoperative Examination") == "materials_and_methods"
    assert canonical_section_name("INDICATIONS") == "materials_and_methods"
    assert canonical_section_name("CONTRAINDICATIONS") == "materials_and_methods"
    assert canonical_section_name("Radiographic Analyses") == "materials_and_methods"
    assert canonical_section_name("| Clinical Examinations") == "materials_and_methods"
    assert canonical_section_name("Outcome Measures") == "materials_and_methods"
    assert canonical_section_name("Randomization and Blinding") == "materials_and_methods"
    assert canonical_section_name("Design") == "materials_and_methods"
    assert canonical_section_name("Sample and Setting") == "materials_and_methods"
    assert canonical_section_name("Protocol and Registration") == "materials_and_methods"
    assert canonical_section_name("Data Charting and Synthesis") == "materials_and_methods"
    assert canonical_section_name("In Vivo Studies") == "materials_and_methods"
    assert canonical_section_name("Medical preparations") == "materials_and_methods"
    assert canonical_section_name("Patient preparation") == "materials_and_methods"
    assert canonical_section_name("Surgical area preparation") == "materials_and_methods"
    assert canonical_section_name("SURGICAL PROCEDURES") == "materials_and_methods"
    assert canonical_section_name("Research Question") == "introduction"
    assert canonical_section_name("Current Medical Therapy") == "introduction"
    assert canonical_section_name("Interpretation of Key Findings") == "discussion"
    assert canonical_section_name("Agreements and Disagreements with Other Studies or Reviews") == "discussion"
    assert canonical_section_name("Clinical Management") == "discussion"
    assert canonical_section_name("Grading the Certainty of Evidence") == "discussion"
    assert canonical_section_name("Certainty of Evidence") == "discussion"
    assert canonical_section_name("Summary of Key Findings") == "conclusions"
    assert canonical_section_name("Summary of Main Findings") == "conclusions"
    assert canonical_section_name("Possible Applications of Research and Future Research Directions") == "conclusions"
    assert canonical_section_name("Clinical Considerations and Practical Recommendations") == "conclusions"
