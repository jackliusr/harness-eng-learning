# Research Papers Mentioned in Build The Loop

Source: https://buildtheloop.dev/

**Total: 9 research papers**

## 1. Coding Agent Architecture and Project Context

### 1.1 Dive into Claude Code: The Design Space of Today's and Future AI Agent Systems
- **Year:** 2026
- **Paper:** https://arxiv.org/abs/2604.14228
- **Topics:** Coding agent architecture, harness design, permissions, context compaction, skills, hooks, and subagents.
- **Referenced in:** [Project Context Is A Tool](https://buildtheloop.dev/posts/project-context-is-a-tool)

### 1.2 Evaluating AGENTS.md: Are Repository-Level Context Files Helpful for Coding Agents?
- **Year:** 2026
- **Paper:** https://arxiv.org/abs/2602.11988
- **Topics:** Repository instructions, AGENTS.md, agent performance, token costs.
- **Key finding:** Repository instruction files do not consistently improve agent performance and can increase costs.
- **Referenced in:** [Project Context Is A Tool](https://buildtheloop.dev/posts/project-context-is-a-tool)

## 2. Context Management and Compression

### 2.1 Active Context Compression: Autonomous Memory Management in LLM Agents
- **Year:** 2026
- **Paper:** https://arxiv.org/abs/2601.07190
- **Topics:** Context compression, autonomous memory management, long-running agents.
- **Referenced in:** [Context Management Is Compression](https://buildtheloop.dev/posts/context-management-is-compression)

### 2.2 Lost in the Middle: How Language Models Use Long Contexts
- **Year:** 2023
- **Paper:** https://arxiv.org/abs/2307.03172
- **Topics:** Long-context retrieval, positional bias, context utilization.
- **Key finding:** Language models often struggle to use information located in the middle of long contexts.
- **Referenced in:** [Context Management Is Compression](https://buildtheloop.dev/posts/context-management-is-compression)

### 2.3 Governance Decay: How Context Compaction Silently Erases Safety Constraints in Long-Horizon LLM Agents
- **Year:** 2026
- **Paper:** https://arxiv.org/abs/2606.22528
- **Topics:** Context compaction, safety constraints, governance decay, long-horizon agents.
- **Key finding:** Context compaction may remove important safety and governance constraints during long-running agent execution.
- **Referenced in:** [Context Management Is Compression](https://buildtheloop.dev/posts/context-management-is-compression)

## 3. Agent Memory

### 3.1 MemGPT: Towards LLMs as Operating Systems
- **Year:** 2023
- **Paper:** https://arxiv.org/abs/2310.08560
- **Topics:** Hierarchical memory, external memory, virtual context management, persistent agents.
- **Referenced in:** [Memory Is External State](https://buildtheloop.dev/posts/memory-is-external-state)

### 3.2 The Algorithmic Self-Portrait: Deconstructing Memory in ChatGPT
- **Year:** 2026
- **Paper:** https://arxiv.org/abs/2602.01450
- **Topics:** AI memory, personalization, privacy, memory accuracy, user control.
- **Referenced in:** [Memory Is External State](https://buildtheloop.dev/posts/memory-is-external-state)

## 4. Agent Evaluation

### 4.1 Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena
- **Year:** 2023
- **Paper:** https://arxiv.org/abs/2306.05685
- **Topics:** LLM-as-a-judge, automated evaluation, human preference alignment, evaluation biases.
- **Referenced in:** [Evals Measure Agent Behavior](https://buildtheloop.dev/posts/evals-measure-agent-behavior)

### 4.2 General Agent Evaluation
- **Year:** 2026
- **Paper:** https://arxiv.org/abs/2602.22953
- **Topics:** Agent evaluation, tool calling, MCP, CLI-based agents, architecture comparison.
- **Referenced in:** [Evals Measure Agent Behavior](https://buildtheloop.dev/posts/evals-measure-agent-behavior)

---

## 5. Recommended Reading Order for Harness Engineering

| Priority | Paper | Focus |
|---|---|---|
| 1 | Dive into Claude Code | Agent architecture and harness design |
| 2 | General Agent Evaluation | Agent architecture and performance evaluation |
| 3 | Evaluating AGENTS.md | Project instructions and context effectiveness |
| 4 | Active Context Compression | Long-running agent context management |
| 5 | Governance Decay | Safety constraints during compaction |
| 6 | MemGPT | Persistent memory architecture |
| 7 | Lost in the Middle | Long-context limitations |
| 8 | Judging LLM-as-a-Judge | Evaluation methodology |
| 9 | The Algorithmic Self-Portrait | Memory, personalization, and privacy |

## 6. Key Research Themes

1. **Agent Harness Architecture**
   - Tool orchestration
   - Permission boundaries
   - Skills and hooks
   - Subagent coordination

2. **Context Engineering**
   - Repository-level instructions
   - Context window utilization
   - Autonomous compression
   - Safety constraint preservation

3. **Memory Engineering**
   - Short-term versus long-term memory
   - External persistent state
   - Hierarchical memory management

4. **Agent Evaluation**
   - Task completion and correctness
   - Tool-use behavior
   - LLM-as-a-judge
   - Architecture benchmarking
