# 路修的Skills

这里记录了一些我自己写的并在用的skills。

## Skills列表

### [`video-notes`](./video-notes/)

一条命令将本地视频转录并整理为结构化 Markdown 笔记。

这个skills主要是为了配合我现在正在实践的Karpathy的基于obsidian的LLM笔记体系，我看的很多课程是本地视频特别是还有一些国外的课程，这个skills可以把视频字幕提取出来到文档里让后存入我的笔记给AI消化，并记录到我的知识库。

在音频处理上最开始用的是Whisper这个项目，但是实际用起来发现处理的太慢了，2个多小时的视频处理了快3个小时还没结束，后面用了字节的ASR API快了很多，而且也不是很贵，可以在火山方舟上去购买并配置，初次使用还会送20个小时。

**功能：**
- 通过 ffmpeg 提取任意视频格式的音频
- 使用字节跳动 ASR API（openspeech.bytedance.com）云端转录语音
- 生成带时间戳的 SRT 字幕文件
- 输出包含元数据、内容摘要、关键要点和完整转录的 Markdown 笔记

**在 Claude Code 中调用：**
```
/video-notes D:/videos/my-lecture.mp4 --lang zh --title "我的课程笔记" --category "课程"
```

**依赖：** Python、ffmpeg、`requests`（首次运行自动安装）

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

## 配置

`video-notes` 技能使用字节跳动 ASR API 进行转录，相关凭证配置在 `video-notes/scripts/process.py` 中：

| 变量名 | 说明 |
|--------|------|
| `BYTEDANCE_APPID` | 字节跳动 ASR App ID |
| `BYTEDANCE_TOKEN` | 字节跳动 ASR Access Token |
