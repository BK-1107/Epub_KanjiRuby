# Japanese EPUB Kanji Ruby Annotator (日文 EPUB 汉字自动注音工具)

这是一个专门为日文 EPUB 电子书设计的汉字自动注音（Furigana / 振假名）工具。它能够自动解析 EPUB 书籍中的日文文本，精确提取汉字并添加标准的 HTML5 `<ruby>` 注音标签。同时，它还内置了针对主流电子书阅读器（如微信读书、Kobo 等）的横竖排版自适应优化样式。

---

## 🌟 核心功能

1. **一键批量处理**：
   支持将多本 EPUB 电子书放入 `repository` 文件夹中，双击运行一键完成“解压 -> 样式注入 -> 文本分析 -> 汉字对齐 -> 自动注音 -> 打包输出”的全流程。
2. **多阅读器自适应排版样式**：
   - **横排模式 (`.hltr`)**：对不支持 HTML5 原生 ruby 的旧设备或阅读器，自动通过 `inline-table` 样式将注音强行对齐在汉字**正上方**，防止注音与正文重叠或错位。
   - **竖排模式 (`.vrtl`)**：完全信任并回归原生竖排注音渲染，保证假名规整排在汉字**正右侧**，绝不会因换行块格式阻断句子纵向阅读流。
3. **精准的分词与音义对齐**：
   - 使用 MeCab (通过 `Fugashi`) 进行精准的日文形态学分词和读音识别。
   - 采用**动态规划 (DP) 智能对齐算法**配合**送假名匹配**，确保只为词汇中的“汉字”部分精准添加注音，保留原本的假名不被处理（如：输入 `戦い`，仅对 `戦` 标注 `たたか`，保留 `い`）。
4. **极致干净的打包**：
   - 处理完后自动删除生成的临时解压文件，输出的书籍保留原文件名保存在主目录下。
   - 自动清理 EPUB 原有 CSS 中的空白规则（Do not use empty rulesets），解决电子书规范校验警告。

---

## 🛠️ 环境准备

在使用本工具前，请确保您的电脑上已安装 **Python 3.x** 环境。

### 1. 安装依赖库

打开命令行（CMD/PowerShell）运行以下命令安装所需的 Python 依赖包：

```bash
pip install beautifulsoup4 lxml fugashi[unidic-lite]
```

> **注意**：`unidic-lite` 是轻量级词典包，会自动随 fugashi 安装，不需要额外配置 MeCab 环境。

---

## 🚀 使用指南

### 方式一：双击一键批量处理（推荐）

1. 将所有需要添加注音的日文 `.epub` 电子书文件放入项目主目录下的 [repository](file:///c:/Users/Administrator/Desktop/Epub_KanjiRuby/repository) 文件夹中。
2. 双击运行主目录下的 [run_batch.bat](file:///c:/Users/Administrator/Desktop/Epub_KanjiRuby/run_batch.bat) 脚本。
3. 等待命令行执行完毕（会显示每一本书的处理进度），执行结束后按任意键关闭窗口。
4. 转换完成的注音版 EPUB 电子书将以**原文件名**直接生成在项目**主目录**下。

### 方式二：命令行手动控制 (CLI)

本工具还支持通过命令行对电子书进行更灵活的单步控制。

#### 1. 解压 EPUB 书籍
```bash
python epub_helper.py extract <path_to_epub> [extract_dir]
# 例如：
# python epub_helper.py extract "book.epub" "extracted_book"
```

#### 2. 对解压目录的网页进行注音
```bash
python epub_helper.py ruby <extract_dir> [--rp] [--include-nav]
# 参数说明：
# --rp: 为老旧不支持 ruby 标签的阅读器添加 <rp>（） 括号包围的备用读音。
# --include-nav: 同时也处理目录页和封面页的文字（默认不处理）。
```

#### 3. 将解压目录打包回 EPUB
```bash
python epub_helper.py pack <extract_dir> <output_epub_path>
# 例如：
# python epub_helper.py pack "extracted_book" "output_book.epub"
```

#### 4. 命令行执行批量任务
```bash
python epub_helper.py batch [--rp] [--include-nav]
```

---

## 📂 项目结构

```text
Epub_KanjiRuby/
│
├── repository/          # [输入目录] 存放待处理的原始日文 EPUB 书籍
├── run_batch.bat        # [一键脚本] Windows 双击批量一键注音处理
│
├── epub_helper.py       # [控制核心] 负责解包、CSS样式注入、打包及批量逻辑
├── add_ruby.py          # [算法核心] 负责日文分词、音形对齐及 DOM 生成
│
├── README.md            # 项目使用说明文档
└── <输出EPUB文件>.epub    # 处理完成后生成的注音版电子书
```
