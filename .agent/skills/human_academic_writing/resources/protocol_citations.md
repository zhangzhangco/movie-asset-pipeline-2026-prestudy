# 学术引用规范 (Academic Citation Protocol)

## 核心原则
所有关键论点、数据引用、标准引用，必须落地有声，有据可查。

## 1. 引用插入规范 (Inline Citation)
*   **Trigger**: 当你在正文中提及任何外部理论、标准、数据或观点时。
*   **Action**: 在句末或关键词后插入上标形式的引用序号，格式为 `[^n]`。
    *   *Example*: "这一理念与 MovieLabs 2030 Vision 的资产中心化工作流不谋而合[^1]。"

## 2. 参考文献库管理 (Reference Management)
*   **File Path**: 必须并在项目根目录或 `docs/` 下维护一个 `references.md` 文件。
*   **Format**: 严格遵循 **GB/T 7714-2015** 《信息与文献 参考文献著录规则》。
    *   *Journal*: [序号] 作者. 文章题目[J]. 期刊名, 出版年, 卷(期): 起止页码.
    *   *Standard*: [序号] 标准编号, 标准名称[S]. 出版地: 出版者, 出版年.
    *   *Electronic*: [序号] 作者. 电子文献题名[EB/OL]. (发表或更新日期)[引用日期]. 获取和访问路径.
*   **Example**:
    ```markdown
    # 参考文献 (References)
    
    [1] MovieLabs. The 2030 Vision: The Future of Media Creation[EB/OL]. (2019-08-08)[2024-06-15]. https://movielabs.com/production-technology/2030-vision/.
    [2] GB/T 36369-2018, 电影数字拷贝 存档元数据[S]. 北京: 中国标准出版社, 2018.
    ```

## 3. 证据留存 (Evidence Archiving) - “核实并保存”
*   **Requirement**: 所有的引用来源必须经过人工或 Codex 核实，确保真实存在。
*   **Archiving**: 如果引用来源是网络公开资源（如 PDF 报告、网页文章）：
    1.  **Download/Save**: 必须尝试将其内容保存到本地目录：`docs/references_archive/`。
    2.  **Naming**: 文件名格式为 `ref_[序号]_[简短标题].ext`（如 `ref_1_MovieLabs_2030_Vision.pdf` 或 `ref_1_MovieLabs_2030_Vision.md`）。
    3.  **Rationale**: 防止链接失效（Link Rot），确保“行政总工”引用的每一句话都有永久的物理证据。
