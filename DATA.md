# Data and licenses

## Common Paper Mutual NDA Standard Terms v1.0

- Source: https://commonpaper.com/standards/mutual-nda/1.0 (text taken from
  https://github.com/CommonPaper/Mutual-NDA, file Mutual-NDA.md)
- License: CC BY 4.0, https://creativecommons.org/licenses/by/4.0/
- Used in: fixtures/source/common_paper_mnda_v1.md, fixtures/common_paper_nda.docx,
  fixtures/counterparty_nda.docx, and the preferred positions and suggested text in playbooks/nda.yaml.
- Changes:
  - HTML span tags around cover page terms removed from the Standard Terms.
  - The cover page is shortened and reworded; its values (purpose, dates, terms, governing law,
    jurisdiction) are filled in by scripts/make_fixtures.py. No party names are used.
  - The cover page introduction says the Standard Terms are based on the Common Paper version,
    since the counterparty variant changes them.
  - fixtures/counterparty_nda.docx applies the deviations listed in fixtures/DEVIATIONS.md.
  - Playbook suggested text paraphrases or shortens the Standard Terms.
