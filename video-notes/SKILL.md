---
name: video-notes
description: 处理本地视频：生成 SRT 字幕 + Markdown 笔记。当用户提到本地视频、视频字幕、视频转文字、视频笔记时触发。
argument-hint: <视频路径> [输出目录] [--title 标题] [--category 分类] [--subcategory 子类] [--number 编号] [--lang zh] [--model medium]
allowed-tools: Bash Read Write
---

# video-notes — 本地视频处理

将本地视频转录为 SRT 字幕文件，并整理为结构化 Markdown 笔记。

## 依赖检查

在处理视频之前，先检查依赖是否就绪：

```bash
python ~/.claude/skills/video-notes/scripts/process.py check
```

如果提示缺少 `openai-whisper`，脚本会自动安装。  
如果缺少 `ffmpeg`，引导用户手动安装（见下方）。

### 安装 ffmpeg（如未安装）

Windows 推荐用 winget：
```bash
winget install ffmpeg
```
或从 https://ffmpeg.org/download.html 下载后添加到系统 PATH。

---

## 用法

### 一键处理（推荐）：字幕 + 笔记同时生成

```bash
python ~/.claude/skills/video-notes/scripts/process.py all \
  "<视频路径>" \
  "<输出目录>" \
  --lang zh \
  --model medium \
  --title "<笔记标题>" \
  --category "<一级分类，如 '06 SEO&相关技术'>" \
  --subcategory "<二级分类，如 '杂记'>" \
  --number "<编号，如 '99'>"
```

**输出文件：**
- `<输出目录>/<编号>-<标题>.md` — Markdown 笔记
- `<输出目录>/<视频名>.srt` — SRT 字幕
- `<输出目录>/<视频名>_transcript.json` — 原始转录数据

---

### 仅生成字幕

```bash
python ~/.claude/skills/video-notes/scripts/process.py transcribe \
  "<视频路径>" \
  --lang zh \
  --model medium
```

SRT 和 JSON 文件会保存在视频同目录下。

---

### 仅从已有转录生成笔记

```bash
python ~/.claude/skills/video-notes/scripts/process.py notes \
  "<视频名.srt>" \
  "<视频路径>" \
  "<输出.md>" \
  --title "<标题>" \
  --category "<分类>" \
  --subcategory "<子类>" \
  --number "<编号>"
```

---

## 参数说明

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--lang` | 语言代码：`zh`/`en`/`ja` 等，不填则自动检测 | 自动 |
| `--model` | Whisper 模型大小：`tiny`/`base`/`small`/`medium`/`large` | `medium` |
| `--title` | 笔记标题（不含编号） | 视频文件名 |
| `--category` | 一级分类目录名，如 `06 SEO&相关技术` | 空 |
| `--subcategory` | 二级分类目录名，如 `杂记` | 空 |
| `--number` | 笔记编号前缀，如 `99` | 空 |

**模型精度 vs 速度：**
- `tiny` / `base` — 快，适合英文，中文效果一般
- `small` / `medium` — 推荐，速度与质量平衡
- `large` — 最准，但速度慢、显存要求高

---

## 生成的 Markdown 笔记格式

```
raw/<category>/<subcategory>/<number>-<title>.md
```

结构如下：

```markdown
# <标题>

## 视频信息
| 字段 | 值 |
| ---- | -- |
| 文件 | `视频.mp4` |
| 时长 | 01:23:45 |
| 日期 | 2026-04-21 |
| 分类 | 06 SEO&相关技术 |
| 子类 | 杂记 |
| 笔记路径 | `raw/06 SEO&相关技术/杂记/99-标题` |

## 内容概述
> 由 Claude 生成摘要

## 关键要点
- 

## 时间戳笔记
- **[00:00]** 开场内容...
- **[01:00]** 第一分钟内容...

## 完整转录
​```
全文转录内容
​```
```

---

## 完整流程示例

用户说：帮我处理视频 `D:/videos/seo-course-l5.mp4`，整理成 `06 SEO&相关技术 > 杂记` 下的第 99 篇笔记，标题是 `Topical Maps SEO & Topical Authority Course L5`

执行：

```bash
python ~/.claude/skills/video-notes/scripts/process.py all \
  "D:/videos/seo-course-l5.mp4" \
  "D:/notes/raw/06 SEO&相关技术/杂记" \
  --lang en \
  --model medium \
  --title "Topical Maps SEO & Topical Authority Course L5" \
  --category "06 SEO&相关技术" \
  --subcategory "杂记" \
  --number "99"
```

完成后，用 Read 工具读取生成的 `.md` 文件，并用 Claude 为"内容概述"和"关键要点"两节补充总结。

---

## 处理步骤

1. 解析用户提供的 `$ARGUMENTS`，提取视频路径、输出目录、标题、分类等信息
2. 检查依赖（运行 `check` 命令）
3. 若缺 ffmpeg，提示用户安装并等待确认
4. 运行 `all` 命令（或按需运行 `transcribe`/`notes`）
5. 读取生成的 `.md` 文件
6. 为"内容概述"和"关键要点"两节生成总结内容并写回文件
7. 报告所有输出文件路径

$ARGUMENTS
