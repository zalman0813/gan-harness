# Agent & Skill design — gan-harness SSoT

> 定稿。取代先前把 conventions 當 skill 的版本。三條 placement rule 是核心;其餘都是推論。

---

## 三條 placement rule(核心)

決定「一段內容該放哪」只看兩個軸:**每輪都要 vs 條件觸發** × **單一 agent vs 跨 agent**。

1. **Rule 1 — skill 只配 conditional 或 shared。**
   一段領域知識獨立成 skill,當且僅當它 **conditional**(不是每輪都載 → 真省 JIT)**或 shared**(≥2 個 agent 用 → 真省 DRY)。兩者都不滿足 = 不該是 skill。

2. **Rule 2 — 每輪必守的行為規則 → CLAUDE.md。**
   守門/反作弊規則放在「要先 load 的 skill」裡是自相矛盾的:載入那步本身會被跳過,正是 drift。CLAUDE.md **自動注入每個 subagent、無法跳過**,是這類內容唯一正確的家。

3. **Rule 3 — 每輪必跑的單一 agent 程序 → inline 在該 agent。**
   單一 agent、每輪都要的程序(stack discovery、契約檢查、輸出 schema、next_action 判定),inline 進 agent 用密集條列。拆到第二個檔只多一個腐爛面、零 JIT 收益。

> 三條合起來:**skill 留給 conditional|shared 的領域知識;行為規則進 CLAUDE.md;每輪單一-agent 程序 inline。**

---

## 內容歸位表

| 內容 | 去處 | 依據 |
|---|---|---|
| Behavioral foundation、anti-cheat、skill-loading rule、write-boundaries、output 契約 | **CLAUDE.md「Harness operating rules」** | Rule 2 |
| Stack discovery | **inline**(generator + evaluator) | Rule 3 |
| Mode 程序、契約 8-checks、門檻、JSON/YAML schema、next_action 判定 | **inline**(各自的 agent) | Rule 3 |
| Archetype 4-criteria 模板 | **inline**(planner) | Rule 3(單一-agent) |
| `deep-module-handbook` | **skill** | Rule 1(shared gen+eval + conditional) |
| `adr-lifecycle` | **skill** | Rule 1(conditional — 多數輪不碰 ADR) |
| stack skills | **skill** | Rule 1(conditional + shared) |
| pattern skills | **skill** | Rule 1(conditional) |
| `generator/planner/evaluator-handbook` | **刪除 → 折回 agent** | 違反 Rule 1(單一-agent + 每輪) |
| `harness-conventions` | **刪除 → CLAUDE.md** | Rule 2 |

---

## Thin agent 骨架(無 Load First)

```markdown
---
name: <agent>
description: |
  <一句角色 + 何時用 + modes>。
  Examples: <2 個 routing 範例,各帶 <commentary> 說明為何選這個 agent>
tools: <least-privilege>
model: <opus|sonnet>
skills: [<只列 conditional/shared 的 skill — 常常是空的>]
---

<identity:一段。你是誰、你擁有什麼、你不擁有什麼、fresh-context 提醒。>

## Stack discovery (僅跑 gate 的 agent 需要 — generator/evaluator)
<~2 行 inline。其餘共用規則在 CLAUDE.md。>

## Your Skills (conditional/shared — Skill tool 觸發時載)
- **<Key>:** `<skill>` — when <條件>

## Two Modes (spawn prompt picks)
### Mode 1 — <NAME> (/loop Phase N)
**Read (locked order):** … → …
**Produce / Procedure:** …
**Rules / checks:** …
**Return:** `<status> <key=value…>`
### Mode 2 — …

## Principles
<- 該 agent 專屬的行為斷言。無外來 package 名、無門檻數字(門檻在 Mode rules)。>

## Boundaries
<- 角色獨有。共用的(spec.md/contracts.jsonl/traces/sibling/git-hooks)在 CLAUDE.md。>
```

**不重述** behavioral foundation、skill-loading、output 一行契約、write-boundaries —— 那些在 CLAUDE.md,自動在 context 裡。
目標長度:planner 71 / generator 77 / evaluator 83 行(原 454 / 337 / 495)。

---

## Output 契約:status token + key=value

parent 自己決定 spawn 哪個 mode,所以**不要 echo mode**。一行 = `<status> <key=value…>`:
- status token 給 parent 分支:`done` / `blocked` / `escalate`。
- key 命名**產物**,不是階段:`draft=…` / `commit=<sha>` / `verdict=<v>` / `eval=…` / `gate=<stage>`。

例:`done verdict=FAIL contract=F standards=P next_action=restart_sprint eval=_evals/S01-R2.json`

---

## Skill 分類學 + 誰建立

| skill 類型 | 內容 | 建立者 | 形狀 |
|---|---|---|---|
| **handbook**(approach) | 跨切方法論(deep-module、TDD、hexagonal) | `approach-handbook-creator` | 概念為主,agent 經 `skills:` 載 |
| **stack skill** | 一個 stack 的版本錨點 + gate `## Commands` | `stack-skill-creator` | 輕量單檔:Version + highlights + Commands + Conventions |
| **pattern skill** | 一個 POC 出來的具體做法 | `pattern-skill-creator` | GodotPrompter 形:`Use when … — … NOT …` + approach 表 + verbatim code + gotchas |

三者都 **不互連**(無 `## Related skills`)。

---

## Skill 之間的關係:在 agent wire,不在 skill 互連

skill 不自我宣告關係。哪些 skill 相關、何時載,由 developer 寫在 **agent 的 `## Your Skills`** 索引。好處:關係集中可見、skill 自包含可移植、少一個腐爛面(skill 改名不必去 N 個 skill 改連結)。

---

## CLAUDE.md「Harness operating rules」(取代 harness-conventions skill)

進到 **agent 實際 run 的 CLAUDE.md**(target 的;gan-harness 自己的 CLAUDE.md 是 maintainer-only,不複製)。自動注入每個 subagent → 無法跳過。內容見 `_analysis/claude-md-harness-rules.md`:Behavioral foundation / Skill-loading rule / Write-boundaries / Output 契約 / Anti-cheat 表。

⚠ **待 wire**:gan-harness CLAUDE.md 不複製到 target → 這個 block 要由 setup 步驟注入 target 的 CLAUDE.md。注入點待確認(`templates/` 目前空)。

---

## 這套設計刪了什麼

- `harness-conventions` skill —— 從未建,內容進 CLAUDE.md。
- `generator-handbook` / `planner-handbook` / `evaluator-handbook` —— 折回各自 agent(單一-agent 每輪,不該是 skill)。
- 每個 agent 的 `## Load First` —— 不需要(conventions 自動在 context)。
- stack skill 的 web-vendoring doc 庫 + `## Related skills` —— 見 `stack-skill-creator.redesign.md`。

保留為 skill:`deep-module-handbook`、`adr-lifecycle`、stack skills、pattern skills、三個 `*-creator`(都 conditional)。
