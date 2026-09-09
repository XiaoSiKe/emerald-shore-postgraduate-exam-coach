# Qingan Kaoyan Sprint Coach

Qingan is an open-source Agent Skill for university students in the final one to four months before China's postgraduate entrance exam. It turns dates, subject score gaps, owned materials, mistakes, and timed checkpoints into a local, evidence-driven sprint loop.

The loop is simple: investigate the current state, identify one principal bottleneck, concentrate effort, test through retrieval or timed work, and replan from observed results.

## Highlights

- Subject-agnostic coaching across memory, understanding, calculation, writing, language, and timed-output tasks.
- Local JSON state, daily plans, mistake ledger, review queue, and Markdown dashboard.
- Local extraction for PDF, DOCX, PPTX, text, Markdown, and HTML; PDF text extraction uses optional `pypdf`.
- Source levels that keep official scope, past papers, user materials, and explanation aids distinct.
- No score guarantee, prediction claim, telemetry, cloud requirement, or automatic upload.

## Quick start

```bash
python qingan.py init ~/kaoyan --exam-date 2026-12-20 --daily-hours 6
python qingan.py subject add ~/kaoyan --name Mathematics --max-score 150 --baseline 70 --target 110 --kind calculation
python qingan.py plan ~/kaoyan
python qingan.py today ~/kaoyan
```

Requires Python 3.9+. See [README.zh-CN.md](README.zh-CN.md) for the primary Chinese guide.

## License

MIT. See `THIRD_PARTY_NOTICES.md` and `docs/SOURCE_AUDIT.md` for provenance.
