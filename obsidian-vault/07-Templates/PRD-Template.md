---
tags: [prd, swarm-generated]
date: <% tp.date.now("YYYY-MM-DD") %>
time: <% tp.date.now("HH:mm") %>
status: draft
---

# <% tp.file.title %>

## 1. Overview
**Agent**: `<% tp.frontmatter.agent || "s3_prd" %>`  
**Date**: <% tp.date.now("YYYY-MM-DD HH:mm") %>  
**Status**: <% tp.frontmatter.status %>

## 2. Problem Statement
> What pain does this solve?

## 3. Goals & Non-Goals
| Goals | Non-Goals |
|-------|-----------|
|       |           |

## 4. User Stories
- As a **user**, I want **X** so that **Y**.

## 5. Acceptance Criteria
- [ ] Criterion 1
- [ ] Criterion 2

## 6. Technical Notes
```dataview
TABLE file.name as "Related", file.mtime as "Modified"
FROM #architecture OR #backend
WHERE contains(file.outlinks, this.file.link)
```

## 7. Open Questions
[ ] Question 1

## 8. Swarm Sign-Off

| Agent        | Status                      | Notes             |
| ------------ | --------------------------- | ----------------- |
| s3_prd       | <% tp.frontmatter.status %> | Initial draft     |
| x1_review    | pending                     | Structural review |
| x2_security  | pending                     | Security audit    |

---
