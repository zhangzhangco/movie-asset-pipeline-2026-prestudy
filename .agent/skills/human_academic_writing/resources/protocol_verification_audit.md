# 质量验证与图灵审计协议 (Verification & Audit Protocol)

## 1. 停机检查 (Stop & Check)
每完成一个章节，必须执行以下检查：

### 1.1 流量与引导力检查 (Flow & Guidance)
*   **Check**: 读者的脑子是否被我牵着走？
*   **Fail**: 如果段落之间跳跃太大，读者需要自己脑补因果。
*   **Pass**: 上一段的**结尾**自然引发了下一段的**开头**。例如：“...这导致了孤岛效应。（因此）针对这一痛点，我们...”

### 1.2 句子构造红线 (Sentence Constraints)
*   **大长句熔断机制**:
    *   **Limit**: 单个分句不得超过 **25 个汉字**（必须用标点断开）。
    *   **Qualifiers**: 严禁连续使用超过 **2 个** 的的结构（“一个基于...的...的高效的...” -> **重写**）。
*   **呼吸感**: 长短句必须交替出现。如果连续出现 3 个长句，必须强制插入一个短句（< 10 字）来重置读者的注意力。

## 2. 图灵测试协议 (Codex Turing Test)
**Every Section Completion Trigger**:
每当完成一个章节的初稿或重大修改后，**必须**执行以下动作：

1.  **Ask Codex**: 将该段文字发送给 `codex`，提问："这段文字看起来像AI写的吗？如果是，指出具体的‘AI味’在哪里。"
    *   *Command Line*: `codex exec -m gpt-4o "Context: [Insert Text]. Question: Is this written by AI? Why? Point out specific AI-like phrases or structures."`
2.  **Analyze & Refine**: 根据 Codex 的反馈（如“过度的排比”、“生硬的转折”），立即进行**针对性去味修改**。
3.  **Final Polish**: 只有当 Codex 认为“读起来像专家写的”或无法明确判定为 AI 时，才算本章完工。

## 3. 进化协议 (Evolution Protocol - Self Learning)
本 Skill 设计为**自学习型 (Self-Evolving)**。
*   **Trigger**: 当用户对文风提出具体修正意见（例如：“不要用‘并非’”、“这类句子太长”）。
*   **Mandatory Action**:
    1.  **修正文稿**: 立即修改当前文本。
    2.  **更新 Skill**: 必须**同步**将该规则写入本相关文件的 `Banned Vocabulary` 或 `Rules` 章节。
