# Claude Code 自定义技能集

这里收录了一系列用于 [Claude Code](https://claude.ai/code) 的自定义技能，将文件夹放入 `~/.claude/skills/` 即可为 Claude 扩展新能力。

## 什么是 Skills？

Skills 是可以在 Claude Code 中通过 `/技能名` 调用的斜杠命令。每个技能包含一个提示词定义文件（`SKILL.md`）和可选的辅助脚本，Claude 会调用这些脚本来完成任务。

## 技能列表

### [`video-notes`](./video-notes/)

一条命令将本地视频转录并整理为结构化 Markdown 笔记。

**功能：**
- 通过 ffmpeg 提取任意视频格式的音频
- 使用 [OpenAI Whisper](https://github.com/openai/whisper) 本地离线转录语音
- 生成带时间戳的 SRT 字幕文件
- 输出包含元数据、内容摘要、关键要点和完整转录的 Markdown 笔记

**在 Claude Code 中调用：**
```
/video-notes D:/videos/my-lecture.mp4 --lang zh --title "我的课程笔记" --category "课程"
```

**依赖：** Python、ffmpeg、`openai-whisper`（首次运行自动安装）

---

## 安装方法

1. 将本仓库克隆到 Claude 技能目录：
   ```bash
   git clone https://github.com/lucius-115/skills ~/.claude/skills-repo
   ```

2. 将需要的技能文件夹复制（或软链接）到 `~/.claude/skills/`：
   ```bash
   cp -r ~/.claude/skills-repo/video-notes ~/.claude/skills/
   ```

3. 重启 Claude Code，即可通过 `/` 调用对应技能。

## 环境变量

部分技能需要通过环境变量传入凭证（代码中不存储任何明文密钥）：

| 变量名 | 使用技能 | 说明 |
|--------|---------|------|
| `BYTEDANCE_APPID` | video-notes | 字节跳动 ASR App ID（可选，备用转录引擎） |
| `BYTEDANCE_TOKEN` | video-notes | 字节跳动 ASR Access Token（可选，备用转录引擎） |

请在系统环境变量或 `.env` 文件中配置，**不要提交到版本控制**。
