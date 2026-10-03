# GitHub 仓库发布清单

本文档说明哪些文件应进入公开仓库、哪些文件只留在内部工作区。原则是：
公开论文结论所需的最小完整证据链，同时不上传缓存、备份、凭据形态文本、
投稿材料或无再分发必要的第三方内容。

## 上传边界

公开 GitHub 仓库的根目录应当是当前内部工作区的 `github_release/` 目录内容，
而不是整个 `llm_inference_engine_bugs/` 工作区。换言之，上传时应看到
`README.md`、`data/`、`paper/`、`reports/`、`results/` 和 `scripts/` 直接位于 GitHub
仓库根目录；不要把外层内部研究目录一并上传，也不要在 GitHub 根目录中
再套一层 `github_release/`。

## 应放入仓库

| 类别 | 路径 | 用途 |
| --- | --- | --- |
| 入口文档 | `README.md` | 研究简介、快速验证、各 RQ 复现命令 |
| 发布边界 | `REPOSITORY_CONTENTS.md` | 纳入/排除规则与发布前检查 |
| 引用信息 | `CITATION.cff` | GitHub 的 Cite this repository 元数据 |
| 环境 | `requirements.txt` | 离线复现所需 Python 依赖 |
| 分析语料 | `data/final_bug_results_with_root_cause_completed_symptom.json` | 12,707 条公开分析字段；已删除 description/LLM reasoning |
| 时间戳 | `data/bug_timestamps.json` | 12,707 个 fixing PR 的创建时间 |
| 修复操作 | `data/final_bug_results_with_root_cause_completed_symptom_fixed_merged_fix_pattern.json` | 12,707 条 repair-operation 标注的公开字段 |
| 派生数据 | `data/pareto/`、`data/bug_function_*`、`data/fix_size_stats.json`、`data/monthly_file_bucket_counts.json` | 复现文件/函数集中度和 file-breadth 图 |
| 报告 | `reports/` | 从 12,707 条正式语料重新生成的 RQ1--RQ3 人类可读报告 |
| 结果 | `results/` | RQ1/RQ2/RQ3 机器可读摘要、计数、JSON、CSV 与完整精度统计 |
| 脚本 | `scripts/` | 数据校验、RQ1/RQ2/RQ3 图表与统计复现 |
| 正式论文 | `paper/` | `main.tex`、被引用 sections/tables/figures、BibTeX 和最终 PDF |

## 不应放入仓库

| 内部路径/类型 | 原因 | 建议去向 |
| --- | --- | --- |
| `.venv/`、`__pycache__/` | 本机环境和缓存 | 本地保留，按 requirements 重建 |
| `cache/` | LLM/API 运行缓存，非论文输入 | 内部归档 |
| `.tmp_doc_check/cover-letter.docx` | 投稿信，可能含作者/投稿元数据 | 私有投稿目录 |
| `data/bug_diffs.json`、`data/filtered_bugs_with_diffs.json` | 278 MiB/92 MiB；完整上游代码 diff，含再分发与敏感文本风险 | 私有归档或受控数据存储 |
| `data/data_supplement/` | 12,961 条旧口径及历史增量，不是论文 12,707 条 canonical corpus | 私有历史归档 |
| `*.backup_before_*`、`*.bak`、`*.old` | 备份，不是权威版本，且有超大文件 | 私有归档 |
| `paper_drafts/`、`paper.tex`、`related_work_condensed.tex` | 旧草稿/预览，不是正式主稿 | 私有历史归档 |
| `TSE_Inference_Bug_Study/ref/` | 第三方论文和另一投稿 PDF，存在版权/保密风险 | 只保留文献链接或 BibTeX |
| LaTeX `*.aux/*.log/*.fls/*.fdb_latexmk/*.blg/*.bbl` | 编译中间件 | 由本地编译重新生成 |
| `tmp/`、生成预览 PDF/PNG | 中间生成物和旧视觉方案 | 私有历史归档 |
| `paperwriting.md` | 包含内部交接、投稿风险和本机绝对路径 | 私有项目管理文档 |
| `key.txt`、`githubtoken.txt`、`.env*` | 凭据 | 永不进入版本控制 |

## 当前发布目录的安全处理

- 只导出 12,707 条正式 merged/fixed/bug-related PR。
- 删除 free-text PR description 与 LLM reasoning；这些字段不参与论文统计。
- 对保留字段再次扫描并替换 `sk-...` 形态字符串。
- 不包含完整 PR diff；文件/函数集中度通过派生权重数据复现。
- 不包含第三方 PDF、cover letter、缓存、日志和备份。
- 所有发布文件由 `SHA256SUMS` 固定校验。

## 公开前仍需作者决定

1. 为代码选择许可证（如 MIT/Apache-2.0）。
2. 为数据选择许可证并确认 GitHub PR 元数据的再分发口径。
3. 确认是否公开尚未正式发表的 `paper/main.pdf`。
4. 论文录用后补充 DOI、venue、year 和正式 BibTeX。
5. 若仓库地址发生变化，同步更新论文 Artifact 链接和 `CITATION.cff`。
