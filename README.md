# Emerald Shore Initiative · Postgraduate Entrance Exam Sprint Coach

Emerald Shore Initiative is an open-source Agent Skill for university students in the final one to four months before China's postgraduate entrance examination. It turns dates, subject and topic gaps, owned materials, source-grounded questions, mistakes, and timed checkpoints into a local, evidence-driven sprint loop.

The loop is simple: investigate the current state, identify one principal bottleneck, concentrate effort, test through retrieval or timed work, and replan from observed results.

## Highlights

- Subject-agnostic coaching across memory, understanding, calculation, writing, language, and timed-output tasks.
- Topic-level score maps driven by exam weight, demonstrated mastery, evidence confidence, errors, and estimated effort.
- Local JSON state, daily plans, mistake ledger, review queue, and Markdown dashboard.
- Local extraction for PDF, DOCX, PPTX, text, Markdown, and HTML; PDF text extraction uses optional `pypdf`.
- Subject-bound source drills that reveal one question at a time and record attempts without leaking answers.
- Weekly self-regulated learning reviews and concrete if–then start plans.
- Source levels that keep official scope, past papers, user materials, and explanation aids distinct.
- No score guarantee, prediction claim, telemetry, cloud requirement, or automatic upload.

## Quick start

```bash
python emerald.py init ~/postgraduate-exam --exam-date 2026-12-20 --daily-hours 6
python emerald.py subject add ~/postgraduate-exam --name Mathematics --max-score 150 --baseline 70 --target 110 --kind calculation
python emerald.py topic add ~/postgraduate-exam --subject Mathematics --name Calculus --weight 3 --mastery 0.35 --confidence 0.7
python emerald.py plan ~/postgraduate-exam
python emerald.py today ~/postgraduate-exam
```

Requires Python 3.9+. See [README.zh-CN.md](README.zh-CN.md) for the primary Chinese guide.

V0.1 workspaces can be copied safely from `.qingan/` to schema 2 with `python emerald.py migrate WORKSPACE`; the legacy directory is preserved.

## License

MIT. See `THIRD_PARTY_NOTICES.md` and `docs/SOURCE_AUDIT.md` for provenance.
